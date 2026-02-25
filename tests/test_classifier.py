"""
Test del clasificador contra el CSV maestro.
Genera métricas de precisión.
"""
import csv
import sys
from pathlib import Path
from collections import defaultdict, Counter

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier import Classifier


def test_classifier(master_csv_path):
    """
    Prueba el clasificador contra todas las transacciones del CSV maestro.

    Args:
        master_csv_path: Ruta al CSV maestro

    Returns:
        Diccionario con métricas y resultados
    """
    print("=" * 80)
    print("TESTING CLASIFICADOR DE TRANSACCIONES")
    print("=" * 80)
    print()

    # Inicializar clasificador
    classifier = Classifier(master_csv_path)
    print()

    # Leer CSV maestro
    transactions = []
    with open(master_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            transactions.append(row)

    total = len(transactions)
    print(f"Total de transacciones a clasificar: {total:,}")
    print()

    # Clasificar todas las transacciones
    results = {
        'total': total,
        'cat1_correct': 0,
        'cat1_cat2_correct': 0,
        'clasificadas': 0,
        'sin_clasificar': 0,
        'errors': [],
        'capa_stats': defaultdict(int),
        'cat1_errors': Counter(),
        'cat1_cat2_errors': Counter(),
    }

    print("Clasificando transacciones...")
    for i, tx in enumerate(transactions):
        if (i + 1) % 1000 == 0:
            print(f"  Procesadas {i + 1:,} / {total:,} ({(i + 1) / total * 100:.1f}%)")

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
    print("RESULTADOS")
    print("=" * 80)
    print()

    # Métricas principales
    cat1_accuracy_clasificadas = results['cat1_correct'] / results['clasificadas'] * 100 if results['clasificadas'] > 0 else 0
    cat1_cat2_accuracy_clasificadas = results['cat1_cat2_correct'] / results['clasificadas'] * 100 if results['clasificadas'] > 0 else 0
    pct_clasificadas = results['clasificadas'] / total * 100
    cat1_accuracy_total = results['cat1_correct'] / total * 100

    print("MÉTRICAS PRINCIPALES:")
    print(f"  Cat1 accuracy (clasificadas):        {cat1_accuracy_clasificadas:.2f}% ({results['cat1_correct']:,} / {results['clasificadas']:,})")
    print(f"  Cat1+Cat2 accuracy (clasificadas):   {cat1_cat2_accuracy_clasificadas:.2f}% ({results['cat1_cat2_correct']:,} / {results['clasificadas']:,})")
    print(f"  % clasificadas (no SIN_CLASIFICAR):  {pct_clasificadas:.2f}% ({results['clasificadas']:,} / {total:,})")
    print(f"  Cat1 accuracy total:                 {cat1_accuracy_total:.2f}% ({results['cat1_correct']:,} / {total:,})")
    print()

    # Estadísticas por capa
    print("COBERTURA POR CAPA:")
    for capa in sorted(results['capa_stats'].keys()):
        count = results['capa_stats'][capa]
        pct = count / total * 100
        capa_name = {
            1: "Capa 1 (Exact Match)",
            2: "Capa 2 (Merchants)",
            3: "Capa 3 (Transfers)",
            4: "Capa 4 (Tokens)",
            5: "Capa 5 (SIN_CLASIFICAR)"
        }.get(capa, f"Capa {capa}")
        print(f"  {capa_name:30s}: {count:6,} ({pct:5.2f}%)")
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
        print("EJEMPLOS DE ERRORES (primeros 20):")
        for i, err in enumerate(results['errors'][:20], 1):
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

    parser = argparse.ArgumentParser(description="Test del clasificador")
    parser.add_argument(
        "--master",
        default="Validación_Categorias_Finsense_04020206_5.csv",
        help="Ruta al CSV maestro"
    )

    args = parser.parse_args()

    test_classifier(args.master)
