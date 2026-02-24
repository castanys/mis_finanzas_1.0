"""
Parser para archivos CSV de Bankinter.

Formato:
- Separador: ;
- Headers: Archivo;Cuenta;Fecha;Fecha Valor;Referencia;Concepto;Importe
- Números españoles sin separador de miles: -10494, 494, 150, -58.3
- Fechas: DD/MM/YYYY
- Cuenta: formato interno 20 dígitos (ej: 0128.8700.18.0105753633)
- Encoding: UTF-8 BOM (Excel)
"""
import csv
from typing import List, Dict
from .base import BankParser


class BankinterParser(BankParser):
    """Parser para CSV de Bankinter."""

    BANK_NAME = "Bankinter"

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse Bankinter CSV file.

        Args:
            filepath: Path to Bankinter CSV

        Returns:
            List of unified transaction records
        """
        records = []
        iban = self.extract_iban_from_filename_bankinter(filepath)

        # Bankinter CSV viene en UTF-8 BOM (típico de Excel)
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')

            line_num = 2  # Start at 2 (after header)
            for row in reader:
                fecha = row.get('Fecha', '').strip()
                concepto = row.get('Concepto', '').strip()
                importe_str = row.get('Importe', '').strip()

                if not fecha or not concepto or not importe_str:
                    line_num += 1
                    continue

                # Convertir fecha DD/MM/YYYY → YYYY-MM-DD
                fecha_iso = self.convert_date_to_iso(fecha)

                # Bankinter usa números españoles (coma decimal, sin separador de miles)
                try:
                    importe = self.parse_spanish_number(importe_str)
                except (ValueError, AttributeError):
                    line_num += 1
                    continue

                # Descripción: usar concepto directamente
                descripcion = concepto

                record = {
                    "fecha": fecha_iso,
                    "importe": importe,
                    "descripcion": descripcion,
                    "banco": self.BANK_NAME,
                    "cuenta": iban,
                    "line_num": line_num,
                    "hash": self.generate_hash(fecha_iso, importe, descripcion, iban, line_num)
                }
                records.append(record)
                line_num += 1

        return records

    @staticmethod
    def extract_iban_from_filename_bankinter(filename: str) -> str:
        """
        Extract account number from Bankinter filename and convert to IBAN.

        Examples:
            'Bankinter_01288700160105752044.csv' → 'ES6001288700160105752044'
            'Bankinter_01288700180105753633.csv' → 'ES6001288700180105753633'

        Args:
            filename: Filename or full path

        Returns:
            IBAN string (ES + check digits + account number) or empty if not found
        """
        import re
        # Extract 20-digit account number
        match = re.search(r'(\d{20})', filename)
        if match:
            cuenta = match.group(1)
            # Calculate IBAN check digits
            check = BankinterParser._calcular_check_digit_iban(cuenta)
            return f"ES{check}{cuenta}"
        return ""

    @staticmethod
    def _calcular_check_digit_iban(cuenta: str) -> str:
        """
        Calculate IBAN check digits for a 20-digit account number.

        Uses the standard IBAN algorithm: mod 97.

        Args:
            cuenta: 20-digit account number

        Returns:
            2-digit check string
        """
        # Rearrange: cuenta + "ES00"
        rearranged = cuenta + "ES00"
        # Convert letters to numbers (E=14, S=28)
        numeric = ""
        for c in rearranged:
            if c.isdigit():
                numeric += c
            else:
                numeric += str(ord(c) - ord("A") + 10)
        # Calculate mod 97
        mod = int(numeric) % 97
        check = 98 - mod
        return f"{check:02d}"
