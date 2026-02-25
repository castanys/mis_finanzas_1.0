#!/usr/bin/env python3
"""
CLI para clasificar transacciones individuales.

Uso:
    python classify.py "COMPRA EN MERCADONA, CON LA TARJETA..." "Openbank" -50.25
"""
import sys
from pathlib import Path
from classifier import Classifier


def main():
    if len(sys.argv) < 4:
        print("Uso: python classify.py <descripción> <banco> <importe>")
        print()
        print("Ejemplo:")
        print('  python classify.py "COMPRA EN MERCADONA, CON LA TARJETA..." "Openbank" -50.25')
        sys.exit(1)

    descripcion = sys.argv[1]
    banco = sys.argv[2]
    importe = sys.argv[3]

    # Inicializar clasificador
    master_csv = Path(__file__).parent / "Validación_Categorias_Finsense_04020206_5.csv"
    classifier = Classifier(str(master_csv))

    # Clasificar
    result = classifier.classify(descripcion, banco, importe)

    # Mostrar resultado
    print()
    print("RESULTADO:")
    print(f"  Cat1: {result['cat1']}")
    print(f"  Cat2: {result['cat2']}")
    print(f"  Tipo: {result['tipo']}")
    print(f"  Capa: {result['capa']}")
    print()


if __name__ == "__main__":
    main()
