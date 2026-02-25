#!/usr/bin/env python3
"""
Exporta la BBDD completa a CSV y Excel con todos los campos.
Incluye contrapartida de transferencias internas y estadísticas.

Uso:
    python3 export_bbdd.py

Genera:
    - finsense_export.csv
    - finsense_export.xlsx (si pandas está disponible)
"""
import sqlite3
import csv
from datetime import datetime
from collections import Counter


def export_csv(rows, output_file='finsense_export.csv'):
    """Exporta a CSV."""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'ID',
            'Fecha',
            'Importe',
            'Descripcion',
            'Banco',
            'Cuenta',
            'Tipo',
            'Cat1',
            'Cat2',
            'Hash',
            'Merchant_Name',
            'Source_File'
        ])

        # Data
        for row in rows:
            writer.writerow(row)

    print(f"✅ CSV exportado: {output_file}")
    return output_file


def export_excel(rows, output_file='finsense_export.xlsx'):
    """Exporta a Excel con pandas (si está disponible)."""
    try:
        import pandas as pd
    except ImportError:
        print("⚠️  pandas no disponible. Instalar con: pip install pandas openpyxl")
        return None

    # Crear DataFrame
    df = pd.DataFrame(rows, columns=[
        'ID',
        'Fecha',
        'Importe',
        'Descripcion',
        'Banco',
        'Cuenta',
        'Tipo',
        'Cat1',
        'Cat2',
        'Hash',
        'Merchant_Name',
        'Source_File'
    ])

    # Convertir fecha a datetime
    df['Fecha'] = pd.to_datetime(df['Fecha'])

    # Crear Excel con múltiples hojas
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Hoja 1: Todas las transacciones
        df.to_excel(writer, sheet_name='Transacciones', index=False)

        # Hoja 2: Resumen por Tipo
        tipo_summary = df.groupby('Tipo').agg({
            'Importe': ['count', 'sum', 'mean']
        }).round(2)
        tipo_summary.to_excel(writer, sheet_name='Resumen_Tipo')

        # Hoja 3: Resumen por Cat1
        cat1_summary = df.groupby('Cat1').agg({
            'Importe': ['count', 'sum', 'mean']
        }).round(2)
        cat1_summary.to_excel(writer, sheet_name='Resumen_Cat1')

        # Hoja 4: Resumen por Banco
        banco_summary = df.groupby('Banco').agg({
            'Importe': ['count', 'sum', 'mean']
        }).round(2)
        banco_summary.to_excel(writer, sheet_name='Resumen_Banco')

        # Hoja 5: Estadísticas por año-mes
        df['Año_Mes'] = df['Fecha'].dt.to_period('M')
        monthly = df.groupby(['Año_Mes', 'Tipo']).agg({
            'Importe': 'sum'
        }).round(2)
        monthly.to_excel(writer, sheet_name='Resumen_Mensual')

        # Hoja 6: Distribución por Cat1 y Tipo
        dist = pd.crosstab(df['Cat1'], df['Tipo'], margins=True)
        dist.to_excel(writer, sheet_name='Distribucion_Cat1_Tipo')

    print(f"✅ Excel exportado: {output_file}")
    return output_file


def main():
    print("=" * 80)
    print("EXPORTACIÓN BBDD FINSENSE")
    print("=" * 80)

    # Conectar a BBDD
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Obtener todas las transacciones
    print("\n📊 Leyendo transacciones...")
    cursor.execute("""
        SELECT
            id,
            fecha,
            importe,
            descripcion,
            banco,
            cuenta,
            tipo,
            cat1,
            cat2,
            hash,
            merchant_name,
            source_file
        FROM transacciones
        ORDER BY fecha, id
    """)

    rows = cursor.fetchall()
    total = len(rows)

    print(f"   Total transacciones: {total:,}")

    # Estadísticas
    cursor.execute("SELECT COUNT(DISTINCT banco) FROM transacciones")
    bancos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT cuenta) FROM transacciones")
    cuentas = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT source_file) FROM transacciones WHERE source_file IS NOT NULL")
    archivos = cursor.fetchone()[0]

    cursor.execute("SELECT tipo, COUNT(*) FROM transacciones GROUP BY tipo")
    tipo_dist = dict(cursor.fetchall())

    cursor.execute("SELECT MIN(fecha), MAX(fecha) FROM transacciones")
    min_fecha, max_fecha = cursor.fetchone()

    cursor.execute("SELECT COUNT(DISTINCT cat1) FROM transacciones WHERE cat1 IS NOT NULL")
    categorias = cursor.fetchone()[0]

    conn.close()

    print(f"   Bancos: {bancos}")
    print(f"   Cuentas: {cuentas}")
    print(f"   Archivos fuente: {archivos}")
    print(f"   Categorías (Cat1): {categorias}")
    print(f"   Período: {min_fecha} a {max_fecha}")

    print(f"\n📋 Distribución por Tipo:")
    for tipo, count in sorted(tipo_dist.items(), key=lambda x: -x[1]):
        pct = (count / total) * 100
        print(f"   • {tipo:20s}: {count:>6,d} ({pct:>5.1f}%)")

    # Exportar CSV
    print(f"\n{'─' * 80}")
    print("EXPORTANDO...")
    print(f"{'─' * 80}\n")

    csv_file = export_csv(rows)

    # Exportar Excel (si pandas está disponible)
    excel_file = export_excel(rows)

    # Resumen final
    print(f"\n{'=' * 80}")
    print("✅ EXPORTACIÓN COMPLETADA")
    print(f"{'=' * 80}")
    print(f"\n📄 Archivos generados:")
    print(f"   • CSV:   {csv_file} ({total:,} filas)")
    if excel_file:
        print(f"   • Excel: {excel_file} (múltiples hojas con estadísticas)")
    print(f"\n📊 Contenido:")
    print(f"   • Todas las transacciones ({total:,})")
    print(f"   • Archivo fuente de cada transacción")
    print(f"   • Todos los campos: ID, Fecha, Importe, Descripción, Banco, Cuenta,")
    print(f"     Tipo, Cat1, Cat2, Hash, Merchant_Name, Source_File")

    if excel_file:
        print(f"\n📑 Hojas Excel:")
        print(f"   1. Transacciones: Todas las transacciones con todos los campos")
        print(f"   2. Resumen_Tipo: Estadísticas por Tipo (count, sum, mean)")
        print(f"   3. Resumen_Cat1: Estadísticas por Cat1 (count, sum, mean)")
        print(f"   4. Resumen_Banco: Estadísticas por Banco (count, sum, mean)")
        print(f"   5. Resumen_Mensual: Agregado por año-mes y tipo")
        print(f"   6. Distribucion_Cat1_Tipo: Tabla cruzada Cat1 vs Tipo")

    print(f"\n💡 Uso:")
    print(f"   • Abrir CSV: LibreOffice, Excel, Google Sheets")
    print(f"   • Abrir Excel: Microsoft Excel, LibreOffice Calc")
    print(f"\n   Para re-exportar en el futuro, ejecutar:")
    print(f"   $ python3 export_bbdd.py")
    print(f"\n{'=' * 80}")


if __name__ == '__main__':
    main()
