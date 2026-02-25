#!/usr/bin/env python3
"""
Test manual de parsers sin pytest.
"""
import os
import sys
from parsers import (
    OpenbankParser,
    MyInvestorParser,
    MediolanumParser,
    RevolutParser,
    TradeRepublicParser,
    B100Parser,
    AbancaParser,
)

INPUT_DIR = 'input'

def test_parser(parser_class, filename):
    """Test un parser específico."""
    parser = parser_class()
    filepath = os.path.join(INPUT_DIR, filename)

    if not os.path.exists(filepath):
        print(f"  ⚠️  Archivo no encontrado: {filename}")
        return None

    try:
        records = parser.parse(filepath)
        print(f"  ✓ {parser.BANK_NAME:20s} {filename:50s} → {len(records):4d} transacciones")

        if records:
            # Validaciones básicas
            assert all('fecha' in r for r in records), "Falta campo 'fecha'"
            assert all('importe' in r for r in records), "Falta campo 'importe'"
            assert all('descripcion' in r for r in records), "Falta campo 'descripcion'"
            assert all('banco' in r for r in records), "Falta campo 'banco'"
            assert all('cuenta' in r for r in records), "Falta campo 'cuenta'"
            assert all('hash' in r for r in records), "Falta campo 'hash'"

            # Mostrar ejemplo
            r = records[0]
            print(f"      Ejemplo: {r['fecha']} | €{r['importe']:10.2f} | {r['descripcion'][:50]}")

        return records
    except Exception as e:
        print(f"  ✗ {parser.BANK_NAME:20s} {filename:50s} → ERROR: {e}")
        return None


def main():
    print("\n" + "=" * 100)
    print("TEST MANUAL DE PARSERS")
    print("=" * 100)

    # Test cada parser con sus archivos
    tests = [
        (OpenbankParser, 'openbank_ES2200730100510135698457.csv'),
        (OpenbankParser, 'Openbank_ES3600730100550435513660.csv'),
        (MyInvestorParser, 'MyInvestor_ES5215447889746650686253.csv'),
        (MyInvestorParser, 'Myinvestor_ES6015447889796650683633.csv'),
        (MyInvestorParser, 'MyInvestor_ES6115447889736650701175.csv'),
        (MediolanumParser, 'mediolanum_ES2501865001680510084831.csv'),
        (RevolutParser, 'Revolut_ES1215830001199090471794.csv'),
        (TradeRepublicParser, 'TradeRepublic_ES8015860001420977164411.csv'),
        (B100Parser, 'MovimientosB100_ES88208001000130433834426.csv'),
        (AbancaParser, 'ABANCA_ES5120800823473040166463.csv'),
    ]

    print("\n📝 Testeando parsers individuales:\n")

    total_records = 0
    success_count = 0

    for parser_class, filename in tests:
        records = test_parser(parser_class, filename)
        if records is not None:
            success_count += 1
            total_records += len(records)

    print("\n" + "-" * 100)
    print(f"✓ {success_count}/{len(tests)} parsers OK | Total: {total_records} transacciones parseadas")
    print("-" * 100)

    # Test conversión de números españoles
    print("\n📊 Test conversión números españoles:\n")
    from parsers.base import BankParser

    test_numbers = [
        ('2.210,00', 2210.00),
        ('-1.500,50', -1500.50),
        ('0,59', 0.59),
        ('-175,00', -175.00),
        ('4027,67', 4027.67),
    ]

    for input_str, expected in test_numbers:
        result = BankParser.parse_spanish_number(input_str)
        status = "✓" if abs(result - expected) < 0.01 else "✗"
        print(f"  {status} '{input_str}' → {result} (esperado: {expected})")

    # Test conversión de fechas
    print("\n📅 Test conversión de fechas:\n")

    test_dates = [
        ('11/11/2025', '2025-11-11'),
        ('03/05/2025', '2025-05-03'),
        ('29-12-2025', '2025-12-29'),
        ('2023-10-09', '2023-10-09'),
        ('02/07/2019 17:19', '2019-07-02'),
    ]

    for input_str, expected in test_dates:
        result = BankParser.convert_date_to_iso(input_str)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{input_str}' → '{result}' (esperado: '{expected}')")

    # Test extracción IBAN
    print("\n🏦 Test extracción IBAN:\n")

    test_ibans = [
        ('openbank_ES2200730100510135698457.csv', 'ES2200730100510135698457'),
        ('MyInvestor_ES5215447889746650686253.csv', 'ES5215447889746650686253'),
        ('Revolut_ES1215830001199090471794.csv', 'ES1215830001199090471794'),
    ]

    for filename, expected in test_ibans:
        result = BankParser.extract_iban_from_filename(filename)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{filename}' → '{result}'")

    print("\n" + "=" * 100)
    print("✅ Tests completados")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
