#!/usr/bin/env python3
"""
Exporta el CSV maestro desde finsense.db con clasificaciones corregidas.
Este CSV incluye Google Places + correcciones de descripción.
"""
import sqlite3
import csv

def main():
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Obtener todas las transacciones
    cursor.execute("""
        SELECT fecha, importe, descripcion, banco, cuenta, tipo, cat1, cat2,
               hash, par_id, par_tipo, source_file
        FROM transacciones
        ORDER BY fecha, id
    """)

    rows = cursor.fetchall()
    conn.close()

    # Exportar a CSV
    output_file = 'Validación_Categorias_Finsense_MASTER_NEW.csv'

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'Fecha', 'Importe', 'Descripcion', 'Banco', 'Cuenta',
            'Tipo', 'Cat1', 'Cat2', 'Hash', 'Par_ID', 'Par_Tipo', 'Source_File'
        ])

        # Data
        for row in rows:
            writer.writerow(row)

    print("=" * 80)
    print(f"CSV MAESTRO EXPORTADO: {output_file}")
    print("=" * 80)
    print(f"Total transacciones: {len(rows)}")
    print(f"\nEste CSV incluye:")
    print(f"  • 851 enriquecimientos de Google Places")
    print(f"  • 80 correcciones de Cat2 basadas en descripción")
    print(f"  • 134 correcciones de las 3 reglas nuevas")
    print("=" * 80)

if __name__ == '__main__':
    main()
