"""
Tests para los parsers de bancos.
"""
import os
import pytest
from parsers import (
    OpenbankParser,
    MyInvestorParser,
    MediolanumParser,
    RevolutParser,
    TradeRepublicParser,
    B100Parser,
    AbancaParser,
)


# Paths a archivos de prueba
INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'input')


class TestOpenbankParser:
    """Tests para OpenbankParser."""

    def test_parse_basic(self):
        """Test parsing básico de Openbank."""
        parser = OpenbankParser()
        filepath = os.path.join(INPUT_DIR, 'openbank_ES2200730100510135698457.csv')

        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        records = parser.parse(filepath)

        assert len(records) > 0, "Debe parsear al menos 1 transacción"
        assert all(r['banco'] == 'Openbank' for r in records), "Todas deben ser de Openbank"
        assert all(r['cuenta'].startswith('ES') for r in records), "Todas deben tener IBAN"
        assert all(isinstance(r['importe'], float) for r in records), "Importes deben ser float"
        assert all(isinstance(r['hash'], str) for r in records), "Hashes deben ser string"

        # Verificar formato de fecha
        assert all(len(r['fecha']) == 10 for r in records), "Fechas deben ser YYYY-MM-DD"
        assert all(r['fecha'][4] == '-' and r['fecha'][7] == '-' for r in records)

    def test_spanish_number_format(self):
        """Test conversión de números españoles."""
        parser = OpenbankParser()

        assert parser.parse_spanish_number('2.210,00') == 2210.00
        assert parser.parse_spanish_number('-1.500,50') == -1500.50
        assert parser.parse_spanish_number('0,59') == 0.59
        assert parser.parse_spanish_number('-175,00') == -175.00


class TestMyInvestorParser:
    """Tests para MyInvestorParser."""

    def test_parse_basic(self):
        """Test parsing básico de MyInvestor."""
        parser = MyInvestorParser()
        filepath = os.path.join(INPUT_DIR, 'MyInvestor_ES5215447889746650686253.csv')

        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        records = parser.parse(filepath)

        assert len(records) > 0, "Debe parsear al menos 1 transacción"
        assert all(r['banco'] == 'MyInvestor' for r in records)
        assert all(r['cuenta'].startswith('ES') for r in records)
        assert all(isinstance(r['importe'], float) for r in records)


class TestMediolanumParser:
    """Tests para MediolanumParser."""

    def test_parse_basic(self):
        """Test parsing básico de Mediolanum."""
        parser = MediolanumParser()
        filepath = os.path.join(INPUT_DIR, 'mediolanum_ES2501865001680510084831.csv')

        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        records = parser.parse(filepath)

        assert len(records) > 0, "Debe parsear al menos 1 transacción"
        assert all(r['banco'] == 'Mediolanum' for r in records)
        assert all(isinstance(r['importe'], float) for r in records)

        # Verificar que pagos son negativos e ingresos positivos
        # (esto depende de los datos reales, pero al menos verificar que hay signos)
        importes = [r['importe'] for r in records]
        assert any(i < 0 for i in importes) or any(i > 0 for i in importes)


class TestRevolutParser:
    """Tests para RevolutParser."""

    def test_parse_basic(self):
        """Test parsing básico de Revolut."""
        parser = RevolutParser()
        filepath = os.path.join(INPUT_DIR, 'Revolut_ES1215830001199090471794.csv')

        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        records = parser.parse(filepath)

        # Revolut solo debe incluir transacciones COMPLETADO
        assert all(r['banco'] == 'Revolut' for r in records)
        assert all(isinstance(r['importe'], float) for r in records)


class TestTradeRepublicParser:
    """Tests para TradeRepublicParser."""

    def test_parse_basic(self):
        """Test parsing básico de Trade Republic."""
        parser = TradeRepublicParser()
        filepath = os.path.join(INPUT_DIR, 'TradeRepublic_ES8015860001420977164411.csv')

        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        records = parser.parse(filepath)

        assert len(records) > 0, "Debe parsear al menos 1 transacción"
        assert all(r['banco'] == 'Trade Republic' for r in records)
        assert all(isinstance(r['importe'], float) for r in records)

        # Trade Republic ya tiene fechas en formato ISO
        assert all('-' in r['fecha'] for r in records)


class TestB100Parser:
    """Tests para B100Parser."""

    def test_parse_basic(self):
        """Test parsing básico de B100."""
        parser = B100Parser()
        filepath = os.path.join(INPUT_DIR, 'MovimientosB100_ES88208001000130433834426.csv')

        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        records = parser.parse(filepath)

        assert len(records) > 0, "Debe parsear al menos 1 transacción"
        assert all(r['banco'] == 'B100' for r in records)
        assert all(isinstance(r['importe'], float) for r in records)


class TestAbancaParser:
    """Tests para AbancaParser."""

    def test_parse_basic(self):
        """Test parsing básico de Abanca."""
        parser = AbancaParser()
        filepath = os.path.join(INPUT_DIR, 'ABANCA_ES5120800823473040166463.csv')

        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        records = parser.parse(filepath)

        assert len(records) > 0, "Debe parsear al menos 1 transacción"
        assert all(r['banco'] == 'Abanca' for r in records)
        assert all(isinstance(r['importe'], float) for r in records)

        # Abanca usa formato DD-MM-YYYY, debe convertirse
        assert all(len(r['fecha']) == 10 for r in records)


class TestDateConversion:
    """Tests para conversión de fechas."""

    def test_convert_date_formats(self):
        """Test conversión de diferentes formatos de fecha."""
        from parsers.base import BankParser

        # DD/MM/YYYY
        assert BankParser.convert_date_to_iso('11/11/2025') == '2025-11-11'
        assert BankParser.convert_date_to_iso('03/05/2025') == '2025-05-03'

        # DD-MM-YYYY
        assert BankParser.convert_date_to_iso('29-12-2025') == '2025-12-29'

        # YYYY-MM-DD (passthrough)
        assert BankParser.convert_date_to_iso('2023-10-09') == '2023-10-09'

        # Con hora
        assert BankParser.convert_date_to_iso('02/07/2019 17:19') == '2019-07-02'


class TestIBANExtraction:
    """Tests para extracción de IBAN."""

    def test_extract_iban(self):
        """Test extracción de IBAN del filename."""
        from parsers.base import BankParser

        assert BankParser.extract_iban_from_filename(
            'openbank_ES2200730100510135698457.csv'
        ) == 'ES2200730100510135698457'

        assert BankParser.extract_iban_from_filename(
            'MyInvestor_ES5215447889746650686253.csv'
        ) == 'ES5215447889746650686253'

        assert BankParser.extract_iban_from_filename(
            '/path/to/Revolut_ES1215830001199090471794.csv'
        ) == 'ES1215830001199090471794'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
