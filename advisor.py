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

# ===== FUNCIONES DE EXPORTACIÓN =====

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
