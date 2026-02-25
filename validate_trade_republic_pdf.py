#!/usr/bin/env python3
"""
Validación del parser PDF de Trade Republic.

Compara las transacciones extraídas del PDF contra el CSV de 920 líneas.
"""
import sys
sys.path.insert(0, '/home/pablo/apps/mis_finanzas_1.0')

from parsers.trade_republic_pdf import TradeRepublicPDFParser
from parsers.trade_republic import TradeRepublicParser


def main():
    print("\n" + "=" * 100)
    print("VALIDACIÓN PARSER PDF TRADE REPUBLIC")
    print("=" * 100)

    # Parsear PDF
    print("\n📄 Parseando PDF...")
    pdf_parser = TradeRepublicPDFParser()
    try:
        pdf_records = pdf_parser.parse('input/Extracto de cuenta.pdf')
        print(f"  ✓ PDF parseado: {len(pdf_records)} transacciones")
    except Exception as e:
        print(f"  ✗ Error parseando PDF: {e}")
        import traceback
        traceback.print_exc()
        return

    # Parsear CSV
    print("\n📄 Parseando CSV...")
    csv_parser = TradeRepublicParser()
    try:
        csv_records = csv_parser.parse('input/TradeRepublic_ES8015860001420977164411.csv')
        print(f"  ✓ CSV parseado: {len(csv_records)} transacciones")
    except Exception as e:
        print(f"  ✗ Error parseando CSV: {e}")
        import traceback
        traceback.print_exc()
        return

    # Comparar conteos
    print("\n" + "=" * 100)
    print("COMPARACIÓN DE CONTEOS")
    print("=" * 100)
    print(f"Transacciones en PDF: {len(pdf_records)}")
    print(f"Transacciones en CSV: {len(csv_records)}")
    print(f"Diferencia:           {len(pdf_records) - len(csv_records):+d}")

    # Mostrar primeras 20 transacciones del PDF
    print("\n" + "=" * 100)
    print("PRIMERAS 20 TRANSACCIONES DEL PDF")
    print("=" * 100)
    print(f"{'Fecha':<12} {'Importe':>12} {'Descripción':<70}")
    print("-" * 100)
    for rec in pdf_records[:20]:
        print(f"{rec['fecha']:<12} {rec['importe']:>12.2f} {rec['descripcion'][:70]}")

    # Mostrar primeras 20 transacciones del CSV
    print("\n" + "=" * 100)
    print("PRIMERAS 20 TRANSACCIONES DEL CSV")
    print("=" * 100)
    print(f"{'Fecha':<12} {'Importe':>12} {'Descripción':<70}")
    print("-" * 100)
    for rec in csv_records[:20]:
        print(f"{rec['fecha']:<12} {rec['importe']:>12.2f} {rec['descripcion'][:70]}")

    # Crear índice para matching
    print("\n" + "=" * 100)
    print("MATCHING")
    print("=" * 100)

    # Índice por fecha+importe
    csv_index = {}
    for rec in csv_records:
        key = f"{rec['fecha']}|{rec['importe']:.2f}"
        if key not in csv_index:
            csv_index[key] = []
        csv_index[key].append(rec)

    pdf_index = {}
    for rec in pdf_records:
        key = f"{rec['fecha']}|{rec['importe']:.2f}"
        if key not in pdf_index:
            pdf_index[key] = []
        pdf_index[key].append(rec)

    # Buscar matches
    matches = 0
    pdf_only = []
    csv_only = []

    for key in pdf_index:
        if key in csv_index:
            matches += len(pdf_index[key])
        else:
            pdf_only.extend(pdf_index[key])

    for key in csv_index:
        if key not in pdf_index:
            csv_only.extend(csv_index[key])

    print(f"\nMatches (fecha+importe): {matches}")
    print(f"Solo en PDF:             {len(pdf_only)}")
    print(f"Solo en CSV:             {len(csv_only)}")

    # Mostrar transacciones solo en PDF
    if pdf_only:
        print("\n" + "=" * 100)
        print(f"TRANSACCIONES SOLO EN PDF (Primeras 50)")
        print("=" * 100)
        print(f"{'Fecha':<12} {'Importe':>12} {'Descripción':<70}")
        print("-" * 100)
        for rec in pdf_only[:50]:
            print(f"{rec['fecha']:<12} {rec['importe']:>12.2f} {rec['descripcion'][:70]}")

    # Mostrar transacciones solo en CSV
    if csv_only:
        print("\n" + "=" * 100)
        print(f"TRANSACCIONES SOLO EN CSV (Primeras 50)")
        print("=" * 100)
        print(f"{'Fecha':<12} {'Importe':>12} {'Descripción':<70}")
        print("-" * 100)
        for rec in csv_only[:50]:
            print(f"{rec['fecha']:<12} {rec['importe']:>12.2f} {rec['descripcion'][:70]}")

    # Resumen final
    print("\n" + "=" * 100)
    print("RESUMEN FINAL")
    print("=" * 100)
    print(f"PDF transacciones:       {len(pdf_records):,}")
    print(f"CSV transacciones:       {len(csv_records):,}")
    print(f"Matches:                 {matches:,}")
    print(f"Solo en PDF:             {len(pdf_only):,}")
    print(f"Solo en CSV:             {len(csv_only):,}")

    if len(pdf_records) == len(csv_records):
        print(f"\n✅ Mismo número de transacciones")
    else:
        diff = len(pdf_records) - len(csv_records)
        print(f"\n⚠️  Diferencia de {diff:+d} transacciones")

    match_rate = 100 * matches / max(len(pdf_records), len(csv_records))
    print(f"\nMatch rate: {match_rate:.1f}%")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
