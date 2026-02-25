"""
Motor de consultas financieras sobre transacciones clasificadas.
"""
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, Dict, List


class QueryEngine:
    """Motor de consultas financieras sobre transacciones clasificadas."""

    def __init__(self, db_path='finsense.db'):
        """Inicializa el motor de consultas."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Cierra la conexión a la base de datos."""
        self.conn.close()

    # =========================================
    # 1. GASTO POR CATEGORÍA
    # =========================================

    def gasto_por_categoria(self, year: int, month: int = None) -> dict:
        """
        Gasto total por Cat1, opcionalmente filtrado por mes.
        EXCLUYE: Tipo=TRANSFERENCIA, Tipo=INVERSION y Cat1=Bizum (solo GASTO puro).

        Args:
            year: Año
            month: Mes (opcional, si None devuelve todo el año)

        Returns:
            Dict con periodo, total y categorías desglosadas
        """
        cursor = self.conn.cursor()

        # Construir filtro de periodo
        if month:
            periodo = f"{year}-{month:02d}"
            date_filter = f"AND strftime('%Y-%m', fecha) = '{periodo}'"
        else:
            periodo = str(year)
            date_filter = f"AND strftime('%Y', fecha) = '{year}'"

        # Gasto total (solo GASTO, excluye TRANSFERENCIA, INVERSION y Bizum)
        cursor.execute(f'''
            SELECT SUM(importe) as total
            FROM transacciones
            WHERE tipo = 'GASTO'
            AND cat1 != 'Bizum'
            {date_filter}
        ''')
        total_gasto = cursor.fetchone()['total'] or 0.0

        # Gasto por Cat1
        cursor.execute(f'''
            SELECT
                cat1,
                SUM(importe) as total,
                COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO'
            AND cat1 != 'Bizum'
            {date_filter}
            GROUP BY cat1
            ORDER BY total ASC
        ''')

        categorias = []
        for row in cursor.fetchall():
            cat1 = row['cat1']
            total_cat1 = row['total']
            num_tx = row['num_tx']
            pct = (abs(total_cat1) / abs(total_gasto) * 100) if total_gasto != 0 else 0

            # Subcategorías (Cat2)
            cursor.execute(f'''
                SELECT
                    cat2,
                    SUM(importe) as total,
                    COUNT(*) as num_tx
                FROM transacciones
                WHERE tipo = 'GASTO'
                AND importe < 0
                AND cat1 = ?
                AND cat1 != 'Bizum'
                {date_filter}
                GROUP BY cat2
                ORDER BY total ASC
            ''', (cat1,))

            subcategorias = []
            for sub_row in cursor.fetchall():
                cat2 = sub_row['cat2'] or '(sin especificar)'
                total_cat2 = sub_row['total']
                num_tx_cat2 = sub_row['num_tx']
                pct_cat2 = (abs(total_cat2) / abs(total_cat1) * 100) if total_cat1 != 0 else 0

                subcategorias.append({
                    'cat2': cat2,
                    'total': total_cat2,
                    'num_tx': num_tx_cat2,
                    'pct': round(pct_cat2, 1),
                })

            categorias.append({
                'cat1': cat1 or '(sin categoría)',
                'total': total_cat1,
                'num_tx': num_tx,
                'pct': round(pct, 1),
                'subcategorias': subcategorias,
            })

        return {
            'periodo': periodo,
            'total': total_gasto,
            'categorias': categorias,
        }

    def gasto_por_categoria_detalle(self, cat1: str, year: int, month: int = None) -> dict:
        """Desglose de Cat2 dentro de una Cat1 específica."""
        cursor = self.conn.cursor()

        # Construir filtro de periodo
        if month:
            periodo = f"{year}-{month:02d}"
            date_filter = f"AND strftime('%Y-%m', fecha) = '{periodo}'"
        else:
            periodo = str(year)
            date_filter = f"AND strftime('%Y', fecha) = '{year}'"

        # Total de la categoría
        cursor.execute(f'''
            SELECT SUM(importe) as total
            FROM transacciones
            WHERE tipo = 'GASTO'
            AND importe < 0
            AND cat1 = ?
            AND cat1 != 'Bizum'
            {date_filter}
        ''', (cat1,))
        total_cat1 = cursor.fetchone()['total'] or 0.0

        # Desglose por Cat2
        cursor.execute(f'''
            SELECT
                cat2,
                SUM(importe) as total,
                COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO'
            AND importe < 0
            AND cat1 = ?
            AND cat1 != 'Bizum'
            {date_filter}
            GROUP BY cat2
            ORDER BY total ASC
        ''', (cat1,))

        subcategorias = []
        for row in cursor.fetchall():
            cat2 = row['cat2'] or '(sin especificar)'
            total = row['total']
            num_tx = row['num_tx']
            pct = (abs(total) / abs(total_cat1) * 100) if total_cat1 != 0 else 0

            subcategorias.append({
                'cat2': cat2,
                'total': total,
                'num_tx': num_tx,
                'pct': round(pct, 1),
            })

        return {
            'periodo': periodo,
            'cat1': cat1,
            'total': total_cat1,
            'subcategorias': subcategorias,
        }

    # =========================================
    # 2. COMPARATIVA MENSUAL
    # =========================================

    def comparativa_mensual(self, year: int, month: int, meses_atras: int = 6) -> dict:
        """
        Compara el mes actual con los N meses anteriores.

        Args:
            year: Año del mes a analizar
            month: Mes a analizar
            meses_atras: Cuántos meses previos usar para calcular media

        Returns:
            Dict con comparativa mensual
        """
        cursor = self.conn.cursor()

        # Periodo actual
        periodo_actual = f"{year}-{month:02d}"

        # Gasto del mes actual
        cursor.execute('''
            SELECT SUM(importe) as total
            FROM transacciones
            WHERE tipo = 'GASTO'
            AND cat1 != 'Bizum'
            AND strftime('%Y-%m', fecha) = ?
        ''', (periodo_actual,))
        gasto_actual = cursor.fetchone()['total'] or 0.0

        # Calcular meses anteriores
        fecha_actual = datetime(year, month, 1)
        periodos_anteriores = []
        for i in range(1, meses_atras + 1):
            fecha_anterior = fecha_actual - timedelta(days=30 * i)
            periodo = fecha_anterior.strftime('%Y-%m')
            periodos_anteriores.append(periodo)

        # Gasto promedio de meses anteriores
        placeholders = ','.join('?' * len(periodos_anteriores))
        cursor.execute(f'''
            SELECT AVG(total_mes) as media
            FROM (
                SELECT strftime('%Y-%m', fecha) as mes, SUM(importe) as total_mes
                FROM transacciones
                WHERE tipo = 'GASTO'
                AND importe < 0
                AND cat1 != 'Bizum'
                AND strftime('%Y-%m', fecha) IN ({placeholders})
                GROUP BY strftime('%Y-%m', fecha)
            )
        ''', periodos_anteriores)
        media_anterior = cursor.fetchone()['media'] or 0.0

        # Variación
        variacion_pct = ((abs(gasto_actual) - abs(media_anterior)) / abs(media_anterior) * 100) if media_anterior != 0 else 0

        # Comparativa por categoría
        por_categoria = []
        cursor.execute(f'''
            SELECT cat1, SUM(importe) as total
            FROM transacciones
            WHERE tipo = 'GASTO'
            AND cat1 != 'Bizum'
            AND strftime('%Y-%m', fecha) = ?
            GROUP BY cat1
        ''', (periodo_actual,))

        categorias_actual = {row['cat1']: row['total'] for row in cursor.fetchall()}

        # Media por categoría en meses anteriores
        cursor.execute(f'''
            SELECT cat1, AVG(total_mes) as media
            FROM (
                SELECT cat1, strftime('%Y-%m', fecha) as mes, SUM(importe) as total_mes
                FROM transacciones
                WHERE tipo = 'GASTO'
                AND importe < 0
                AND cat1 != 'Bizum'
                AND strftime('%Y-%m', fecha) IN ({placeholders})
                GROUP BY cat1, strftime('%Y-%m', fecha)
            )
            GROUP BY cat1
        ''', periodos_anteriores)

        categorias_media = {row['cat1']: row['media'] for row in cursor.fetchall()}

        # Combinar
        todas_categorias = set(categorias_actual.keys()) | set(categorias_media.keys())
        for cat1 in todas_categorias:
            actual = categorias_actual.get(cat1, 0.0)
            media = categorias_media.get(cat1, 0.0)
            if media != 0:
                var_pct = ((abs(actual) - abs(media)) / abs(media) * 100)
            else:
                var_pct = 0 if actual == 0 else 100

            # Tendencia
            if abs(var_pct) < 5:
                tendencia = 'estable'
            elif var_pct > 0:
                tendencia = 'subiendo'
            else:
                tendencia = 'bajando'

            por_categoria.append({
                'cat1': cat1,
                'mes_actual': actual,
                'media_anterior': media,
                'variacion_pct': round(var_pct, 1),
                'tendencia': tendencia,
            })

        # Ordenar por variación absoluta
        por_categoria.sort(key=lambda x: abs(x['variacion_pct']), reverse=True)

        # Generar alertas
        alertas = []
        for cat in por_categoria[:5]:  # Top 5 variaciones
            if abs(cat['variacion_pct']) > 10:
                if cat['variacion_pct'] > 0:
                    diff = abs(cat['mes_actual']) - abs(cat['media_anterior'])
                    alertas.append(f"{cat['cat1']}: +{cat['variacion_pct']:.0f}% vs media (€{abs(diff):.0f} más de lo habitual)")
                else:
                    diff = abs(cat['media_anterior']) - abs(cat['mes_actual'])
                    alertas.append(f"{cat['cat1']}: {cat['variacion_pct']:.0f}% vs media (€{abs(diff):.0f} menos, buen mes)")

        return {
            'mes_actual': {
                'periodo': periodo_actual,
                'gasto_total': gasto_actual,
            },
            'media_anterior': media_anterior,
            'variacion_pct': round(variacion_pct, 1),
            'por_categoria': por_categoria,
            'alertas': alertas,
        }

    # =========================================
    # 3. RECIBOS RECURRENTES
    # =========================================

    def recibos_recurrentes(self, year: int = None, month: int = None) -> dict:
        """
        Detecta gastos recurrentes (mismo merchant, frecuencia regular).
        Un recibo es recurrente si aparece >=3 veces con periodicidad similar.

        Args:
            year: Año (opcional, para filtrar)
            month: Mes (opcional, para filtrar)

        Returns:
            Dict con recibos recurrentes detectados
        """
        cursor = self.conn.cursor()

        # Filtro de periodo (si se especifica)
        date_filter = ""
        if year and month:
            periodo = f"{year}-{month:02d}"
            date_filter = f"AND strftime('%Y-%m', fecha) = '{periodo}'"
        elif year:
            date_filter = f"AND strftime('%Y', fecha) = '{year}'"

        # Buscar transacciones que se repiten por cat2 o descripción
        # Agrupar por cat1+cat2 para merchants específicos
        cursor.execute(f'''
            SELECT
                cat1,
                cat2,
                descripcion,
                COUNT(*) as num_ocurrencias,
                AVG(importe) as importe_medio,
                MIN(fecha) as primera_fecha,
                MAX(fecha) as ultima_fecha,
                GROUP_CONCAT(fecha) as todas_fechas
            FROM transacciones
            WHERE tipo = 'GASTO'
            AND cat1 != 'Bizum'
            {date_filter}
            GROUP BY cat1, cat2, SUBSTR(descripcion, 1, 50)
            HAVING num_ocurrencias >= 3
            ORDER BY num_ocurrencias DESC
        ''')

        recurrentes = []
        for row in cursor.fetchall():
            cat1 = row['cat1']
            cat2 = row['cat2'] or '(genérico)'
            descripcion = row['descripcion']
            num = row['num_ocurrencias']
            importe_medio = row['importe_medio']
            primera = row['primera_fecha']
            ultima = row['ultima_fecha']
            todas_fechas_str = row['todas_fechas']

            # Calcular periodicidad
            fechas = [datetime.strptime(f, '%Y-%m-%d') for f in todas_fechas_str.split(',')]
            fechas.sort()

            if len(fechas) >= 2:
                # Calcular diferencias entre fechas consecutivas
                diffs = [(fechas[i+1] - fechas[i]).days for i in range(len(fechas) - 1)]
                promedio_dias = sum(diffs) / len(diffs) if diffs else 0

                # Skip si todas las transacciones son en la misma fecha
                if promedio_dias == 0:
                    continue

                # Determinar frecuencia
                if 25 <= promedio_dias <= 35:
                    frecuencia = 'mensual'
                elif 85 <= promedio_dias <= 95:
                    frecuencia = 'trimestral'
                elif 350 <= promedio_dias <= 370:
                    frecuencia = 'anual'
                else:
                    frecuencia = f'cada {int(promedio_dias)} días'

                # Estimar próximo cargo
                proximo = fechas[-1] + timedelta(days=int(promedio_dias))
                proximo_estimado = proximo.strftime('%Y-%m-%d')

                # Estimar total anual
                if frecuencia == 'mensual':
                    total_anual = importe_medio * 12
                elif frecuencia == 'trimestral':
                    total_anual = importe_medio * 4
                elif frecuencia == 'anual':
                    total_anual = importe_medio
                else:
                    total_anual = importe_medio * (365 / promedio_dias)

                # Solo incluir si parece verdaderamente recurrente (periodicidad regular)
                if max(diffs) - min(diffs) < 15:  # Variación máxima de 15 días
                    recurrentes.append({
                        'descripcion': descripcion[:60] if len(descripcion) > 60 else descripcion,
                        'cat1': cat1,
                        'cat2': cat2,
                        'frecuencia': frecuencia,
                        'importe_medio': importe_medio,
                        'ultimo_cargo': ultima,
                        'proximo_estimado': proximo_estimado,
                        'total_anual_estimado': total_anual,
                        'num_ocurrencias': num,
                    })

        # Calcular totales
        total_mensual = sum(r['importe_medio'] for r in recurrentes if r['frecuencia'] == 'mensual')
        total_anual = sum(r['total_anual_estimado'] for r in recurrentes)

        # Ordenar por importe anual estimado
        recurrentes.sort(key=lambda x: abs(x['total_anual_estimado']), reverse=True)

        return {
            'recurrentes': recurrentes,
            'total_mensual_recurrente': total_mensual,
            'total_anual_recurrente': total_anual,
        }

    # =========================================
    # 4. EVOLUCIÓN DE AHORRO
    # =========================================

    def evolucion_ahorro(self, meses: int = 12) -> dict:
        """
        Calcula ahorro mensual = ingresos - gastos (excluyendo transferencias internas).

        IMPORTANTE:
        - Ingresos = Tipo=INGRESO (nóminas, intereses, etc.)
        - Gastos = Tipo=GASTO (compras, recibos, etc.)
        - EXCLUIR Tipo=TRANSFERENCIA (movimiento entre cuentas)
        - EXCLUIR Tipo=INVERSION (es ahorro/inversión, no gasto consumo)
        - EXCLUIR Cat1=Bizum (movimientos entre personas que se compensan)

        Args:
            meses: Número de meses a analizar

        Returns:
            Dict con evolución de ahorro
        """
        cursor = self.conn.cursor()

        # Obtener últimos N meses con datos
        cursor.execute(f'''
            SELECT DISTINCT strftime('%Y-%m', fecha) as periodo
            FROM transacciones
            ORDER BY periodo DESC
            LIMIT ?
        ''', (meses,))

        periodos = [row['periodo'] for row in cursor.fetchall()]
        periodos.reverse()  # Orden cronológico

        meses_data = []
        for periodo in periodos:
            # Ingresos del mes
            cursor.execute('''
                SELECT SUM(importe) as total
                FROM transacciones
                WHERE tipo = 'INGRESO'
                AND importe > 0
                AND cat1 != 'Bizum'
                AND strftime('%Y-%m', fecha) = ?
            ''', (periodo,))
            ingresos = cursor.fetchone()['total'] or 0.0

            # Gastos del mes (solo GASTO, NO transferencias ni inversiones ni Bizum)
            # IMPORTANTE: Incluir positivos (devoluciones) y negativos (gastos)
            cursor.execute('''
                SELECT SUM(importe) as total
                FROM transacciones
                WHERE tipo = 'GASTO'
                AND cat1 != 'Bizum'
                AND strftime('%Y-%m', fecha) = ?
            ''', (periodo,))
            gastos = cursor.fetchone()['total'] or 0.0

            # Ahorro
            ahorro = ingresos + gastos  # gastos es negativo
            tasa_ahorro_pct = (ahorro / ingresos * 100) if ingresos > 0 else 0

            meses_data.append({
                'periodo': periodo,
                'ingresos': ingresos,
                'gastos': gastos,
                'ahorro': ahorro,
                'tasa_ahorro_pct': round(tasa_ahorro_pct, 1),
            })

        # Calcular estadísticas
        if meses_data:
            media_ahorro = sum(m['ahorro'] for m in meses_data) / len(meses_data)

            # Tendencia (comparar últimos 3 vs primeros 3)
            if len(meses_data) >= 6:
                primeros_3 = sum(m['ahorro'] for m in meses_data[:3]) / 3
                ultimos_3 = sum(m['ahorro'] for m in meses_data[-3:]) / 3
                if ultimos_3 > primeros_3 * 1.05:
                    tendencia = 'mejorando'
                elif ultimos_3 < primeros_3 * 0.95:
                    tendencia = 'empeorando'
                else:
                    tendencia = 'estable'
            else:
                tendencia = 'datos insuficientes'

            mejor_mes = max(meses_data, key=lambda x: x['ahorro'])
            peor_mes = min(meses_data, key=lambda x: x['ahorro'])
        else:
            media_ahorro = 0
            tendencia = 'sin datos'
            mejor_mes = {'periodo': 'N/A', 'ahorro': 0}
            peor_mes = {'periodo': 'N/A', 'ahorro': 0}

        return {
            'meses': meses_data,
            'media_ahorro': media_ahorro,
            'tendencia': tendencia,
            'mejor_mes': mejor_mes,
            'peor_mes': peor_mes,
        }

    # =========================================
    # 5. TOP MERCHANTS
    # =========================================

    def top_merchants(self, n: int = 20, year: int = None, month: int = None) -> dict:
        """
        Top N merchants por volumen de gasto.
        Agrupa por Cat2 (merchant específico) o por descripción normalizada.

        Args:
            n: Número de merchants a devolver
            year: Año (opcional)
            month: Mes (opcional)

        Returns:
            Dict con top merchants
        """
        cursor = self.conn.cursor()

        # Construir filtro de periodo
        if year and month:
            periodo = f"{year}-{month:02d}"
            date_filter = f"AND strftime('%Y-%m', fecha) = '{periodo}'"
        elif year:
            periodo = str(year)
            date_filter = f"AND strftime('%Y', fecha) = '{year}'"
        else:
            periodo = 'todos'
            date_filter = ""

        # Agrupar por cat2 (si está disponible) o por descripción
        cursor.execute(f'''
            SELECT
                CASE
                    WHEN cat2 != '' AND cat2 IS NOT NULL THEN cat2
                    ELSE SUBSTR(descripcion, 1, 40)
                END as merchant,
                cat1,
                SUM(importe) as total,
                COUNT(*) as num_transacciones,
                AVG(importe) as ticket_medio
            FROM transacciones
            WHERE tipo = 'GASTO'
            AND cat1 != 'Bizum'
            {date_filter}
            GROUP BY merchant, cat1
            ORDER BY total ASC
            LIMIT ?
        ''', (n,))

        top = []
        for row in cursor.fetchall():
            top.append({
                'merchant': row['merchant'],
                'cat1': row['cat1'],
                'total': row['total'],
                'num_transacciones': row['num_transacciones'],
                'ticket_medio': row['ticket_medio'],
            })

        return {
            'periodo': periodo,
            'top': top,
        }

    # =========================================
    # 6. RESUMEN MENSUAL INTELIGENTE
    # =========================================

    def resumen_mensual(self, year: int, month: int) -> dict:
        """
        Resumen completo de un mes. Esta función es la que el LLM
        usará para generar el análisis en lenguaje natural.

        Combina: gasto por categoría + comparativa + recurrentes + ahorro + top merchants

        Args:
            year: Año
            month: Mes

        Returns:
            Dict con resumen completo del mes
        """
        periodo = f"{year}-{month:02d}"
        cursor = self.conn.cursor()

        # Totales del mes
        cursor.execute('''
            SELECT SUM(importe) as total
            FROM transacciones
            WHERE tipo = 'INGRESO'
            AND importe > 0
            AND cat1 != 'Bizum'
            AND strftime('%Y-%m', fecha) = ?
        ''', (periodo,))
        ingreso_total = cursor.fetchone()['total'] or 0.0

        cursor.execute('''
            SELECT SUM(importe) as total
            FROM transacciones
            WHERE tipo = 'GASTO'
            AND cat1 != 'Bizum'
            AND strftime('%Y-%m', fecha) = ?
        ''', (periodo,))
        gasto_total = cursor.fetchone()['total'] or 0.0

        ahorro = ingreso_total + gasto_total  # gasto_total es negativo
        tasa_ahorro_pct = (ahorro / ingreso_total * 100) if ingreso_total > 0 else 0

        # Comparativa con meses anteriores
        comparativa = self.comparativa_mensual(year, month, meses_atras=6)

        # Categorías arriba/abajo
        categorias_arriba = [c for c in comparativa['por_categoria'] if c['variacion_pct'] > 10][:5]
        categorias_abajo = [c for c in comparativa['por_categoria'] if c['variacion_pct'] < -10][:5]

        # Top 5 gastos
        top_gastos = self.top_merchants(n=5, year=year, month=month)['top']

        # Recurrentes del mes
        recurrentes_mes = self.recibos_recurrentes(year=year, month=month)

        # Alertas y logros
        alertas = comparativa['alertas']

        logros = []
        # Verificar si es el mejor mes de ahorro
        evol_ahorro = self.evolucion_ahorro(meses=6)
        if evol_ahorro['meses'] and evol_ahorro['meses'][-1]['periodo'] == periodo:
            if evol_ahorro['meses'][-1]['ahorro'] >= max(m['ahorro'] for m in evol_ahorro['meses'][:-1]):
                logros.append('Mejor mes de ahorro en los últimos 6 meses')

        # Verificar reducciones significativas
        for cat in categorias_abajo:
            if cat['variacion_pct'] < -15:
                logros.append(f"Has reducido {cat['cat1']} un {abs(cat['variacion_pct']):.0f}%")

        return {
            'periodo': periodo,
            'gasto_total': gasto_total,
            'ingreso_total': ingreso_total,
            'ahorro': ahorro,
            'tasa_ahorro_pct': round(tasa_ahorro_pct, 1),
            'vs_media': {
                'variacion_pct': comparativa['variacion_pct'],
                'categorias_arriba': categorias_arriba,
                'categorias_abajo': categorias_abajo,
            },
            'top_5_gastos': top_gastos,
            'recurrentes_del_mes': recurrentes_mes,
            'alertas': alertas,
            'logros': logros,
        }
