#!/usr/bin/env python3
"""
Aplica los merchants de Google Places mediante SQL UPDATE directo.
Lee merchants_places.json y actualiza Cat2 en la BBDD.
"""
import sqlite3
import json
from extractors import extract_merchant

def main():
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("🗺️  APLICANDO GOOGLE PLACES MERCHANTS (SQL UPDATE)")
    print("=" * 80)

    # Cargar merchants_places.json
    print("\n📖 Cargando merchants_places.json...")
    with open('merchants_places.json', 'r', encoding='utf-8') as f:
        merchants_places = json.load(f)

    print(f"   ✓ {len(merchants_places)} merchants cargados")

    # Leer todas las transacciones
    print("\n🔍 Buscando transacciones que coincidan con merchants...")
    cursor.execute("""
        SELECT id, descripcion, banco, cat1, cat2
        FROM transacciones
    """)

    all_transactions = cursor.fetchall()
    print(f"   ✓ {len(all_transactions):,} transacciones leídas")

    # Procesar cada transacción
    updates = []
    matches = 0

    for tx_id, descripcion, banco, cat1_actual, cat2_actual in all_transactions:
        # Extraer merchant name
        merchant_name = extract_merchant(descripcion, banco)

        if merchant_name and merchant_name in merchants_places:
            merchant_data = merchants_places[merchant_name]
            cat1_places = merchant_data['cat1']
            cat2_places = merchant_data['cat2']

            # Solo actualizar si Cat2 es diferente y no está ya enriquecido
            # (evitar sobrescribir Cat2 específicos ya existentes)
            if cat2_actual in ('', 'Otros', None) and cat2_places not in ('', None):
                updates.append({
                    'id': tx_id,
                    'merchant': merchant_name,
                    'cat1_old': cat1_actual,
                    'cat2_old': cat2_actual or '',
                    'cat1_new': cat1_places,
                    'cat2_new': cat2_places,
                    'descripcion': descripcion[:60]
                })
                matches += 1

    print(f"\n   ✓ {matches} transacciones coinciden con Google Places merchants")

    if updates:
        print(f"\n   Primeros 10 ejemplos de lo que se va a actualizar:")
        print("   " + "─" * 76)
        for i, u in enumerate(updates[:10], 1):
            print(f"   {i}. {u['merchant'][:30]:30s} | {u['cat2_old']:15s} → {u['cat2_new']}")

        # Aplicar updates
        print(f"\n   Aplicando {len(updates)} UPDATEs...")
        for u in updates:
            cursor.execute("""
                UPDATE transacciones
                SET cat1 = ?,
                    cat2 = ?
                WHERE id = ?
            """, (u['cat1_new'], u['cat2_new'], u['id']))

        conn.commit()
        print(f"   ✅ {len(updates)} transacciones actualizadas con Google Places")

        # Estadísticas
        print(f"\n   Distribución de Cat2 enriquecidos:")
        cat2_counts = {}
        for u in updates:
            cat2 = u['cat2_new']
            cat2_counts[cat2] = cat2_counts.get(cat2, 0) + 1

        for cat2, count in sorted(cat2_counts.items(), key=lambda x: -x[1])[:15]:
            print(f"      {cat2:30s} {count:4d} transacciones")

    else:
        print(f"   ℹ️  No hay transacciones que actualizar")

    conn.close()

    print("\n" + "=" * 80)
    print("✅ GOOGLE PLACES APLICADO")
    print("=" * 80)
    print(f"Total transacciones enriquecidas: {len(updates)}")
    print("=" * 80)

if __name__ == '__main__':
    main()
