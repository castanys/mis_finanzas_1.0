"""
Parser para archivos CSV de MyInvestor.

Formato:
- Separador: ;
- Encoding: UTF-8 con BOM
- Headers: Fecha de operación;Fecha de valor;Concepto;Importe;Divisa
- Números con punto decimal: -200.2
- Fechas: DD/MM/YYYY
- Concepto puede estar vacío
"""
import csv
from typing import List, Dict
from .base import BankParser


class MyInvestorParser(BankParser):
    """Parser para CSV de MyInvestor."""

    BANK_NAME = "MyInvestor"

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse MyInvestor CSV file.

        Args:
            filepath: Path to MyInvestor CSV

        Returns:
            List of unified transaction records
        """
        records = []
        iban = self.extract_iban_from_filename(filepath)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')

            line_num = 2  # Start at 2 (after header)
            for row in reader:
                fecha = row.get('Fecha de operación', '').strip()
                concepto = row.get('Concepto', '').strip()
                importe_str = row.get('Importe', '').strip()

                if not fecha:
                    continue

                # Convertir fecha DD/MM/YYYY → YYYY-MM-DD
                fecha_iso = self.convert_date_to_iso(fecha)

                # MyInvestor usa punto decimal directo
                try:
                    importe = float(importe_str) if importe_str else 0.0
                except ValueError:
                    continue

                # Si no hay concepto, usar placeholder
                if not concepto:
                    concepto = "Movimiento sin concepto"

                record = {
                    "fecha": fecha_iso,
                    "importe": importe,
                    "descripcion": concepto,
                    "banco": self.BANK_NAME,
                    "cuenta": iban,
                    "line_num": line_num,
                    "hash": self.generate_hash(fecha_iso, importe, concepto, iban, line_num)
                }
                records.append(record)
                line_num += 1

        return records
