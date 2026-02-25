"""
Parser para archivos CSV de Revolut.

Formato:
- Separador: ;
- Encoding: UTF-8 con BOM
- Headers: Tipo;Producto;Fecha de inicio;Fecha de finalización;Descripción;Importe;Comisión;Divisa;State;Saldo
- Números con punto decimal
- Fechas: DD/MM/YYYY HH:MM o DD/MM/YYYY HH:MM
- State puede ser COMPLETADO, REVERTED, etc (parsear TODAS)
"""
import csv
from typing import List, Dict
from .base import BankParser


class RevolutParser(BankParser):
    """Parser para CSV de Revolut."""

    BANK_NAME = "Revolut"

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse Revolut CSV file.

        Args:
            filepath: Path to Revolut CSV

        Returns:
            List of unified transaction records
        """
        records = []
        iban = self.extract_iban_from_filename(filepath)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')

            line_num = 2  # Start at 2 (after header)
            for row in reader:
                state = row.get('State', '').strip()
                fecha_fin = row.get('Fecha de finalización', '').strip()
                fecha_inicio = row.get('Fecha de inicio', '').strip()
                descripcion = row.get('Descripción', '').strip()
                importe_str = row.get('Importe', '').strip()

                # NO filtrar por state - parsear todas las transacciones
                # Incluir state en la descripción para referencia
                if state and state != 'COMPLETADO':
                    descripcion = f"[{state}] {descripcion}" if descripcion else f"[{state}] Movimiento Revolut"

                # Usar fecha de finalización si existe, sino fecha de inicio
                fecha = fecha_fin if fecha_fin else fecha_inicio

                if not fecha:
                    continue

                # Convertir fecha (puede incluir hora)
                fecha_iso = self.convert_date_to_iso(fecha)

                # Revolut usa punto decimal
                try:
                    importe = float(importe_str) if importe_str else 0.0
                except ValueError:
                    continue

                if not descripcion:
                    descripcion = "Movimiento Revolut"

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
