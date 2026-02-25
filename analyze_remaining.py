"""
Script para analizar las transacciones que quedan SIN_CLASIFICAR.
"""
import csv
import sys
from pathlib import Path
from collections import Counter

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from extractors import extract_merchant
from tests.test_cross_validation import CrossValidationClassifier


def load_master_csv(csv_path):
    """Carga el CSV maestro."""
    transactions = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            transactions.append(row)
    return transactions


def analyze_remaining(master_csv_path, test_size=1000):
    """
    Analiza las transacciones que quedan SIN_CLASIFICAR.

    Args:
        master_csv_path: Ruta al CSV maestro
        test_size: Número de transacciones a usar como test

    Returns:
        Lista de transacciones sin clasificar
    """
    print("=" * 80)
    print("ANÁLISIS DE TRANSACCIONES RESTANTES SIN_CLASIFICAR")
    print("=" * 80)
    print()

    # Leer todas las transacciones
    all_transactions = load_master_csv(master_csv_path)

    # Separar train/test
    train_transactions = all_transactions[:-test_size]
    test_transactions = all_transactions[-test_size:]

    # Inicializar clasificador
    classifier = CrossValidationClassifier(train_transactions)

    # Encontrar transacciones SIN_CLASIFICAR
    unclassified = []

    for tx in test_transactions:
        descripcion = tx['Descripción']
        banco = tx['Banco']
        importe = tx['Importe']
        cat1_real = tx['Cat1']
        cat2_real = tx['Cat2']

        # Clasificar
        pred = classifier.classify(descripcion, banco, importe)

        if pred['cat1'] == 'SIN_CLASIFICAR':
            merchant_name = extract_merchant(descripcion, banco)
            unclassified.append({
                'descripcion': descripcion,
                'banco': banco,
                'importe': importe,
                'merchant_name': merchant_name,
                'cat1_real': cat1_real,
                'cat2_real': cat2_real,
            })

    print(f"Total transacciones SIN_CLASIFICAR: {len(unclassified)}")
    print()

    # Agrupar por Cat1
    by_cat1 = {}
    for tx in unclassified:
        cat1 = tx['cat1_real']
        if cat1 not in by_cat1:
            by_cat1[cat1] = []
        by_cat1[cat1].append(tx)

    print("=" * 80)
    print("TRANSACCIONES SIN_CLASIFICAR AGRUPADAS POR CATEGORÍA")
    print("=" * 80)
    print()

    for cat1 in sorted(by_cat1.keys()):
        txs = by_cat1[cat1]
        print(f"\n{'=' * 80}")
        print(f"CATEGORÍA: {cat1} ({len(txs)} transacciones)")
        print('=' * 80)
        print()

        # Mostrar todas las transacciones
        for i, tx in enumerate(txs, 1):
            print(f"{i}. [{tx['banco']}] {tx['descripcion']}")
            print(f"   Real: {tx['cat1_real']}|{tx['cat2_real']}")
            print(f"   Importe: {tx['importe']}")
            if tx['merchant_name']:
                print(f"   Merchant: {tx['merchant_name']}")
            print()

    # Análisis de patrones
    print("\n" + "=" * 80)
    print("ANÁLISIS DE PATRONES")
    print("=" * 80)
    print()

    patterns = {
        'Cashback': [],
        'Intereses': [],
        'Suscripciones con divisas': [],
        'Otros': []
    }

    for tx in unclassified:
        desc = tx['descripcion'].upper()
        cat1 = tx['cat1_real']

        if cat1 == 'Cashback' or 'SAVEBACK' in desc or 'BONIFICACION' in desc or 'BONIFICACIÓN' in desc:
            patterns['Cashback'].append(tx)
        elif cat1 == 'Intereses' or 'INTEREST' in desc or 'INTERÉS' in desc:
            patterns['Intereses'].append(tx)
        elif 'EXCHANGE RATE' in desc or 'ECB RATE' in desc or 'MARKUP' in desc:
            patterns['Suscripciones con divisas'].append(tx)
        else:
            patterns['Otros'].append(tx)

    for pattern_name, txs in patterns.items():
        if txs:
            print(f"\n{pattern_name}: {len(txs)} transacciones")

            # Buscar palabras clave comunes
            all_words = []
            for tx in txs:
                words = tx['descripcion'].upper().split()
                all_words.extend(words)

            word_counter = Counter(all_words)
            common_words = word_counter.most_common(10)

            print(f"  Palabras clave más frecuentes:")
            for word, count in common_words:
                if len(word) > 2:  # Ignorar palabras muy cortas
                    print(f"    - {word}: {count}x")

    # Proponer soluciones
    print("\n" + "=" * 80)
    print("PROPUESTAS DE SOLUCIÓN")
    print("=" * 80)
    print()

    solutions = []

    # Solución para Cashback
    if patterns['Cashback']:
        print("1. CASHBACK:")
        print("   - Añadir regla en tokens.py para detectar 'SAVEBACK', 'BONIFICACION', 'BONIFICACIÓN'")
        print(f"   - Categoría: Cashback|")
        print(f"   - Afecta a {len(patterns['Cashback'])} transacciones")
        print()
        solutions.append({
            'type': 'token',
            'keywords': ['SAVEBACK', 'BONIFICACION', 'BONIFICACIÓN'],
            'cat1': 'Cashback',
            'cat2': '',
        })

    # Solución para Intereses
    if patterns['Intereses']:
        print("2. INTERESES:")
        print("   - Añadir regla en tokens.py para detectar 'INTEREST PAYMENT', 'INTERÉS'")
        print(f"   - Categoría: Intereses|")
        print(f"   - Afecta a {len(patterns['Intereses'])} transacciones")
        print()
        solutions.append({
            'type': 'token',
            'keywords': ['INTEREST PAYMENT', 'INTEREST', 'INTERÉS'],
            'cat1': 'Intereses',
            'cat2': '',
        })

    # Solución para Suscripciones con divisas
    if patterns['Suscripciones con divisas']:
        print("3. SUSCRIPCIONES CON DIVISAS:")
        print("   - Estas transacciones contienen información de tipo de cambio")
        print("   - Son principalmente de GITHUB y OPENAI")
        print("   - Se pueden detectar por el merchant antes del texto de divisas")
        print(f"   - Afecta a {len(patterns['Suscripciones con divisas'])} transacciones")
        print()

        # Extraer merchants de estas transacciones
        merchants_divisas = set()
        for tx in patterns['Suscripciones con divisas']:
            desc = tx['descripcion']
            # El merchant suele estar antes de la coma o antes de "exchange rate"
            if ',' in desc:
                merchant_part = desc.split(',')[0].strip()
                if 'Transacción' in merchant_part:
                    merchant_part = merchant_part.replace('Transacción', '').strip()
                merchants_divisas.add(merchant_part.upper())

        print(f"   Merchants detectados: {', '.join(merchants_divisas)}")
        print()

        for merchant in merchants_divisas:
            # Buscar categoría en el CSV maestro
            for tx in patterns['Suscripciones con divisas']:
                if merchant in tx['descripcion'].upper():
                    solutions.append({
                        'type': 'merchant',
                        'keyword': merchant,
                        'cat1': tx['cat1_real'],
                        'cat2': tx['cat2_real'],
                    })
                    break

    # Solución para Otros
    if patterns['Otros']:
        print("4. OTROS:")
        print(f"   - Quedan {len(patterns['Otros'])} transacciones sin patrón claro")
        print("   - Requieren análisis caso por caso")
        print()
        for tx in patterns['Otros']:
            print(f"   - {tx['descripcion'][:80]}")
            print(f"     Real: {tx['cat1_real']}|{tx['cat2_real']}")
            print()

    return unclassified, solutions


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analiza transacciones restantes SIN_CLASIFICAR")
    parser.add_argument(
        "--master",
        default="Validación_Categorias_Finsense_04020206_5.csv",
        help="Ruta al CSV maestro"
    )
    parser.add_argument(
        "--test-size",
        type=int,
        default=1000,
        help="Número de transacciones a usar como test"
    )

    args = parser.parse_args()

    unclassified, solutions = analyze_remaining(args.master, args.test_size)

    print("\n" + "=" * 80)
    print("RESUMEN DE SOLUCIONES")
    print("=" * 80)
    print()
    print(f"Total de transacciones SIN_CLASIFICAR: {len(unclassified)}")
    print(f"Soluciones propuestas: {len(solutions)}")
    print()
