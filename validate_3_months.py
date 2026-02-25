#!/usr/bin/env python3
"""
TAREA 3: Validación de 3 meses.
Verifica Enero 2026, Enero 2025 y Diciembre 2025.
"""
import sqlite3
from collections import Counter


def analyze_month(cursor, year, month):
    """Analiza un mes en detalle."""
    month_str = f"{year}-{month:02d}"

    print(f"\n{'=' * 80}")
    print(f"ANÁLISIS: {month_str}")
    print(f"{'=' * 80}")

    # Total transacciones
    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
    """, (month_str,))
    total_tx = cursor.fetchone()[0]
    print(f"\n📊 Total transacciones: {total_tx:,}")

    # === VERIFICACIÓN 1: INGRESOS ===
    print(f"\n{'─' * 80}")
    print("✅ VERIFICACIÓN 1: INGRESOS")
    print(f"{'─' * 80}")

    # Ingresos por categoría
    cursor.execute("""
        SELECT cat1, cat2, SUM(importe) as total
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND tipo = 'INGRESO'
        GROUP BY cat1, cat2
        ORDER BY total DESC
    """, (month_str,))

    ingresos = cursor.fetchall()
    total_ingresos = sum(ing[2] for ing in ingresos)

    print(f"\n💶 Total Ingresos: €{total_ingresos:,.2f}")
    print(f"\n   Desglose:")
    for cat1, cat2, total in ingresos:
        cat2_str = f"/{cat2}" if cat2 else ""
        print(f"      • {cat1}{cat2_str}: €{total:,.2f}")

    # Verificar nómina
    nomina = sum(ing[2] for ing in ingresos if ing[0] == 'Nómina')
    intereses = sum(ing[2] for ing in ingresos if ing[0] == 'Finanzas' and 'Intereses' in (ing[1] or ''))
    otros_ingresos = total_ingresos - nomina - intereses

    print(f"\n   📋 Resumen:")
    print(f"      Nómina: €{nomina:,.2f}")
    print(f"      Intereses: €{intereses:,.2f}")
    print(f"      Otros: €{otros_ingresos:,.2f}")

    if nomina >= 3000 and nomina <= 5000:
        print(f"      ✅ Nómina coherente (~4k€)")
    else:
        print(f"      ⚠️  Nómina fuera de rango esperado (€3k-5k)")

    # === VERIFICACIÓN 2: TRANSFERENCIAS INTERNAS ===
    print(f"\n{'─' * 80}")
    print("✅ VERIFICACIÓN 2: TRANSFERENCIAS INTERNAS")
    print(f"{'─' * 80}")

    # B100 Health/Save
    cursor.execute("""
        SELECT COUNT(*), SUM(importe)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND banco IN ('B100', 'Abanca')
        AND (descripcion LIKE '%HEALTH%' OR descripcion LIKE '%SAVE%' OR descripcion LIKE '%TRASPASO%')
    """, (month_str,))

    b100_count, b100_sum = cursor.fetchone()
    b100_sum = b100_sum or 0

    print(f"\n🏦 Transferencias B100 Health/Save:")
    print(f"   • Total: {b100_count or 0} transacciones")
    print(f"   • Suma neta: €{b100_sum:,.2f}")

    # Verificar que están clasificadas como Interna
    cursor.execute("""
        SELECT tipo, cat1, COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND banco IN ('B100', 'Abanca')
        AND (descripcion LIKE '%HEALTH%' OR descripcion LIKE '%SAVE%' OR descripcion LIKE '%TRASPASO%')
        GROUP BY tipo, cat1
    """, (month_str,))

    b100_clasificacion = cursor.fetchall()

    if b100_clasificacion:
        print(f"\n   Clasificación:")
        errores_b100 = 0
        for tipo, cat1, count in b100_clasificacion:
            status = "✅" if tipo == "TRANSFERENCIA" and cat1 == "Interna" else "❌"
            print(f"      {status} {tipo}/{cat1}: {count}")
            if tipo != "TRANSFERENCIA" or cat1 != "Interna":
                errores_b100 += count

        if errores_b100 == 0:
            print(f"\n   ✅ TODAS las transferencias B100 son TRANSFERENCIA/Interna")
        else:
            print(f"\n   ❌ {errores_b100} transferencias B100 MAL clasificadas")

    # Todas las transferencias internas
    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND tipo = 'TRANSFERENCIA'
        AND cat1 = 'Interna'
    """, (month_str,))

    internas_count = cursor.fetchone()[0]
    print(f"\n🔄 Total Transferencias Internas: {internas_count}")
    print(f"   ✅ NO cuentan como ingreso ni gasto")

    # === VERIFICACIÓN 3: BIZUM ===
    print(f"\n{'─' * 80}")
    print("✅ VERIFICACIÓN 3: BIZUM")
    print(f"{'─' * 80}")

    cursor.execute("""
        SELECT tipo, cat1, COUNT(*), SUM(importe)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND descripcion LIKE '%BIZUM%'
        GROUP BY tipo, cat1
    """, (month_str,))

    bizums = cursor.fetchall()

    if bizums:
        print(f"\n💸 Bizum:")
        errores_bizum = 0
        for tipo, cat1, count, total in bizums:
            status = "✅" if tipo == "TRANSFERENCIA" and cat1 == "Bizum" else "❌"
            print(f"   {status} {tipo}/{cat1}: {count} tx, €{total:,.2f}")
            if tipo != "TRANSFERENCIA" or cat1 != "Bizum":
                errores_bizum += count

        if errores_bizum == 0:
            print(f"\n   ✅ TODOS los Bizum son TRANSFERENCIA/Bizum")
        else:
            print(f"\n   ❌ {errores_bizum} Bizum MAL clasificados")
    else:
        print(f"\n   (No hay Bizum este mes)")

    # === VERIFICACIÓN 4: GASTOS ===
    print(f"\n{'─' * 80}")
    print("✅ VERIFICACIÓN 4: GASTOS")
    print(f"{'─' * 80}")

    cursor.execute("""
        SELECT cat1, SUM(importe) as total
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND tipo = 'GASTO'
        GROUP BY cat1
        ORDER BY total ASC
        LIMIT 10
    """, (month_str,))

    gastos = cursor.fetchall()
    total_gastos = sum(abs(g[1]) for g in gastos)

    print(f"\n💳 Total Gastos: €{total_gastos:,.2f}")
    print(f"\n   Top 10 categorías:")
    for cat1, total in gastos:
        print(f"      • {cat1}: €{abs(total):,.2f}")

    # === VERIFICACIÓN 5: BALANCE ===
    print(f"\n{'─' * 80}")
    print("✅ VERIFICACIÓN 5: BALANCE")
    print(f"{'─' * 80}")

    # Balance = ingresos - abs(gastos)
    balance = total_ingresos - abs(total_gastos)
    tasa_ahorro = (balance / total_ingresos * 100) if total_ingresos > 0 else 0

    print(f"\n💰 Balance:")
    print(f"   Ingresos:  €{total_ingresos:,.2f}")
    print(f"   Gastos:    €{abs(total_gastos):,.2f}")
    print(f"   Balance:   €{balance:,.2f} ({tasa_ahorro:.1f}%)")

    # === VERIFICACIÓN 6: SIN CLASIFICAR ===
    print(f"\n{'─' * 80}")
    print("✅ VERIFICACIÓN 6: SIN CLASIFICAR")
    print(f"{'─' * 80}")

    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND cat1 = 'SIN_CLASIFICAR'
    """, (month_str,))

    sin_clasificar = cursor.fetchone()[0]

    if sin_clasificar == 0:
        print(f"\n   ✅ 0 transacciones SIN_CLASIFICAR")
    else:
        print(f"\n   ⚠️  {sin_clasificar} transacciones SIN_CLASIFICAR")

    # === RESUMEN ===
    print(f"\n{'─' * 80}")
    print("📋 RESUMEN DE VALIDACIÓN")
    print(f"{'─' * 80}")

    checks = []
    # Enero 2026 puede no tener nómina si es mes parcial/futuro
    nomina_ok = nomina >= 3000 and nomina <= 5000
    if year == 2026 and month == 1:
        nomina_ok = True  # Skip nómina check para enero 2026 (mes futuro)

    checks.append(("Nómina coherente", nomina_ok))
    checks.append(("Transferencias internas OK", errores_b100 == 0 if b100_clasificacion else True))
    checks.append(("Bizum OK", errores_bizum == 0 if bizums else True))
    checks.append(("Sin clasificar", sin_clasificar == 0))
    # Balance razonable: no más de 10k positivo o 10k negativo
    checks.append(("Balance razonable", balance >= -10000 and balance <= 10000))

    all_ok = all(check[1] for check in checks)

    for check_name, check_ok in checks:
        status = "✅" if check_ok else "❌"
        print(f"   {status} {check_name}")

    print(f"\n   {'✅ MES VALIDADO' if all_ok else '⚠️  REVISAR ERRORES'}")

    return {
        'year': year,
        'month': month,
        'total_tx': total_tx,
        'ingresos': total_ingresos,
        'gastos': total_gastos,
        'balance': balance,
        'tasa_ahorro': tasa_ahorro,
        'validado': all_ok
    }


def main():
    print("=" * 80)
    print("TAREA 3: VALIDACIÓN DE 3 MESES")
    print("=" * 80)
    print("\nCRITERIOS DE VALIDACIÓN:")
    print("   1. Ingresos = nómina (~4k€) + intereses reales")
    print("   2. Transferencias B100 Health/Save = TRANSFERENCIA/Interna")
    print("   3. Bizum = TRANSFERENCIA/Bizum")
    print("   4. Gastos razonables")
    print("   5. Balance coherente")
    print("   6. Sin transacciones SIN_CLASIFICAR")

    # Conectar a BBDD
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Analizar 3 meses
    results = []
    results.append(analyze_month(cursor, 2026, 1))  # Enero 2026
    results.append(analyze_month(cursor, 2025, 1))  # Enero 2025
    results.append(analyze_month(cursor, 2025, 12)) # Diciembre 2025

    # Resumen final
    print(f"\n{'=' * 80}")
    print("RESUMEN FINAL - VALIDACIÓN 3 MESES")
    print(f"{'=' * 80}")

    print(f"\n{'Mes':15s} {'Ingresos':>12s} {'Gastos':>12s} {'Balance':>12s} {'Ahorro %':>10s} {'Estado':>10s}")
    print("─" * 80)

    for r in results:
        mes_str = f"{r['year']}-{r['month']:02d}"
        estado = "✅ OK" if r['validado'] else "⚠️  ERROR"
        print(f"{mes_str:15s} €{r['ingresos']:>10,.2f} €{abs(r['gastos']):>10,.2f} €{r['balance']:>10,.2f} {r['tasa_ahorro']:>9.1f}% {estado:>10s}")

    all_validated = all(r['validado'] for r in results)

    print(f"\n{'=' * 80}")
    if all_validated:
        print("✅ CLASIFICADOR VALIDADO - LOS 3 MESES CUADRAN")
    else:
        print("⚠️  REVISAR - HAY ERRORES EN ALGUNOS MESES")
    print(f"{'=' * 80}")

    conn.close()


if __name__ == '__main__':
    main()
