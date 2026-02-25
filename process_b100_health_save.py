#!/usr/bin/env python3
"""
Procesa archivos B100 Health y Save de Enablebanking:
1. Parsea los CSVs
2. Clasifica las transacciones
3. Verifica que todas salen como TRANSFERENCIA/Interna
4. Muestra diagnóstico antes de insertar
"""
import sys
sys.path.append('src/parsers')

from enablebanking import EnablebankingParser
from classifier.engine import Classifier

def main():
    # Archivos a procesar
    files = [
        ('input/new/enable_abanca_ES66208001000130433834434_EUR_20260214-221642.csv', 'Health'),
        ('input/new/enable_abanca_ES95208001000830433834442_EUR_20260214-221634.csv', 'Save'),
    ]

    parser = EnablebankingParser()
    classifier = Classifier('Validación_Categorias_Finsense_MASTER_NEW.csv')

    print("=" * 80)
    print("PROCESAMIENTO B100 HEALTH & SAVE - DIAGNÓSTICO")
    print("=" * 80)

    all_transactions = []

    for file_path, account_type in files:
        print(f"\n📁 Procesando {account_type}: {file_path.split('/')[-1]}")
        print("─" * 80)

        # Parsear
        transactions = parser.parse(file_path)
        print(f"✅ Parseadas: {len(transactions)} transacciones")

        if transactions:
            # Mostrar IBAN y banco
            print(f"   IBAN: {transactions[0]['cuenta']}")
            print(f"   Banco: {transactions[0]['banco']}")

            # Clasificar y diagnosticar
            cat1_counts = {}
            tipo_counts = {}
            errors = []

            for tx in transactions:
                # Clasificar
                result = classifier.classify(
                    descripcion=tx['concepto'],
                    banco=tx['banco'],
                    importe=tx['importe'],
                    fecha=str(tx['fecha'])
                )

                # Guardar clasificación
                tx['cat1'] = result['cat1']
                tx['cat2'] = result['cat2']
                tx['tipo'] = result['tipo']
                tx['capa'] = result['capa']

                # Contar
                cat1_counts[result['cat1']] = cat1_counts.get(result['cat1'], 0) + 1
                tipo_counts[result['tipo']] = tipo_counts.get(result['tipo'], 0) + 1

                # Detectar errores (no es TRANSFERENCIA/Interna)
                if result['tipo'] != 'TRANSFERENCIA' or result['cat1'] != 'Interna':
                    errors.append({
                        'fecha': tx['fecha'],
                        'importe': tx['importe'],
                        'concepto': tx['concepto'][:50],
                        'tipo': result['tipo'],
                        'cat1': result['cat1']
                    })

            # Mostrar estadísticas
            print(f"\n   📊 Clasificación por Cat1:")
            for cat1, count in sorted(cat1_counts.items(), key=lambda x: -x[1]):
                print(f"      • {cat1:20s}: {count:>3d}")

            print(f"\n   📊 Clasificación por Tipo:")
            for tipo, count in sorted(tipo_counts.items(), key=lambda x: -x[1]):
                print(f"      • {tipo:20s}: {count:>3d}")

            # Mostrar errores
            if errors:
                print(f"\n   ⚠️  {len(errors)} transacciones NO son TRANSFERENCIA/Interna:")
                for i, err in enumerate(errors[:10], 1):
                    status = "✗"
                    print(f"      {status} {err['fecha']} | €{err['importe']:>8.2f} | "
                          f"{err['tipo']:15s} | {err['cat1']:15s} | {err['concepto']}")
                if len(errors) > 10:
                    print(f"      ... y {len(errors) - 10} más")
            else:
                print(f"\n   ✅ TODAS las transacciones son TRANSFERENCIA/Interna")

            all_transactions.extend(transactions)

    # Resumen global
    print("\n" + "=" * 80)
    print("RESUMEN GLOBAL")
    print("=" * 80)
    print(f"Total transacciones: {len(all_transactions)}")

    # Contar errores globales
    total_errors = sum(
        1 for tx in all_transactions
        if tx['tipo'] != 'TRANSFERENCIA' or tx['cat1'] != 'Interna'
    )

    if total_errors == 0:
        print("✅ TODAS las transacciones se clasifican como TRANSFERENCIA/Interna")
        print("\n⚠️  PERO ESTO ES INCORRECTO - Los traspasos B100 Health/Save DEBEN ser Interna")
        print("⚠️  Necesitamos añadir una REGLA al clasificador para forzar esto")
    else:
        print(f"⚠️  {total_errors} transacciones NO se clasifican como TRANSFERENCIA/Interna")
        print("⚠️  Necesitamos añadir una REGLA al clasificador")

    print("=" * 80)

if __name__ == '__main__':
    main()
