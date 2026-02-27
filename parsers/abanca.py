"""
Parser para archivos CSV de Abanca.

Formato 1 (descarga banco directo):
- Separador: ;
- Headers: Fecha ctble;Fecha valor;Concepto;Importe;Moneda;Saldo;Moneda;Concepto ampliado
- Números españoles con coma: 4027,67, -1000,00
- Fechas: DD-MM-YYYY (con guiones!)
- Concepto puede ser "NA"
- Encoding issues posibles (ej: CAMPA\u00d1A)

Formato 2 (descarga web/app):
- Separador: ,
- Headers: Fecha,Concepto,Saldo,Importe,Fecha operación,Fecha valor
- Números con punto y símbolo €: -4025.0 €, 1.69 €
- Fechas: DD-MM-YYYY (con guiones!)
"""
import csv
import re
from typing import List, Dict
from .base import BankParser


class AbancaParser(BankParser):
    """Parser para CSV de Abanca. Soporta formato ; (banco directo) y formato , (web/app)."""

    BANK_NAME = "Abanca"

    def _detect_format(self, filepath: str) -> str:
        """Detecta el formato del CSV: 'semicolon' o 'comma'."""
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline().strip()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='latin-1') as f:
                first_line = f.readline().strip()

        if first_line.startswith('Fecha,Concepto,Saldo,Importe'):
            return 'comma'
        return 'semicolon'

    def _parse_euro_amount(self, value: str) -> float:
        """Parsea importes con símbolo € y punto decimal: '-4025.0 €' → -4025.0"""
        cleaned = value.replace('€', '').replace(' ', '').strip()
        # Eliminar puntos de miles si hay más de 3 decimales (ej: 1.234.56 no es válido)
        # El formato es punto decimal directamente (ej: -4025.0, 1.69)
        return float(cleaned)

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse Abanca CSV file (ambos formatos).

        Args:
            filepath: Path to Abanca CSV

        Returns:
            List of unified transaction records
        """
        formato = self._detect_format(filepath)

        if formato == 'comma':
            return self._parse_comma_format(filepath)
        else:
            return self._parse_semicolon_format(filepath)

    def _parse_semicolon_format(self, filepath: str) -> List[Dict]:
        """Formato original: separador ; con números españoles (coma decimal)."""
        records = []
        iban = self.extract_iban_from_filename(filepath)

        encoding = 'utf-8-sig'
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                f.read()
        except UnicodeDecodeError:
            encoding = 'latin-1'

        with open(filepath, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=';')

            line_num = 2
            for row in reader:
                fecha = row.get('Fecha ctble', '').strip()
                concepto = row.get('Concepto', '').strip()
                concepto_ampliado = row.get('Concepto ampliado', '').strip()
                importe_str = row.get('Importe', '').strip()

                if not fecha:
                    continue

                fecha_iso = self.convert_date_to_iso(fecha)

                try:
                    importe = self.parse_spanish_number(importe_str)
                except (ValueError, AttributeError):
                    continue

                if concepto_ampliado and concepto_ampliado != "NA":
                    descripcion = concepto_ampliado
                elif concepto and concepto != "NA":
                    descripcion = concepto
                else:
                    descripcion = "Movimiento Abanca"

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

    def _parse_comma_format(self, filepath: str) -> List[Dict]:
        """Formato web/app: separador , con importes en formato '€' y punto decimal."""
        records = []
        iban = self.extract_iban_from_filename(filepath)

        encoding = 'utf-8-sig'
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                f.read()
        except UnicodeDecodeError:
            encoding = 'latin-1'

        with open(filepath, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=',')

            line_num = 2
            for row in reader:
                # Cabecera: Fecha,Concepto,Saldo,Importe,Fecha operación,Fecha valor
                fecha = row.get('Fecha', '').strip()
                concepto = row.get('Concepto', '').strip()
                importe_str = row.get('Importe', '').strip()

                if not fecha:
                    continue

                # Fecha ya viene en DD-MM-YYYY
                fecha_iso = self.convert_date_to_iso(fecha)

                try:
                    importe = self._parse_euro_amount(importe_str)
                except (ValueError, AttributeError):
                    continue

                descripcion = concepto if concepto else "Movimiento Abanca"

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
