#!/usr/bin/env python3
"""
TAREA 4: Validación final de taxonomía v2.

Verifica que TODAS las transacciones en la BBDD cumplan con la taxonomía canónica.
"""
import sqlite3
from collections import Counter
from taxonomia import validar_taxonomia, get_combinaciones_validas, TAXONOMIA


def main():
    print("=" * 80)
    print("VALIDACIÓN TAXONOMÍA CANÓNICA V2")
    print("=" * 80)

    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Total transacciones
    cursor.execute("SELECT COUNT(*) FROM transacciones")
    total_tx = cursor.fetchone()[0]

    print(f"\n📊 Total transacciones en BBDD: {total_tx:,}")

    # === CHECK 4A: VERIFICAR 0 COMBINACIONES INVÁLIDAS ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 4A: COMBINACIONES INVÁLIDAS")
    print(f"{'=' * 80}")

    cursor.execute("""
        SELECT id, fecha, importe, descripcion, tipo, cat1, cat2
        FROM transacciones
        ORDER BY fecha DESC
    """)

    todas_tx = cursor.fetchall()

    invalidas = []

    for tx in todas_tx:
        tx_id, fecha, importe, desc, tipo, cat1, cat2 = tx

        # Validar contra taxonomía
        if not validar_taxonomia(tipo, cat1, cat2):
            invalidas.append({
                'id': tx_id,
                'fecha': fecha,
                'importe': importe,
                'desc': desc[:60],
                'tipo': tipo,
                'cat1': cat1,
                'cat2': cat2
            })

    if len(invalidas) == 0:
        print(f"\n   ✅ 0 combinaciones inválidas")
        print(f"   ✅ TODAS las {total_tx:,} transacciones cumplen la taxonomía")
    else:
        print(f"\n   ❌ {len(invalidas)} combinaciones inválidas encontradas:")
        print(f"\n   {'ID':>6s} {'Fecha':10s} {'Tipo':15s} {'Cat1':25s} {'Cat2':20s}")
        print(f"   {'-' * 80}")

        # Agrupar por combinación
        by_combo = {}
        for inv in invalidas:
            combo = (inv['tipo'], inv['cat1'], inv['cat2'])
            if combo not in by_combo:
                by_combo[combo] = []
            by_combo[combo].append(inv)

        for combo, txs in sorted(by_combo.items(), key=lambda x: -len(x[1]))[:20]:
            tipo, cat1, cat2 = combo
            count = len(txs)
            print(f"\n   {tipo:15s} / {cat1:25s} / {cat2:20s} ({count} tx)")

            # Mostrar primeras 3 transacciones
            for tx in txs[:3]:
                print(f"      #{tx['id']:>5d} {tx['fecha']:10s} €{tx['importe']:>8.2f} | {tx['desc']}")

    # === CHECK 4B: CONTAR COMBINACIONES ÚNICAS ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 4B: COMBINACIONES ÚNICAS EN BBDD")
    print(f"{'=' * 80}")

    cursor.execute("""
        SELECT tipo, cat1, cat2, COUNT(*) as n
        FROM transacciones
        GROUP BY tipo, cat1, cat2
        ORDER BY tipo, cat1, cat2
    """)

    combinaciones_bbdd = cursor.fetchall()

    print(f"\n   Total combinaciones únicas en BBDD: {len(combinaciones_bbdd)}")

    # Comparar con taxonomía
    combinaciones_taxonomia = get_combinaciones_validas()
    print(f"   Total combinaciones en taxonomía: {len(combinaciones_taxonomia)}")

    # Mostrar por tipo
    by_tipo = Counter([c[0] for c in combinaciones_bbdd])

    print(f"\n   Por tipo:")
    for tipo in ["GASTO", "INGRESO", "INVERSION", "TRANSFERENCIA"]:
        count_bbdd = by_tipo.get(tipo, 0)
        count_tax = sum(1 for c in combinaciones_taxonomia if c[0] == tipo)
        print(f"      {tipo:15s}: {count_bbdd:>3d} en BBDD / {count_tax:>3d} en taxonomía")

    # Top 20 combinaciones más usadas
    print(f"\n   Top 20 combinaciones más usadas:")
    print(f"\n   {'Tipo':15s} {'Cat1':25s} {'Cat2':20s} {'Count':>8s}")
    print(f"   {'-' * 80}")

    for tipo, cat1, cat2, count in sorted(combinaciones_bbdd, key=lambda x: -x[3])[:20]:
        cat2_display = cat2 if cat2 else "(vacío)"
        print(f"   {tipo:15s} {cat1:25s} {cat2_display:20s} {count:>8,d}")

    # === CHECK 4C: VALIDAR 3 MESES ===
    print(f"\n{'=' * 80}")
    print("✅ CHECK 4C: VALIDAR 3 MESES")
    print(f"{'=' * 80}")

    import subprocess

    meses = [
        ("2026", "01", "Enero 2026"),
        ("2025", "01", "Enero 2025"),
        ("2025", "12", "Diciembre 2025"),
    ]

    validacion_meses_ok = True

    for year, month, nombre in meses:
        print(f"\n   Validando {nombre}...")

        result = subprocess.run(
            ["python3", "validate_month.py", year, month],
            capture_output=True,
            text=True
        )

        # Buscar si dice "MES VALIDADO" en la salida
        if "MES VALIDADO" in result.stdout:
            print(f"      ✅ {nombre} validado")
        else:
            print(f"      ❌ {nombre} con errores")
            validacion_meses_ok = False

    # === CHECK 4D: REPORTE RESUMEN ===
    print(f"\n{'=' * 80}")
    print("📋 REPORTE RESUMEN")
    print(f"{'=' * 80}")

    print(f"\n   Total transacciones en BBDD: {total_tx:,}")
    print(f"   Total combinaciones Tipo/Cat1/Cat2 únicas: {len(combinaciones_bbdd)}")
    print(f"   Total combinaciones en taxonomía: {len(combinaciones_taxonomia)}")

    # Criterio de éxito
    print(f"\n{'=' * 80}")
    print("CRITERIO DE ÉXITO")
    print(f"{'=' * 80}\n")

    checks = [
        ("0 combinaciones inválidas", len(invalidas) == 0),
        ("Combinaciones BBDD ≤ Taxonomía", len(combinaciones_bbdd) <= len(combinaciones_taxonomia)),
        ("Los 3 meses validados", validacion_meses_ok),
    ]

    all_ok = all(check[1] for check in checks)

    for check_name, check_ok in checks:
        status = "✅" if check_ok else "❌"
        print(f"   {status} {check_name}")

    print(f"\n{'=' * 80}")
    if all_ok:
        print("✅ TAXONOMÍA V2 APLICADA CORRECTAMENTE")
    else:
        print("⚠️  REVISAR - HAY ERRORES")
    print(f"{'=' * 80}")

    conn.close()


if __name__ == '__main__':
    main()
