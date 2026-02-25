"""
Parser para archivos CSV de Abanca.

Formato:
- Separador: ;
- Headers: Fecha ctble;Fecha valor;Concepto;Importe;Moneda;Saldo;Moneda;Concepto ampliado
- Números españoles con coma: 4027,67, -1000,00
- Fechas: DD-MM-YYYY (con guiones!)
- Concepto puede ser "NA"
- Encoding issues posibles (ej: CAMPA�A)
"""
import csv
from typing import List, Dict
from .base import BankParser


class AbancaParser(BankParser):
    """Parser para CSV de Abanca."""

    BANK_NAME = "Abanca"

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse Abanca CSV file.

        Args:
            filepath: Path to Abanca CSV

        Returns:
            List of unified transaction records
        """
        records = []
        iban = self.extract_iban_from_filename(filepath)

        # Abanca puede venir en latin-1 (tiene Ñ, byte 0xD1) o utf-8
        # Intentar utf-8-sig primero, latin-1 como fallback
        encoding = 'utf-8-sig'
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                f.read()
        except UnicodeDecodeError:
            encoding = 'latin-1'

        with open(filepath, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=';')

            line_num = 2  # Start at 2 (after header)
            for row in reader:
                fecha = row.get('Fecha ctble', '').strip()
                concepto = row.get('Concepto', '').strip()
                concepto_ampliado = row.get('Concepto ampliado', '').strip()
                importe_str = row.get('Importe', '').strip()

                if not fecha:
                    continue

                # Convertir fecha DD-MM-YYYY → YYYY-MM-DD
                fecha_iso = self.convert_date_to_iso(fecha)

                # Abanca usa formato español con coma
                try:
                    importe = self.parse_spanish_number(importe_str)
                except (ValueError, AttributeError):
                    continue

                # Usar concepto ampliado si está disponible, sino concepto normal
                if concepto_ampliado and concepto_ampliado != "NA":
                    descripcion = concepto_ampliado
                elif concepto and concepto != "NA":
                    descripcion = concepto
                else:
                    descripcion = "Movimiento Abanca"

                # Normalizar número de tarjeta en concepto para deduplicación cross-file
                descripcion_for_hash = self.normalize_card_number(descripcion)

                record = {
                    "fecha": fecha_iso,
                    "importe": importe,
                    "descripcion": descripcion,
                    "banco": self.BANK_NAME,
                    "cuenta": iban,
                    "line_num": line_num,
                    "hash": self.generate_hash(fecha_iso, importe, descripcion_for_hash, iban, line_num)
                }
                records.append(record)
                line_num += 1

        return records
