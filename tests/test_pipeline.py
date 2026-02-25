"""
Tests para el pipeline completo.
"""
import os
import pytest
from pipeline import TransactionPipeline


# Paths
PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
INPUT_DIR = os.path.join(PROJECT_DIR, 'input')
MASTER_CSV = os.path.join(PROJECT_DIR, 'Validación_Categorias_Finsense_04020206_5.csv')


class TestPipeline:
    """Tests para TransactionPipeline."""

    def test_detect_bank(self):
        """Test detección de banco desde filename."""
        pipeline = TransactionPipeline(MASTER_CSV)

        assert pipeline.detect_bank('openbank_ES2200730100510135698457.csv') == 'openbank'
        assert pipeline.detect_bank('MyInvestor_ES5215447889746650686253.csv') == 'myinvestor'
        assert pipeline.detect_bank('mediolanum_ES2501865001680510084831.csv') == 'mediolanum'
        assert pipeline.detect_bank('Revolut_ES1215830001199090471794.csv') == 'revolut'
        assert pipeline.detect_bank('TradeRepublic_ES8015860001420977164411.csv') == 'trade_republic'
        assert pipeline.detect_bank('MovimientosB100_ES88208001000130433834426.csv') == 'b100'
        assert pipeline.detect_bank('ABANCA_ES5120800823473040166463.csv') == 'abanca'

    def test_process_single_file(self):
        """Test procesamiento de un archivo individual."""
        if not os.path.exists(MASTER_CSV):
            pytest.skip(f"Master CSV no encontrado: {MASTER_CSV}")

        pipeline = TransactionPipeline(MASTER_CSV)

        # Test con archivo Openbank
        filepath = os.path.join(INPUT_DIR, 'openbank_ES2200730100510135698457.csv')
        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        records = pipeline.process_file(filepath, classify=True)

        # Verificaciones básicas
        assert isinstance(records, list)
        if records:
            r = records[0]
            assert 'fecha' in r
            assert 'importe' in r
            assert 'descripcion' in r
            assert 'banco' in r
            assert 'cuenta' in r
            assert 'hash' in r
            assert 'cat1' in r
            assert 'cat2' in r
            assert 'tipo' in r
            assert 'capa' in r

    def test_deduplication(self):
        """Test que la deduplicación funciona."""
        if not os.path.exists(MASTER_CSV):
            pytest.skip(f"Master CSV no encontrado: {MASTER_CSV}")

        pipeline = TransactionPipeline(MASTER_CSV)

        filepath = os.path.join(INPUT_DIR, 'openbank_ES2200730100510135698457.csv')
        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        # Primera pasada
        records1 = pipeline.process_file(filepath, classify=False)
        count1 = len(records1)

        # Segunda pasada (mismo archivo)
        records2 = pipeline.process_file(filepath, classify=False)
        count2 = len(records2)

        # La segunda pasada debe ser 0 (todas duplicadas)
        assert count2 == 0, f"Segunda pasada debería retornar 0 transacciones, retornó {count2}"
        assert count1 > 0, "Primera pasada debe tener transacciones"

    def test_classification_all_transactions(self):
        """Test que todas las transacciones se clasifican."""
        if not os.path.exists(MASTER_CSV):
            pytest.skip(f"Master CSV no encontrado: {MASTER_CSV}")

        pipeline = TransactionPipeline(MASTER_CSV)

        filepath = os.path.join(INPUT_DIR, 'openbank_ES2200730100510135698457.csv')
        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        records = pipeline.process_file(filepath, classify=True)

        if records:
            # Todas deben tener cat1
            assert all('cat1' in r for r in records)
            assert all('tipo' in r for r in records)
            assert all('capa' in r for r in records)

            # cat1 nunca debe estar vacío
            assert all(r['cat1'] != '' for r in records)

    def test_process_directory(self):
        """Test procesamiento de directorio completo."""
        if not os.path.exists(MASTER_CSV):
            pytest.skip(f"Master CSV no encontrado: {MASTER_CSV}")

        if not os.path.exists(INPUT_DIR):
            pytest.skip(f"Input dir no encontrado: {INPUT_DIR}")

        pipeline = TransactionPipeline(MASTER_CSV)

        # Procesar sin clasificar (más rápido)
        records = pipeline.process_directory(INPUT_DIR, classify=False)

        # Debe procesar múltiples archivos
        assert isinstance(records, list)
        print(f"\nTotal transacciones parseadas: {len(records)}")

        if records:
            # Verificar que hay múltiples bancos
            bancos = set(r['banco'] for r in records)
            print(f"Bancos encontrados: {bancos}")
            assert len(bancos) >= 2, "Debe haber al menos 2 bancos diferentes"

    def test_statistics(self):
        """Test generación de estadísticas."""
        if not os.path.exists(MASTER_CSV):
            pytest.skip(f"Master CSV no encontrado: {MASTER_CSV}")

        pipeline = TransactionPipeline(MASTER_CSV)

        filepath = os.path.join(INPUT_DIR, 'openbank_ES2200730100510135698457.csv')
        if not os.path.exists(filepath):
            pytest.skip(f"Archivo no encontrado: {filepath}")

        records = pipeline.process_file(filepath, classify=True)

        if records:
            stats = pipeline.get_statistics(records)

            assert 'total' in stats
            assert stats['total'] == len(records)
            assert 'by_bank' in stats
            assert 'by_cat1' in stats
            assert 'by_tipo' in stats
            assert 'date_range' in stats

            print("\nEstadísticas:")
            print(f"  Total: {stats['total']}")
            print(f"  Bancos: {list(stats['by_bank'].keys())}")
            print(f"  Categorías: {len(stats['by_cat1'])}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
