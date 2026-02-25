"""
Parser para archivos CSV ya pre-procesados.

Estos archivos ya están en formato unificado o cercano a él:
- Formato: Fecha,Importe,Descripcion,Banco,Cuenta
- Separador: ,
- Ya tienen las columnas principales

Este parser es útil para archivos exportados de versiones anteriores del sistema.
"""
import csv
from typing import List, Dict
from .base import BankParser


class PreprocessedParser(BankParser):
    """Parser para CSV ya pre-procesados."""

    # El nombre del banco se toma del archivo si está disponible
    BANK_NAME = "Unknown"

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse pre-processed CSV file.

        Args:
            filepath: Path to pre-processed CSV

        Returns:
            List of unified transaction records
        """
        records = []

        # Intentar extraer IBAN del filename, sino usar el del archivo
        iban = self.extract_iban_from_filename(filepath)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=',')

            line_num = 2  # Start at 2 (after header)
            for row in reader:
                fecha = row.get('Fecha', '').strip()
                importe_str = row.get('Importe', '').strip()
                descripcion = row.get('Descripcion', '').strip()
                banco = row.get('Banco', '').strip()
                cuenta = row.get('Cuenta', '').strip()

                if not fecha or not importe_str or not descripcion:
                    continue

                # Si cuenta es UNKNOWN o vacía, usar IBAN del filename
                if not cuenta or cuenta == 'UNKNOWN':
                    cuenta = iban

                # Si no tenemos cuenta válida, skip
                if not cuenta or not cuenta.startswith('ES'):
                    continue

                # Usar banco del archivo si está disponible
                if banco:
                    self.BANK_NAME = banco

                # Convertir fecha (puede ya estar en formato ISO)
                fecha_iso = self.convert_date_to_iso(fecha)

                # Importe
                try:
                    importe = float(importe_str)
                except (ValueError, AttributeError):
                    continue

                record = {
                    "fecha": fecha_iso,
                    "importe": importe,
                    "descripcion": descripcion,
                    "banco": self.BANK_NAME,
                    "cuenta": cuenta,
                    "line_num": line_num,
                    "hash": self.generate_hash(fecha_iso, importe, descripcion, cuenta, line_num)
                }
                records.append(record)
                line_num += 1

        return records
