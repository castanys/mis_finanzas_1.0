#!/usr/bin/env python3
"""
Valida que las 3 reglas nuevas se aplican correctamente en Diciembre 2025.
"""
import sqlite3

def main():
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("VALIDACIÓN DE REGLAS - DICIEMBRE 2025")
    print("=" * 80)

    # REGLA 1: B100 Health/Save/Traspaso → TRANSFERENCIA, NO INGRESO
    print("\n1. REGLA B100 Health/Save/Traspaso → TRANSFERENCIA")
    print("─" * 80)

    cursor.execute("""
        SELECT fecha, importe, descripcion, tipo, cat1
        FROM transacciones
        WHERE banco = 'B100'
          AND strftime('%Y-%m', fecha) = '2025-12'
          AND (descripcion LIKE '%Health%'
               OR descripcion LIKE '%Save%'
               OR descripcion LIKE '%Traspaso%'
               OR descripcion LIKE '%AHORRO PARA HUCHA%'
               OR descripcion LIKE '%Move to save%')
        ORDER BY fecha
    """)

    b100_rows = cursor.fetchall()

    if b100_rows:
        print(f"Transacciones B100 encontradas: {len(b100_rows)}\n")

        ingreso_count = 0
        transferencia_count = 0

        for fecha, importe, desc, tipo, cat1 in b100_rows:
            status = "✓" if tipo == "TRANSFERENCIA" else "✗"
            print(f"{status} {fecha} | €{importe:>8.2f} | {tipo:15s} | {cat1:15s} | {desc[:40]}")

            if tipo == "INGRESO":
                ingreso_count += 1
            elif tipo == "TRANSFERENCIA":
                transferencia_count += 1

        print(f"\nResultado REGLA 1:")
        print(f"  • TRANSFERENCIA (correcto): {transferencia_count}")
        print(f"  • INGRESO (ERROR): {ingreso_count}")

        if ingreso_count > 0:
            print(f"\n⚠️  ANOMALÍA: {ingreso_count} transacciones B100 clasificadas como INGRESO")
    else:
        print("✓ No hay transacciones B100 con esos keywords en diciembre 2025")

    # REGLA 2: Amazon refunds (positivos) → GASTO
    print("\n" + "=" * 80)
    print("2. REGLA Amazon Refunds (importe positivo) → GASTO")
    print("─" * 80)

    cursor.execute("""
        SELECT fecha, importe, descripcion, tipo, cat1
        FROM transacciones
        WHERE (descripcion LIKE '%Amazon%' OR descripcion LIKE '%AMZN%')
          AND importe > 0
          AND strftime('%Y-%m', fecha) = '2025-12'
        ORDER BY fecha
    """)

    amazon_rows = cursor.fetchall()

    if amazon_rows:
        print(f"Devoluciones Amazon encontradas: {len(amazon_rows)}\n")

        gasto_count = 0
        ingreso_count = 0

        for fecha, importe, desc, tipo, cat1 in amazon_rows:
            status = "✓" if tipo == "GASTO" else "✗"
            print(f"{status} {fecha} | €{importe:>8.2f} | {tipo:15s} | {cat1:15s} | {desc[:40]}")

            if tipo == "GASTO":
                gasto_count += 1
            else:
                ingreso_count += 1

        print(f"\nResultado REGLA 2:")
        print(f"  • GASTO (correcto): {gasto_count}")
        print(f"  • INGRESO u otro (ERROR): {ingreso_count}")

        if ingreso_count > 0:
            print(f"\n⚠️  ANOMALÍA: {ingreso_count} devoluciones Amazon NO clasificadas como GASTO")
    else:
        print("✓ No hay devoluciones Amazon en diciembre 2025")

    # REGLA 3: Devoluciones positivas con cat gasto → GASTO
    print("\n" + "=" * 80)
    print("3. REGLA Devoluciones explícitas con Cat1 de gasto → GASTO")
    print("─" * 80)

    cursor.execute("""
        SELECT fecha, importe, descripcion, tipo, cat1
        FROM transacciones
        WHERE importe > 0
          AND (descripcion LIKE '%devolución%'
               OR descripcion LIKE '%devolucion%'
               OR descripcion LIKE '%reembolso%'
               OR descripcion LIKE '%refund%'
               OR descripcion LIKE '%return%')
          AND cat1 IN ('Compras', 'Alimentación', 'Restauración', 'Transporte',
                       'Vivienda', 'Salud y Belleza', 'Ocio y Cultura',
                       'Ropa y Calzado', 'Educación', 'Recibos', 'Suscripciones',
                       'Tecnología', 'Mascotas', 'Hogar', 'Deporte', 'Otros')
          AND strftime('%Y-%m', fecha) = '2025-12'
        ORDER BY fecha
    """)

    refund_rows = cursor.fetchall()

    if refund_rows:
        print(f"Devoluciones explícitas encontradas: {len(refund_rows)}\n")

        gasto_count = 0
        ingreso_count = 0

        for fecha, importe, desc, tipo, cat1 in refund_rows:
            status = "✓" if tipo == "GASTO" else "✗"
            print(f"{status} {fecha} | €{importe:>8.2f} | {tipo:15s} | {cat1:15s} | {desc[:40]}")

            if tipo == "GASTO":
                gasto_count += 1
            else:
                ingreso_count += 1

        print(f"\nResultado REGLA 3:")
        print(f"  • GASTO (correcto): {gasto_count}")
        print(f"  • INGRESO u otro (ERROR): {ingreso_count}")

        if ingreso_count > 0:
            print(f"\n⚠️  ANOMALÍA: {ingreso_count} devoluciones NO clasificadas como GASTO")
    else:
        print("✓ No hay devoluciones explícitas en diciembre 2025")

    # Resumen de validación
    print("\n" + "=" * 80)
    print("RESUMEN DE VALIDACIÓN")
    print("=" * 80)

    total_errors = 0
    if b100_rows:
        b100_errors = sum(1 for _, _, _, tipo, _ in b100_rows if tipo != "TRANSFERENCIA")
        total_errors += b100_errors
    if amazon_rows:
        amazon_errors = sum(1 for _, _, _, tipo, _ in amazon_rows if tipo != "GASTO")
        total_errors += amazon_errors
    if refund_rows:
        refund_errors = sum(1 for _, _, _, tipo, _ in refund_rows if tipo != "GASTO")
        total_errors += refund_errors

    if total_errors == 0:
        print("✅ TODAS LAS REGLAS SE APLICAN CORRECTAMENTE")
    else:
        print(f"⚠️  {total_errors} TRANSACCIONES CON ERRORES DETECTADOS")

    print("=" * 80)

    conn.close()

if __name__ == '__main__':
    main()
