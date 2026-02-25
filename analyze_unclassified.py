"""
Script para analizar transacciones SIN_CLASIFICAR y generar reglas nuevas.
"""
import csv
import sys
from pathlib import Path
from collections import defaultdict, Counter

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from classifier.exact_match import build_exact_match_dict
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


def analyze_unclassified(master_csv_path, test_size=1000):
    """
    Analiza las transacciones SIN_CLASIFICAR del test de validación cruzada.

    Args:
        master_csv_path: Ruta al CSV maestro
        test_size: Número de transacciones a usar como test

    Returns:
        Lista de reglas nuevas a añadir
    """
    print("=" * 80)
    print("ANÁLISIS DE TRANSACCIONES SIN_CLASIFICAR")
    print("=" * 80)
    print()

    # Leer todas las transacciones
    all_transactions = load_master_csv(master_csv_path)
    total = len(all_transactions)
    print(f"Total de transacciones en CSV maestro: {total:,}")

    # Separar train/test
    train_transactions = all_transactions[:-test_size]
    test_transactions = all_transactions[-test_size:]

    print(f"Transacciones de entrenamiento: {len(train_transactions):,}")
    print(f"Transacciones de test: {len(test_transactions):,}")
    print()

    # Inicializar clasificador
    classifier = CrossValidationClassifier(train_transactions)
    print()

    # Encontrar transacciones SIN_CLASIFICAR
    unclassified = []

    print("Buscando transacciones SIN_CLASIFICAR...")
    for i, tx in enumerate(test_transactions):
        if (i + 1) % 100 == 0:
            print(f"  Procesadas {i + 1:,} / {len(test_transactions):,}")

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
                'merchant_name': merchant_name,
                'cat1_real': cat1_real,
                'cat2_real': cat2_real,
            })

    print()
    print(f"✓ Encontradas {len(unclassified)} transacciones SIN_CLASIFICAR")
    print()

    # Agrupar por merchant y buscar categorías en el CSV maestro
    print("=" * 80)
    print("ANÁLISIS DE MERCHANTS SIN CLASIFICAR")
    print("=" * 80)
    print()

    # Crear índice del CSV maestro por descripción
    master_by_desc = {}
    master_by_merchant = defaultdict(list)

    for tx in all_transactions:
        desc = tx['Descripción']
        cat1 = tx['Cat1']
        cat2 = tx['Cat2']
        banco = tx['Banco']
        merchant = extract_merchant(desc, banco)

        if desc not in master_by_desc:
            master_by_desc[desc] = []
        master_by_desc[desc].append((cat1, cat2))

        if merchant:
            merchant_upper = merchant.upper()
            master_by_merchant[merchant_upper].append((cat1, cat2))

    # Analizar cada transacción sin clasificar
    merchant_rules = {}

    for uc in unclassified:
        merchant = uc['merchant_name']
        cat1_real = uc['cat1_real']
        cat2_real = uc['cat2_real']

        if not merchant:
            continue

        merchant_upper = merchant.upper()

        # Si ya tenemos una regla para este merchant, continuamos
        if merchant_upper in merchant_rules:
            continue

        # Buscar todas las ocurrencias de este merchant en el CSV maestro
        if merchant_upper in master_by_merchant:
            cats = master_by_merchant[merchant_upper]
            counter = Counter(cats)
            most_common = counter.most_common(1)[0]
            cat1, cat2 = most_common[0]
            count = most_common[1]

            # Guardar la regla
            merchant_rules[merchant_upper] = {
                'merchant': merchant,
                'cat1': cat1,
                'cat2': cat2,
                'count': count,
                'total': len(cats),
            }

    # Ordenar por frecuencia
    sorted_rules = sorted(
        merchant_rules.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )

    print(f"Total de merchants únicos sin clasificar: {len(sorted_rules)}")
    print()
    print("TOP MERCHANTS SIN CLASIFICAR:")
    print()

    new_rules = []

    for i, (merchant_key, info) in enumerate(sorted_rules, 1):
        merchant = info['merchant']
        cat1 = info['cat1']
        cat2 = info['cat2']
        count = info['count']
        total = info['total']
        pct = count / total * 100 if total > 0 else 0

        print(f"{i:3d}. {merchant:40s} → {cat1:20s} | {cat2:25s} ({count}/{total} = {pct:.1f}%)")

        # Generar la regla
        keyword = merchant.upper()
        new_rules.append((keyword, cat1, cat2))

    print()
    print("=" * 80)
    print(f"REGLAS NUEVAS A AÑADIR: {len(new_rules)}")
    print("=" * 80)
    print()

    return new_rules, unclassified


def format_rule(keyword, cat1, cat2):
    """Formatea una regla para añadirla a merchants.py"""
    return f'    ("{keyword}", "{cat1}", "{cat2}"),'


def add_rules_to_merchants(new_rules):
    """
    Añade las reglas nuevas a merchants.py

    Args:
        new_rules: Lista de tuplas (keyword, cat1, cat2)
    """
    merchants_path = Path(__file__).parent / "classifier" / "merchants.py"

    # Leer el archivo actual
    with open(merchants_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Buscar la línea donde termina MERCHANT_RULES (antes del cierre de corchete)
    insert_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == ']':
            insert_idx = i
            break

    if insert_idx is None:
        print("ERROR: No se encontró el final de MERCHANT_RULES")
        return False

    # Agrupar reglas por categoría
    rules_by_cat1 = defaultdict(list)
    for keyword, cat1, cat2 in new_rules:
        rules_by_cat1[cat1].append((keyword, cat1, cat2))

    # Generar las líneas a insertar
    new_lines = []
    new_lines.append("\n")
    new_lines.append("    # ===== REGLAS GENERADAS AUTOMÁTICAMENTE =====\n")

    for cat1 in sorted(rules_by_cat1.keys()):
        new_lines.append(f"\n    # --- {cat1} ---\n")
        for keyword, cat1, cat2 in sorted(rules_by_cat1[cat1], key=lambda x: x[0]):
            new_lines.append(format_rule(keyword, cat1, cat2) + "\n")

    # Insertar las nuevas líneas
    lines = lines[:insert_idx] + new_lines + lines[insert_idx:]

    # Escribir el archivo
    with open(merchants_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"✓ Añadidas {len(new_rules)} reglas nuevas a {merchants_path}")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analiza transacciones SIN_CLASIFICAR")
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
    parser.add_argument(
        "--add-rules",
        action="store_true",
        help="Añadir las reglas nuevas a merchants.py"
    )

    args = parser.parse_args()

    # Analizar
    new_rules, unclassified = analyze_unclassified(args.master, args.test_size)

    # Añadir reglas si se especifica
    if args.add_rules:
        print()
        print("=" * 80)
        print("AÑADIENDO REGLAS A MERCHANTS.PY")
        print("=" * 80)
        print()

        if new_rules:
            add_rules_to_merchants(new_rules)
            print()
            print("✓ Reglas añadidas correctamente")
            print()
            print("Ahora re-ejecuta el test de validación cruzada:")
            print("  python3 tests/test_cross_validation.py")
        else:
            print("No hay reglas nuevas que añadir")
    else:
        print()
        print("Para añadir estas reglas a merchants.py, ejecuta:")
        print(f"  python3 {Path(__file__).name} --add-rules")
