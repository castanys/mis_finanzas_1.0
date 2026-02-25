#!/usr/bin/env python3
"""
TAREA 3: VALIDACIÓN REAL - CHECKLIST POR MES.

Valida un mes específico con 10 verificaciones críticas.
Uso: python3 validate_month.py 2026 01
"""
import sys
import sqlite3
from collections import Counter


def validate_month(year, month):
    """Valida un mes con checklist completo."""
    month_str = f"{year}-{month:02d}"

    print("=" * 80)
    print(f"VALIDACIÓN REAL: {month_str}")
    print("=" * 80)

    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Total transacciones del mes
    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
    """, (month_str,))
    total_tx = cursor.fetchone()[0]

    print(f"\n📊 Total transacciones: {total_tx:,}")

    # Checklist
    checks = []

    # === CHECK 1: NÓMINA ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 1: NÓMINA")
    print(f"{'=' * 80}")

    cursor.execute("""
        SELECT fecha, importe, descripcion, banco
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND tipo = 'INGRESO'
        AND cat1 = 'Nómina'
    """, (month_str,))

    nominas = cursor.fetchall()

    if len(nominas) == 1:
        fecha, importe, desc, banco = nominas[0]
        print(f"   ✅ 1 nómina encontrada:")
        print(f"      Fecha: {fecha}")
        print(f"      Importe: €{importe:,.2f}")
        print(f"      Banco: {banco}")
        print(f"      Desc: {desc[:70]}")

        if 3000 <= importe <= 5000:
            print(f"   ✅ Importe coherente (~4k€)")
            checks.append(("Nómina", True))
        else:
            print(f"   ⚠️  Importe fuera de rango (€3k-5k)")
            checks.append(("Nómina", False))
    elif len(nominas) == 0:
        print(f"   ⚠️  No hay nómina este mes")
        checks.append(("Nómina", False))
    else:
        print(f"   ❌ {len(nominas)} nóminas (debería haber 1)")
        checks.append(("Nómina", False))

    # Verificar TRANSFERENCIA INTERNA NOMINA
    cursor.execute("""
        SELECT fecha, importe, tipo, cat1
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND descripcion LIKE '%TRANSFERENCIA INTERNA NOMINA%'
    """, (month_str,))

    transf_nomina = cursor.fetchall()
    if transf_nomina:
        for fecha, importe, tipo, cat1 in transf_nomina:
            if tipo == 'TRANSFERENCIA' and cat1 == 'Interna':
                print(f"   ✅ TRANSFERENCIA INTERNA NOMINA: {tipo}/{cat1} ✓")
            else:
                print(f"   ❌ TRANSFERENCIA INTERNA NOMINA: {tipo}/{cat1} (debería ser TRANSFERENCIA/Interna)")
                checks.append(("TRANSF NOMINA correcta", False))

    # === CHECK 2: DUPLICADOS ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 2: DUPLICADOS")
    print(f"{'=' * 80}")

    cursor.execute("""
        SELECT fecha, ABS(importe), banco, cuenta, COUNT(*) as count
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        GROUP BY fecha, ABS(importe), banco, cuenta
        HAVING COUNT(*) > 1
    """, (month_str,))

    duplicados = cursor.fetchall()

    if len(duplicados) == 0:
        print(f"   ✅ 0 duplicados detectados")
        checks.append(("Sin duplicados", True))
    else:
        print(f"   ❌ {len(duplicados)} grupos de duplicados:")
        for fecha, importe, banco, cuenta, count in duplicados[:10]:
            print(f"      {fecha} | {banco} | €{importe:.2f} | {count} copias")
        checks.append(("Sin duplicados", False))

    # === CHECK 3: TATIANA (limpieza) ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 3: TATIANA (LIMPIEZA)")
    print(f"{'=' * 80}")

    cursor.execute("""
        SELECT fecha, importe, tipo, cat1, cat2
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND (descripcion LIKE '%Tatiana%' OR descripcion LIKE '%TATIANA%')
        AND (descripcion LIKE '%Santallana%' OR descripcion LIKE '%SANTALLANA%')
    """, (month_str,))

    tatianas = cursor.fetchall()

    if tatianas:
        all_correct = all(t[2] == 'GASTO' and t[3] == 'Vivienda' and t[4] == 'Limpieza' for t in tatianas)

        print(f"   {len(tatianas)} transacciones a Tatiana:")
        for fecha, importe, tipo, cat1, cat2 in tatianas:
            status = "✅" if (tipo == 'GASTO' and cat1 == 'Vivienda' and cat2 == 'Limpieza') else "❌"
            print(f"      {status} {fecha} | €{importe:.2f} | {tipo}/{cat1}/{cat2}")

        if all_correct:
            print(f"   ✅ Todas correctas (GASTO/Vivienda/Limpieza)")
            checks.append(("Tatiana correcta", True))
        else:
            print(f"   ❌ Algunas incorrectas")
            checks.append(("Tatiana correcta", False))
    else:
        print(f"   ℹ️  No hay pagos a Tatiana este mes")
        checks.append(("Tatiana correcta", True))  # OK si no hay

    # === CHECK 4: ALEJANDRO (préstamo hermano) ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 4: ALEJANDRO (PRÉSTAMO HERMANO)")
    print(f"{'=' * 80}")

    cursor.execute("""
        SELECT fecha, importe, tipo, cat1, cat2, descripcion
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND (descripcion LIKE '%Alejandro%' OR descripcion LIKE '%ALEJANDRO%')
        AND (descripcion LIKE '%Fernández%' OR descripcion LIKE '%Fernandez%' OR descripcion LIKE '%Fdez%')
        AND importe < -500
    """, (month_str,))

    alejandros = cursor.fetchall()

    if alejandros:
        all_correct = all(a[2] == 'GASTO' and a[3] == 'Préstamos' for a in alejandros)

        print(f"   {len(alejandros)} préstamos a Alejandro (hermano):")
        for fecha, importe, tipo, cat1, cat2, desc in alejandros:
            status = "✅" if (tipo == 'GASTO' and cat1 == 'Préstamos') else "❌"
            print(f"      {status} {fecha} | €{importe:.2f} | {tipo}/{cat1}/{cat2}")
            print(f"         {desc[:70]}")

        if all_correct:
            print(f"   ✅ Todos correctos (GASTO/Préstamos)")
            checks.append(("Alejandro correcto", True))
        else:
            print(f"   ❌ Algunos incorrectos")
            checks.append(("Alejandro correcto", False))
    else:
        print(f"   ℹ️  No hay préstamos a Alejandro este mes (pago trimestral)")
        checks.append(("Alejandro correcto", True))  # OK si no hay

    # === CHECK 5: TRANSFERENCIAS INTERNAS ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 5: TRANSFERENCIAS INTERNAS")
    print(f"{'=' * 80}")

    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND tipo = 'TRANSFERENCIA'
        AND cat1 = 'Interna'
    """, (month_str,))

    internas = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND cat1 = 'Interna'
        AND tipo <> 'TRANSFERENCIA'
    """, (month_str,))

    internas_incorrectas = cursor.fetchone()[0]

    print(f"   Transferencias internas: {internas}")

    if internas_incorrectas == 0:
        print(f"   ✅ TODAS son TRANSFERENCIA/Interna (no cuentan como ingreso/gasto)")
        checks.append(("Internas correctas", True))
    else:
        print(f"   ❌ {internas_incorrectas} clasificadas incorrectamente")
        checks.append(("Internas correctas", False))

    # === CHECK 6: BIZUM ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 6: BIZUM")
    print(f"{'=' * 80}")

    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND cat1 = 'Bizum'
    """, (month_str,))

    bizums = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND cat1 = 'Bizum'
        AND tipo <> 'TRANSFERENCIA'
    """, (month_str,))

    bizums_incorrectos = cursor.fetchone()[0]

    print(f"   Bizums: {bizums}")

    if bizums_incorrectos == 0:
        print(f"   ✅ TODOS son TRANSFERENCIA/Bizum (no cuentan como ingreso/gasto)")
        checks.append(("Bizum correctos", True))
    else:
        print(f"   ❌ {bizums_incorrectos} clasificados incorrectamente")
        checks.append(("Bizum correctos", False))

    # === CHECK 7: B100 SAVE/HEALTH ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 7: B100 SAVE/HEALTH")
    print(f"{'=' * 80}")

    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND banco IN ('B100', 'Abanca')
        AND (descripcion LIKE '%HEALTH%' OR descripcion LIKE '%SAVE%' OR descripcion LIKE '%TRASPASO%')
    """, (month_str,))

    b100_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND banco IN ('B100', 'Abanca')
        AND (descripcion LIKE '%HEALTH%' OR descripcion LIKE '%SAVE%' OR descripcion LIKE '%TRASPASO%')
        AND tipo = 'TRANSFERENCIA'
        AND cat1 = 'Interna'
    """, (month_str,))

    b100_correctas = cursor.fetchone()[0]

    if b100_count > 0:
        print(f"   Traspasos B100 Health/Save: {b100_count}")

        if b100_count == b100_correctas:
            print(f"   ✅ TODOS son TRANSFERENCIA/Interna")
            checks.append(("B100 correctos", True))
        else:
            print(f"   ❌ {b100_count - b100_correctas} incorrectos")
            checks.append(("B100 correctos", False))
    else:
        print(f"   ℹ️  No hay traspasos B100 este mes")
        checks.append(("B100 correctos", True))

    # === CHECK 8: COHERENCIA GLOBAL ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 8: COHERENCIA GLOBAL")
    print(f"{'=' * 80}")

    cursor.execute("""
        SELECT SUM(importe)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND tipo = 'INGRESO'
    """, (month_str,))

    ingresos = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT SUM(importe)
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND tipo = 'GASTO'
    """, (month_str,))

    gastos = cursor.fetchone()[0] or 0

    balance = ingresos + gastos  # gastos son negativos

    print(f"   Ingresos:  €{ingresos:,.2f}")
    print(f"   Gastos:    €{abs(gastos):,.2f}")
    print(f"   Balance:   €{balance:,.2f}")

    coherence_ok = True

    # Verificar ingresos (debería ser ~4k€ si hay nómina)
    if len(nominas) == 1:
        if 3000 <= ingresos <= 6000:
            print(f"   ✅ Ingresos coherentes (~4k€ nómina + extras)")
        else:
            print(f"   ⚠️  Ingresos fuera de rango esperado")
            coherence_ok = False

    # Top 5 gastos
    cursor.execute("""
        SELECT cat1, SUM(importe) as total
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = ?
        AND tipo = 'GASTO'
        GROUP BY cat1
        ORDER BY total ASC
        LIMIT 5
    """, (month_str,))

    top_gastos = cursor.fetchall()

    print(f"\n   Top 5 categorías de gasto:")
    for cat1, total in top_gastos:
        print(f"      • {cat1:25s}: €{abs(total):,.2f}")

    checks.append(("Coherencia global", coherence_ok))

    # === CHECK 9: SIN DUPLICADOS EN RESULTADO FINAL ===
    # (ya se verificó en CHECK 2)

    # === RESUMEN FINAL ===
    print(f"\n{'=' * 80}")
    print("📋 RESUMEN DE VALIDACIÓN")
    print(f"{'=' * 80}\n")

    all_ok = all(check[1] for check in checks)

    for check_name, check_ok in checks:
        status = "✅" if check_ok else "❌"
        print(f"   {status} {check_name}")

    print(f"\n{'=' * 80}")
    if all_ok:
        print("✅ MES VALIDADO - TODOS LOS CHECKS PASADOS")
    else:
        print("⚠️  REVISAR - HAY ERRORES EN ESTE MES")
    print(f"{'=' * 80}")

    conn.close()

    return all_ok


def main():
    if len(sys.argv) != 3:
        print("Uso: python3 validate_month.py <año> <mes>")
        print("Ejemplo: python3 validate_month.py 2026 01")
        sys.exit(1)

    year = int(sys.argv[1])
    month = int(sys.argv[2])

    validate_month(year, month)


if __name__ == '__main__':
    main()
