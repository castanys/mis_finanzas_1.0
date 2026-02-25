#!/usr/bin/env python3
"""
FASE 2D: Enriquecimiento de Cat2 con Google Places API

Uso:
    python3 enrich_cat2.py --dry-run    # Solo muestra qué haría
    python3 enrich_cat2.py              # Ejecuta con API (requiere GOOGLE_PLACES_API_KEY)
"""
import os
import sys
import csv
import argparse
from src.enrichment import MerchantCache, enrich_cat2


def load_transactions(csv_path: str) -> list:
    """Carga transacciones desde CSV."""
    transactions = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)  # Auto-detect delimiter
        for row in reader:
            transactions.append(row)
    return transactions


def save_transactions(transactions: list, csv_path: str):
    """Guarda transacciones a CSV."""
    if not transactions:
        print("⚠️  No hay transacciones para guardar")
        return

    fieldnames = transactions[0].keys()
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)  # Use default comma delimiter
        writer.writeheader()
        writer.writerows(transactions)


def print_report(stats: dict, cache_stats: dict):
    """Imprime reporte de resultados."""
    print("\n" + "=" * 60)
    print("=== ENRIQUECIMIENTO Cat2 ===")
    print("=" * 60)
    print(f"Candidatas totales:          {stats['candidates']}")
    print(f"Merchants únicos:            {stats['unique_merchants']}")

    if stats['api_calls'] > 0:
        print(f"Encontrados en Google:       {cache_stats['with_results']} ({cache_stats['with_results']/stats['unique_merchants']*100:.1f}%)")
        print(f"Cat2 asignados:              {stats['enriched']} ({stats['enriched']/stats['candidates']*100:.1f}%)")
        print(f"Sin resultado:               {cache_stats['no_results']}")
        print(f"Consultas a API:             {stats['api_calls']}")
        print(f"Cache hits:                  {stats.get('cache_hits', 0)}")

        # Costo estimado (Google Places Text Search = $32 per 1000 requests)
        cost = (stats['api_calls'] / 1000) * 32
        print(f"Coste estimado:              ${cost:.2f}")

        print("\nPor confianza:")
        for conf, count in cache_stats.get('by_confidence', {}).items():
            print(f"  {conf:12s}: {count:4d}")

        print("\nPor ámbito geográfico:")
        for loc, count in cache_stats.get('by_location', {}).items():
            print(f"  {loc:12s}: {count:4d}")


def main():
    parser = argparse.ArgumentParser(
        description='Enriquece Cat2 usando Google Places API'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Solo muestra qué haría sin llamar a la API'
    )
    parser.add_argument(
        '--input',
        default='output/transacciones_completas.csv',
        help='Archivo CSV de entrada (default: output/transacciones_completas.csv)'
    )
    parser.add_argument(
        '--output',
        default='output/transacciones_completas.csv',
        help='Archivo CSV de salida (default: output/transacciones_completas.csv)'
    )
    parser.add_argument(
        '--cache-db',
        default='merchant_cache.db',
        help='Base de datos de caché (default: merchant_cache.db)'
    )

    args = parser.parse_args()

    # Validar API key si no es dry-run
    api_key = None
    if not args.dry_run:
        api_key = os.environ.get('GOOGLE_PLACES_API_KEY')
        if not api_key:
            print("❌ Error: GOOGLE_PLACES_API_KEY no está configurada")
            print("Configura la variable de entorno:")
            print("  export GOOGLE_PLACES_API_KEY='tu-api-key'")
            print("O ejecuta en modo dry-run:")
            print("  python3 enrich_cat2.py --dry-run")
            sys.exit(1)

    # Cargar transacciones
    print(f"📂 Cargando transacciones desde {args.input}...")
    transactions = load_transactions(args.input)
    print(f"✅ {len(transactions)} transacciones cargadas")

    # Inicializar caché
    cache = MerchantCache(args.cache_db)
    print(f"📦 Caché inicializado: {args.cache_db}")

    # Enriquecer
    print("\n🔍 Iniciando enriquecimiento Cat2...")
    print("=" * 60)

    transactions, stats = enrich_cat2(
        transactions,
        cache,
        api_key=api_key,
        dry_run=args.dry_run
    )

    # Guardar si no es dry-run
    if not args.dry_run:
        print(f"\n💾 Guardando transacciones en {args.output}...")
        save_transactions(transactions, args.output)
        print(f"✅ Guardado completado")

    # Reporte
    cache_stats = cache.get_stats()
    print_report(stats, cache_stats)

    cache.close()


if __name__ == '__main__':
    main()
