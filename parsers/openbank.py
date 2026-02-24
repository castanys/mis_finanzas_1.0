"""
Parser para archivos CSV de Openbank.

Soporta dos formatos:

1. Formato "nuevo" (con columnas vacías):
   - Headers: ;Fecha Operación;;Fecha Valor;;Concepto;;Importe;;Saldo;
   - Números en formato español: -2.210,00

2. Formato "TOTAL" (formato limpio):
   - Headers: Fecha valor;Concepto;Importe;Cuenta;Saldo

Ambos:
- Separador: ;
- Encoding: UTF-8 con BOM
- Fechas: DD/MM/YYYY
"""
import csv
import re
from typing import List, Dict
from .base import BankParser


class OpenbankParser(BankParser):
    """Parser para CSV de Openbank (ambos formatos)."""

    BANK_NAME = "Openbank"

    @staticmethod
    def _normalize_description_for_hash(descripcion: str) -> str:
        """
        Normaliza la descripción para hash, enmascarando números de tarjeta.
        
        Esto permite que transacciones idénticas de diferentes formatos CSV
        (TOTAL con tarjeta completa vs. nuevo con tarjeta enmascarada) generen
        el mismo hash para deduplicación correcta.
        
        Ejemplo: 
        - "COMPRA EN SIMYO, CON LA TARJETA : 5489133068682036 EL 2026-01-19"
        - "COMPRA EN SIMYO, CON LA TARJETA : XXXXXXXXXXXX2036 EL 2026-01-19"
        Ambas se normalizan a: "COMPRA EN SIMYO, CON LA TARJETA : XXXXXXXXXXXX2036 EL 2026-01-19"
        """
        # Enmascarar números de tarjeta: reemplaza los primeros 12 dígitos por "X"
        # Patrón: 12+ dígitos consecutivos
        descripcion_normalizada = re.sub(r'\b\d{12,}\b', lambda m: 'X' * 12 + m.group(0)[-4:], descripcion)
        return descripcion_normalizada

    def _detect_format(self, headers: List[str]) -> str:
        """
        Detect which Openbank format this file uses.

        Args:
            headers: First row of CSV

        Returns:
            'nuevo' or 'total'
        """
        # Formato TOTAL tiene header limpio "Fecha valor" (con v minúscula)
        if 'Fecha valor' in headers:
            return 'total'

        # Formato nuevo tiene "Fecha Operación" (con O mayúscula) o primera columna vacía
        if 'Fecha Operación' in headers or (len(headers) > 0 and headers[0] == ''):
            return 'nuevo'

        # Default: nuevo
        return 'nuevo'

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse Openbank CSV file (autodetects format).

        Args:
            filepath: Path to Openbank CSV

        Returns:
            List of unified transaction records
        """
        records = []
        iban = self.extract_iban_from_filename(filepath)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            # Read first line to detect format
            first_line = f.readline()
            f.seek(0)  # Reset to beginning

            # Parse with detected format
            reader = csv.reader(f, delimiter=';')
            headers = next(reader)
            file_format = self._detect_format(headers)

            if file_format == 'total':
                records = self._parse_total_format(reader, iban, headers, filepath)
            else:
                records = self._parse_nuevo_format(reader, iban, filepath)

        return records

    def _parse_nuevo_format(self, reader, iban: str, filepath: str) -> List[Dict]:
        """
        Parse Openbank "nuevo" format with empty columns.

        Format: ;Fecha Operación;;Fecha Valor;;Concepto;;Importe;;Saldo;
        """
        records = []
        line_num = 2  # Start at 2 (after header)

        for row in reader:
            if len(row) < 7:
                line_num += 1
                continue

            # Índices: 0(vacío), 1(Fecha Op), 2(vacío), 3(Fecha Valor), 4(vacío), 5(Concepto), 6(vacío), 7(Importe)
            fecha = row[1].strip() if len(row) > 1 else ""
            concepto = row[5].strip() if len(row) > 5 else ""
            importe_str = row[7].strip() if len(row) > 7 else ""

            if not fecha or not concepto:
                line_num += 1
                continue

            # Convertir fecha DD/MM/YYYY → YYYY-MM-DD
            fecha_iso = self.convert_date_to_iso(fecha)

            # Convertir importe español a float
            try:
                importe = self.parse_spanish_number(importe_str)
            except (ValueError, AttributeError):
                line_num += 1
                continue

            # Normalizar descripción para hash (enmascarar números de tarjeta)
            descripcion_normalizada = self._normalize_description_for_hash(concepto)
            
            record = {
                "fecha": fecha_iso,
                "importe": importe,
                "descripcion": concepto,
                "banco": self.BANK_NAME,
                "cuenta": iban,
                "line_num": line_num,
                "hash": self.generate_hash(fecha_iso, importe, descripcion_normalizada, iban, line_num)
            }
            records.append(record)
            line_num += 1

        return records

    def _parse_total_format(self, reader, iban: str, headers: List[str], filepath: str) -> List[Dict]:
        """
        Parse Openbank "TOTAL" format with clean columns.

        Format: Fecha valor;Concepto;Importe;Cuenta;Saldo
        """
        records = []
        line_num = 2  # Start at 2 (after header)

        # Find column indices
        try:
            fecha_idx = headers.index('Fecha valor')
            concepto_idx = headers.index('Concepto')
            importe_idx = headers.index('Importe')
            cuenta_idx = headers.index('Cuenta') if 'Cuenta' in headers else None
        except ValueError as e:
            # Headers not found, cannot parse
            return records

        for row in reader:
            if len(row) <= max(fecha_idx, concepto_idx, importe_idx):
                line_num += 1
                continue

            fecha = row[fecha_idx].strip()
            concepto = row[concepto_idx].strip()
            importe_str = row[importe_idx].strip()

            # Get IBAN from row if available
            if cuenta_idx is not None and len(row) > cuenta_idx:
                cuenta = row[cuenta_idx].strip()
                if cuenta and cuenta.startswith('ES'):
                    iban = cuenta

            if not iban:
                line_num += 1
                continue

            if not fecha or not concepto or not importe_str:
                line_num += 1
                continue

            # Convertir fecha DD/MM/YYYY → YYYY-MM-DD
            fecha_iso = self.convert_date_to_iso(fecha)

            # Importe con punto decimal (formato inglés)
            try:
                importe = float(importe_str)
            except (ValueError, AttributeError):
                line_num += 1
                continue

            # Normalizar descripción para hash (enmascarar números de tarjeta)
            descripcion_normalizada = self._normalize_description_for_hash(concepto)
            
            record = {
                "fecha": fecha_iso,
                "importe": importe,
                "descripcion": concepto,
                "banco": self.BANK_NAME,
                "cuenta": iban,
                "line_num": line_num,
                "hash": self.generate_hash(fecha_iso, importe, descripcion_normalizada, iban, line_num)
            }
            records.append(record)
            line_num += 1

        return records
