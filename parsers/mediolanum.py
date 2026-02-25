"""
Parser para archivos CSV de Mediolanum.

Formato:
- Separador: ;
- Encoding: UTF-8 con BOM
- Headers: Fecha Operación;Concepto;Fecha Valor;Pagos;Ingresos;Saldo;;;;
- Números españoles con coma decimal (sin punto miles en ejemplos)
- Dos columnas: Pagos (gastos) e Ingresos
- Fechas: DD/MM/YYYY
"""
import csv
from typing import List, Dict
from .base import BankParser


class MediolanumParser(BankParser):
    """Parser para CSV de Mediolanum."""

    BANK_NAME = "Mediolanum"

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse Mediolanum CSV file.

        Args:
            filepath: Path to Mediolanum CSV

        Returns:
            List of unified transaction records
        """
        records = []
        iban = self.extract_iban_from_filename(filepath)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')

            line_num = 2  # Start at 2 (after header)
            for row in reader:
                fecha = row.get('Fecha Operación', '').strip()
                concepto = row.get('Concepto', '').strip()
                pagos_str = row.get('Pagos', '').strip()
                ingresos_str = row.get('Ingresos', '').strip()

                if not fecha:
                    continue

                # Convertir fecha DD/MM/YYYY → YYYY-MM-DD
                fecha_iso = self.convert_date_to_iso(fecha)

                # Determinar importe: si hay Pagos, es negativo; si hay Ingresos, es positivo
                try:
                    if pagos_str:
                        importe = -abs(self.parse_spanish_number(pagos_str))
                    elif ingresos_str:
                        importe = abs(self.parse_spanish_number(ingresos_str))
                    else:
                        continue
                except (ValueError, AttributeError):
                    continue

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
