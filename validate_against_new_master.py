#!/usr/bin/env python3
"""
Valida la precisión de Cat1, Cat2 y Tipo contra el nuevo CSV maestro.
"""
import sqlite3
import csv

def main():
    # Cargar nuevo maestro
    master = {}
    with open('Validación_Categorias_Finsense_MASTER_NEW.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['Fecha'], row['Importe'], row['Descripcion'], row['Banco'])
            master[key] = {
                'tipo': row['Tipo'],
                'cat1': row['Cat1'],
                'cat2': row['Cat2']
            }

    # Obtener transacciones actuales de la DB
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT fecha, importe, descripcion, banco, tipo, cat1, cat2
        FROM transacciones
    """)

    db_rows = cursor.fetchall()
    conn.close()

    # Contadores de precisión
    total = len(db_rows)
    cat1_correct = 0
    cat2_correct = 0
    tipo_correct = 0

    cat1_errors = []
    cat2_errors = []
    tipo_errors = []

    for fecha, importe, descripcion, banco, tipo_db, cat1_db, cat2_db in db_rows:
        key = (fecha, str(importe), descripcion, banco)

        if key in master:
            master_data = master[key]

            # Validar Cat1
            if cat1_db == master_data['cat1']:
                cat1_correct += 1
            else:
                cat1_errors.append({
                    'fecha': fecha,
                    'descripcion': descripcion[:50],
                    'db': cat1_db,
                    'master': master_data['cat1']
                })

            # Validar Cat2
            if cat2_db == master_data['cat2']:
                cat2_correct += 1
            else:
                cat2_errors.append({
                    'fecha': fecha,
                    'descripcion': descripcion[:50],
                    'db': cat2_db,
                    'master': master_data['cat2']
                })

            # Validar Tipo
            if tipo_db == master_data['tipo']:
                tipo_correct += 1
            else:
                tipo_errors.append({
                    'fecha': fecha,
                    'descripcion': descripcion[:50],
                    'db': tipo_db,
                    'master': master_data['tipo']
                })

    # Calcular porcentajes
    cat1_pct = (cat1_correct / total) * 100
    cat2_pct = (cat2_correct / total) * 100
    tipo_pct = (tipo_correct / total) * 100

    # Reporte
    print("=" * 80)
    print("VALIDACIÓN CONTRA NUEVO MAESTRO (CON GOOGLE PLACES + CORRECCIONES)")
    print("=" * 80)
    print(f"\nTotal transacciones: {total}\n")
    print(f"{'Métrica':12s} {'Correctas':>12s} {'Incorrectas':>12s} {'Precisión':>12s}")
    print("─" * 80)
    print(f"{'Cat1':12s} {cat1_correct:>12d} {total - cat1_correct:>12d} {cat1_pct:>11.2f}%")
    print(f"{'Cat2':12s} {cat2_correct:>12d} {total - cat2_correct:>12d} {cat2_pct:>11.2f}%")
    print(f"{'Tipo':12s} {tipo_correct:>12d} {total - tipo_correct:>12d} {tipo_pct:>11.2f}%")
    print("=" * 80)

    # Mostrar ejemplos de errores Cat2
    if cat2_errors:
        print(f"\nEJEMPLOS DE ERRORES Cat2 (primeros 10 de {len(cat2_errors)}):")
        print("─" * 80)
        for i, err in enumerate(cat2_errors[:10], 1):
            print(f"{i:2d}. {err['fecha']} | {err['descripcion']:50s}")
            print(f"    DB: '{err['db']}' | MASTER: '{err['master']}'")

    print("\n" + "=" * 80)
    print("VALIDACIÓN COMPLETADA")
    print("=" * 80)

if __name__ == '__main__':
    main()
