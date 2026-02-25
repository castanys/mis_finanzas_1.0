#!/usr/bin/env python3
"""
TAREA 2: Análisis de Cat2="Otros".
Identifica las 1,335 transacciones con Cat2="Otros" y sugiere estrategias
para reducirlas a <500.
"""
import sqlite3
import json
from collections import Counter


def main():
    print("=" * 80)
    print("TAREA 2: ANÁLISIS CAT2='OTROS'")
    print("=" * 80)

    # Conectar a BBDD
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Leer transacciones con Cat2="Otros"
    cursor.execute("""
        SELECT fecha, importe, descripcion, banco, cuenta, tipo, cat1, cat2
        FROM transacciones
        WHERE cat2 = 'Otros'
        ORDER BY cat1, fecha DESC
    """)

    otros = cursor.fetchall()
    total_otros = len(otros)

    print(f"\n📊 Total transacciones con Cat2='Otros': {total_otros:,}")

    # Distribución por Cat1
    cat1_dist = Counter([tx[6] for tx in otros])

    print(f"\n📋 Distribución por Cat1:")
    print(f"\n{'Cat1':25s} {'Count':>8s} {'%':>8s}")
    print("─" * 80)
    for cat1, count in cat1_dist.most_common():
        pct = (count / total_otros) * 100
        print(f"{cat1:25s} {count:>8,d} {pct:>7.1f}%")

    # Cargar merchants_places.json
    merchants_places = {}
    if os.path.exists('merchants_places.json'):
        with open('merchants_places.json', 'r', encoding='utf-8') as f:
            merchants_places = json.load(f)

    print(f"\n🗺️  Merchants con Google Places: {len(merchants_places):,}")

    # Analizar cada Cat1 con más "Otros"
    top_cats = ["Restauración", "Compras", "Recibos", "Alimentación", "Ropa y Calzado"]

    for cat1 in top_cats:
        print(f"\n{'=' * 80}")
        print(f"ANÁLISIS: {cat1}")
        print(f"{'=' * 80}")

        # Filtrar transacciones de esta cat1
        cat1_txs = [tx for tx in otros if tx[6] == cat1]
        print(f"\n📊 Total '{cat1}' con Cat2='Otros': {len(cat1_txs):,}")

        # Extractar descripciones
        descs = [tx[2] for tx in cat1_txs]
        desc_counter = Counter(descs)

        # Contar cuántas tienen Google Places
        with_places = 0
        without_places = 0
        places_types = Counter()

        for tx in cat1_txs:
            desc = tx[2]
            if desc in merchants_places:
                with_places += 1
                place_type = merchants_places[desc].get('type', 'unknown')
                places_types[place_type] += 1
            else:
                without_places += 1

        print(f"\n   • Con Google Places: {with_places:,} ({with_places/len(cat1_txs)*100:.1f}%)")
        print(f"   • Sin Google Places: {without_places:,} ({without_places/len(cat1_txs)*100:.1f}%)")

        if places_types:
            print(f"\n   📍 Tipos de Google Places:")
            for ptype, count in places_types.most_common(10):
                print(f"      {ptype}: {count}")

        # Mostrar ejemplos (primeros 10)
        print(f"\n   📝 Ejemplos de descripciones (primeras 10):")
        for desc, count in desc_counter.most_common(10):
            has_places = "✓" if desc in merchants_places else "✗"
            print(f"      [{has_places}] {desc[:70]} ({count})")

    # Estimación de reducción
    print(f"\n{'=' * 80}")
    print("ESTRATEGIA DE REDUCCIÓN")
    print(f"{'=' * 80}")

    total_with_places = sum(1 for tx in otros if tx[2] in merchants_places)
    total_without_places = total_otros - total_with_places

    print(f"\n📊 Resumen:")
    print(f"   • Total Cat2='Otros': {total_otros:,}")
    print(f"   • Con Google Places: {total_with_places:,} ({total_with_places/total_otros*100:.1f}%)")
    print(f"   • Sin Google Places: {total_without_places:,} ({total_without_places/total_otros*100:.1f}%)")

    print(f"\n💡 Estrategia:")
    print(f"   1. Usar Google Places para asignar Cat2 a {total_with_places:,} transacciones")
    print(f"   2. Implementar reglas específicas para merchants reconocibles sin Places")
    print(f"   3. Dejar como 'Otros' solo merchants antiguos/oscuros")
    print(f"\n   🎯 Objetivo: Reducir de {total_otros:,} a <500")
    print(f"   📉 Potencial reducción: ~{total_with_places:,} tx si usamos Google Places")

    conn.close()


if __name__ == '__main__':
    import os
    main()
