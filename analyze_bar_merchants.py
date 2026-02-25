#!/usr/bin/env python3
"""
Analiza los merchants más frecuentes clasificados como 'Bar' por Google Places.
"""
import sqlite3
from extractors import extract_merchant
from collections import Counter

def main():
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Obtener todas las transacciones con cat2='Bar'
    cursor.execute("""
        SELECT descripcion, banco, COUNT(*) as count
        FROM transacciones
        WHERE cat2 = 'Bar'
        GROUP BY descripcion, banco
        ORDER BY count DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    # Extraer merchants y contar
    merchant_counts = Counter()

    for descripcion, banco, count in rows:
        merchant_name = extract_merchant(descripcion, banco)
        if merchant_name:
            merchant_counts[merchant_name] += count

    # Mostrar top 20
    print("=" * 80)
    print("TOP 20 MERCHANTS MÁS FRECUENTES CON CAT2='Bar' (GOOGLE PLACES)")
    print("=" * 80)
    print(f"\nTotal transacciones con Cat2='Bar': {sum(merchant_counts.values())}")
    print(f"Merchants únicos: {len(merchant_counts)}\n")
    print(f"{'MERCHANT':50s} {'TRANSACCIONES':>15s}")
    print("─" * 80)

    for i, (merchant, count) in enumerate(merchant_counts.most_common(20), 1):
        print(f"{i:2d}. {merchant[:47]:47s} {count:>15d}")

    print("=" * 80)

if __name__ == '__main__':
    main()
