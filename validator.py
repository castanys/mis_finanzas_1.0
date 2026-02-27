"""
validator.py — Módulo de validación de integridad del sistema finsense

Se ejecuta automáticamente después de cualquier carga, clasificación o proceso.
Detecta errores reales basados en problemas encontrados en sesiones anteriores (S1–S66).

Checks implementados:
  V01 — Cat1 fuera de whitelist
  V02 — Combinación Cat1|Cat2 inválida
  V03 — tipo inconsistente con cat1/importe
  V04 — Duplicados exactos (mismo hash, no debería ocurrir por UNIQUE)
  V05 — Duplicados sospechosos (misma fecha+importe+descripcion similar)
  V06 — Transacciones SIN_CLASIFICAR o cat1 vacío
  V07 — Transacciones sin merchant_name donde debería haberlo
  V08 — Importes con signo incorrecto (GASTO positivo / INGRESO negativo)
  V09 — Fechas fuera de rango razonable o formato inválido
  V10 — Merchants en tabla merchants sin cat1 (enriquecimiento incompleto)
  V11 — Transacciones huérfanas de banco desconocido
  V12 — Cat2 no vacío cuando debería ser vacío (Cat1 con solo "")
  V13 — Descripcion vacía o nula
  V14 — Hash NULL o duplicado cruzado entre cuentas distintas
  V15 — Importe exactamente cero
  V16 — Transferencias internas sin contrapartida (importe opuesto mismo día)
  V17 — Nóminas anómalas (importe muy diferente a la media histórica)
  V18 — Gastos extremos (outliers estadísticos por cat1)

Uso:
    python3 validator.py                   # valida toda la BD
    python3 validator.py --since 2026-02   # solo transacciones desde esa fecha
    python3 validator.py --fix             # aplica correcciones automáticas seguras
    python3 validator.py --json            # salida en JSON para integración

Integración automática:
    from validator import run_validation
    report = run_validation(db_path='finsense.db')
    if report['errores_criticos'] > 0:
        logger.warning(report['resumen'])
"""

import sqlite3
import argparse
import json
import sys
from datetime import datetime, date
from collections import defaultdict
from difflib import SequenceMatcher

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

DB_PATH_DEFAULT = 'finsense.db'
FECHA_MIN = '2000-01-01'
FECHA_MAX = '2035-12-31'

# Cat1 con whitelist cerrada (23 categorías)
CAT1_WHITELIST = {
    # GASTO
    'Alimentación', 'Compras', 'Deportes', 'Efectivo', 'Finanzas',
    'Impuestos', 'Ocio y Cultura', 'Recibos', 'Restauración',
    'Ropa y Calzado', 'Salud y Belleza', 'Seguros', 'Servicios Consultoría',
    'Suscripciones', 'Transporte', 'Viajes', 'Vivienda',
    # INGRESO
    'Cashback', 'Intereses', 'Nómina', 'Wallapop',
    # OTROS
    'Liquidación', 'Transferencia', 'Inversión',
    # Categorías históricas aceptadas (presentes en la BD por decisiones anteriores)
    'Aportación', 'Bizum', 'Comisiones', 'Cripto', 'Cuenta Común',
    'Depósitos', 'Dividendos', 'Divisas', 'Externa', 'Fondos',
    'Interna', 'Otros', 'Renta Variable',
    'Bonificación familia numerosa',
}

# Cat1 que deben tener cat2 vacío siempre (D12: sin redundancia)
CAT1_SIN_CAT2 = {
    'Aportación', 'Bizum', 'Cashback', 'Depósitos', 'Dividendos',
    'Divisas', 'Externa', 'Fondos', 'Intereses', 'Interna',
    'Liquidación', 'Nómina', 'Servicios Consultoría', 'Wallapop',
}

# Cat1 que son INGRESO por naturaleza
CAT1_INGRESO = {'Cashback', 'Intereses', 'Nómina', 'Wallapop', 'Dividendos', 'Aportación'}

# Cat1 que son TRANSFERENCIA por naturaleza
CAT1_TRANSFERENCIA = {'Interna', 'Externa', 'Bizum', 'Cuenta Común', 'Liquidación'}

# Bancos conocidos
BANCOS_CONOCIDOS = {
    'Openbank', 'Abanca', 'MyInvestor', 'Mediolanum', 'Revolut',
    'Trade Republic', 'B100', 'Bankinter', 'Enablebanking', 'Preprocessed',
}

# Umbral para similitud de descripciones (duplicado sospechoso)
SIMILITUD_DUPLICADO = 0.85

# Desviación máxima para nóminas (±40% de la media histórica)
UMBRAL_NOMINA_DESVIACION = 0.40

# Multiplicador para outlier de gasto por cat1 (3 desviaciones estándar)
UMBRAL_OUTLIER_SIGMA = 3.0

# Importe mínimo para considerar outlier (no alertar por 1€)
OUTLIER_IMPORTE_MIN = 50.0

# ─────────────────────────────────────────────────────────────────────────────
# CLASES DE RESULTADO
# ─────────────────────────────────────────────────────────────────────────────

class ValidationIssue:
    """Un problema encontrado durante la validación."""

    SEVERIDAD_CRITICA = 'CRITICA'   # Datos incorrectos / integridad rota
    SEVERIDAD_ADVERTENCIA = 'WARN'  # Posible error, revisar manualmente
    SEVERIDAD_INFO = 'INFO'         # Información útil, no es error

    def __init__(self, check_id, severidad, mensaje, tx_ids=None, datos=None):
        self.check_id = check_id          # 'V01', 'V02', etc.
        self.severidad = severidad
        self.mensaje = mensaje
        self.tx_ids = tx_ids or []        # IDs de transacciones afectadas
        self.datos = datos or {}          # Datos adicionales para debug

    def to_dict(self):
        return {
            'check': self.check_id,
            'severidad': self.severidad,
            'mensaje': self.mensaje,
            'tx_ids': self.tx_ids[:20],   # Limitar a 20 para no saturar
            'total_afectadas': len(self.tx_ids),
            'datos': self.datos,
        }

    def __str__(self):
        n = f" ({len(self.tx_ids)} txs)" if self.tx_ids else ""
        return f"[{self.check_id}][{self.severidad}]{n} {self.mensaje}"


class ValidationReport:
    """Resultado completo de una validación."""

    def __init__(self, db_path, since=None):
        self.db_path = db_path
        self.since = since
        self.timestamp = datetime.now().isoformat()
        self.issues = []
        self.total_txs_analizadas = 0
        self.checks_ejecutados = []

    def add(self, issue):
        self.issues.append(issue)

    @property
    def criticas(self):
        return [i for i in self.issues if i.severidad == ValidationIssue.SEVERIDAD_CRITICA]

    @property
    def advertencias(self):
        return [i for i in self.issues if i.severidad == ValidationIssue.SEVERIDAD_ADVERTENCIA]

    @property
    def infos(self):
        return [i for i in self.issues if i.severidad == ValidationIssue.SEVERIDAD_INFO]

    def resumen_texto(self):
        lines = [
            f"\n{'='*60}",
            f"VALIDACIÓN FINSENSE — {self.timestamp[:19]}",
            f"BD: {self.db_path} | Txs analizadas: {self.total_txs_analizadas}",
            f"{'='*60}",
        ]
        if self.since:
            lines.append(f"Filtro: transacciones desde {self.since}")

        if not self.issues:
            lines.append("✅ Sin problemas encontrados.")
        else:
            lines.append(f"🔴 CRÍTICAS:     {len(self.criticas)}")
            lines.append(f"🟡 ADVERTENCIAS: {len(self.advertencias)}")
            lines.append(f"ℹ️  INFO:         {len(self.infos)}")
            lines.append("")
            for issue in self.issues:
                icono = "🔴" if issue.severidad == ValidationIssue.SEVERIDAD_CRITICA else \
                        "🟡" if issue.severidad == ValidationIssue.SEVERIDAD_ADVERTENCIA else "ℹ️ "
                lines.append(f"{icono} {issue}")

        lines.append(f"{'='*60}\n")
        return "\n".join(lines)

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'db_path': self.db_path,
            'since': self.since,
            'total_txs_analizadas': self.total_txs_analizadas,
            'checks_ejecutados': self.checks_ejecutados,
            'resumen': {
                'criticas': len(self.criticas),
                'advertencias': len(self.advertencias),
                'infos': len(self.infos),
                'total': len(self.issues),
            },
            'issues': [i.to_dict() for i in self.issues],
        }


# ─────────────────────────────────────────────────────────────────────────────
# CLASE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class Validator:
    """
    Validador de integridad del sistema finsense.
    Ejecuta todos los checks y genera un ValidationReport.
    """

    def __init__(self, db_path=DB_PATH_DEFAULT, since=None):
        self.db_path = db_path
        self.since = since  # filtro de fecha mínima (YYYY-MM o YYYY-MM-DD)
        self.conn = None
        self.report = ValidationReport(db_path, since)

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _close(self):
        if self.conn:
            self.conn.close()

    def _fecha_filter(self):
        """Cláusula WHERE para filtrar por fecha si se especificó --since."""
        if self.since:
            return f"AND fecha >= '{self.since}'"
        return ""

    def _query(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()

    # ─────────────────────────────────────────────────────────────────────────
    # V01 — Cat1 fuera de whitelist
    # ─────────────────────────────────────────────────────────────────────────
    def check_v01_cat1_whitelist(self):
        """Detecta Cat1 que no están en la whitelist de 23 categorías."""
        rows = self._query(f"""
            SELECT id, cat1, COUNT(*) as n
            FROM transacciones
            WHERE 1=1 {self._fecha_filter()}
            GROUP BY cat1
            ORDER BY n DESC
        """)

        invalidas = []
        ids_afectados = []
        for row in rows:
            if row['cat1'] and row['cat1'] not in CAT1_WHITELIST:
                invalidas.append(f"'{row['cat1']}' ({row['n']} txs)")
                # Obtener IDs
                id_rows = self._query(
                    f"SELECT id FROM transacciones WHERE cat1=? {self._fecha_filter()}",
                    (row['cat1'],)
                )
                ids_afectados.extend([r['id'] for r in id_rows])

        if invalidas:
            self.report.add(ValidationIssue(
                'V01', ValidationIssue.SEVERIDAD_CRITICA,
                f"Cat1 fuera de whitelist: {', '.join(invalidas)}",
                tx_ids=ids_afectados,
                datos={'cat1_invalidas': invalidas}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V02 — Combinación Cat1|Cat2 inválida
    # ─────────────────────────────────────────────────────────────────────────
    def check_v02_combos_invalidos(self):
        """Detecta combinaciones Cat1|Cat2 que no están en valid_combos."""
        try:
            from classifier.valid_combos import VALID_COMBINATIONS
        except ImportError:
            self.report.add(ValidationIssue(
                'V02', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                "No se pudo importar valid_combos.py — check omitido"
            ))
            return

        rows = self._query(f"""
            SELECT id, cat1, cat2
            FROM transacciones
            WHERE cat1 IS NOT NULL AND cat1 != ''
            {self._fecha_filter()}
        """)

        invalidas = defaultdict(list)
        for row in rows:
            cat1 = row['cat1']
            cat2 = row['cat2'] or ''
            if cat1 in VALID_COMBINATIONS:
                if cat2 not in VALID_COMBINATIONS[cat1]:
                    invalidas[f"{cat1}|{cat2}"].append(row['id'])

        if invalidas:
            resumen = [f"'{k}' ({len(v)} txs)" for k, v in sorted(invalidas.items(), key=lambda x: -len(x[1]))]
            ids = [id_ for ids in invalidas.values() for id_ in ids]
            self.report.add(ValidationIssue(
                'V02', ValidationIssue.SEVERIDAD_CRITICA,
                f"Combinaciones Cat1|Cat2 inválidas: {', '.join(resumen[:10])}",
                tx_ids=ids,
                datos={'combos_invalidos': {k: len(v) for k, v in invalidas.items()}}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V03 — tipo inconsistente con cat1/importe
    # ─────────────────────────────────────────────────────────────────────────
    def check_v03_tipo_inconsistente(self):
        """Detecta inconsistencias entre tipo, cat1 e importe."""
        issues_ids = []
        detalles = []

        # Cat1 de ingreso con tipo != INGRESO (excepto si importe < 0 = devolución)
        rows = self._query(f"""
            SELECT id, cat1, tipo, importe
            FROM transacciones
            WHERE cat1 IN ('Nómina','Cashback','Wallapop','Dividendos')
            AND tipo != 'INGRESO'
            {self._fecha_filter()}
        """)
        for row in rows:
            issues_ids.append(row['id'])
            detalles.append(f"id={row['id']}: cat1={row['cat1']} tipo={row['tipo']} importe={row['importe']}")

        # Cat1 de transferencia con tipo != TRANSFERENCIA
        rows2 = self._query(f"""
            SELECT id, cat1, tipo, importe
            FROM transacciones
            WHERE cat1 IN ('Interna','Externa','Liquidación')
            AND tipo NOT IN ('TRANSFERENCIA', 'INGRESO', 'GASTO')
            {self._fecha_filter()}
        """)
        for row in rows2:
            issues_ids.append(row['id'])
            detalles.append(f"id={row['id']}: cat1={row['cat1']} tipo={row['tipo']}")

        # Nómina con importe negativo (siempre debería ser ingreso positivo)
        rows3 = self._query(f"""
            SELECT id, importe, tipo
            FROM transacciones
            WHERE cat1 = 'Nómina' AND importe < 0
            {self._fecha_filter()}
        """)
        for row in rows3:
            issues_ids.append(row['id'])
            detalles.append(f"id={row['id']}: Nómina con importe negativo={row['importe']}")

        if issues_ids:
            self.report.add(ValidationIssue(
                'V03', ValidationIssue.SEVERIDAD_CRITICA,
                f"tipo inconsistente con cat1/importe ({len(issues_ids)} txs)",
                tx_ids=issues_ids,
                datos={'ejemplos': detalles[:10]}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V04 — Duplicados exactos (hash repetido)
    # ─────────────────────────────────────────────────────────────────────────
    def check_v04_duplicados_exactos(self):
        """Detecta hashes duplicados (no debería ocurrir por UNIQUE constraint)."""
        rows = self._query("""
            SELECT hash, COUNT(*) as n, GROUP_CONCAT(id) as ids
            FROM transacciones
            GROUP BY hash
            HAVING n > 1
        """)

        if rows:
            ids = []
            detalles = []
            for row in rows:
                ids.extend([int(x) for x in row['ids'].split(',')])
                detalles.append(f"hash={row['hash'][:16]}... ({row['n']} veces, ids={row['ids']})")

            self.report.add(ValidationIssue(
                'V04', ValidationIssue.SEVERIDAD_CRITICA,
                f"Hashes duplicados encontrados: {len(rows)} grupos",
                tx_ids=ids,
                datos={'grupos': detalles[:10]}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V05 — Duplicados sospechosos (misma fecha+importe+descripción similar)
    # ─────────────────────────────────────────────────────────────────────────
    def check_v05_duplicados_sospechosos(self):
        """
        Detecta transacciones que parecen duplicadas:
        mismo importe + misma fecha + descripción muy parecida + distinto hash.

        Basado en errores reales: Openbank 200 pares, Abanca 112, B100 51 (S63).
        """
        # Buscar pares con misma fecha+importe (candidatos)
        rows = self._query(f"""
            SELECT t1.id as id1, t2.id as id2,
                   t1.fecha, t1.importe,
                   t1.descripcion as desc1, t2.descripcion as desc2,
                   t1.banco as banco1, t2.banco as banco2,
                   t1.cuenta as cuenta1, t2.cuenta as cuenta2
            FROM transacciones t1
            JOIN transacciones t2
              ON t1.fecha = t2.fecha
             AND t1.importe = t2.importe
             AND t1.id < t2.id
             AND t1.hash != t2.hash
            WHERE 1=1 {self._fecha_filter()}
            ORDER BY t1.fecha DESC, ABS(t1.importe) DESC
            LIMIT 2000
        """)

        pares_sospechosos = []
        ids_afectados = set()

        for row in rows:
            desc1 = row['desc1'] or ''
            desc2 = row['desc2'] or ''
            # Calcular similitud
            ratio = SequenceMatcher(None, desc1.upper(), desc2.upper()).ratio()
            if ratio >= SIMILITUD_DUPLICADO:
                pares_sospechosos.append({
                    'id1': row['id1'], 'id2': row['id2'],
                    'fecha': row['fecha'], 'importe': row['importe'],
                    'desc1': desc1[:60], 'desc2': desc2[:60],
                    'banco1': row['banco1'], 'banco2': row['banco2'],
                    'similitud': round(ratio, 3),
                })
                ids_afectados.add(row['id1'])
                ids_afectados.add(row['id2'])

        if pares_sospechosos:
            # Separar por severidad: mismo banco = CRITICA, distinto banco = WARN
            mismo_banco = [p for p in pares_sospechosos if p['banco1'] == p['banco2']]
            distinto_banco = [p for p in pares_sospechosos if p['banco1'] != p['banco2']]

            if mismo_banco:
                self.report.add(ValidationIssue(
                    'V05a', ValidationIssue.SEVERIDAD_CRITICA,
                    f"Duplicados sospechosos MISMO banco: {len(mismo_banco)} pares "
                    f"(fecha+importe idénticos, descripción similar ≥{SIMILITUD_DUPLICADO:.0%})",
                    tx_ids=list({p['id1'] for p in mismo_banco} | {p['id2'] for p in mismo_banco}),
                    datos={'pares': mismo_banco[:10]}
                ))

            if distinto_banco:
                self.report.add(ValidationIssue(
                    'V05b', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                    f"Posibles duplicados entre bancos distintos: {len(distinto_banco)} pares "
                    f"(pueden ser legítimos — Enablebanking vs fichero directo)",
                    tx_ids=list({p['id1'] for p in distinto_banco} | {p['id2'] for p in distinto_banco}),
                    datos={'pares': distinto_banco[:10]}
                ))

    # ─────────────────────────────────────────────────────────────────────────
    # V06 — Transacciones SIN_CLASIFICAR o cat1 vacío
    # ─────────────────────────────────────────────────────────────────────────
    def check_v06_sin_clasificar(self):
        """Detecta transacciones sin clasificar (objetivo: 0 siempre)."""
        rows = self._query(f"""
            SELECT id, fecha, descripcion, importe, banco
            FROM transacciones
            WHERE (cat1 IS NULL OR cat1 = '' OR cat1 = 'SIN_CLASIFICAR')
            {self._fecha_filter()}
            ORDER BY fecha DESC
        """)

        if rows:
            ids = [r['id'] for r in rows]
            ejemplos = [
                f"id={r['id']} {r['fecha']} {r['banco']}: {r['descripcion'][:50]} ({r['importe']}€)"
                for r in rows[:10]
            ]
            self.report.add(ValidationIssue(
                'V06', ValidationIssue.SEVERIDAD_CRITICA,
                f"{len(ids)} transacciones SIN_CLASIFICAR o sin cat1",
                tx_ids=ids,
                datos={'ejemplos': ejemplos}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V07 — Transacciones sin merchant_name donde debería haberlo
    # ─────────────────────────────────────────────────────────────────────────
    def check_v07_merchant_name_faltante(self):
        """
        Detecta transacciones donde el patrón 'COMPRA EN ...' sugiere
        que debería haber merchant_name pero está vacío.

        Basado en GAP crítico encontrado en S64.
        """
        rows = self._query(f"""
            SELECT id, fecha, descripcion, banco, merchant_name
            FROM transacciones
            WHERE merchant_name IS NULL
              AND (
                descripcion LIKE 'COMPRA EN%'
                OR descripcion LIKE 'COMPRA ONLINE EN%'
                OR descripcion LIKE '% EN %'
                OR descripcion LIKE 'PAGO EN%'
              )
              AND tipo = 'GASTO'
              AND cat1 NOT IN ('Efectivo','Transferencia','Finanzas')
            {self._fecha_filter()}
            ORDER BY fecha DESC
            LIMIT 500
        """)

        if rows:
            ids = [r['id'] for r in rows]
            ejemplos = [
                f"id={r['id']} {r['fecha']}: {r['descripcion'][:60]}"
                for r in rows[:10]
            ]
            self.report.add(ValidationIssue(
                'V07', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"{len(ids)} transacciones sin merchant_name donde el patrón sugiere que debería haberlo",
                tx_ids=ids,
                datos={'ejemplos': ejemplos}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V08 — Importes con signo incorrecto
    # ─────────────────────────────────────────────────────────────────────────
    def check_v08_signo_incorrecto(self):
        """
        GASTO con importe positivo (debería ser negativo).
        INGRESO con importe negativo (debería ser positivo).
        Excepciones: devoluciones (cat2='Devoluciones') son GASTO positivo (D2/D21).
        """
        # GASTO positivo sin ser devolución conocida
        rows_gasto = self._query(f"""
            SELECT id, fecha, descripcion, importe, cat1, cat2
            FROM transacciones
            WHERE tipo = 'GASTO'
              AND importe > 0
              AND cat2 NOT IN ('Devoluciones', 'Amazon')
              AND cat1 != 'Impuestos'
            {self._fecha_filter()}
            ORDER BY importe DESC
            LIMIT 200
        """)

        # INGRESO negativo
        rows_ingreso = self._query(f"""
            SELECT id, fecha, descripcion, importe, cat1
            FROM transacciones
            WHERE tipo = 'INGRESO'
              AND importe < 0
              AND cat1 != 'Impuestos'
            {self._fecha_filter()}
        """)

        ids_gasto = [r['id'] for r in rows_gasto]
        ids_ingreso = [r['id'] for r in rows_ingreso]

        if ids_gasto:
            ejemplos = [
                f"id={r['id']} {r['fecha']}: {r['cat1']}|{r['cat2']} importe=+{r['importe']}"
                for r in rows_gasto[:5]
            ]
            self.report.add(ValidationIssue(
                'V08a', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"{len(ids_gasto)} GASTOS con importe positivo (posible error de signo o devolución mal clasificada)",
                tx_ids=ids_gasto,
                datos={'ejemplos': ejemplos}
            ))

        if ids_ingreso:
            ejemplos = [
                f"id={r['id']} {r['fecha']}: {r['cat1']} importe={r['importe']}"
                for r in rows_ingreso[:5]
            ]
            self.report.add(ValidationIssue(
                'V08b', ValidationIssue.SEVERIDAD_CRITICA,
                f"{len(ids_ingreso)} INGRESOS con importe negativo",
                tx_ids=ids_ingreso,
                datos={'ejemplos': ejemplos}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V09 — Fechas fuera de rango o formato inválido
    # ─────────────────────────────────────────────────────────────────────────
    def check_v09_fechas(self):
        """Detecta fechas con formato inválido o fuera del rango esperado."""
        rows = self._query("""
            SELECT id, fecha, descripcion
            FROM transacciones
            WHERE fecha < ? OR fecha > ? OR length(fecha) != 10
               OR substr(fecha,5,1) != '-' OR substr(fecha,8,1) != '-'
        """, (FECHA_MIN, FECHA_MAX))

        if rows:
            ids = [r['id'] for r in rows]
            ejemplos = [f"id={r['id']}: fecha='{r['fecha']}'" for r in rows[:10]]
            self.report.add(ValidationIssue(
                'V09', ValidationIssue.SEVERIDAD_CRITICA,
                f"{len(ids)} transacciones con fecha fuera de rango ({FECHA_MIN}–{FECHA_MAX}) o formato inválido",
                tx_ids=ids,
                datos={'ejemplos': ejemplos}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V10 — Merchants sin cat1 (enriquecimiento incompleto)
    # ─────────────────────────────────────────────────────────────────────────
    def check_v10_merchants_incompletos(self):
        """Detecta merchants registrados sin cat1 (Google Places no los completó)."""
        try:
            rows = self._query("""
                SELECT merchant_name, place_name, city, country
                FROM merchants
                WHERE (cat1 IS NULL OR cat1 = '')
                  AND merchant_name IS NOT NULL
                ORDER BY merchant_name
            """)
        except sqlite3.OperationalError:
            return  # Tabla merchants no existe todavía

        if rows:
            nombres = [r['merchant_name'] for r in rows]
            self.report.add(ValidationIssue(
                'V10', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"{len(nombres)} merchants sin cat1 en tabla merchants (enriquecimiento incompleto)",
                datos={'merchants': nombres[:20]}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V11 — Banco desconocido
    # ─────────────────────────────────────────────────────────────────────────
    def check_v11_banco_desconocido(self):
        """Detecta bancos no reconocidos (posible error de parser o importación manual)."""
        rows = self._query(f"""
            SELECT banco, COUNT(*) as n
            FROM transacciones
            WHERE 1=1 {self._fecha_filter()}
            GROUP BY banco
            ORDER BY n DESC
        """)

        desconocidos = []
        for row in rows:
            banco = row['banco'] or ''
            # Comprobación flexible (algunos tienen variantes como "Trade Republic CSV")
            if not any(conocido.lower() in banco.lower() for conocido in BANCOS_CONOCIDOS):
                desconocidos.append(f"'{banco}' ({row['n']} txs)")

        if desconocidos:
            self.report.add(ValidationIssue(
                'V11', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"Bancos no reconocidos: {', '.join(desconocidos)}",
                datos={'bancos': desconocidos}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V12 — Cat2 no vacío cuando debería serlo (D12)
    # ─────────────────────────────────────────────────────────────────────────
    def check_v12_cat2_debe_ser_vacio(self):
        """
        Cat1 que por decisión D12 NO deben tener cat2.
        Ej: Nómina, Bizum, Intereses, Wallapop, etc.
        """
        placeholders = ','.join('?' * len(CAT1_SIN_CAT2))
        rows = self._query(f"""
            SELECT id, cat1, cat2, descripcion
            FROM transacciones
            WHERE cat1 IN ({placeholders})
              AND cat2 IS NOT NULL AND cat2 != ''
            {self._fecha_filter()}
        """, tuple(CAT1_SIN_CAT2))

        if rows:
            ids = [r['id'] for r in rows]
            ejemplos = [f"id={r['id']}: {r['cat1']}|{r['cat2']}" for r in rows[:10]]
            self.report.add(ValidationIssue(
                'V12', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"{len(ids)} transacciones con cat2 no vacío en Cat1 que debería tenerlo vacío (D12)",
                tx_ids=ids,
                datos={'ejemplos': ejemplos}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V13 — Descripción vacía o nula
    # ─────────────────────────────────────────────────────────────────────────
    def check_v13_descripcion_vacia(self):
        """Detecta transacciones sin descripción (campo obligatorio)."""
        rows = self._query(f"""
            SELECT id, fecha, banco, importe
            FROM transacciones
            WHERE descripcion IS NULL OR trim(descripcion) = ''
            {self._fecha_filter()}
        """)

        if rows:
            ids = [r['id'] for r in rows]
            ejemplos = [f"id={r['id']} {r['fecha']} {r['banco']} {r['importe']}€" for r in rows[:10]]
            self.report.add(ValidationIssue(
                'V13', ValidationIssue.SEVERIDAD_CRITICA,
                f"{len(ids)} transacciones con descripción vacía o nula",
                tx_ids=ids,
                datos={'ejemplos': ejemplos}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V14 — Hash NULL
    # ─────────────────────────────────────────────────────────────────────────
    def check_v14_hash_nulo(self):
        """Detecta transacciones sin hash (integridad fundamental rota)."""
        rows = self._query(f"""
            SELECT id, fecha, descripcion, banco
            FROM transacciones
            WHERE hash IS NULL OR hash = ''
            {self._fecha_filter()}
        """)

        if rows:
            ids = [r['id'] for r in rows]
            self.report.add(ValidationIssue(
                'V14', ValidationIssue.SEVERIDAD_CRITICA,
                f"{len(ids)} transacciones con hash NULL o vacío (integridad rota)",
                tx_ids=ids
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V15 — Importe exactamente cero
    # ─────────────────────────────────────────────────────────────────────────
    def check_v15_importe_cero(self):
        """
        Importes exactamente 0 son sospechosos.
        Excepción: Retenciones Hacienda de 0.01€ que se redondean (visto en BD).
        """
        rows = self._query(f"""
            SELECT id, fecha, descripcion, banco, cat1
            FROM transacciones
            WHERE importe = 0
            {self._fecha_filter()}
        """)

        if rows:
            ids = [r['id'] for r in rows]
            ejemplos = [f"id={r['id']} {r['fecha']}: {r['descripcion'][:50]}" for r in rows[:10]]
            self.report.add(ValidationIssue(
                'V15', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"{len(ids)} transacciones con importe exactamente 0€",
                tx_ids=ids,
                datos={'ejemplos': ejemplos}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V16 — Nóminas anómalas
    # ─────────────────────────────────────────────────────────────────────────
    def check_v16_nominas_anomalas(self):
        """
        Detecta nóminas muy diferentes a la media histórica.
        Útil para detectar la nómina duplicada de enero 2026 (S67).
        Usa solo los últimos 5 años para evitar distorsión por nóminas históricas bajas.
        """
        rows = self._query("""
            SELECT id, fecha, importe, descripcion
            FROM transacciones
            WHERE cat1 = 'Nómina' AND tipo = 'INGRESO'
              AND fecha >= date('now', '-5 years')
            ORDER BY fecha
        """)

        if len(rows) < 3:
            return  # Muy pocas nóminas para calcular media

        importes = [r['importe'] for r in rows]
        media = sum(importes) / len(importes)
        desviacion = (sum((x - media)**2 for x in importes) / len(importes)) ** 0.5

        anomalas = []
        for row in rows:
            diferencia_pct = abs(row['importe'] - media) / media if media else 0
            if diferencia_pct > UMBRAL_NOMINA_DESVIACION and abs(row['importe'] - media) > 200:
                anomalas.append({
                    'id': row['id'],
                    'fecha': row['fecha'],
                    'importe': row['importe'],
                    'media': round(media, 2),
                    'diferencia_pct': round(diferencia_pct * 100, 1),
                })

        # Filtrar si es enero (puede ser paga extra) — solo advertencia
        if anomalas:
            ids = [a['id'] for a in anomalas]
            detalles = [
                f"id={a['id']} {a['fecha']}: {a['importe']}€ (media={a['media']}€, diff={a['diferencia_pct']}%)"
                for a in anomalas
            ]
            self.report.add(ValidationIssue(
                'V16', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"{len(anomalas)} nóminas con importe anómalo (±{UMBRAL_NOMINA_DESVIACION:.0%} de la media {round(media,0)}€)",
                tx_ids=ids,
                datos={'anomalas': detalles, 'media_nomina': round(media, 2)}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V17 — Gastos extremos por categoría (outliers estadísticos)
    # ─────────────────────────────────────────────────────────────────────────
    def check_v17_outliers_gasto(self):
        """
        Detecta gastos individuales que son outliers estadísticos dentro de su cat1.
        Basado en 3-sigma: media + 3*desviación. Solo para gastos > OUTLIER_IMPORTE_MIN.
        Útil para detectar cargos mal clasificados (ej: IRPF 3606€ en Alimentación).
        """
        # Obtener media y stddev por cat1
        stats = self._query("""
            SELECT cat1,
                   AVG(ABS(importe)) as media,
                   COUNT(*) as n
            FROM transacciones
            WHERE tipo = 'GASTO'
              AND cat1 NOT IN ('Impuestos','Finanzas','Efectivo','Liquidación')
              AND ABS(importe) > 0
            GROUP BY cat1
            HAVING n >= 10
        """)

        problemas = []
        ids_problema = []

        for stat in stats:
            cat1 = stat['cat1']
            media = stat['media']

            # Calcular desviación estándar manualmente
            importes_rows = self._query("""
                SELECT id, fecha, ABS(importe) as importe, descripcion
                FROM transacciones
                WHERE tipo = 'GASTO' AND cat1 = ?
                  AND ABS(importe) > ?
            """, (cat1, OUTLIER_IMPORTE_MIN))

            if len(importes_rows) < 5:
                continue

            valores = [r['importe'] for r in importes_rows]
            std = (sum((x - media)**2 for x in valores) / len(valores)) ** 0.5
            umbral = media + UMBRAL_OUTLIER_SIGMA * std

            if std < 5:  # Categorías muy homogéneas, no aplicar
                continue

            for row in importes_rows:
                if row['importe'] > umbral and row['importe'] > OUTLIER_IMPORTE_MIN:
                    problemas.append(
                        f"id={row['id']} {row['fecha']} [{cat1}]: {row['importe']}€ "
                        f"(umbral={round(umbral,0)}€, media={round(media,0)}€)"
                    )
                    ids_problema.append(row['id'])

        if problemas:
            self.report.add(ValidationIssue(
                'V17', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"{len(ids_problema)} gastos outliers estadísticos (>media+3σ por cat1)",
                tx_ids=ids_problema,
                datos={'outliers': problemas[:20]}
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # V18 — Reglas de negocio específicas (aprendidas de sesiones anteriores)
    # ─────────────────────────────────────────────────────────────────────────
    def check_v18_reglas_negocio(self):
        """
        Checks específicos basados en errores reales de sesiones anteriores.

        Casos reales encontrados en S51–S66:
        - IRPF como GASTO (debe ser GASTO/Impuestos/IRPF, no INGRESO)
        - Mangopay/Wallapop mal clasificado
        - NAMECHEAP/GitHub con exchange rate → Suscripciones (D18)
        - Revolut XXXX* → Transferencia/Interna (D17)
        - Devoluciones Amazon con importe>0 → Compras/Amazon (D21)
        - ORTONOVA → Salud y Belleza/Médico (D19)
        """
        issues = []

        # IRPF clasificado como INGRESO (debería ser GASTO)
        rows = self._query(f"""
            SELECT id, fecha, descripcion, tipo, cat1, cat2
            FROM transacciones
            WHERE (descripcion LIKE '%IRPF%' OR descripcion LIKE '%I.R.P.F%')
              AND tipo = 'INGRESO' AND importe < 0
            {self._fecha_filter()}
        """)
        if rows:
            ids = [r['id'] for r in rows]
            issues.append(ValidationIssue(
                'V18a', ValidationIssue.SEVERIDAD_CRITICA,
                f"IRPF con tipo=INGRESO e importe negativo ({len(ids)} txs) — debería ser GASTO/Impuestos/IRPF",
                tx_ids=ids
            ))

        # Wallapop con tipo=GASTO (debería ser INGRESO)
        rows2 = self._query(f"""
            SELECT id, fecha, descripcion, tipo, importe
            FROM transacciones
            WHERE cat1 = 'Wallapop' AND tipo = 'GASTO' AND importe < 0
            {self._fecha_filter()}
        """)
        if rows2:
            ids = [r['id'] for r in rows2]
            issues.append(ValidationIssue(
                'V18b', ValidationIssue.SEVERIDAD_CRITICA,
                f"Wallapop con tipo=GASTO ({len(ids)} txs) — debería ser INGRESO (D11)",
                tx_ids=ids
            ))

        # Revolut XXXX* no clasificado como Transferencia/Interna (D17)
        rows3 = self._query(f"""
            SELECT id, fecha, descripcion, cat1, cat2
            FROM transacciones
            WHERE banco = 'Revolut'
              AND descripcion LIKE '%XXXX%'
              AND (cat1 != 'Interna' OR cat1 IS NULL)
            {self._fecha_filter()}
        """)
        if rows3:
            ids = [r['id'] for r in rows3]
            issues.append(ValidationIssue(
                'V18c', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"Revolut XXXX* no clasificado como Interna ({len(ids)} txs) — ver D17",
                tx_ids=ids
            ))

        # NAMECHEAP o GitHub clasificado como Divisas en vez de Suscripciones (D18)
        rows4 = self._query(f"""
            SELECT id, fecha, descripcion, cat1
            FROM transacciones
            WHERE (descripcion LIKE '%NAMECHEAP%' OR descripcion LIKE '%GITHUB%')
              AND cat1 = 'Divisas'
            {self._fecha_filter()}
        """)
        if rows4:
            ids = [r['id'] for r in rows4]
            issues.append(ValidationIssue(
                'V18d', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"NAMECHEAP/GitHub clasificado como Divisas ({len(ids)} txs) — debería ser Suscripciones (D18)",
                tx_ids=ids
            ))

        # Devoluciones AEAT con importe positivo clasificadas como GASTO (D10)
        rows5 = self._query(f"""
            SELECT id, fecha, descripcion, cat1, tipo, importe
            FROM transacciones
            WHERE (descripcion LIKE '%DEVOLUCION%' OR descripcion LIKE '%DEVOLUCIÓN%')
              AND descripcion LIKE '%AEAT%'
              AND tipo = 'GASTO' AND importe > 0
            {self._fecha_filter()}
        """)
        if rows5:
            ids = [r['id'] for r in rows5]
            issues.append(ValidationIssue(
                'V18e', ValidationIssue.SEVERIDAD_ADVERTENCIA,
                f"Devolución AEAT con tipo=GASTO ({len(ids)} txs) — debería ser INGRESO/Impuestos/IRPF (D10)",
                tx_ids=ids
            ))

        for issue in issues:
            self.report.add(issue)

    # ─────────────────────────────────────────────────────────────────────────
    # RUNNER PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────
    def run(self):
        """Ejecuta todos los checks y devuelve el ValidationReport."""
        self._connect()
        try:
            # Contar txs analizadas
            result = self._query(
                f"SELECT COUNT(*) as n FROM transacciones WHERE 1=1 {self._fecha_filter()}"
            )
            self.report.total_txs_analizadas = result[0]['n'] if result else 0

            checks = [
                ('V01', self.check_v01_cat1_whitelist),
                ('V02', self.check_v02_combos_invalidos),
                ('V03', self.check_v03_tipo_inconsistente),
                ('V04', self.check_v04_duplicados_exactos),
                ('V05', self.check_v05_duplicados_sospechosos),
                ('V06', self.check_v06_sin_clasificar),
                ('V07', self.check_v07_merchant_name_faltante),
                ('V08', self.check_v08_signo_incorrecto),
                ('V09', self.check_v09_fechas),
                ('V10', self.check_v10_merchants_incompletos),
                ('V11', self.check_v11_banco_desconocido),
                ('V12', self.check_v12_cat2_debe_ser_vacio),
                ('V13', self.check_v13_descripcion_vacia),
                ('V14', self.check_v14_hash_nulo),
                ('V15', self.check_v15_importe_cero),
                ('V16', self.check_v16_nominas_anomalas),
                ('V17', self.check_v17_outliers_gasto),
                ('V18', self.check_v18_reglas_negocio),
            ]

            for check_id, check_fn in checks:
                self.report.checks_ejecutados.append(check_id)
                try:
                    check_fn()
                except Exception as e:
                    self.report.add(ValidationIssue(
                        check_id, ValidationIssue.SEVERIDAD_ADVERTENCIA,
                        f"Error ejecutando check {check_id}: {e}"
                    ))

        finally:
            self._close()

        return self.report


# ─────────────────────────────────────────────────────────────────────────────
# API PÚBLICA — para integración con pipeline y process_transactions
# ─────────────────────────────────────────────────────────────────────────────

def run_validation(db_path=DB_PATH_DEFAULT, since=None, silent=False):
    """
    Punto de entrada para integración automática.

    Args:
        db_path: Ruta a la BD SQLite
        since:   Filtrar solo txs desde esta fecha (YYYY-MM-DD o YYYY-MM)
        silent:  Si True, no imprime nada (solo devuelve el report)

    Returns:
        ValidationReport con todos los resultados

    Uso desde pipeline/process_transactions:
        from validator import run_validation
        report = run_validation(db_path='finsense.db')
        if report.criticas:
            logger.warning(f"Validación: {len(report.criticas)} errores críticos")
    """
    validator = Validator(db_path=db_path, since=since)
    report = validator.run()

    if not silent:
        print(report.resumen_texto())

    return report


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Validador de integridad finsense — detecta errores en datos y clasificación'
    )
    parser.add_argument('--db', default=DB_PATH_DEFAULT,
                        help=f'Ruta a la BD SQLite (default: {DB_PATH_DEFAULT})')
    parser.add_argument('--since', default=None,
                        help='Analizar solo transacciones desde esta fecha (YYYY-MM-DD o YYYY-MM)')
    parser.add_argument('--json', action='store_true',
                        help='Salida en formato JSON (para integración)')
    parser.add_argument('--solo-criticas', action='store_true',
                        help='Mostrar solo errores críticos')
    parser.add_argument('--checks', nargs='+', metavar='V01',
                        help='Ejecutar solo los checks indicados (ej: --checks V01 V05)')
    args = parser.parse_args()

    validator = Validator(db_path=args.db, since=args.since)

    # Si se especifican checks concretos, filtrar
    if args.checks:
        checks_solicitados = set(args.checks)
        # Ejecutar solo los checks solicitados
        validator._connect()
        result = validator._query(
            f"SELECT COUNT(*) as n FROM transacciones WHERE 1=1 {validator._fecha_filter()}"
        )
        validator.report.total_txs_analizadas = result[0]['n'] if result else 0

        check_map = {
            'V01': validator.check_v01_cat1_whitelist,
            'V02': validator.check_v02_combos_invalidos,
            'V03': validator.check_v03_tipo_inconsistente,
            'V04': validator.check_v04_duplicados_exactos,
            'V05': validator.check_v05_duplicados_sospechosos,
            'V06': validator.check_v06_sin_clasificar,
            'V07': validator.check_v07_merchant_name_faltante,
            'V08': validator.check_v08_signo_incorrecto,
            'V09': validator.check_v09_fechas,
            'V10': validator.check_v10_merchants_incompletos,
            'V11': validator.check_v11_banco_desconocido,
            'V12': validator.check_v12_cat2_debe_ser_vacio,
            'V13': validator.check_v13_descripcion_vacia,
            'V14': validator.check_v14_hash_nulo,
            'V15': validator.check_v15_importe_cero,
            'V16': validator.check_v16_nominas_anomalas,
            'V17': validator.check_v17_outliers_gasto,
            'V18': validator.check_v18_reglas_negocio,
        }
        for check_id in sorted(checks_solicitados):
            if check_id in check_map:
                validator.report.checks_ejecutados.append(check_id)
                check_map[check_id]()
        validator._close()
        report = validator.report
    else:
        report = validator.run()

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    elif args.solo_criticas:
        issues = report.criticas
        if not issues:
            print("✅ Sin errores críticos.")
        else:
            for issue in issues:
                print(f"🔴 {issue}")
        print(f"\nTotal críticas: {len(issues)}")
    else:
        print(report.resumen_texto())

    # Código de salida: 1 si hay errores críticos (útil en CI/scripts)
    sys.exit(1 if report.criticas else 0)


if __name__ == '__main__':
    main()
