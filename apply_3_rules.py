#!/usr/bin/env python3
"""
Aplica las 3 reglas nuevas mediante SQL UPDATE directo.
NO reprocesa, solo actualiza las transacciones afectadas.
"""
import sqlite3

def main():
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("🔧 APLICANDO LAS 3 REGLAS NUEVAS (SQL UPDATE)")
    print("=" * 80)

    # REGLA 1: B100 Health/Save/Traspaso → TRANSFERENCIA/Interna
    print("\n1️⃣  REGLA 1: B100 Health/Save/Traspaso → TRANSFERENCIA/Interna")
    print("─" * 80)

    cursor.execute("""
        SELECT id, fecha, importe, descripcion, tipo, cat1, cat2
        FROM transacciones
        WHERE banco = 'B100'
          AND (descripcion LIKE '%Health%'
               OR descripcion LIKE '%Save%'
               OR descripcion LIKE '%Traspaso%'
               OR descripcion LIKE '%AHORRO PARA HUCHA%'
               OR descripcion LIKE '%Move to save%')
    """)

    regla1_rows = cursor.fetchall()
    print(f"   Encontradas: {len(regla1_rows)} transacciones")

    if regla1_rows:
        print(f"\n   Ejemplos antes del UPDATE:")
        for i, (tx_id, fecha, importe, desc, tipo, cat1, cat2) in enumerate(regla1_rows[:3], 1):
            print(f"   {i}. {fecha} | €{importe:>8.2f} | {tipo:15s}/{cat1:15s} | {desc[:40]}")

        # UPDATE
        cursor.execute("""
            UPDATE transacciones
            SET tipo = 'TRANSFERENCIA',
                cat1 = 'Interna',
                cat2 = ''
            WHERE banco = 'B100'
              AND (descripcion LIKE '%Health%'
                   OR descripcion LIKE '%Save%'
                   OR descripcion LIKE '%Traspaso%'
                   OR descripcion LIKE '%AHORRO PARA HUCHA%'
                   OR descripcion LIKE '%Move to save%')
        """)

        updated1 = cursor.rowcount
        print(f"\n   ✅ Actualizadas: {updated1} transacciones")
    else:
        print(f"   ℹ️  No hay transacciones que actualizar")
        updated1 = 0

    # REGLA 2: Amazon con importe positivo → GASTO
    print("\n2️⃣  REGLA 2: Amazon con importe positivo → GASTO")
    print("─" * 80)

    cursor.execute("""
        SELECT id, fecha, importe, descripcion, tipo, cat1, cat2
        FROM transacciones
        WHERE importe > 0
          AND cat2 = 'Amazon'
          AND tipo != 'GASTO'
    """)

    regla2_rows = cursor.fetchall()
    print(f"   Encontradas: {len(regla2_rows)} transacciones")

    if regla2_rows:
        print(f"\n   Ejemplos antes del UPDATE:")
        for i, (tx_id, fecha, importe, desc, tipo, cat1, cat2) in enumerate(regla2_rows[:3], 1):
            print(f"   {i}. {fecha} | €{importe:>8.2f} | {tipo:15s}/{cat1}/{cat2} | {desc[:40]}")

        # UPDATE
        cursor.execute("""
            UPDATE transacciones
            SET tipo = 'GASTO'
            WHERE importe > 0
              AND cat2 = 'Amazon'
              AND tipo != 'GASTO'
        """)

        updated2 = cursor.rowcount
        print(f"\n   ✅ Actualizadas: {updated2} transacciones")
    else:
        print(f"   ℹ️  No hay transacciones que actualizar")
        updated2 = 0

    # REGLA 3: Devoluciones explícitas con importe positivo → GASTO
    # Solo si la descripción contiene keywords de devolución Y cat1 es de gasto (excluyendo Finanzas)
    print("\n3️⃣  REGLA 3: Devoluciones explícitas (importe+) → GASTO")
    print("─" * 80)

    cursor.execute("""
        SELECT id, fecha, importe, descripcion, tipo, cat1, cat2
        FROM transacciones
        WHERE importe > 0
          AND tipo != 'GASTO'
          AND cat1 IN ('Compras', 'Alimentación', 'Restauración', 'Transporte',
                       'Vivienda', 'Salud y Belleza', 'Ocio y Cultura', 'Ropa y Calzado',
                       'Educación', 'Recibos', 'Suscripciones', 'Tecnología',
                       'Mascotas', 'Hogar', 'Deporte', 'Otros')
          AND (descripcion LIKE '%devolución%'
               OR descripcion LIKE '%devolucion%'
               OR descripcion LIKE '%devolucio%'
               OR descripcion LIKE '%reembolso%'
               OR descripcion LIKE '%refund%'
               OR descripcion LIKE '%return%'
               OR descripcion LIKE '%reversal%')
    """)

    regla3_rows = cursor.fetchall()
    print(f"   Encontradas: {len(regla3_rows)} transacciones")

    if regla3_rows:
        print(f"\n   Ejemplos antes del UPDATE:")
        for i, (tx_id, fecha, importe, desc, tipo, cat1, cat2) in enumerate(regla3_rows[:5], 1):
            print(f"   {i}. {fecha} | €{importe:>8.2f} | {tipo:15s}/{cat1:20s} | {desc[:40]}")

        # UPDATE
        cursor.execute("""
            UPDATE transacciones
            SET tipo = 'GASTO'
            WHERE importe > 0
              AND tipo != 'GASTO'
              AND cat1 IN ('Compras', 'Alimentación', 'Restauración', 'Transporte',
                           'Vivienda', 'Salud y Belleza', 'Ocio y Cultura', 'Ropa y Calzado',
                           'Educación', 'Recibos', 'Suscripciones', 'Tecnología',
                           'Mascotas', 'Hogar', 'Deporte', 'Otros')
              AND (descripcion LIKE '%devolución%'
                   OR descripcion LIKE '%devolucion%'
                   OR descripcion LIKE '%devolucio%'
                   OR descripcion LIKE '%reembolso%'
                   OR descripcion LIKE '%refund%'
                   OR descripcion LIKE '%return%'
                   OR descripcion LIKE '%reversal%')
        """)

        updated3 = cursor.rowcount
        print(f"\n   ✅ Actualizadas: {updated3} transacciones")
    else:
        print(f"   ℹ️  No hay transacciones que actualizar")
        updated3 = 0

    # Commit
    conn.commit()
    conn.close()

    # Resumen
    total_updated = updated1 + updated2 + updated3
    print("\n" + "=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    print(f"REGLA 1 (B100):                {updated1:4d} transacciones")
    print(f"REGLA 2 (Amazon):              {updated2:4d} transacciones")
    print(f"REGLA 3 (Devoluciones):        {updated3:4d} transacciones")
    print("─" * 80)
    print(f"TOTAL:                         {total_updated:4d} transacciones")
    print("=" * 80)

if __name__ == '__main__':
    main()
