"""
Análisis detallado de errores de clasificación.
Identifica patrones y sugiere mejoras.
"""
import csv
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_cross_validation import CrossValidationClassifier


def analyze_errors(master_csv_path, test_size=1000):
    """
    Analiza los errores de clasificación en detalle.
    """
    # Leer todas las transacciones
    all_transactions = []
    with open(master_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            all_transactions.append(row)

    # Separar train/test
    train_transactions = all_transactions[:-test_size]
    test_transactions = all_transactions[-test_size:]

    # Inicializar clasificador
    classifier = CrossValidationClassifier(train_transactions)

    # Analizar errores por categoría
    sin_clasificar_by_cat1 = Counter()
    sin_clasificar_examples = {}

    for tx in test_transactions:
        descripcion = tx['Descripción']
        banco = tx['Banco']
        importe = tx['Importe']
        cat1_real = tx['Cat1']

        pred = classifier.classify(descripcion, banco, importe)

        if pred['cat1'] == 'SIN_CLASIFICAR':
            sin_clasificar_by_cat1[cat1_real] += 1

            if cat1_real not in sin_clasificar_examples:
                sin_clasificar_examples[cat1_real] = []

            if len(sin_clasificar_examples[cat1_real]) < 10:
                sin_clasificar_examples[cat1_real].append({
                    'desc': descripcion,
                    'banco': banco,
                    'cat2': tx['Cat2']
                })

    print("=" * 80)
    print("ANÁLISIS DE TRANSACCIONES SIN CLASIFICAR")
    print("=" * 80)
    print()

    print("DISTRIBUCIÓN POR CAT1:")
    for cat1, count in sin_clasificar_by_cat1.most_common():
        print(f"  {cat1:30s}: {count:4,} transacciones sin clasificar")
    print()

    print("=" * 80)
    print("EJEMPLOS DE SIN_CLASIFICAR POR CATEGORÍA")
    print("=" * 80)
    print()

    for cat1 in sin_clasificar_by_cat1.most_common(10):
        cat1_name = cat1[0]
        count = cat1[1]

        print(f"\n{cat1_name} ({count} transacciones sin clasificar):")
        print("-" * 80)

        for i, ex in enumerate(sin_clasificar_examples[cat1_name][:10], 1):
            print(f"{i}. [{ex['banco']}] {ex['desc']}")
            print(f"   → Debería ser: {cat1_name}|{ex['cat2']}")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Análisis de errores")
    parser.add_argument(
        "--master",
        default="Validación_Categorias_Finsense_04020206_5.csv",
        help="Ruta al CSV maestro"
    )
    parser.add_argument(
        "--test-size",
        type=int,
        default=1000,
        help="Número de transacciones de test"
    )

    args = parser.parse_args()

    analyze_errors(args.master, args.test_size)
