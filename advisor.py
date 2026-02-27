"""
advisor.py — Análisis financiero y generación de mensajes personalizados
Consulta gastos vs presupuesto y cargos extraordinarios próximos
Genera prompts contextualizados para LLM (Qwen / Claude fallback)
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os
import sys
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "finsense.db")

# ===== FUNCIONES AUXILIARES =====

def get_current_month_year() -> Tuple[int, int]:
    """Retorna año y mes actual"""
    today = datetime.now()
    return today.year, today.month

def get_mes_nombre(mes: int) -> str:
    """Convierte número de mes a nombre en español"""
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    return meses[mes - 1] if 1 <= mes <= 12 else "?"

def get_dias_para_fin_mes() -> int:
    """Retorna días restantes para fin de mes"""
    hoy = datetime.now()
    primer_dia_proximo_mes = (hoy.replace(day=1) + timedelta(days=32)).replace(day=1)
    ultimo_dia_mes = primer_dia_proximo_mes - timedelta(days=1)
    dias_restantes = (ultimo_dia_mes - hoy).days
    return max(0, dias_restantes)

# ===== CONSULTAS A LA BD =====

def get_gastos_mes_actual() -> Dict[str, Dict]:
    """
    Obtiene gastos del mes actual por categoría
    Retorna: {
        'cat1|cat2': {
            'cat1': str,
            'cat2': str,
            'gasto': float,
            'num_tx': int
        }
    }
    """
    try:
        year, month = get_current_month_year()
        periodo = f"{year}-{month:02d}"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT cat1, cat2, SUM(importe) as total, COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO'
              AND strftime('%Y-%m', fecha) = '{periodo}'
              AND cat1 != 'Bizum'
            GROUP BY cat1, cat2
            ORDER BY cat1, cat2
        """)
        
        gastos = {}
        for row in cursor.fetchall():
            cat1, cat2, total, num_tx = row
            key = f"{cat1}|{cat2}"
            gastos[key] = {
                'cat1': cat1,
                'cat2': cat2,
                'gasto': abs(total),
                'num_tx': num_tx
            }
        
        conn.close()
        return gastos
    
    except Exception as e:
        print(f"❌ Error obteniendo gastos: {e}", file=sys.stderr)
        return {}

def get_presupuestos() -> Dict[str, Dict]:
    """
    Obtiene presupuestos activos
    Retorna: {
        'cat1|cat2': {
            'cat1': str,
            'cat2': str,
            'presupuesto': float
        }
    }
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cat1, cat2, importe_mensual
            FROM presupuestos
            WHERE activo = 1
            ORDER BY cat1, cat2
        """)
        
        presupuestos = {}
        for row in cursor.fetchall():
            cat1, cat2, importe = row
            key = f"{cat1}|{cat2}"
            presupuestos[key] = {
                'cat1': cat1,
                'cat2': cat2,
                'presupuesto': importe
            }
        
        conn.close()
        return presupuestos
    
    except Exception as e:
        print(f"❌ Error obteniendo presupuestos: {e}", file=sys.stderr)
        return {}

def get_cargos_extraordinarios_proximos(dias_aviso: int = 10) -> List[Dict]:
    """
    Obtiene cargos extraordinarios próximos en los próximos N días
    
    Retorna: [
        {
            'mes': int,
            'dia': int | None,
            'descripcion': str,
            'importe': float,
            'dias_para_aviso': int
        }
    ]
    """
    try:
        year, month = get_current_month_year()
        hoy = datetime.now()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT mes, dia, descripcion, importe_estimado, dias_aviso
            FROM cargos_extraordinarios
            WHERE activo = 1
            ORDER BY mes, dia
        """)
        
        cargos_proximos = []
        
        for row in cursor.fetchall():
            mes_cargo, dia_cargo, descripcion, importe, dias_aviso_config = row
            
            # Construir fecha estimada del cargo
            if dia_cargo:
                # Cargo en día específico
                año_cargo = year if mes_cargo >= month else year + 1
                fecha_cargo = datetime(año_cargo, mes_cargo, dia_cargo)
            else:
                # Cargo a principios de mes (asumir día 5)
                año_cargo = year if mes_cargo >= month else year + 1
                fecha_cargo = datetime(año_cargo, mes_cargo, 5)
            
            # Calcular días hasta el aviso
            fecha_aviso = fecha_cargo - timedelta(days=dias_aviso_config)
            dias_para_aviso = (fecha_aviso - hoy).days
            
            # Si estamos dentro de la ventana de aviso (dias_para_aviso <= 0 y cargo aún no pasó)
            if dias_para_aviso <= 0 <= (fecha_cargo - hoy).days:
                cargos_proximos.append({
                    'mes': mes_cargo,
                    'dia': dia_cargo or 5,
                    'descripcion': descripcion,
                    'importe': importe,
                    'dias_para_aviso': (fecha_cargo - hoy).days,
                    'fecha_cargo': fecha_cargo.strftime("%d/%m/%Y")
                })
        
        conn.close()
        return sorted(cargos_proximos, key=lambda x: x['dias_para_aviso'])
    
    except Exception as e:
        print(f"❌ Error obteniendo cargos extraordinarios: {e}", file=sys.stderr)
        return []

# ===== ANÁLISIS Y CONSTRUCCIÓN DE CONTEXTO =====

def analizar_presupuestos() -> Dict:
    """
    Análisis completo de presupuestos vs gastos
    Retorna estadísticas para el prompt del LLM
    """
    gastos = get_gastos_mes_actual()
    presupuestos = get_presupuestos()
    
    stats = {
        'mes_nombre': get_mes_nombre(get_current_month_year()[1]),
        'categorias_info': [],
        'total_presupuesto': sum(p['presupuesto'] for p in presupuestos.values()),
        'total_gasto': sum(g['gasto'] for g in gastos.values()),
        'dias_restantes': get_dias_para_fin_mes(),
        'categorias_en_rojo': [],
        'categorias_en_naranja': [],
        'categorias_dentro_plan': []
    }
    
    # Analizar cada categoría
    for key, presupuesto_info in presupuestos.items():
        gasto_info = gastos.get(key, {'gasto': 0, 'num_tx': 0})
        gasto = gasto_info['gasto']
        presupuesto = presupuesto_info['presupuesto']
        pct = (gasto / presupuesto * 100) if presupuesto > 0 else 0
        
        cat_data = {
            'cat1': presupuesto_info['cat1'],
            'cat2': presupuesto_info['cat2'],
            'presupuesto': presupuesto,
            'gasto': gasto,
            'pct': pct,
            'num_tx': gasto_info['num_tx'],
            'restante': max(0, presupuesto - gasto)
        }
        
        stats['categorias_info'].append(cat_data)
        
        # Clasificar según estado
        if pct >= 100:
            stats['categorias_en_rojo'].append(cat_data)
        elif pct >= 80:
            stats['categorias_en_naranja'].append(cat_data)
        else:
            stats['categorias_dentro_plan'].append(cat_data)
    
    # Diferencia total
    stats['diferencia_total'] = stats['total_presupuesto'] - stats['total_gasto']
    stats['pct_total'] = (stats['total_gasto'] / stats['total_presupuesto'] * 100) if stats['total_presupuesto'] > 0 else 0
    
    return stats

def construir_prompt_para_llm() -> str:
    """
    Construye un prompt rico en contexto para el LLM
    Incluye análisis de presupuestos y cargos extraordinarios próximos
    """
    stats = analizar_presupuestos()
    cargos = get_cargos_extraordinarios_proximos()
    
    prompt = f"""# Análisis Financiero — {stats['mes_nombre'].capitalize()}

## Presupuestos vs Gastos Actuales

**Resumen General:**
- Presupuesto total: €{stats['total_presupuesto']:.2f}
- Gastos reales: €{stats['total_gasto']:.2f}
- Diferencia: €{stats['diferencia_total']:.2f}
- Progreso: {stats['pct_total']:.1f}%
- Días restantes del mes: {stats['dias_restantes']}

**Categorías en plan (✅ < 80%):**
"""
    
    for cat in stats['categorias_dentro_plan']:
        prompt += f"  - {cat['cat1']} → {cat['cat2']}: €{cat['gasto']:.2f} / €{cat['presupuesto']:.2f} ({cat['pct']:.1f}%)\n"
    
    if stats['categorias_en_naranja']:
        prompt += "\n**Categorías en naranja (⚠️ 80-100%):**\n"
        for cat in stats['categorias_en_naranja']:
            prompt += f"  - {cat['cat1']} → {cat['cat2']}: €{cat['gasto']:.2f} / €{cat['presupuesto']:.2f} ({cat['pct']:.1f}%)\n"
    
    if stats['categorias_en_rojo']:
        prompt += "\n**Categorías en rojo (🔴 > 100%):**\n"
        for cat in stats['categorias_en_rojo']:
            prompt += f"  - {cat['cat1']} → {cat['cat2']}: €{cat['gasto']:.2f} / €{cat['presupuesto']:.2f} ({cat['pct']:.1f}%)\n"
    
    # Cargos extraordinarios
    if cargos:
        prompt += "\n## Cargos Extraordinarios Próximos\n"
        for cargo in cargos:
            prompt += f"  - {cargo['descripcion']}: €{cargo['importe']:.2f} ({cargo['fecha_cargo']}, en {cargo['dias_para_aviso']} días)\n"
    
    # Instrucciones para el LLM
    prompt += """
## Instrucciones para tu respuesta

Eres un asesor financiero cercano, informal y motivador. Tu mensaje debe:

1. **Tono**: Conversacional, sin ser corporativo. Ocasionalmente incluye un comentario humorístico (máximo 1 chiste por semana).
2. **Estructura**: 2-4 párrafos máximo. Sé breve pero significativo.
3. **Contenido**:
   - Analiza el progreso general del mes (¿vamos bien o mal?)
   - Si hay categorías en rojo/naranja, comenta cómo mitigarlas
   - Si hay cargos extraordinarios próximos, recuérdaselos con tono amigable
4. **Motivación**: Si vamos bien, anima a seguir. Si vamos mal, sugiere pequeños ajustes realistas.

Responde directamente como si fueras el asesor (sin formato especial, sin asteriscos de formato, sin cabeceras). 
"""
    
    return prompt


# ===== FONDO DE CAPRICHOS =====

CATS_CONTROLABLES = [
    'Alimentación', 'Restauración', 'Compras',
    'Ropa y Calzado', 'Salud y Belleza', 'Ocio y Cultura'
]
ANIO_INICIO_FONDO = 2026
MES_INICIO_FONDO = 2  # Febrero 2026


def get_presupuestos_controlables() -> Dict[str, float]:
    """Lee presupuestos de las categorías controlables desde BD."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cat1, importe_mensual FROM presupuestos
            WHERE activo = 1 AND cat1 IN ({})
        """.format(','.join('?' * len(CATS_CONTROLABLES))), CATS_CONTROLABLES)
        result = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return result
    except Exception as e:
        print(f"❌ Error leyendo presupuestos: {e}", file=sys.stderr)
        return {}


def calcular_fondo_mes(anio: int, mes: int) -> List[Dict]:
    """
    Calcula el fondo de caprichos para un mes cerrado.
    Compara gasto_real vs presupuesto por categoría controlable.
    Guarda/actualiza en tabla fondo_caprichos.
    Retorna lista de dicts con detalle por categoría.
    """
    try:
        periodo = f"{anio}-{mes:02d}"
        presupuestos = get_presupuestos_controlables()
        if not presupuestos:
            return []

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        resultado = []
        for cat1 in CATS_CONTROLABLES:
            presupuesto = presupuestos.get(cat1, 0.0)
            cursor.execute("""
                SELECT COALESCE(SUM(ABS(importe)), 0)
                FROM transacciones
                WHERE tipo = 'GASTO'
                  AND cat1 = ?
                  AND strftime('%Y-%m', fecha) = ?
            """, (cat1, periodo))
            gasto_real = cursor.fetchone()[0]
            diferencia = presupuesto - gasto_real  # positivo = ahorro, negativo = exceso

            # Guardar/actualizar en BD
            cursor.execute("""
                INSERT INTO fondo_caprichos (anio, mes, cat1, presupuesto, gasto_real, diferencia, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(anio, mes, cat1) DO UPDATE SET
                    presupuesto = excluded.presupuesto,
                    gasto_real = excluded.gasto_real,
                    diferencia = excluded.diferencia,
                    updated_at = excluded.updated_at
            """, (anio, mes, cat1, presupuesto, gasto_real, diferencia))

            resultado.append({
                'cat1': cat1,
                'presupuesto': presupuesto,
                'gasto_real': gasto_real,
                'diferencia': diferencia
            })

        conn.commit()
        conn.close()
        return resultado

    except Exception as e:
        print(f"❌ Error calculando fondo mes {anio}-{mes:02d}: {e}", file=sys.stderr)
        return []


def get_fondo_acumulado_anio(anio: int) -> Dict:
    """
    Retorna el fondo acumulado del año desde MES_INICIO_FONDO.
    Solo incluye meses cerrados (no el mes actual en curso).
    Retorna dict con: acumulado total, detalle por mes, detalle por categoría.
    """
    try:
        hoy = datetime.now()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Solo meses cerrados desde el inicio del fondo
        cursor.execute("""
            SELECT mes, cat1, presupuesto, gasto_real, diferencia
            FROM fondo_caprichos
            WHERE anio = ?
              AND mes >= ?
              AND (anio < ? OR mes < ?)
            ORDER BY mes, cat1
        """, (anio, MES_INICIO_FONDO, hoy.year, hoy.month))

        rows = cursor.fetchall()
        conn.close()

        acumulado = 0.0
        por_mes = {}
        por_cat = {}

        for mes, cat1, presupuesto, gasto_real, diferencia in rows:
            acumulado += diferencia
            if mes not in por_mes:
                por_mes[mes] = 0.0
            por_mes[mes] += diferencia
            if cat1 not in por_cat:
                por_cat[cat1] = 0.0
            por_cat[cat1] += diferencia

        return {
            'acumulado': acumulado,
            'por_mes': por_mes,
            'por_cat': por_cat,
            'meses_incluidos': sorted(por_mes.keys())
        }

    except Exception as e:
        print(f"❌ Error leyendo fondo acumulado: {e}", file=sys.stderr)
        return {'acumulado': 0.0, 'por_mes': {}, 'por_cat': {}, 'meses_incluidos': []}


def get_bloque_seguimiento_mes() -> str:
    """
    Genera el bloque de texto fijo con seguimiento del mes actual
    y fondo de caprichos acumulado. Se añade al pie de cada mensaje diario.
    """
    try:
        hoy = datetime.now()
        anio, mes = hoy.year, hoy.month
        periodo = f"{anio}-{mes:02d}"
        dias_mes = (hoy.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        dias_mes = dias_mes.day
        dia_hoy = hoy.day

        presupuestos = get_presupuestos_controlables()
        if not presupuestos:
            return ""

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Mes anterior para comparativa
        if mes == 1:
            mes_ant, anio_ant = 12, anio - 1
        else:
            mes_ant, anio_ant = mes - 1, anio
        periodo_ant = f"{anio_ant}-{mes_ant:02d}"

        lineas = []
        total_presup = 0.0
        total_actual = 0.0
        total_anterior = 0.0

        for cat1 in CATS_CONTROLABLES:
            presup = presupuestos.get(cat1, 0.0)

            cursor.execute("""
                SELECT COALESCE(SUM(ABS(importe)), 0) FROM transacciones
                WHERE tipo='GASTO' AND cat1=? AND strftime('%Y-%m', fecha)=?
            """, (cat1, periodo))
            actual = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COALESCE(SUM(ABS(importe)), 0) FROM transacciones
                WHERE tipo='GASTO' AND cat1=? AND strftime('%Y-%m', fecha)=?
            """, (cat1, periodo_ant))
            anterior = cursor.fetchone()[0]

            total_presup += presup
            total_actual += actual
            total_anterior += anterior

            diferencia = presup - actual
            if diferencia >= 0:
                icono = "✅"
            elif diferencia > -30:
                icono = "⚠️"
            else:
                icono = "❌"

            # Variación vs mes anterior
            if anterior > 0:
                pct = ((actual - anterior) / anterior) * 100
                var = f"{pct:+.0f}%"
            else:
                var = "—"

            nombre_corto = cat1.replace(' y ', '/').replace('Restauración', 'Restaurac.')
            lineas.append(
                f"{icono} {nombre_corto:<16} {actual:>6.0f}€ / {presup:.0f}€  vs ant: {var}"
            )

        conn.close()

        # Fondo acumulado (meses cerrados)
        fondo = get_fondo_acumulado_anio(anio)
        acumulado = fondo['acumulado']
        meses_n = len(fondo['meses_incluidos'])

        if acumulado >= 0:
            fondo_txt = f"+{acumulado:.0f}€ disponibles"
        else:
            fondo_txt = f"{acumulado:.0f}€ (en negativo)"

        mes_nombre = get_mes_nombre(mes).capitalize()
        bloque = (
            f"\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 {mes_nombre} — día {dia_hoy}/{dias_mes}\n"
            f"\n"
            + "\n".join(lineas) +
            f"\n"
            f"{'─' * 25}\n"
            f"Total:            {total_actual:>6.0f}€ / {total_presup:.0f}€\n"
            f"\n"
            f"💰 Fondo caprichos {anio}: {fondo_txt}"
            + (f" ({meses_n} mes{'es' if meses_n != 1 else ''} cerrado{'s' if meses_n != 1 else ''})" if meses_n > 0 else " (desde este mes)")
        )
        return bloque

    except Exception as e:
        print(f"❌ Error generando bloque seguimiento: {e}", file=sys.stderr)
        return ""


def get_bloque_fondo_mensual(anio: int, mes_cerrado: int) -> str:
    """
    Genera el bloque detallado del fondo de caprichos para el cierre mensual.
    Muestra desglose por categoría del mes cerrado y acumulado del año.
    """
    try:
        detalle = calcular_fondo_mes(anio, mes_cerrado)
        fondo = get_fondo_acumulado_anio(anio)
        mes_nombre = get_mes_nombre(mes_cerrado).capitalize()

        lineas = [f"\n💰 Fondo caprichos — cierre {mes_nombre}\n"]
        total_mes = 0.0
        for item in detalle:
            dif = item['diferencia']
            total_mes += dif
            icono = "✅" if dif >= 0 else "❌"
            lineas.append(
                f"{icono} {item['cat1']:<18} {dif:>+.0f}€  "
                f"(gastado {item['gasto_real']:.0f}€ / presup {item['presupuesto']:.0f}€)"
            )

        acumulado = fondo['acumulado']
        lineas.append(f"{'─' * 30}")
        lineas.append(f"Este mes:   {total_mes:>+.0f}€")
        lineas.append(f"Acumulado {anio}: {acumulado:>+.0f}€")

        if acumulado > 0:
            lineas.append(f"\n¡Tienes {acumulado:.0f}€ de margen para un capricho!")
        elif acumulado < 0:
            lineas.append(f"\nAún {abs(acumulado):.0f}€ por recuperar antes del capricho.")

        return "\n".join(lineas)

    except Exception as e:
        print(f"❌ Error generando bloque fondo mensual: {e}", file=sys.stderr)
        return ""


def obtener_mensaje_para_bot() -> str:
    """
    Genera un mensaje listo para enviar al usuario por Telegram
    Este es el flujo principal que usa bot_telegram.py
    """
    prompt = construir_prompt_para_llm()
    
    # Aquí se llamaría al LLM (Qwen / Claude)
    # Por ahora, retornamos un placeholder que se llenará en bot_telegram.py
    
    return prompt

def obtener_contexto_json() -> Dict:
    """
    Retorna análisis como JSON para consumo programático
    """
    stats = analizar_presupuestos()
    cargos = get_cargos_extraordinarios_proximos()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'mes': get_current_month_year()[1],
        'año': get_current_month_year()[0],
        'presupuesto_total': stats['total_presupuesto'],
        'gasto_total': stats['total_gasto'],
        'diferencia': stats['diferencia_total'],
        'pct_utilizado': stats['pct_total'],
        'dias_restantes': stats['dias_restantes'],
        'categorias': stats['categorias_info'],
        'cargos_extraordinarios': cargos
    }

# ===== CONSULTAS GEOGRÁFICAS =====

def get_gastos_por_ubicacion(country: str = None, city: str = None, 
                             fecha_inicio: str = None, fecha_fin: str = None) -> Dict:
    """
    Obtiene gastos filtrados por ubicación geográfica del merchant.
    
    Args:
        country: código de país (ej: 'Spain', 'Colombia', 'USA')
        city: nombre de ciudad (ej: 'Cartagena', 'Murcia', 'Bogotá')
        fecha_inicio: fecha inicio en formato 'YYYY-MM-DD' (opcional)
        fecha_fin: fecha fin en formato 'YYYY-MM-DD' (opcional)
    
    Returns:
        {
            'total_gasto': float,
            'num_transacciones': int,
            'por_categoria': { 'cat1|cat2': {'cat1': str, 'cat2': str, 'gasto': float, 'num_tx': int} },
            'merchants': [ {'merchant_name': str, 'address': str, 'gasto': float, 'num_tx': int} ]
        }
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Construir WHERE
        where_clauses = ["t.tipo = 'GASTO'", "m.merchant_name IS NOT NULL"]
        params = []
        
        if country:
            where_clauses.append("m.country = ?")
            params.append(country)
        
        if city:
            where_clauses.append("m.city = ?")
            params.append(city)
        
        if fecha_inicio:
            where_clauses.append("t.fecha >= ?")
            params.append(fecha_inicio)
        
        if fecha_fin:
            where_clauses.append("t.fecha <= ?")
            params.append(fecha_fin)
        
        where_sql = " AND ".join(where_clauses)
        
        # Total por categoría
        query_cat = f"""
            SELECT t.cat1, t.cat2, SUM(t.importe) as total, COUNT(*) as num_tx
            FROM transacciones t
            LEFT JOIN merchants m ON t.merchant_name = m.merchant_name
            WHERE {where_sql}
            GROUP BY t.cat1, t.cat2
            ORDER BY total DESC
        """
        cursor.execute(query_cat, params)
        
        por_categoria = {}
        total_gasto = 0
        total_tx = 0
        
        for row in cursor.fetchall():
            cat1, cat2, total, num_tx = row
            key = f"{cat1}|{cat2}"
            por_categoria[key] = {
                'cat1': cat1,
                'cat2': cat2,
                'gasto': abs(total),
                'num_tx': num_tx
            }
            total_gasto += abs(total)
            total_tx += num_tx
        
        # Detalle por merchant
        query_merchants = f"""
            SELECT t.merchant_name, m.address, m.city, m.country, 
                   SUM(t.importe) as total, COUNT(*) as num_tx
            FROM transacciones t
            LEFT JOIN merchants m ON t.merchant_name = m.merchant_name
            WHERE {where_sql}
            GROUP BY t.merchant_name
            ORDER BY total DESC
            LIMIT 20
        """
        cursor.execute(query_merchants, params)
        
        merchants = []
        for row in cursor.fetchall():
            merchant_name, address, city, country_m, total, num_tx = row
            merchants.append({
                'merchant_name': merchant_name,
                'address': address,
                'city': city,
                'country': country_m,
                'gasto': abs(total),
                'num_tx': num_tx
            })
        
        conn.close()
        
        return {
            'total_gasto': total_gasto,
            'num_transacciones': total_tx,
            'filtros': {
                'country': country,
                'city': city,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'por_categoria': por_categoria,
            'merchants': merchants
        }
    
    except Exception as e:
        print(f"❌ Error obteniendo gastos por ubicación: {e}", file=sys.stderr)
        return {}


def get_gastos_viaje(viaje_nombre: str = None, fecha_inicio: str = None, 
                     fecha_fin: str = None) -> Dict:
    """
    Obtiene gastos de un viaje (por fechas y/o nombre).
    
    Args:
        viaje_nombre: nombre descriptivo (ej: 'Colombia', 'Galicia')
        fecha_inicio: fecha inicio en 'YYYY-MM-DD'
        fecha_fin: fecha fin en 'YYYY-MM-DD'
    
    Returns:
        Dict con resumen del viaje
    """
    # Alias de ubicación comunes
    ubicaciones_comunes = {
        'colombia': {'country': 'Colombia'},
        'eeuu': {'country': 'United States'},
        'usa': {'country': 'United States'},
        'galicia': {'city': 'Galicia'},  # Nota: Galicia es región, no ciudad en Google Places
        'madrid': {'city': 'Madrid'},
        'barcelona': {'city': 'Barcelona'},
        'berlin': {'city': 'Berlin'},
        'francia': {'country': 'France'},
        'italia': {'country': 'Italy'},
    }
    
    filtros = ubicaciones_comunes.get(viaje_nombre.lower()) if viaje_nombre else {}
    
    return get_gastos_por_ubicacion(
        country=filtros.get('country'),
        city=filtros.get('city'),
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )


def get_resumen_geografico(fecha_inicio: str = None, fecha_fin: str = None) -> Dict:
    """
    Obtiene resumen geográfico completo: todos los países con gastos, transacciones, ciudades, etc.
    Usada por el dashboard geográfico para rendimiento (1 query en lugar de N).
    
    Args:
        fecha_inicio: fecha inicio en formato 'YYYY-MM-DD' (opcional)
        fecha_fin: fecha fin en formato 'YYYY-MM-DD' (opcional)
    
    Returns:
        {
            'total_gasto': float,
            'num_transacciones': int,
            'paises': [
                {
                    'country': str,
                    'gasto': float,
                    'num_tx': int,
                    'num_merchants': int,
                    'ciudades': int,
                    'ciudades_lista': [str],
                    'lat': float,  # promedio de merchants en el país
                    'lng': float
                }
            ]
        }
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Construir WHERE
        where_clauses = ["t.tipo = 'GASTO'", "m.merchant_name IS NOT NULL", "m.country IS NOT NULL"]
        params = []
        
        if fecha_inicio:
            where_clauses.append("t.fecha >= ?")
            params.append(fecha_inicio)
        
        if fecha_fin:
            where_clauses.append("t.fecha <= ?")
            params.append(fecha_fin)
        
        where_sql = " AND ".join(where_clauses)
        
        # Query agregada por país
        query_paises = f"""
            SELECT 
                m.country,
                SUM(t.importe) as total,
                COUNT(*) as num_tx,
                COUNT(DISTINCT t.merchant_name) as num_merchants,
                COUNT(DISTINCT m.city) as num_ciudades,
                GROUP_CONCAT(m.city, '|') as ciudades_concat,
                AVG(m.lat) as lat_promedio,
                AVG(m.lng) as lng_promedio
            FROM transacciones t
            LEFT JOIN merchants m ON t.merchant_name = m.merchant_name
            WHERE {where_sql}
            GROUP BY m.country
            ORDER BY total DESC
        """
        cursor.execute(query_paises, params)
        
        paises = []
        total_gasto = 0
        total_tx = 0
        
        for row in cursor.fetchall():
            country, total, num_tx, num_merchants, num_ciudades, ciudades_concat, lat, lng = row
            
            # Procesar lista de ciudades
            ciudades_lista = [c.strip() for c in ciudades_concat.split('|') if c.strip()] if ciudades_concat else []
            
            paises.append({
                'country': country,
                'gasto': abs(total),
                'num_tx': num_tx,
                'num_merchants': num_merchants,
                'num_ciudades': num_ciudades or 0,
                'ciudades_lista': ciudades_lista,
                'lat': lat if lat else 0.0,
                'lng': lng if lng else 0.0
            })
            
            total_gasto += abs(total)
            total_tx += num_tx
        
        conn.close()
        
        return {
            'total_gasto': total_gasto,
            'num_transacciones': total_tx,
            'filtros': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'paises': paises
        }
    
    except Exception as e:
        print(f"❌ Error obteniendo resumen geográfico: {e}", file=sys.stderr)
        return {'total_gasto': 0, 'num_transacciones': 0, 'filtros': {}, 'paises': []}


def get_merchants_para_mapa(fecha_inicio: str = None, fecha_fin: str = None) -> List[Dict]:
    """
    Obtiene lista de merchants con coords para mapa interactivo con zoom.
    Cada punto representa un merchant con su gasto total agregado.
    
    Args:
        fecha_inicio: fecha inicio en formato 'YYYY-MM-DD' (opcional)
        fecha_fin: fecha fin en formato 'YYYY-MM-DD' (opcional)
    
    Returns:
        [
            {
                'name': nombre del merchant,
                'lat': latitud,
                'lng': longitud,
                'city': ciudad,
                'country': país,
                'address': dirección,
                'gasto': gasto total,
                'num_tx': nº transacciones,
                'cat1': categoría principal,
                'cat2': subcategoría
            }
        ]
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Construir WHERE
        # Lista de merchants virtuales/online que NO deben aparecer en mapa
        merchants_virtuales = [
            'RAKUTEN', 'PAYPAL', 'GOOGLE', 'NETFLIX', 'SPOTIFY', 'XBOX',
            'KINDLE', 'APPLE', 'AMAZON', 'STEAM', 'ADOBE', 'FIGMA',
            'GITHUB', 'NOTION', 'TWITCH', 'INSTAGRAM', 'FACEBOOK',
            'WHATSAPP', 'TELEGRAM', 'SLACK', 'ZOOM', 'DROPBOX',
            'FLICKR', 'YOUTUBE', 'GMAIL', 'OUTLOOK', 'DISCORD'
        ]
        
        where_clauses = [
            "t.tipo = 'GASTO'",
            "m.merchant_name IS NOT NULL",
            "m.lat IS NOT NULL",
            "m.lng IS NOT NULL",
            "m.lat != 0",
            "m.lng != 0"
        ]
        params = []
        
        # Excluir categorías que son claramente virtuales
        where_clauses.append("t.cat1 NOT IN ('Suscripciones', 'Transferencia')")
        
        # Excluir merchants conocidos como virtuales
        placeholders = ', '.join(['?' for _ in merchants_virtuales])
        where_clauses.append(f"UPPER(m.merchant_name) NOT IN ({placeholders})")
        params.extend(merchants_virtuales)
        
        if fecha_inicio:
            where_clauses.append("t.fecha >= ?")
            params.append(fecha_inicio)
        
        if fecha_fin:
            where_clauses.append("t.fecha <= ?")
            params.append(fecha_fin)
        
        where_sql = " AND ".join(where_clauses)
        
        # Query: merchants con coords y gasto agregado
        query = f"""
            SELECT 
                m.merchant_name,
                m.lat,
                m.lng,
                m.city,
                m.country,
                m.address,
                SUM(ABS(t.importe)) as gasto_total,
                COUNT(*) as num_tx,
                t.cat1,
                t.cat2
            FROM transacciones t
            LEFT JOIN merchants m ON t.merchant_name = m.merchant_name
            WHERE {where_sql}
            GROUP BY m.merchant_name, t.cat1, t.cat2
            ORDER BY gasto_total DESC
        """
        
        cursor.execute(query, params)
        
        merchants = []
        for row in cursor.fetchall():
            merchant_name, lat, lng, city, country, address, gasto, num_tx, cat1, cat2 = row
            
            merchants.append({
                'name': merchant_name or '(sin nombre)',
                'lat': lat,
                'lng': lng,
                'city': city or '(sin ciudad)',
                'country': country or '(sin país)',
                'address': address or '(sin dirección)',
                'gasto': abs(gasto),
                'num_tx': num_tx,
                'cat1': cat1 or '(sin categoría)',
                'cat2': cat2 or '(sin subcategoría)'
            })
        
        conn.close()
        return merchants
        
    except Exception as e:
        print(f"❌ Error obteniendo merchants para mapa: {e}", file=sys.stderr)
        return []


# ===== MAIN (para testing) =====

if __name__ == "__main__":
    print("=== Análisis Financiero ===\n")
    
    # Obtener contexto
    contexto = obtener_contexto_json()
    
    print(f"Mes: {get_mes_nombre(contexto['mes']).capitalize()}")
    print(f"Presupuesto: €{contexto['presupuesto_total']:.2f}")
    print(f"Gasto: €{contexto['gasto_total']:.2f}")
    print(f"Utilizado: {contexto['pct_utilizado']:.1f}%")
    print(f"Días restantes: {contexto['dias_restantes']}")
    
    print("\n=== Prompt para LLM ===\n")
    prompt = construir_prompt_para_llm()
    print(prompt)
    
    print("\n=== Cargos Extraordinarios Próximos ===\n")
    cargos = get_cargos_extraordinarios_proximos()
    if cargos:
        for cargo in cargos:
            print(f"- {cargo['descripcion']}: €{cargo['importe']:.2f} ({cargo['fecha_cargo']})")
    else:
        print("Sin cargos próximos")


# ===== SISTEMA 3-LEVEL DE MENSAJES (BLOQUE 3) =====

# Pool de tonos rotativos para mensajes diarios
TONOS_DISPONIBLES = [
    "amigo_whatsapp",      # Directo, sin florituras
    "coach_energico",      # Motivador, con sugerencias
    "analista_seco",       # Bloomberg terminal, solo hechos
    "narrador_curioso",    # Cuenta datos como historias
    "bromista_financiero"  # Incluye chiste sobre dinero
]

# Pool de ángulos para push diario (aleatorio cada día)
ANGULOS_DIARIOS = [
    "gastos_ayer",         # Desglose de ayer
    "ritmo_mes",          # Extrapolación del mes
    "presupuesto_peligro", # Categoría en riesgo
    "comparativa_semana",  # Esta semana vs semana anterior
    "merchant_sorpresa",   # Merchant más caro/frecuente
    "ahorro_diario",       # Ahorro de ayer vs media
    "cargo_alerta",        # Cargas extraordinarias próximas
    "libre_llm"           # El LLM elige qué contar
]

# Pool de ángulos para push mensual (rotación por mes)
ANGULOS_MENSUALES = [
    "cierre_vs_anterior",  # Comparativa vs mes anterior
    "cierre_fire",         # Proyección FIRE
    "cierre_patrones"      # Patrones y revelaciones
]


def get_gastos_ayer() -> Dict:
    """Obtiene gastos del día anterior con desglose por categoría"""
    try:
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT cat1, cat2, SUM(importe) as total, COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO' AND fecha = '{ayer}'
            GROUP BY cat1, cat2
            ORDER BY total DESC
        """)
        
        gastos = []
        total = 0
        for row in cursor.fetchall():
            cat1, cat2, monto, num_tx = row
            monto = abs(monto)
            gastos.append({
                'cat1': cat1,
                'cat2': cat2,
                'monto': monto,
                'num_tx': num_tx
            })
            total += monto
        
        conn.close()
        return {
            'fecha': ayer,
            'total': total,
            'gastos': gastos,
            'num_transacciones': sum(g['num_tx'] for g in gastos)
        }
    
    except Exception as e:
        print(f"❌ Error obteniendo gastos de ayer: {e}", file=sys.stderr)
        return {'fecha': None, 'total': 0, 'gastos': [], 'num_transacciones': 0}


def get_ritmo_mes() -> Dict:
    """Extrapola el ritmo de gasto del mes en curso"""
    try:
        stats = analizar_presupuestos()
        dias_transcurridos = 28 - stats['dias_restantes']
        
        if dias_transcurridos == 0:
            return {'dias_transcurridos': 0, 'extrapolacion': None}
        
        gasto_diario_promedio = stats['total_gasto'] / dias_transcurridos if dias_transcurridos > 0 else 0
        extrapolacion_mes = gasto_diario_promedio * 28  # Asumir mes de 28 días
        presupuesto_total = stats['total_presupuesto']
        
        estado = "bien" if extrapolacion_mes <= presupuesto_total else "mal"
        diferencia = abs(extrapolacion_mes - presupuesto_total)
        
        return {
            'dias_transcurridos': dias_transcurridos,
            'gasto_actual': stats['total_gasto'],
            'gasto_diario_promedio': gasto_diario_promedio,
            'extrapolacion_mes': extrapolacion_mes,
            'presupuesto_total': presupuesto_total,
            'estado': estado,
            'diferencia': diferencia
        }
    
    except Exception as e:
        print(f"❌ Error calculando ritmo del mes: {e}", file=sys.stderr)
        return {}


def get_merchant_top_mes() -> Dict:
    """Obtiene el merchant más caro/frecuente del mes en curso"""
    try:
        year, month = get_current_month_year()
        periodo = f"{year}-{month:02d}"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Por gasto total
        cursor.execute(f"""
            SELECT merchant_name, SUM(importe) as total, COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO' AND strftime('%Y-%m', fecha) = '{periodo}'
              AND merchant_name IS NOT NULL
            GROUP BY merchant_name
            ORDER BY total DESC
            LIMIT 1
        """)
        
        row_caro = cursor.fetchone()
        merchant_caro = None
        if row_caro:
            merchant_caro = {
                'name': row_caro[0],
                'total': abs(row_caro[1]),
                'num_tx': row_caro[2],
                'tipo': 'más caro'
            }
        
        # Por frecuencia
        cursor.execute(f"""
            SELECT merchant_name, SUM(importe) as total, COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO' AND strftime('%Y-%m', fecha) = '{periodo}'
              AND merchant_name IS NOT NULL
            GROUP BY merchant_name
            ORDER BY num_tx DESC
            LIMIT 1
        """)
        
        row_frecuente = cursor.fetchone()
        merchant_frecuente = None
        if row_frecuente:
            merchant_frecuente = {
                'name': row_frecuente[0],
                'total': abs(row_frecuente[1]),
                'num_tx': row_frecuente[2],
                'tipo': 'más frecuente'
            }
        
        conn.close()
        
        # Elegir cuál reportar (el más caro por defecto)
        merchant = merchant_caro or merchant_frecuente
        return merchant if merchant else {}
    
    except Exception as e:
        print(f"❌ Error obteniendo merchant top: {e}", file=sys.stderr)
        return {}


def get_comparativa_semanas() -> Dict:
    """Compara gastos de esta semana vs la misma semana del mes anterior"""
    try:
        hoy = datetime.now()
        num_semana_actual = hoy.isocalendar()[1]
        semana_anterior_inicio = hoy - timedelta(days=7)
        semana_anterior_fin = hoy
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Gastos esta semana (últimos 7 días)
        cursor.execute("""
            SELECT SUM(importe) as total, COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO'
              AND fecha >= date('now', '-7 days')
        """)
        row_actual = cursor.fetchone()
        gasto_esta_semana = abs(row_actual[0]) if row_actual[0] else 0
        num_tx_esta = row_actual[1] if row_actual else 0
        
        # Gastos hace 7-14 días (semana anterior)
        cursor.execute("""
            SELECT SUM(importe) as total, COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO'
              AND fecha BETWEEN date('now', '-14 days') AND date('now', '-7 days')
        """)
        row_anterior = cursor.fetchone()
        gasto_semana_anterior = abs(row_anterior[0]) if row_anterior[0] else 0
        num_tx_anterior = row_anterior[1] if row_anterior else 0
        
        conn.close()
        
        diferencia = gasto_esta_semana - gasto_semana_anterior
        pct_cambio = (diferencia / gasto_semana_anterior * 100) if gasto_semana_anterior > 0 else 0
        tendencia = "↑" if diferencia > 0 else "↓" if diferencia < 0 else "="
        
        return {
            'gasto_esta_semana': gasto_esta_semana,
            'gasto_semana_anterior': gasto_semana_anterior,
            'diferencia': diferencia,
            'pct_cambio': pct_cambio,
            'tendencia': tendencia,
            'num_tx_esta': num_tx_esta,
            'num_tx_anterior': num_tx_anterior
        }
    
    except Exception as e:
        print(f"❌ Error comparando semanas: {e}", file=sys.stderr)
        return {}


def get_ahorro_diario() -> Dict:
    """Calcula el ahorro de ayer vs media diaria del mes"""
    try:
        # Ahorro de ayer (nómina - gastos)
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Gastos de ayer
        cursor.execute(f"""
            SELECT SUM(importe) FROM transacciones
            WHERE tipo = 'GASTO' AND fecha = '{ayer}'
        """)
        gastos_ayer = abs(cursor.fetchone()[0] or 0)
        
        # Ingresos de ayer
        cursor.execute(f"""
            SELECT SUM(importe) FROM transacciones
            WHERE tipo = 'INGRESO' AND fecha = '{ayer}'
        """)
        ingresos_ayer = cursor.fetchone()[0] or 0
        ahorro_ayer = ingresos_ayer - gastos_ayer
        
        # Media diaria del mes
        year, month = get_current_month_year()
        periodo = f"{year}-{month:02d}"
        
        cursor.execute(f"""
            SELECT 
                SUM(CASE WHEN tipo = 'INGRESO' THEN importe ELSE 0 END) as ingresos,
                SUM(CASE WHEN tipo = 'GASTO' THEN ABS(importe) ELSE 0 END) as gastos
            FROM transacciones
            WHERE strftime('%Y-%m', fecha) = '{periodo}'
        """)
        row = cursor.fetchone()
        ingresos_mes = row[0] or 0
        gastos_mes = row[1] or 0
        
        dias_transcurridos = 28 - get_dias_para_fin_mes()
        media_diaria = (ingresos_mes - gastos_mes) / dias_transcurridos if dias_transcurridos > 0 else 0
        
        conn.close()
        
        diferencia_vs_media = ahorro_ayer - media_diaria
        estado = "por encima" if diferencia_vs_media > 0 else "por debajo"
        
        return {
            'fecha': ayer,
            'ahorro_ayer': ahorro_ayer,
            'media_diaria_mes': media_diaria,
            'diferencia_vs_media': diferencia_vs_media,
            'estado': estado
        }
    
    except Exception as e:
        print(f"❌ Error calculando ahorro diario: {e}", file=sys.stderr)
        return {}


def prompt_gastos_ayer(datos: Dict) -> str:
    """Genera prompt para ángulo: gastos_ayer"""
    if not datos['gastos']:
        return "Ayer no hubo gastos. ¡Excelente día! 🎉"
    
    desglose = "\n".join([
        f"  • {g['cat1']}/{g['cat2']}: €{g['monto']:.2f} ({g['num_tx']} transacciones)"
        for g in datos['gastos'][:5]  # Top 5
    ])
    
    return f"""Gastos de ayer ({datos['fecha']}): €{datos['total']:.2f}

Desglose:
{desglose}

Total: {datos['num_transacciones']} transacciones"""


def prompt_ritmo_mes(datos: Dict) -> str:
    """Genera prompt para ángulo: ritmo_mes"""
    if not datos:
        return "No hay datos suficientes del mes."
    
    dias_falta = 28 - datos['dias_transcurridos']
    return f"""Ritmo actual del mes:

Gastos reales: €{datos['total_gasto']:.2f} (en {datos['dias_transcurridos']} días)
Gasto diario: €{datos['gasto_diario_promedio']:.2f}

Si sigues así...
→ Gastarías: €{datos['extrapolacion_mes']:.2f} para fin de mes
→ Presupuesto: €{datos['presupuesto_total']:.2f}
→ Estado: {datos['estado'].upper()}

Te quedan {dias_falta} días."""


def prompt_presupuesto_peligro(stats: Dict) -> str:
    """Genera prompt para ángulo: presupuesto_peligro"""
    if not stats['categorias_en_rojo'] and not stats['categorias_en_naranja']:
        return "Todas las categorías están dentro del plan. ¡Vas bien! ✅"
    
    riesgo = stats['categorias_en_rojo'] + stats['categorias_en_naranja']
    riesgo.sort(key=lambda x: x['pct'], reverse=True)
    
    top_riesgo = riesgo[0]
    pct = top_riesgo['pct']
    cat_name = f"{top_riesgo['cat1']}/{top_riesgo['cat2']}"
    gasto = top_riesgo['gasto']
    presupuesto = top_riesgo['presupuesto']
    restante = top_riesgo['restante']
    
    if pct >= 100:
        return f"🔴 ALERTA: {cat_name} está reventada ({pct:.0f}%)\nGasto: €{gasto:.2f} / Presupuesto: €{presupuesto:.2f}\nSobrepasada por: €{gasto - presupuesto:.2f}"
    else:
        return f"⚠️ NARANJA: {cat_name} al {pct:.0f}%\nGasto: €{gasto:.2f} / Presupuesto: €{presupuesto:.2f}\nRestante: €{restante:.2f}"


def prompt_merchant_sorpresa(datos: Dict) -> str:
    """Genera prompt para ángulo: merchant_sorpresa"""
    if not datos:
        return "Sin datos de merchants este mes."
    
    name = datos['name']
    total = datos['total']
    num_tx = datos['num_tx']
    
    return f"Revelación del mes: {name}\nHas gastado €{total:.2f} en {num_tx} compras\nPromedio por compra: €{total/num_tx:.2f}"


def prompt_ahorro_diario(datos: Dict) -> str:
    """Genera prompt para ángulo: ahorro_diario"""
    if not datos:
        return "Sin datos de ahorro."
    
    ayer = datos['fecha']
    ahorro = datos['ahorro_ayer']
    media = datos['media_diaria_mes']
    estado = datos['estado']
    
    return f"Ahorro de ayer ({ayer}): €{ahorro:.2f}\nMedia diaria del mes: €{media:.2f}\nEstás {estado} de la media"


def prompt_cargo_alerta(cargos: List[Dict]) -> str:
    """Genera prompt para ángulo: cargo_alerta"""
    if not cargos:
        return "No hay cargos extraordinarios próximos. Respira. 😌"
    
    cargo = cargos[0]
    return f"⏰ Alerta: {cargo['descripcion']}\n€{cargo['importe']:.2f} en {cargo['dias_para_aviso']} días ({cargo['fecha_cargo']})"


def generate_daily_message() -> str:
    """
    Genera mensaje diario con ángulo aleatorio y tono rotativo.
    
    Returns:
        str: Prompt listo para enviar al LLM o como fallback
    """
    # Elegir ángulo aleatorio
    angulo = random.choice(ANGULOS_DIARIOS)
    tono = random.choice(TONOS_DISPONIBLES)
    
    # Recopilar datos según ángulo
    if angulo == "gastos_ayer":
        datos = get_gastos_ayer()
        contenido = prompt_gastos_ayer(datos)
    
    elif angulo == "ritmo_mes":
        datos = get_ritmo_mes()
        contenido = prompt_ritmo_mes(datos)
    
    elif angulo == "presupuesto_peligro":
        stats = analizar_presupuestos()
        contenido = prompt_presupuesto_peligro(stats)
    
    elif angulo == "comparativa_semana":
        datos = get_comparativa_semanas()
        if datos:
            tren = datos['tendencia']
            gasto_esta = datos['gasto_esta_semana']
            gasto_anterior = datos['gasto_semana_anterior']
            pct = datos['pct_cambio']
            contenido = f"Comparativa semana:\nEsta semana: €{gasto_esta:.2f}\nSemana anterior: €{gasto_anterior:.2f}\nCambio: {tren} {pct:+.1f}%"
        else:
            contenido = "Sin datos para comparativa."
    
    elif angulo == "merchant_sorpresa":
        datos = get_merchant_top_mes()
        contenido = prompt_merchant_sorpresa(datos)
    
    elif angulo == "ahorro_diario":
        datos = get_ahorro_diario()
        contenido = prompt_ahorro_diario(datos)
    
    elif angulo == "cargo_alerta":
        cargos = get_cargos_extraordinarios_proximos()
        contenido = prompt_cargo_alerta(cargos)
    
    else:  # libre_llm
        stats = analizar_presupuestos()
        cargos = get_cargos_extraordinarios_proximos()
        contenido = f"Análisis libre del mes:\n{stats['mes_nombre'].capitalize()}: €{stats['total_gasto']:.2f} gastado, {stats['pct_total']:.0f}% utilizado"
    
    # Construir prompt con instrucciones de tono
    instrucciones_tono = _get_instrucciones_tono(tono)
    
    prompt = f"""Eres un asesor financiero personal de Telegram.

## Tono a usar: {tono}
{instrucciones_tono}

## Datos del análisis de hoy:
{contenido}

## Instrucciones generales:
- Sé breve: 2-3 párrafos máximo
- Tono conversacional, sin jerga corporativa
- Ocasionalmente incluye humor (especialmente si tono = bromista_financiero)
- Responde directamente, sin formateo especial
- No uses emojis excesivos

Genera un mensaje para enviar por Telegram:"""
    
    return prompt


def _get_instrucciones_tono(tono: str) -> str:
    """Retorna instrucciones específicas para cada tono"""
    instrucciones = {
        "amigo_whatsapp": "Habla como si fueras un amigo que entiende de finanzas. Directo, sin rodeos. Frases cortas. WhatsApp vibes.",
        "coach_energico": "Sé motivador pero realista. Sugiere acciones concretas. Energía positiva pero sin falsedad.",
        "analista_seco": "Sólo hechos y números. Bloomberg terminal energy. Minimalista, sin formalidades innecesarias.",
        "narrador_curioso": "Cuenta los datos como si fuera un cuento interesante. Busca patrones, conexiones inusuales.",
        "bromista_financiero": "Incluye UN chiste o comentario humorous sobre dinero/finanzas. El resto puede ser serio."
    }
    return instrucciones.get(tono, "Sé cercano e informal.")


def generate_monthly_message() -> str:
    """
    Genera mensaje mensual con ángulo rotativo.
    El ángulo se elige según el mes del año (enero→cierre_vs_anterior, febrero→cierre_fire, etc.)
    
    Returns:
        str: Prompt listo para enviar al LLM
    """
    # Elegir ángulo según el mes (rotación fija)
    mes_actual = datetime.now().month
    angulo_index = (mes_actual - 1) % len(ANGULOS_MENSUALES)
    angulo = ANGULOS_MENSUALES[angulo_index]
    
    # Mes anterior (para cierre)
    hoy = datetime.now()
    primer_dia_mes_actual = hoy.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)
    mes_anterior = ultimo_dia_mes_anterior.month
    año_anterior = ultimo_dia_mes_anterior.year
    
    periodo_anterior = f"{año_anterior}-{mes_anterior:02d}"
    periodo_actual = f"{hoy.year}-{hoy.month:02d}"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Query para mes anterior
        cursor.execute(f"""
            SELECT 
                SUM(CASE WHEN tipo = 'INGRESO' THEN importe ELSE 0 END) as ingresos,
                SUM(CASE WHEN tipo = 'GASTO' THEN ABS(importe) ELSE 0 END) as gastos
            FROM transacciones
            WHERE strftime('%Y-%m', fecha) = '{periodo_anterior}'
        """)
        row_anterior = cursor.fetchone()
        ingresos_anterior = row_anterior[0] or 0
        gastos_anterior = row_anterior[1] or 0
        ahorro_anterior = ingresos_anterior - gastos_anterior
        
        # Query para mes actual (hasta hoy)
        cursor.execute(f"""
            SELECT 
                SUM(CASE WHEN tipo = 'INGRESO' THEN importe ELSE 0 END) as ingresos,
                SUM(CASE WHEN tipo = 'GASTO' THEN ABS(importe) ELSE 0 END) as gastos
            FROM transacciones
            WHERE strftime('%Y-%m', fecha) <= '{periodo_actual}'
              AND fecha <= date('now')
        """)
        row_actual = cursor.fetchone()
        ingresos_actual = row_actual[0] or 0
        gastos_actual = row_actual[1] or 0
        ahorro_actual = ingresos_actual - gastos_actual
        
        conn.close()
        
        # Generar contenido según ángulo
        if angulo == "cierre_vs_anterior":
            mes_anterior_nombre = get_mes_nombre(mes_anterior)
            mes_actual_nombre = get_mes_nombre(hoy.month)
            delta_gasto = gastos_anterior - gastos_actual
            delta_ahorro = ahorro_anterior - ahorro_actual
            
            contenido = f"""Cierre de {mes_anterior_nombre.capitalize()}:
            
Ingresos: €{ingresos_anterior:.2f}
Gastos: €{gastos_anterior:.2f}
Ahorro: €{ahorro_anterior:.2f}

Comparativa vs {mes_actual_nombre}:
Gastos: {delta_gasto:+.2f}€
Ahorro: {delta_ahorro:+.2f}€"""
        
        elif angulo == "cierre_fire":
            tasa_ahorro = (ahorro_anterior / ingresos_anterior * 100) if ingresos_anterior > 0 else 0
            # Asumir FI target de 1 millón y SWR de 4%
            ahorro_anual_proyectado = ahorro_anterior * 12
            meses_para_fire = (1000000 / ahorro_anual_proyectado * 12) if ahorro_anual_proyectado > 0 else float('inf')
            
            mes_nombre = get_mes_nombre(mes_anterior)
            contenido = f"""Análisis FIRE — {mes_nombre.capitalize()}:

Ahorro del mes: €{ahorro_anterior:.2f}
Tasa de ahorro: {tasa_ahorro:.1f}%

Proyección anual: €{ahorro_anual_proyectado:.2f}
Meses para FI (target €1M): {meses_para_fire:.0f}"""
        
        else:  # cierre_patrones
            # Top categoría del mes
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT cat1, cat2, SUM(ABS(importe)) as total, COUNT(*) as num_tx
                FROM transacciones
                WHERE tipo = 'GASTO' AND strftime('%Y-%m', fecha) = '{periodo_anterior}'
                GROUP BY cat1, cat2
                ORDER BY total DESC
                LIMIT 1
            """)
            row_top = cursor.fetchone()
            if row_top:
                top_cat = f"{row_top[0]}/{row_top[1]}: €{row_top[2]:.2f}"
            else:
                top_cat = "Sin datos"
            
            mes_nombre = get_mes_nombre(mes_anterior)
            contenido = f"""Patrones de {mes_nombre.capitalize()}:

Gasto total: €{gastos_anterior:.2f}
Top categoría: {top_cat}
Transacciones: Ver detalle en dashboard"""
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error generando mensaje mensual: {e}", file=sys.stderr)
        contenido = "Error al analizar datos mensuales."
    
    prompt = f"""Eres un asesor financiero personal que hace cierre mensual.

## Ángulo de análisis: {angulo}
Estilo: Analítico, con datos concretos y recomendaciones.

## Datos del cierre:
{contenido}

## Instrucciones:
- 2-4 párrafos, análisis serio
- Incluye observaciones sobre tendencias
- Si hay oportunidades de mejora, sugierelas
- Sin emojis, tono profesional pero cercano

Genera el cierre mensual para Telegram:"""
    
    return prompt


def generate_annual_message() -> str:
    """
    Genera mensaje anual (1 de enero) con revisión del año anterior.
    
    Returns:
        str: Prompt listo para enviar al LLM
    """
    try:
        año_anterior = datetime.now().year - 1
        periodo = f"{año_anterior}%"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Query para año completo
        cursor.execute(f"""
            SELECT 
                SUM(CASE WHEN tipo = 'INGRESO' THEN importe ELSE 0 END) as ingresos,
                SUM(CASE WHEN tipo = 'GASTO' THEN ABS(importe) ELSE 0 END) as gastos,
                COUNT(*) as num_tx
            FROM transacciones
            WHERE strftime('%Y', fecha) = '{año_anterior}'
        """)
        row = cursor.fetchone()
        ingresos = row[0] or 0
        gastos = row[1] or 0
        num_tx = row[2] or 0
        ahorro = ingresos - gastos
        tasa_ahorro = (ahorro / ingresos * 100) if ingresos > 0 else 0
        
        # Top 5 categorías
        cursor.execute(f"""
            SELECT cat1, cat2, SUM(ABS(importe)) as total
            FROM transacciones
            WHERE tipo = 'GASTO' AND strftime('%Y', fecha) = '{año_anterior}'
            GROUP BY cat1, cat2
            ORDER BY total DESC
            LIMIT 5
        """)
        
        top_cats = []
        for row_cat in cursor.fetchall():
            top_cats.append(f"{row_cat[0]}/{row_cat[1]}: €{row_cat[2]:.2f}")
        
        # Proyección FIRE
        ahorro_anual = ahorro
        meses_para_fire = (1000000 / ahorro_anual * 12) if ahorro_anual > 0 else float('inf')
        
        conn.close()
        
        contenido = f"""Revisión Anual {año_anterior}:

**Resumen Financiero:**
- Ingresos totales: €{ingresos:.2f}
- Gastos totales: €{gastos:.2f}
- Ahorro neto: €{ahorro:.2f}
- Tasa de ahorro: {tasa_ahorro:.1f}%
- Transacciones: {num_tx}

**Top 5 Categorías de Gasto:**
{chr(10).join(['• ' + cat for cat in top_cats])}

**Proyección FIRE:**
- Ahorro anual: €{ahorro_anual:.2f}
- Meses para FI (target €1M): {meses_para_fire:.0f}
- Equivalente a {meses_para_fire/12:.1f} años"""
        
    except Exception as e:
        print(f"❌ Error generando mensaje anual: {e}", file=sys.stderr)
        contenido = "Error al analizar datos anuales."
    
    prompt = f"""Eres un asesor financiero personal haciendo un cierre anual.

## Revisión del Año {año_anterior}

{contenido}

## Instrucciones para tu respuesta:
- Tono: Estratégico, reflexivo, motivador
- 3-5 párrafos máximo
- Analiza tendencias y logros
- Sugiere objetivos para el año nuevo
- Celebra los ahorros conseguidos
- Sé realista pero optimista

Genera el mensaje anual para Telegram:"""
    
    return prompt
