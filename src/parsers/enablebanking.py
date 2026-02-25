"""
Parser para ficheros CSV de Enablebanking.

Enablebanking es una plataforma de agregación bancaria que proporciona
un formato CSV unificado para múltiples bancos (Abanca, Openbank, etc.).

Formato CSV:
- Cabeceras: booking_datetime,value_datetime,amount,currency,balance_after,remittance_information,uid
- Fechas: YYYY-MM-DD (ISO 8601)
- Importes: formato inglés con punto decimal, CON signo (4025.21, -4025.00)
- Separador: coma
- IBAN: en el nombre del archivo (formato: banco_IBAN_EUR_timestamp.csv)
"""
import csv
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class EnablebankingParser:
    """Parser para CSVs de Enablebanking (Abanca, Openbank, etc.)."""

    def __init__(self):
        self.banco_map = {
            '2080': 'Abanca',     # Código banco Abanca
            '0073': 'Openbank',   # Código banco Openbank
        }

    def parse(self, file_path: str) -> List[Dict]:
        """
        Parsea un CSV de Enablebanking.

        Args:
            file_path: Ruta al archivo CSV

        Returns:
            Lista de transacciones parseadas
        """
        # Extraer IBAN del nombre del archivo
        iban = self._extract_iban_from_filename(file_path)
        if not iban:
            raise ValueError(f"No se pudo extraer IBAN del nombre del archivo: {file_path}")

        # Detectar banco por IBAN
        banco = self._detect_banco(iban)

        transactions = []
        line_num = 2  # Empezar en línea 2 (línea 1 es header)

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            # Detectar dialecto CSV
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample)
            except:
                dialect = csv.excel  # Fallback

            reader = csv.DictReader(f, dialect=dialect)

            for row in reader:
                # Saltar filas vacías
                # Soportar ambos: booking_date y booking_datetime
                if not row.get('booking_datetime') and not row.get('booking_date'):
                    line_num += 1
                    continue

                # Parsear transacción con número de línea
                transaction = self._parse_transaction(row, iban, banco, line_num)
                if transaction:
                    transactions.append(transaction)
                
                line_num += 1

        return transactions

    def _extract_iban_from_filename(self, file_path: str) -> Optional[str]:
        """
        Extrae el IBAN del nombre del archivo.

        Formato esperado: banco_ESXXXXXXXXXXXXXXXXXX_EUR_timestamp.csv

        Args:
            file_path: Ruta al archivo

        Returns:
            IBAN extraído o None
        """
        filename = Path(file_path).name

        # Buscar patrón ES + 22-24 dígitos (soportar variaciones)
        # Primero intentar ES + 24 dígitos, luego ES + 22 dígitos
        for pattern in [r'ES\d{24}', r'ES\d{23}', r'ES\d{22}']:
            match = re.search(pattern, filename)
            if match:
                return match.group(0)

        return None

    def _detect_banco(self, iban: str) -> str:
        """
        Detecta el banco por el código en el IBAN.

        IBAN español: ES + 2 dígitos control + 4 dígitos banco + 4 dígitos sucursal + 2 control + 10 cuenta
        Soporta IBANs de 24 (estándar) y 26 caracteres (variaciones)

        Args:
            iban: IBAN completo

        Returns:
            Nombre del banco
        """
        if len(iban) not in [24, 25, 26]:
            return "Desconocido"

        # Extraer código banco (posiciones 4-8 en ambos formatos)
        codigo_banco = iban[4:8]

        return self.banco_map.get(codigo_banco, f"Banco {codigo_banco}")

    def _parse_transaction(self, row: Dict, iban: str, banco: str, line_num: int = 0) -> Optional[Dict]:
        """
        Parsea una fila del CSV a formato estándar.

        Args:
            row: Fila del CSV
            iban: IBAN de la cuenta
            banco: Nombre del banco
            line_num: Número de línea en el fichero (para hash único)

        Returns:
            Diccionario con transacción parseada
        """
        try:
            # Fecha (soportar booking_date y booking_datetime)
            fecha_str = row.get('booking_datetime') or row.get('booking_date', '')
            fecha_str = fecha_str.strip()
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()

            # Fecha valor (soportar value_date y value_datetime)
            fecha_valor_str = row.get('value_datetime') or row.get('value_date', '')
            fecha_valor_str = fecha_valor_str.strip()
            fecha_valor = None
            if fecha_valor_str:
                try:
                    fecha_valor = datetime.strptime(fecha_valor_str, '%Y-%m-%d').date()
                except:
                    pass

            # Importe (ya viene con signo)
            importe_str = row['amount'].strip()
            importe = float(importe_str)

            # Concepto (remittance_information)
            concepto = row.get('remittance_information', '').strip()
            if not concepto:
                concepto = 'Sin concepto'

            # Balance después de la transacción (opcional)
            balance_str = row.get('balance_after', '').strip()
            balance = None
            if balance_str:
                try:
                    balance = float(balance_str)
                except:
                    pass

            # UID único de Enablebanking (opcional)
            uid = row.get('uid', '').strip()

            # Convertir fecha a string ISO para consistencia con el resto de parsers
            fecha_str = fecha.isoformat()

            # CUSTOM HASH PARA ENABLEBANKING: incluye número de línea
            # Esto permite transacciones idénticas dentro del mismo fichero
            # y proporciona deduplicación correcta contra TOTAL format (que también usa line_num)
            hash_input = f"{fecha_str}|{importe:.2f}|{concepto}|{iban}|line_{line_num}"
            hash_val = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

            return {
                'fecha': fecha_str,
                'fecha_valor': fecha_valor.isoformat() if fecha_valor else None,
                'descripcion': concepto,   # campo estándar esperado por el pipeline
                'concepto': concepto,
                'importe': importe,
                'balance': balance,
                'moneda': row.get('currency', 'EUR').strip(),
                'cuenta': iban,
                'banco': banco,
                'uid_externo': uid,
                'hash': hash_val,
                'line_num': line_num,
            }

        except Exception as e:
            print(f"⚠️  Error parseando fila: {e}")
            print(f"   Fila: {row}")
            return None


def test_parser():
    """Test del parser con los ficheros nuevos."""
    import glob

    parser = EnablebankingParser()

    # Buscar todos los CSVs de Enablebanking
    files = (glob.glob('input/new/abanca_*.csv') +
             glob.glob('input/new/enable_abanca_*.csv') +
             glob.glob('input/new/openbank_*.csv'))

    total = 0
    for file_path in files:
        print(f"\n{'='*60}")
        print(f"Parseando: {Path(file_path).name}")
        print('='*60)

        try:
            transactions = parser.parse(file_path)
            print(f"✅ Transacciones parseadas: {len(transactions)}")

            if transactions:
                print(f"\nPrimera transacción:")
                t = transactions[0]
                print(f"  Fecha: {t['fecha']}")
                print(f"  Concepto: {t['concepto'][:50]}...")
                print(f"  Importe: {t['importe']:.2f} {t['moneda']}")
                print(f"  Banco: {t['banco']}")
                print(f"  IBAN: {t['cuenta']}")

            total += len(transactions)

        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\n{'='*60}")
    print(f"TOTAL ENABLEBANKING: {total} transacciones")
    print('='*60)


if __name__ == '__main__':
    test_parser()
