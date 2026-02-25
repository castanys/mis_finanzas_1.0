#!/usr/bin/env python3
"""
Analiza los cambios realizados por el reprocesamiento.
Identifica qué cambios fueron por cada regla.
"""
import sqlite3
from classifier import Classifier
from classifier.normalization import normalize_description

def classify_change_reason(old_tipo, old_cat1, old_cat2, new_tipo, new_cat1, new_cat2,
                          descripcion, banco, importe):
    """Determina la razón del cambio."""

    desc_upper = descripcion.upper()

    # REGLA 1: B100 Health/Save/Traspaso
    if banco == "B100":
        b100_keywords = ["HEALTH", "SAVE", "TRASPASO", "AHORRO PARA HUCHA", "MOVE TO SAVE"]
        if any(kw in desc_upper for kw in b100_keywords):
            if new_cat1 == "Interna" and old_cat1 != "Interna":
                return "REGLA_1_B100"

    # REGLA 2: Amazon refunds
    amazon_keywords = ["AMAZON", "AMZN"]
    refund_keywords = ["DEVOLUCIÓN", "DEVOLUCION", "REEMBOLSO", "REFUND", "RETURN"]
    if importe > 0:
        if any(kw in desc_upper for kw in amazon_keywords):
            if new_tipo == "GASTO" and old_tipo != "GASTO":
                return "REGLA_2_AMAZON"

        # REGLA 3: Devoluciones generales (importe+ con Cat1 de gasto)
        categorias_gasto = [
            "Compras", "Alimentación", "Restauración", "Transporte", "Vivienda",
            "Salud y Belleza", "Ocio y Cultura", "Ropa y Calzado", "Educación",
            "Recibos", "Finanzas", "Suscripciones", "Tecnología", "Mascotas",
            "Hogar", "Deporte", "Otros"
        ]
        if new_cat1 in categorias_gasto:
            if new_tipo == "GASTO" and old_tipo == "INGRESO":
                return "REGLA_3_DEVOLUCION"

    # OTROS: cambios no relacionados con las 3 reglas
    return "OTROS"

def main():
    # Conectar a la BBDD
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Cargar clasificador actual
    print("🔧 Inicializando clasificador...")
    classifier = Classifier('Validación_Categorias_Finsense_04020206_5.csv')

    # Simular clasificación antigua (sin las reglas nuevas)
    # Para esto, necesitamos reclasificar y comparar
    print("\n📊 Analizando cambios en transacciones...\n")

    # Leer todas las transacciones
    cursor.execute("""
        SELECT id, fecha, importe, descripcion, banco, tipo, cat1, cat2
        FROM transacciones
        ORDER BY id
    """)

    transactions = cursor.fetchall()

    # Contadores por regla
    cambios_por_regla = {
        'REGLA_1_B100': [],
        'REGLA_2_AMAZON': [],
        'REGLA_3_DEVOLUCION': [],
        'OTROS': []
    }

    # Para tracking: guardar clasificación antigua simulada
    # Vamos a hacer un análisis retrospectivo basado en los cambios

    # Método alternativo: analizar directamente qué transacciones cambiaron
    # comparando características conocidas

    # B100 Health/Save
    cursor.execute("""
        SELECT id, fecha, importe, descripcion, banco, tipo, cat1, cat2
        FROM transacciones
        WHERE banco = 'B100'
          AND (descripcion LIKE '%Health%'
               OR descripcion LIKE '%Save%'
               OR descripcion LIKE '%Traspaso%'
               OR descripcion LIKE '%AHORRO PARA HUCHA%'
               OR descripcion LIKE '%Move to save%')
          AND tipo = 'TRANSFERENCIA'
          AND cat1 = 'Interna'
    """)

    b100_transactions = cursor.fetchall()
    cambios_por_regla['REGLA_1_B100'] = b100_transactions

    # Amazon con importe positivo clasificadas como GASTO
    cursor.execute("""
        SELECT id, fecha, importe, descripcion, banco, tipo, cat1, cat2
        FROM transacciones
        WHERE importe > 0
          AND cat2 = 'Amazon'
          AND tipo = 'GASTO'
    """)

    amazon_refunds = cursor.fetchall()
    cambios_por_regla['REGLA_2_AMAZON'] = amazon_refunds

    # Devoluciones generales: importe+ con Cat1 de gasto, tipo GASTO
    # Excluir Amazon (ya contadas)
    cursor.execute("""
        SELECT id, fecha, importe, descripcion, banco, tipo, cat1, cat2
        FROM transacciones
        WHERE importe > 0
          AND tipo = 'GASTO'
          AND cat1 IN ('Compras', 'Alimentación', 'Restauración', 'Transporte',
                       'Vivienda', 'Salud y Belleza', 'Ocio y Cultura', 'Ropa y Calzado',
                       'Educación', 'Recibos', 'Finanzas', 'Suscripciones', 'Tecnología',
                       'Mascotas', 'Hogar', 'Deporte', 'Otros')
          AND cat2 != 'Amazon'
    """)

    devolucion_transactions = cursor.fetchall()
    cambios_por_regla['REGLA_3_DEVOLUCION'] = devolucion_transactions

    # Imprimir resumen
    print("=" * 80)
    print("📊 DESGLOSE DE TRANSACCIONES POR REGLA")
    print("=" * 80)

    print(f"\n1️⃣  REGLA 1 (B100 Health/Save): {len(cambios_por_regla['REGLA_1_B100']):,} transacciones")
    print(f"2️⃣  REGLA 2 (Amazon refunds): {len(cambios_por_regla['REGLA_2_AMAZON']):,} transacciones")
    print(f"3️⃣  REGLA 3 (Devoluciones generales): {len(cambios_por_regla['REGLA_3_DEVOLUCION']):,} transacciones")

    total_reglas = (len(cambios_por_regla['REGLA_1_B100']) +
                    len(cambios_por_regla['REGLA_2_AMAZON']) +
                    len(cambios_por_regla['REGLA_3_DEVOLUCION']))

    print(f"\n   Total explicado por reglas: {total_reglas:,}")
    print(f"   ⚠️  Diferencia (cambios por OTROS motivos): {2549 - total_reglas:,}")

    # Ejemplos de REGLA 3 que NO sean Amazon
    print("\n" + "=" * 80)
    print("🔍 EJEMPLOS DE REGLA 3 (Devoluciones NO-Amazon)")
    print("=" * 80)
    print("\nPrimeros 10 ejemplos de transacciones con importe+ clasificadas como GASTO:")
    print("─" * 80)

    for i, (tx_id, fecha, importe, descripcion, banco, tipo, cat1, cat2) in enumerate(devolucion_transactions[:10], 1):
        print(f"\n{i}. {fecha} | {banco:15s} | €{importe:>8.2f}")
        print(f"   {descripcion[:70]}")
        print(f"   → {tipo}/{cat1}/{cat2 or ''}")

    # Analizar posibles falsos positivos
    print("\n" + "=" * 80)
    print("⚠️  ANÁLISIS DE POSIBLES FALSOS POSITIVOS")
    print("=" * 80)

    # Buscar patrones sospechosos en REGLA 3
    sospechosos = []

    for tx_id, fecha, importe, descripcion, banco, tipo, cat1, cat2 in devolucion_transactions:
        desc_upper = descripcion.upper()

        # Patrones que podrían ser falsos positivos
        if any(kw in desc_upper for kw in ["WALLAPOP", "VINTED", "BONIFICACION", "BONIFICACIÓN",
                                             "INTERES", "INTERÉS", "DIVIDENDO", "ABONO PENSION",
                                             "SALARIO", "NOMINA", "NÓMINA"]):
            sospechosos.append((tx_id, fecha, importe, descripcion, banco, tipo, cat1, cat2))

    if sospechosos:
        print(f"\n🚨 Encontrados {len(sospechosos)} posibles FALSOS POSITIVOS:")
        print("   (Estos deberían ser INGRESO, no GASTO)\n")
        print("─" * 80)

        for i, (tx_id, fecha, importe, descripcion, banco, tipo, cat1, cat2) in enumerate(sospechosos[:15], 1):
            print(f"{i}. {fecha} | €{importe:>8.2f} | {descripcion[:60]}")
            print(f"   → {tipo}/{cat1}/{cat2 or ''}")
            print()
    else:
        print("\n✅ No se encontraron falsos positivos obvios en los primeros análisis")

    print("=" * 80 + "\n")

    conn.close()

if __name__ == '__main__':
    main()
