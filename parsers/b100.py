"""
Parser para archivos CSV de B100.

Formato:
- Separador: ,
- Headers: Fecha de Operación,Fecha valor,Detalle,Concepto,Cantidad,Saldo tras operación,Divisa,Tipo de Movimiento
- Números con punto decimal: -34.00
- Fechas: DD/MM/YYYY
- Tiene "Tipo de Movimiento" que puede ser Gasto/Ingreso
- Concepto puede ser "NA"
"""
import csv
from typing import List, Dict
from .base import BankParser


class B100Parser(BankParser):
    """Parser para CSV de B100."""

    BANK_NAME = "B100"

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse B100 CSV file.

        Args:
            filepath: Path to B100 CSV

        Returns:
            List of unified transaction records
        """
        records = []
        iban = self.extract_iban_from_filename(filepath)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=',')

            line_num = 2  # Start at 2 (after header)
            for row in reader:
                fecha = row.get('Fecha de Operación', '').strip()
                detalle = row.get('Detalle', '').strip()
                concepto = row.get('Concepto', '').strip()
                cantidad_str = row.get('Cantidad', '').strip()

                if not fecha:
                    continue

                # Convertir fecha DD/MM/YYYY → YYYY-MM-DD
                fecha_iso = self.convert_date_to_iso(fecha)

                # B100 usa punto decimal
                try:
                    importe = float(cantidad_str) if cantidad_str else 0.0
                except ValueError:
                    continue

                # Usar Detalle como descripción principal, si Concepto es "NA" o vacío
                if concepto and concepto != "NA":
                    descripcion = concepto
                elif detalle:
                    descripcion = detalle
                else:
                    descripcion = "Movimiento B100"

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
