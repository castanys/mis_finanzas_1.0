#!/usr/bin/env python3
"""
Aplica correcciones quirúrgicas de Cat2 basadas en descripción.
Estas correcciones se aplicarán también como reglas en engine.py.
"""
import sqlite3

def main():
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("APLICANDO CORRECCIONES Cat2 BASADAS EN DESCRIPCIÓN")
    print("=" * 80)

    # CORRECCIÓN 1: RESTAURANTE en descripción → Cat2=Restaurante
    print("\n1. Corrigiendo transacciones con 'RESTAURANTE' en descripción...")
    cursor.execute("""
        UPDATE transacciones
        SET cat2 = 'Restaurante'
        WHERE descripcion LIKE '%RESTAURANTE%'
          AND cat2 != 'Restaurante'
          AND cat1 = 'Restauración'
    """)
    count1 = cursor.rowcount
    print(f"   ✓ {count1} transacciones corregidas a Cat2='Restaurante'")

    # CORRECCIÓN 2: ARROCERIA en descripción → Cat2=Restaurante
    print("\n2. Corrigiendo transacciones con 'ARROCERIA' en descripción...")
    cursor.execute("""
        UPDATE transacciones
        SET cat2 = 'Restaurante'
        WHERE descripcion LIKE '%ARROCERIA%'
          AND cat2 != 'Restaurante'
          AND cat1 = 'Restauración'
    """)
    count2 = cursor.rowcount
    print(f"   ✓ {count2} transacciones corregidas a Cat2='Restaurante'")

    # CORRECCIÓN 3: KIOSKO/QUIOSCO en descripción → Cat2=Kiosco
    print("\n3. Corrigiendo transacciones con 'KIOSKO'/'QUIOSCO' en descripción...")
    cursor.execute("""
        UPDATE transacciones
        SET cat2 = 'Kiosco'
        WHERE (descripcion LIKE '%KIOSKO%' OR descripcion LIKE '%QUIOSCO%')
          AND cat2 != 'Kiosco'
    """)
    count3 = cursor.rowcount
    print(f"   ✓ {count3} transacciones corregidas a Cat2='Kiosco'")

    # CORRECCIÓN 4: CHURRERIA en descripción → Cat2=Churrería
    print("\n4. Corrigiendo transacciones con 'CHURRERIA' en descripción...")
    cursor.execute("""
        UPDATE transacciones
        SET cat2 = 'Churrería'
        WHERE descripcion LIKE '%CHURRERIA%'
          AND cat2 != 'Churrería'
          AND cat1 = 'Restauración'
    """)
    count4 = cursor.rowcount
    print(f"   ✓ {count4} transacciones corregidas a Cat2='Churrería'")

    # Commit
    conn.commit()

    total = count1 + count2 + count3 + count4
    print("\n" + "=" * 80)
    print(f"TOTAL: {total} transacciones corregidas")
    print("=" * 80)

    # Verificar algunas correcciones
    print("\nVerificando ejemplos de correcciones:")
    cursor.execute("""
        SELECT descripcion, cat1, cat2
        FROM transacciones
        WHERE descripcion LIKE '%RESTAURANTE%' AND cat2 = 'Restaurante'
        LIMIT 5
    """)

    print("\nEjemplos con 'RESTAURANTE' → Cat2='Restaurante':")
    for desc, cat1, cat2 in cursor.fetchall():
        print(f"  • {desc[:60]:60s} | {cat1:15s} | {cat2}")

    conn.close()

if __name__ == '__main__':
    main()
