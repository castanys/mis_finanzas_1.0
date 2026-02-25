"""
Parser para archivos PDF de Trade Republic.

Trade Republic entrega extractos en PDF, no CSV. Este parser extrae
las transacciones del PDF y las convierte al formato unificado.
"""
import pdfplumber
import re
from typing import List, Dict, Optional
from .base import BankParser
from .tr_hash_normalizer import normalize_tr_description_for_hash


class TradeRepublicPDFParser(BankParser):
    """Parser para PDF de Trade Republic."""

    BANK_NAME = "Trade Republic"

    def parse(self, filepath: str) -> List[Dict]:
        """
        Parse Trade Republic PDF statement.

        Args:
            filepath: Path to PDF file

        Returns:
            List of unified transaction records
        """
        records = []

        # Extraer IBAN del texto del PDF (primera página)
        iban = self._extract_iban(filepath)
        if not iban:
            iban = "ES8015860001420977164411"  # IBAN por defecto del PDF

        with pdfplumber.open(filepath) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extraer texto de la página
                text = page.extract_text()
                if not text:
                    continue

                # Parsear transacciones de esta página
                page_records = self._parse_page_text(text, iban, page_num)
                records.extend(page_records)

        return records

    def _extract_iban(self, filepath: str) -> str:
        """Extraer IBAN de la primera página del PDF."""
        with pdfplumber.open(filepath) as pdf:
            if pdf.pages:
                text = pdf.pages[0].extract_text()
                if text:
                    # Buscar IBAN (formato ES + 22 dígitos)
                    match = re.search(r'IBAN\s+(ES\d{22})', text)
                    if match:
                        return match.group(1)
        return ""

    def _parse_page_text(self, text: str, iban: str, page_num: int) -> List[Dict]:
        """
        Parsear transacciones del texto de una página.

        El formato puede ser:

        Tipo 1 (3 líneas):
        dd mmm DESCRIPCION_INICIO
        TIPO DESCRIPCION_RESTO IMPORTE € BALANCE €
        yyyy DESCRIPCION_EXTRA

        Tipo 2 (3 líneas):
        dd mmm
        TIPO DESCRIPCION IMPORTE € BALANCE €
        yyyy
        """
        records = []
        lines = text.split('\n')

        # Buscar el inicio de transacciones
        start_idx = 0
        for i, line in enumerate(lines):
            if 'FECHA TIPO DESCRIPCIÓN' in line or 'FECHA TIPO DESCRIPCION' in line:
                start_idx = i + 1
                break

        # Procesar líneas - rastrear balance anterior
        i = start_idx
        balance_anterior = None
        while i < len(lines):
            line = lines[i].strip()

            # Skip líneas vacías o headers
            if not line or line.startswith('TRADE REPUBLIC') or 'FECHA TIPO' in line:
                i += 1
                continue

            # Intentar parsear como inicio de transacción
            transaction = self._parse_transaction_multi_line(lines, i, iban, page_num, balance_anterior)
            if transaction:
                records.append(transaction)
                # Actualizar balance anterior para la siguiente transacción
                balance_anterior = transaction.get('_balance_actual')
                i += transaction.get('_lines_consumed', 1)
            else:
                i += 1

        return records

    def _parse_transaction_multi_line(self, lines: List[str], idx: int, iban: str, page_num: int, balance_anterior: Optional[float] = None) -> Optional[Dict]:
        """
        Parsear transacción que puede estar en 2-3 líneas.

        Formato esperado:
        Línea 1: dd mmm [DESCRIPCION_INICIO]
        Línea 2: [TIPO] DESCRIPCION [IMPORTES]
        Línea 3: yyyy [DESCRIPCION_EXTRA]

        Args:
            balance_anterior: Balance de la transacción anterior (para determinar signo)
        """
        if idx >= len(lines):
            return None

        line1 = lines[idx].strip()

        # Detectar si la primera línea tiene fecha (dd mmm)
        match_date = re.match(r'^(\d{1,2})\s+([a-z]{3})\s*(.*)$', line1, re.IGNORECASE)
        if not match_date:
            return None

        dia = match_date.group(1).zfill(2)
        mes_nombre = match_date.group(2).lower()
        resto_linea1 = match_date.group(3).strip()

        # Convertir mes a número
        meses = {
            'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
        }
        mes = meses.get(mes_nombre, '01')

        # Leer siguientes líneas
        if idx + 2 >= len(lines):
            return None

        line2 = lines[idx + 1].strip()
        line3 = lines[idx + 2].strip()

        # Buscar año en line3 (debe empezar con 4 dígitos)
        match_year = re.match(r'^(\d{4})(.*)$', line3)
        if not match_year:
            return None

        anio = match_year.group(1)
        resto_linea3 = match_year.group(2).strip()

        # Construir fecha
        fecha = f"{anio}-{mes}-{dia}"

        # Construir descripción completa
        descripcion_parts = []
        if resto_linea1:
            descripcion_parts.append(resto_linea1)

        # line2 contiene el tipo, descripción e importes
        # Extraer importes de line2
        importes = re.findall(r'([\d.]+,\d{2})\s*€', line2)

        if len(importes) < 2:
            return None  # Necesitamos al menos importe y balance

        # Último importe es balance, el anterior es el importe de transacción
        balance_str = importes[-1]
        importe_str = importes[-2]

        # Eliminar importes de line2 para extraer descripción
        descripcion_line2 = line2
        for imp in importes:
            descripcion_line2 = descripcion_line2.replace(f"{imp} €", "")
        descripcion_line2 = descripcion_line2.strip()

        descripcion_parts.append(descripcion_line2)

        if resto_linea3:
            descripcion_parts.append(resto_linea3)

        # Filter out 'null' strings before joining
        descripcion_parts = [p for p in descripcion_parts if p and p.lower() != 'null']
        descripcion_completa = " ".join(descripcion_parts)
        descripcion_completa = re.sub(r'\s+', ' ', descripcion_completa).strip()
        # Clean any remaining 'null' occurrences
        descripcion_completa = re.sub(r'\bnull\b', '', descripcion_completa, flags=re.IGNORECASE)
        descripcion_completa = re.sub(r'\s+', ' ', descripcion_completa).strip()

        # Convertir importes
        importe = self.parse_spanish_number(importe_str)
        balance = self.parse_spanish_number(balance_str)

        # Determinar signo basado en el CAMBIO DEL BALANCE (método más robusto)
        # Si balance aumentó → ENTRADA (positivo)
        # Si balance disminuyó → SALIDA (negativo)
        if balance_anterior is not None:
            cambio_balance = balance - balance_anterior
            if cambio_balance > 0:
                # Balance aumentó → es un ingreso
                importe = abs(importe)
            elif cambio_balance < 0:
                # Balance disminuyó → es un gasto
                importe = -abs(importe)
            else:
                # Balance no cambió (raro, pero mantener como está)
                importe = abs(importe) if importe > 0 else -abs(importe)
        else:
            # Sin balance anterior, usar lógica de palabras clave como fallback
            if 'Ingreso aceptado' in descripcion_completa or 'Incoming transfer' in descripcion_completa:
                importe = abs(importe)
            elif 'Interés' in descripcion_completa or 'Your interest payment' in descripcion_completa:
                importe = abs(importe)
            elif 'PayOut' in descripcion_completa or 'payout' in descripcion_completa.lower():
                importe = -abs(importe)
            elif 'Transacción' in descripcion_completa and 'con tarjeta' in descripcion_completa:
                importe = -abs(importe)
            elif 'Savings plan execution' in descripcion_completa:
                importe = -abs(importe)
            elif 'Outgoing transfer' in descripcion_completa:
                importe = -abs(importe)
            else:
                # Por defecto, asumir positivo si no hay contexto
                importe = abs(importe)

        # Normalizar descripción para hash (evita duplicados CSV/PDF)
        descripcion_normalizada = normalize_tr_description_for_hash(descripcion_completa)

        record = {
            "fecha": fecha,
            "importe": importe,
            "descripcion": descripcion_completa,
            "banco": self.BANK_NAME,
            "cuenta": iban,
            "line_num": page_num,
            "hash": self.generate_hash(fecha, importe, descripcion_normalizada, iban, page_num),
            "_lines_consumed": 3,  # Consumimos 3 líneas
            "_balance_actual": balance  # Guardar balance para la siguiente transacción
        }

        return record
