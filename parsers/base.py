"""
Clase base para todos los parsers de bancos.
"""
from abc import ABC, abstractmethod
from typing import List, Dict
import hashlib
import re
from datetime import datetime


class BankParser(ABC):
    """Base class for all bank CSV parsers."""

    BANK_NAME: str = ""  # Override in subclass

    @abstractmethod
    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse CSV and return list of unified records.

        Args:
            filepath: Path to CSV file

        Returns:
            List of dicts with keys: fecha, importe, descripcion, banco, cuenta, hash
        """
        pass

    @staticmethod
    def generate_hash(fecha: str, importe: float, descripcion: str, cuenta: str, line_id: int = 0) -> str:
        """
        Generate unique hash for deduplication.

        Args:
            fecha: Date in YYYY-MM-DD format
            importe: Amount as float
            descripcion: Transaction description
            cuenta: Account IBAN
            line_id: Line number (AHORA INCLUIDO en el hash para permitir txs idénticas dentro del mismo fichero)

        Returns:
            SHA256 hash as hex string
        """
        # Hash AHORA INCLUYE line_id para distinguir transacciones idénticas dentro del mismo fichero
        # Ejemplo: 5 compras el mismo día por el mismo monto en el mismo comercio
        # tienen el mismo fecha|importe|descripcion|cuenta pero números de línea distintos
        # Esto permite que todas se guarden en la BD (0 pérdidas de txs reales)
        # Nota: Esto SÍ rompe deduplicación cross-file de transacciones idénticas
        # pero eso es aceptable porque los ficheros no deberían tener txs 100% idénticas
        # entre distintas versiones del mismo extracto
        if line_id > 0:
            raw = f"{fecha}|{importe:.2f}|{descripcion}|{cuenta}|line_{line_id}"
        else:
            # Fallback si line_id no es proporcionado (backwards compatibility)
            raw = f"{fecha}|{importe:.2f}|{descripcion}|{cuenta}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def normalize_card_number(concepto: str) -> str:
        """
        Normalizar números de tarjeta en la descripción para deduplicación cross-file.
        
        Problema: Diferentes bancos representan tarjetas de formas distintas:
        - Openbank TOTAL: números completos (5489133068682036)
        - Openbank enablebanking: números enmascarados (XXXXXXXXXXXX2036)
        - Abanca/B100: pueden tener patrones similares
        
        Solución: Reemplazar ambos patrones por una forma canónica ****XXXX (últimos 4 dígitos).
        
        Args:
            concepto: Descripción original de la transacción
            
        Returns:
            Descripción con números de tarjeta normalizados
        """
        if not concepto:
            return concepto
            
        # Patrón 1: Números enmascarados "XXXXXXXXXXXX2036" → "****2036"
        # Ej: "CON LA TARJETA : XXXXXXXXXXXX2036" → "CON LA TARJETA : ****2036"
        concepto = re.sub(r'[X]+(\d{4})', r'****\1', concepto)
        
        # Patrón 2: Números completos "5489133068682036" → "****2036"
        # Ej: "CON LA TARJETA : 5489133068682036" → "CON LA TARJETA : ****2036"
        concepto = re.sub(r'\b\d{12}(\d{4})\b', r'****\1', concepto)
        
        return concepto

    @staticmethod
    def parse_spanish_number(s: str) -> float:
        """
        Convert Spanish number format to float.

        Examples:
            '2.210,50' → 2210.50
            '-1.500,00' → -1500.00
            '1.234' → 1234.00 (asume que es miles)
            '1234,56' → 1234.56

        Args:
            s: Number string in Spanish format

        Returns:
            Float value
        """
        if not s or s.strip() == '':
            return 0.0

        s = s.strip()

        # Si tiene coma, es el separador decimal
        if ',' in s:
            # Eliminar puntos (separador de miles) y reemplazar coma por punto
            s = s.replace('.', '').replace(',', '.')
        # Si solo tiene punto y está en posición de miles (ej: 1.234), eliminarlo
        elif '.' in s:
            parts = s.split('.')
            # Si el último grupo tiene 3 dígitos, es separador de miles
            if len(parts[-1]) == 3:
                s = s.replace('.', '')

        return float(s)

    @staticmethod
    def extract_iban_from_filename(filename: str) -> str:
        """
        Extract IBAN from filename.

        Examples:
            'openbank_ES2200730100510135698457.csv' → 'ES2200730100510135698457'
            'MyInvestor_ES5215447889746650686253.csv' → 'ES5215447889746650686253'

        Args:
            filename: Filename or full path

        Returns:
            IBAN string or empty if not found
        """
        match = re.search(r'ES\d{22}', filename)
        return match.group(0) if match else ""

    @staticmethod
    def convert_date_to_iso(date_str: str) -> str:
        """
        Convert various date formats to YYYY-MM-DD.

        Supported formats:
            DD/MM/YYYY → YYYY-MM-DD
            DD-MM-YYYY → YYYY-MM-DD
            YYYY-MM-DD → YYYY-MM-DD (passthrough)
            DD/MM/YYYY HH:MM → YYYY-MM-DD (ignores time)

        Args:
            date_str: Date string in various formats

        Returns:
            Date in YYYY-MM-DD format
        """
        if not date_str:
            return ""

        date_str = date_str.strip()

        # Extract date part if there's time
        if ' ' in date_str:
            date_str = date_str.split(' ')[0]

        # Try DD/MM/YYYY
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                dia, mes, anio = parts
                return f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"

        # Try DD-MM-YYYY
        if '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3:
                # Check if already YYYY-MM-DD
                if len(parts[0]) == 4:
                    return date_str
                # Convert DD-MM-YYYY
                dia, mes, anio = parts
                return f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"

        return date_str
