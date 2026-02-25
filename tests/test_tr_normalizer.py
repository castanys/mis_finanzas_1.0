"""
Tests para tr_hash_normalizer.py — validar que CSV y PDF de Trade Republic
produzcan hashes iguales y eviten duplicados en futuras importaciones.
"""
import pytest
from parsers.tr_hash_normalizer import normalize_tr_description_for_hash


class TestTRHashNormalizer:
    """Tests para normalizador de Trade Republic."""

    def test_github_csv_pdf_equivalence_enero(self):
        """Test: GitHub enero 2026 (variante A) — CSV y PDF deben ser iguales."""
        csv_desc = (
            "Otros Transacción GITHUB, INC., 21,52 $, exchange rate: 0,8633829, "
            "ECB rate: con tarjeta 0,8608074374, markup: 0,29919149 %null"
        )
        pdf_desc = "GITHUB, INC., 21,52 $, exchange rate: 0,8633829, ECB rate: 0,8608074374,"

        csv_norm = normalize_tr_description_for_hash(csv_desc)
        pdf_norm = normalize_tr_description_for_hash(pdf_desc)

        assert csv_norm == pdf_norm, f"CSV y PDF deberían ser iguales. CSV: '{csv_norm}', PDF: '{pdf_norm}'"
        assert csv_norm == "GITHUB, INC., 21,52 $", f"Debería conservar solo merchant + divisa. Got: '{csv_norm}'"

    def test_github_csv_pdf_equivalence_diciembre(self):
        """Test: GitHub diciembre 2025 (variante B) — CSV y PDF deben ser iguales."""
        csv_desc = (
            "Otros Transacción GITHUB, INC., 10,00 $, exchange rate: 0,861, "
            "ECB rate: 0,859549596, con tarjeta markup: 0,16874 %null"
        )
        pdf_desc = "GITHUB, INC., 10,00 $, exchange rate: 0,861, ECB rate: 0,859549596,"

        csv_norm = normalize_tr_description_for_hash(csv_desc)
        pdf_norm = normalize_tr_description_for_hash(pdf_desc)

        assert csv_norm == pdf_norm, f"CSV y PDF deberían ser iguales. CSV: '{csv_norm}', PDF: '{pdf_norm}'"
        assert csv_norm == "GITHUB, INC., 10,00 $"

    def test_anthropic_csv_pdf_equivalence(self):
        """Test: Anthropic — CSV y PDF deben ser iguales."""
        csv_desc = (
            "Otros Transacción ANTHROPIC, 18,15 $, exchange rate: 0,8440771, "
            "ECB rate: con tarjeta 0,8351428094, markup: 1,06979196 %null"
        )
        pdf_desc = "ANTHROPIC, 18,15 $, exchange rate: 0,8440771, ECB rate: 0,8351428094,"

        csv_norm = normalize_tr_description_for_hash(csv_desc)
        pdf_norm = normalize_tr_description_for_hash(pdf_desc)

        assert csv_norm == pdf_norm
        assert csv_norm == "ANTHROPIC, 18,15 $"

    def test_multiple_github_transactions_same_day_different_amounts(self):
        """Test: Dos transacciones GitHub el mismo día con distinto importe quedan distintas."""
        desc1 = "Otros Transacción GITHUB, INC., 10,00 $, exchange rate: 0,861, ECB rate: 0,859549596, con tarjeta markup: 0,16874 %"
        desc2 = "Otros Transacción GITHUB, INC., 20,00 $, exchange rate: 0,861, ECB rate: 0,859549596, con tarjeta markup: 0,16874 %"

        norm1 = normalize_tr_description_for_hash(desc1)
        norm2 = normalize_tr_description_for_hash(desc2)

        assert norm1 != norm2, "Importes distintos deben producir strings distintos"
        assert norm1 == "GITHUB, INC., 10,00 $"
        assert norm2 == "GITHUB, INC., 20,00 $"

    def test_savings_plan_not_affected(self):
        """Test: Savings plans (sin exchange rate) no deben ser alterados."""
        desc = (
            "Otros Savings plan execution IE00B5BMR087 iShares VII plc - "
            "iShares Core Operar S&P 500 UCITS ETF USD (Acc), quantity: 0.017378"
        )
        norm = normalize_tr_description_for_hash(desc)

        # No debe contener "exchange rate" → no debería truncarse
        assert "exchange rate" not in desc  # Confirmación de que no tiene FX
        # Sí debería limpiar Operar y quantity
        assert "Operar" not in norm
        assert "quantity" not in norm
        assert "iShares Core S&P 500" in norm  # Debe quitar el "Operar"

    def test_transfer_not_affected(self):
        """Test: Transferencias (sin exchange rate) no deben ser alteradas."""
        desc = "Outgoing transfer for FERNANDEZ CASTANYS (ES3600730100550435513660)"
        norm = normalize_tr_description_for_hash(desc)

        # No debe contener exchange rate → no debe truncarse
        assert "Outgoing transfer" not in norm  # Se limpia el verbo
        assert "for FERNANDEZ" in norm
        # IBAN en paréntesis se elimina
        assert "ES3600730100550435513660" not in norm

    def test_idempotency(self):
        """Test: Normalizar dos veces debe producir el mismo resultado."""
        desc = (
            "Otros Transacción GITHUB, INC., 21,52 $, exchange rate: 0,8633829, "
            "ECB rate: con tarjeta 0,8608074374, markup: 0,29919149 %null"
        )
        norm1 = normalize_tr_description_for_hash(desc)
        norm2 = normalize_tr_description_for_hash(norm1)

        assert norm1 == norm2, "Normalización debe ser idempotente"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
