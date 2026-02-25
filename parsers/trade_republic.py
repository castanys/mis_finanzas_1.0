"""
Parser para archivos CSV de Trade Republic.

Formato:
- Separador: ,
- Headers: fecha,importe,concepto,banco,balance
- Números con punto decimal: 17305.0, -3200.0
- Fechas: YYYY-MM-DD (ya en formato ISO)
- Concepto describe el tipo: "Transferencia", "Interés"
"""
import csv
from typing import List, Dict
from .base import BankParser
from .tr_hash_normalizer import normalize_tr_description_for_hash


class TradeRepublicParser(BankParser):
    """Parser para CSV de Trade Republic."""

    BANK_NAME = "Trade Republic"

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse Trade Republic CSV file.

        Args:
            filepath: Path to Trade Republic CSV

        Returns:
            List of unified transaction records
        """
        records = []
        iban = self.extract_iban_from_filename(filepath)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=',')

            line_num = 2  # Start at 2 (after header)
            for row in reader:
                fecha = row.get('fecha', '').strip()
                concepto = row.get('concepto', '').strip()
                importe_str = row.get('importe', '').strip()

                if not fecha:
                    continue

                # Fecha ya viene en formato ISO
                fecha_iso = fecha

                # Trade Republic usa punto decimal
                try:
                    importe = float(importe_str) if importe_str else 0.0
                except ValueError:
                    continue

                if not concepto:
                    concepto = "Movimiento Trade Republic"

                # Normalizar descripción PARA HASH (sincroniza CSV con PDF)
                # Pero guardar descripción original en el registro
                descripcion_normalizada = normalize_tr_description_for_hash(concepto)

                record = {
                    "fecha": fecha_iso,
                    "importe": importe,
                    "descripcion": concepto,  # Original, sin normalizar
                    "banco": self.BANK_NAME,
                    "cuenta": iban,
                    "line_num": line_num,
                    "hash": self.generate_hash(fecha_iso, importe, descripcion_normalizada, iban, line_num)  # Hash con line_num
                }
                records.append(record)
                line_num += 1

        return records
