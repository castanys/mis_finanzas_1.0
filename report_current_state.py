#!/usr/bin/env python3
"""
Reporta el estado actual de la BBDD después del reprocesamiento.
"""
import sqlite3

def main():
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("📊 REPORTE DE ESTADO ACTUAL")
    print("=" * 80)

    # 1. Cambios por las 3 reglas nuevas
    print("\n1️⃣  CAMBIOS POR LAS 3 REGLAS NUEVAS:")
    print("─" * 80)

    # REGLA 1: B100 Health/Save
    cursor.execute("""
        SELECT COUNT(*)
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
    regla1_count = cursor.fetchone()[0]
    print(f"   REGLA 1 (B100 Health/Save):        {regla1_count:4d} transacciones")

    # REGLA 2: Amazon refunds
    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE importe > 0
          AND cat2 = 'Amazon'
          AND tipo = 'GASTO'
    """)
    regla2_count = cursor.fetchone()[0]
    print(f"   REGLA 2 (Amazon refunds):          {regla2_count:4d} transacciones")

    # REGLA 3: Devoluciones generales (importe+ con Cat1 de gasto, excluyendo Amazon)
    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE importe > 0
          AND tipo = 'GASTO'
          AND cat1 IN ('Compras', 'Alimentación', 'Restauración', 'Transporte',
                       'Vivienda', 'Salud y Belleza', 'Ocio y Cultura', 'Ropa y Calzado',
                       'Educación', 'Recibos', 'Finanzas', 'Suscripciones', 'Tecnología',
                       'Mascotas', 'Hogar', 'Deporte', 'Otros')
          AND cat2 != 'Amazon'
    """)
    regla3_count = cursor.fetchone()[0]
    print(f"   REGLA 3 (Devoluciones generales):  {regla3_count:4d} transacciones")

    total_reglas = regla1_count + regla2_count + regla3_count
    print(f"\n   TOTAL (3 reglas):                  {total_reglas:4d} transacciones")

    # 2. Cambios por sincronización con maestro
    print("\n2️⃣  CAMBIOS POR SINCRONIZACIÓN CON MAESTRO:")
    print("─" * 80)
    print(f"   Total cambios:                     2,549 transacciones")
    print(f"   Cambios por 3 reglas:               -{total_reglas:4d} transacciones")
    otros_cambios = 2549 - total_reglas
    print(f"   Cambios por sincronización:        {otros_cambios:5d} transacciones")

    # Desglose de cambios por sincronización
    print("\n   Desglose de sincronización:")
    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE cat2 = 'Otros'
          AND cat1 IN ('Recibos', 'Restauración', 'Compras', 'Ropa y Calzado')
    """)
    otros_count = cursor.fetchone()[0]
    print(f"      • Cat2 → 'Otros':                {otros_count:5d} transacciones")

    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE cat2 IN ('Ajustes', 'Regularización')
    """)
    ajustes_count = cursor.fetchone()[0]
    print(f"      • Cat2 → 'Ajustes/Regularización': {ajustes_count:5d} transacciones")

    # 3. Google Places enriquecimientos
    print("\n3️⃣  ENRIQUECIMIENTOS DE GOOGLE PLACES:")
    print("─" * 80)

    # Verificar si hay columna merchant_name o merchant_category
    cursor.execute("PRAGMA table_info(transacciones)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'merchant_category' in columns:
        cursor.execute("""
            SELECT COUNT(*)
            FROM transacciones
            WHERE merchant_category IS NOT NULL AND merchant_category != ''
        """)
        enriched_count = cursor.fetchone()[0]
        print(f"   Cat2 enriquecidos con Google:      {enriched_count:5d} transacciones")

        if enriched_count > 0:
            print("   ✅ Los enriquecimientos de Google Places se MANTIENEN")
        else:
            print("   ⚠️  No se encontraron enriquecimientos de Google Places")
    else:
        # Verificar por Cat2 específicos que vendrían de Google Places
        cursor.execute("""
            SELECT COUNT(DISTINCT cat2)
            FROM transacciones
            WHERE cat2 IS NOT NULL AND cat2 != ''
              AND cat2 NOT IN ('', 'Otros', 'Ajustes', 'Regularización')
        """)
        unique_cat2 = cursor.fetchone()[0]
        print(f"   Cat2 únicos (no genéricos):        {unique_cat2:5d} valores")
        print("   ℹ️  No hay columna merchant_category en la BBDD")
        print("   ℹ️  Los enriquecimientos de Google Places NO se guardaron en columnas separadas")

    # 4. Estadísticas generales
    print("\n4️⃣  ESTADÍSTICAS GENERALES:")
    print("─" * 80)

    cursor.execute("SELECT COUNT(*) FROM transacciones")
    total = cursor.fetchone()[0]
    print(f"   Total transacciones:               {total:5,}")

    cursor.execute("""
        SELECT tipo, COUNT(*)
        FROM transacciones
        GROUP BY tipo
        ORDER BY COUNT(*) DESC
    """)
    print("\n   Distribución por Tipo:")
    for tipo, count in cursor.fetchall():
        pct = 100.0 * count / total
        tipo_str = tipo if tipo else "(vacío)"
        print(f"      {tipo_str:20s} {count:6,} ({pct:5.2f}%)")

    print("\n" + "=" * 80 + "\n")

    conn.close()

if __name__ == '__main__':
    main()
