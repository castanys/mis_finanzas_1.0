"""
Test de validación cruzada del clasificador.
Separa las últimas N transacciones, las excluye del Exact Match,
y las clasifica solo con Capas 2-5.
"""
import csv
import sys
from pathlib import Path
from collections import defaultdict, Counter

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier.exact_match import build_exact_match_dict, lookup_exact
from classifier.merchants import lookup_merchant
from classifier.transfers import detect_transfer
from classifier.tokens import match_token
from classifier.valid_combos import validate_combination
from classifier.engine import determine_tipo
from extractors import extract_merchant


class CrossValidationClassifier:
    """
    Clasificador para validación cruzada.
    Permite construir el exact match excluyendo ciertas transacciones.
    """

    def __init__(self, train_transactions):
        """
        Inicializa el clasificador con transacciones de entrenamiento.

        Args:
            train_transactions: Lista de transacciones para construir exact match
        """
        # Construir exact match solo con transacciones de entrenamiento
        self.exact_match_dict = self._build_exact_match(train_transactions)
        print(f"✓ Exact Match construido con {len(self.exact_match_dict)} descripciones únicas")

    def _build_exact_match(self, transactions):
        """Construye diccionario de exact match desde lista de transacciones."""
        desc_classifications = {}

        for tx in transactions:
            desc = tx['Descripción']
            cat1 = tx['Cat1']
            cat2 = tx['Cat2']

            if desc not in desc_classifications:
                desc_classifications[desc] = []

            desc_classifications[desc].append((cat1, cat2))

        # Usar clasificación más frecuente para cada descripción
        exact_match = {}
        for desc, classifications in desc_classifications.items():
            counter = Counter(classifications)
            most_common = counter.most_common(1)[0][0]
            exact_match[desc] = most_common

        return exact_match

    def classify(self, descripcion, banco, importe):
        """
        Clasifica una transacción aplicando las 5 capas en orden.
        """
        merchant_name = extract_merchant(descripcion, banco)

        # === CAPA 1: Exact Match ===
        result = lookup_exact(descripcion, self.exact_match_dict)
        if result:
            cat1, cat2 = validate_combination(*result)
            tipo = determine_tipo(cat1, importe)
            return {
                'cat1': cat1,
                'cat2': cat2,
                'tipo': tipo,
                'capa': 1
            }

        # === CAPA 2: Merchant Lookup ===
        result = lookup_merchant(descripcion, merchant_name)
        if result:
            cat1, cat2 = validate_combination(*result)
            tipo = determine_tipo(cat1, importe)
            return {
                'cat1': cat1,
                'cat2': cat2,
                'tipo': tipo,
                'capa': 2
            }

        # === CAPA 3: Transfer Detection ===
        result = detect_transfer(descripcion, banco, importe)
        if result:
            cat1, cat2 = validate_combination(*result)
            tipo = determine_tipo(cat1, importe)
            return {
                'cat1': cat1,
                'cat2': cat2,
                'tipo': tipo,
                'capa': 3
            }

        # === CAPA 4: Token Heurístico ===
        result = match_token(descripcion)
        if result:
            cat1, cat2 = validate_combination(*result)
            tipo = determine_tipo(cat1, importe)
            return {
                'cat1': cat1,
                'cat2': cat2,
                'tipo': tipo,
                'capa': 4
            }

        # === CAPA 5: SIN_CLASIFICAR ===
        return {
            'cat1': 'SIN_CLASIFICAR',
            'cat2': '',
            'tipo': '',
            'capa': 5
        }


def test_cross_validation(master_csv_path, test_size=1000):
    """
    Test de validación cruzada.

    Args:
        master_csv_path: Ruta al CSV maestro
        test_size: Número de transacciones a usar como test
    """
    print("=" * 80)
    print("TEST DE VALIDACIÓN CRUZADA")
    print("=" * 80)
    print()

    # Leer todas las transacciones
    all_transactions = []
    with open(master_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            all_transactions.append(row)

    total = len(all_transactions)
    print(f"Total de transacciones en CSV maestro: {total:,}")

    # Separar train/test: las últimas test_size para test
    train_transactions = all_transactions[:-test_size]
    test_transactions = all_transactions[-test_size:]

    print(f"Transacciones de entrenamiento: {len(train_transactions):,}")
    print(f"Transacciones de test: {len(test_transactions):,}")
    print()

    # Inicializar clasificador con solo train_transactions
    classifier = CrossValidationClassifier(train_transactions)
    print()

    # Clasificar transacciones de test
    results = {
        'total': len(test_transactions),
        'cat1_correct': 0,
        'cat1_cat2_correct': 0,
        'clasificadas': 0,
        'sin_clasificar': 0,
        'errors': [],
        'capa_stats': defaultdict(int),
        'cat1_errors': Counter(),
        'cat1_cat2_errors': Counter(),
    }

    print("Clasificando transacciones de test...")
    for i, tx in enumerate(test_transactions):
        if (i + 1) % 100 == 0:
            print(f"  Procesadas {i + 1:,} / {len(test_transactions):,} ({(i + 1) / len(test_transactions) * 100:.1f}%)")

        descripcion = tx['Descripción']
        banco = tx['Banco']
        importe = tx['Importe']
        cat1_real = tx['Cat1']
        cat2_real = tx['Cat2']

        # Clasificar
        pred = classifier.classify(descripcion, banco, importe)
        cat1_pred = pred['cat1']
        cat2_pred = pred['cat2']
        capa = pred['capa']

        # Estadísticas por capa
        results['capa_stats'][capa] += 1

        # Contar clasificadas vs sin clasificar
        if cat1_pred == 'SIN_CLASIFICAR':
            results['sin_clasificar'] += 1
        else:
            results['clasificadas'] += 1

        # Verificar Cat1
        if cat1_pred == cat1_real:
            results['cat1_correct'] += 1
        else:
            # Guardar error
            error_key = f"{cat1_real} → {cat1_pred}"
            results['cat1_errors'][error_key] += 1

            if len(results['errors']) < 100:  # Guardar primeros 100 errores
                results['errors'].append({
                    'descripcion': descripcion,
                    'banco': banco,
                    'importe': importe,
                    'cat1_real': cat1_real,
                    'cat2_real': cat2_real,
                    'cat1_pred': cat1_pred,
                    'cat2_pred': cat2_pred,
                    'capa': capa,
                })

        # Verificar Cat1 + Cat2
        if cat1_pred == cat1_real and cat2_pred == cat2_real:
            results['cat1_cat2_correct'] += 1
        else:
            error_key = f"{cat1_real}|{cat2_real} → {cat1_pred}|{cat2_pred}"
            results['cat1_cat2_errors'][error_key] += 1

    print()
    print("=" * 80)
    print("RESULTADOS DE VALIDACIÓN CRUZADA")
    print("=" * 80)
    print()

    # Métricas principales
    total_test = results['total']
    cat1_accuracy_clasificadas = results['cat1_correct'] / results['clasificadas'] * 100 if results['clasificadas'] > 0 else 0
    cat1_cat2_accuracy_clasificadas = results['cat1_cat2_correct'] / results['clasificadas'] * 100 if results['clasificadas'] > 0 else 0
    pct_clasificadas = results['clasificadas'] / total_test * 100
    cat1_accuracy_total = results['cat1_correct'] / total_test * 100

    print("MÉTRICAS PRINCIPALES:")
    print(f"  Cat1 accuracy (clasificadas):        {cat1_accuracy_clasificadas:.2f}% ({results['cat1_correct']:,} / {results['clasificadas']:,})")
    print(f"  Cat1+Cat2 accuracy (clasificadas):   {cat1_cat2_accuracy_clasificadas:.2f}% ({results['cat1_cat2_correct']:,} / {results['clasificadas']:,})")
    print(f"  % clasificadas (no SIN_CLASIFICAR):  {pct_clasificadas:.2f}% ({results['clasificadas']:,} / {total_test:,})")
    print(f"  Cat1 accuracy total:                 {cat1_accuracy_total:.2f}% ({results['cat1_correct']:,} / {total_test:,})")
    print()

    # Estadísticas por capa
    print("COBERTURA POR CAPA (solo en transacciones de test):")
    for capa in sorted(results['capa_stats'].keys()):
        count = results['capa_stats'][capa]
        pct = count / total_test * 100
        capa_name = {
            1: "Capa 1 (Exact Match)",
            2: "Capa 2 (Merchants)",
            3: "Capa 3 (Transfers)",
            4: "Capa 4 (Tokens)",
            5: "Capa 5 (SIN_CLASIFICAR)"
        }.get(capa, f"Capa {capa}")
        print(f"  {capa_name:30s}: {count:6,} ({pct:5.2f}%)")
    print()

    # Estadísticas de capas 2-5 (sin exact match)
    capas_2_5 = sum(results['capa_stats'][i] for i in [2, 3, 4, 5])
    if capas_2_5 > 0:
        print("RENDIMIENTO DE CAPAS 2-5 (sin Exact Match):")
        cat1_correct_2_5 = 0
        cat1_cat2_correct_2_5 = 0
        clasificadas_2_5 = 0

        # Re-contar solo para capas 2-5
        for tx in test_transactions:
            descripcion = tx['Descripción']
            banco = tx['Banco']
            importe = tx['Importe']
            cat1_real = tx['Cat1']
            cat2_real = tx['Cat2']

            pred = classifier.classify(descripcion, banco, importe)
            if pred['capa'] in [2, 3, 4, 5]:
                if pred['cat1'] != 'SIN_CLASIFICAR':
                    clasificadas_2_5 += 1
                if pred['cat1'] == cat1_real:
                    cat1_correct_2_5 += 1
                if pred['cat1'] == cat1_real and pred['cat2'] == cat2_real:
                    cat1_cat2_correct_2_5 += 1

        if clasificadas_2_5 > 0:
            cat1_acc_2_5 = cat1_correct_2_5 / clasificadas_2_5 * 100
            cat1_cat2_acc_2_5 = cat1_cat2_correct_2_5 / clasificadas_2_5 * 100
            pct_clas_2_5 = clasificadas_2_5 / capas_2_5 * 100
            print(f"  Transacciones procesadas por Capas 2-5: {capas_2_5:,}")
            print(f"  Cat1 accuracy (Capas 2-5):               {cat1_acc_2_5:.2f}% ({cat1_correct_2_5:,} / {clasificadas_2_5:,})")
            print(f"  Cat1+Cat2 accuracy (Capas 2-5):          {cat1_cat2_acc_2_5:.2f}% ({cat1_cat2_correct_2_5:,} / {clasificadas_2_5:,})")
            print(f"  % clasificadas (Capas 2-5):              {pct_clas_2_5:.2f}% ({clasificadas_2_5:,} / {capas_2_5:,})")
        print()

    # Errores más comunes en Cat1
    print("TOP 20 ERRORES EN CAT1:")
    for error, count in results['cat1_errors'].most_common(20):
        print(f"  {count:4,}x  {error}")
    print()

    # Errores más comunes en Cat1+Cat2
    print("TOP 20 ERRORES EN CAT1|CAT2:")
    for error, count in results['cat1_cat2_errors'].most_common(20):
        print(f"  {count:4,}x  {error}")
    print()

    # Ejemplos de errores
    if results['errors']:
        print("EJEMPLOS DE ERRORES (primeros 30):")
        for i, err in enumerate(results['errors'][:30], 1):
            print(f"{i}. [{err['banco']}] {err['descripcion']}")
            print(f"   Real: {err['cat1_real']}|{err['cat2_real']}")
            print(f"   Pred: {err['cat1_pred']}|{err['cat2_pred']} (Capa {err['capa']})")
            print()

    # Evaluación vs objetivos
    print("=" * 80)
    print("EVALUACIÓN VS OBJETIVOS")
    print("=" * 80)
    print()

    objectives = {
        "Cat1 accuracy (clasificadas)": {
            "value": cat1_accuracy_clasificadas,
            "objetivo": 95,
            "aceptable": 92,
        },
        "Cat1+Cat2 accuracy (clasificadas)": {
            "value": cat1_cat2_accuracy_clasificadas,
            "objetivo": 85,
            "aceptable": 80,
        },
        "% clasificadas": {
            "value": pct_clasificadas,
            "objetivo": 90,
            "aceptable": 85,
        },
        "Cat1 accuracy total": {
            "value": cat1_accuracy_total,
            "objetivo": 85,
            "aceptable": 80,
        },
    }

    for metric, values in objectives.items():
        value = values["value"]
        objetivo = values["objetivo"]
        aceptable = values["aceptable"]

        if value >= objetivo:
            status = "✓ OBJETIVO ALCANZADO"
        elif value >= aceptable:
            status = "~ Aceptable"
        else:
            status = "✗ Por debajo de lo aceptable"

        print(f"{metric:35s}: {value:6.2f}%  [{status}]")

    print()

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test de validación cruzada")
    parser.add_argument(
        "--master",
        default="Validación_Categorias_Finsense_04020206_5.csv",
        help="Ruta al CSV maestro"
    )
    parser.add_argument(
        "--test-size",
        type=int,
        default=1000,
        help="Número de transacciones a usar como test (default: 1000)"
    )

    args = parser.parse_args()

    test_cross_validation(args.master, args.test_size)
