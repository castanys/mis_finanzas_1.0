"""
Parser para PDFs de Trade Republic.

Formato PDF:
- IBAN en página 1: ES8015860001420977164411
- Periodo: DD MMM YYYY - DD MMM YYYY (español)
- Estructura semi-tabular:
  * FECHA | TIPO | DESCRIPCIÓN | ENTRADA/SALIDA | BALANCE
  * Fechas: "DD MMM" o "DD MMM\nYYYY" (formato español)
  * Importes: formato español con coma decimal y símbolo € (0,41 €, 192,70 €)
  * Tipos: Transferencia, Transacción con tarjeta, Operar, Interés
"""
import pdfplumber
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from parsers.tr_hash_normalizer import normalize_tr_description_for_hash


class TradeRepublicParser:
    """Parser para PDFs de Trade Republic."""

    BANCO = "Trade Republic"

    # Mapeo de meses en español a números
    MESES_ES = {
        'ene': 1, 'enero': 1,
        'feb': 2, 'febrero': 2,
        'mar': 3, 'marzo': 3,
        'abr': 4, 'abril': 4,
        'may': 5, 'mayo': 5,
        'jun': 6, 'junio': 6,
        'jul': 7, 'julio': 7,
        'ago': 8, 'agosto': 8,
        'sep': 9, 'sept': 9, 'septiembre': 9,
        'oct': 10, 'octubre': 10,
        'nov': 11, 'noviembre': 11,
        'dic': 12, 'diciembre': 12,
    }

    # Tipos de transacción
    TIPOS_TRANSFERENCIA = ['Transferencia', 'Incoming transfer', 'Outgoing transfer']
    TIPOS_TARJETA = ['Transacción con tarjeta', 'Transacción\ncon tarjeta']
    TIPOS_INVERSION = ['Operar', 'Savings plan execution']
    TIPOS_INTERES = ['Interés', 'Interest payment']

    def __init__(self):
        self.iban = None
        self.year_context = None  # Año del periodo (para transacciones sin año explícito)

    def parse(self, file_path: str) -> List[Dict]:
        """
        Parsea un PDF de Trade Republic.

        Args:
            file_path: Ruta al archivo PDF

        Returns:
            Lista de transacciones parseadas
        """
        transactions = []

        with pdfplumber.open(file_path) as pdf:
            # Página 1: extraer IBAN y periodo
            if len(pdf.pages) > 0:
                first_page_text = pdf.pages[0].extract_text()
                self.iban = self._extract_iban(first_page_text)
                self.year_context = self._extract_year_from_periodo(first_page_text)

            # Procesar todas las páginas
            for page in pdf.pages:
                page_transactions = self._parse_page(page)
                transactions.extend(page_transactions)

        return transactions

    def _extract_iban(self, text: str) -> Optional[str]:
        """
        Extrae el IBAN del texto de la primera página.

        Args:
            text: Texto de la página

        Returns:
            IBAN o None
        """
        # Buscar patrón "IBAN ESXXXXXXXXXXXXXXXXXX"
        match = re.search(r'IBAN\s+(ES\d{22})', text)
        if match:
            return match.group(1)
        return None

    def _extract_year_from_periodo(self, text: str) -> Optional[int]:
        """
        Extrae el año del periodo en el encabezado.

        Formato: "FECHA 01 dic 2025 - 13 feb 2026"

        Args:
            text: Texto de la página

        Returns:
            Año más reciente del periodo
        """
        # Buscar patrón "FECHA DD MMM YYYY - DD MMM YYYY"
        match = re.search(r'FECHA\s+\d+\s+\w+\s+(\d{4})\s*-\s*\d+\s+\w+\s+(\d{4})', text)
        if match:
            # Devolver el año más reciente (segundo año)
            return int(match.group(2))

        # Fallback: buscar cualquier año 20XX
        match = re.search(r'20\d{2}', text)
        if match:
            return int(match.group(0))

        return None

    def _parse_page(self, page) -> List[Dict]:
        """
        Parsea una página del PDF.

        Args:
            page: Página de pdfplumber

        Returns:
            Lista de transacciones de la página
        """
        text = page.extract_text()
        if not text:
            return []

        transactions = []
        lines = text.split('\n')

        i = 0
        balance_anterior = None  # Rastrear balance para determinar signo
        while i < len(lines):
            line = lines[i].strip()

            # Detectar inicio de transacción por fecha (DD MMM)
            fecha_match = re.match(r'^(\d{1,2})\s+(ene|feb|mar|abr|may|jun|jul|ago|sep|sept|oct|nov|dic)', line, re.IGNORECASE)

            if fecha_match:
                # Verificar que las siguientes líneas existan y contengan importes €
                # Esto evita falsos positivos
                has_importes = False
                for offset in range(1, 4):
                    if i + offset < len(lines):
                        if '€' in lines[i + offset]:
                            has_importes = True
                            break

                if has_importes:
                    # Intentar parsear transacción multi-línea con balance anterior
                    transaction, lines_consumed = self._parse_transaction(lines, i, balance_anterior)
                    if transaction:
                        transactions.append(transaction)
                        # Actualizar balance anterior para la siguiente transacción
                        balance_anterior = transaction.get('balance')
                    i += lines_consumed
                else:
                    i += 1
            else:
                i += 1

        return transactions

    def _parse_transaction(self, lines: List[str], start_idx: int, balance_anterior: Optional[float] = None) -> tuple[Optional[Dict], int]:
        """
        Parsea una transacción multi-línea.

        Formato observado (3-4 líneas):
        Línea 0: DD MMM [Descripción parte 1]
        Línea 1: Tipo [Descripción parte 2] Importes
        Línea 2: YYYY [info adicional]
        [Línea 3: info adicional opcional]

        Args:
            lines: Todas las líneas del texto
            start_idx: Índice de la línea de fecha
            balance_anterior: Balance de la transacción anterior (para determinar signo)

        Returns:
            (Transacción parseada, número de líneas consumidas)
        """
        try:
            # Reunir las 3-4 líneas de la transacción
            if start_idx + 2 >= len(lines):
                return None, 1

            line0 = lines[start_idx].strip()      # DD MMM [descripción]
            line1 = lines[start_idx + 1].strip()  # Tipo + Descripción + Importes
            line2 = lines[start_idx + 2].strip()  # YYYY [+ info]

            # Extraer fecha de line0
            fecha_match = re.match(r'^(\d{1,2})\s+(ene|feb|mar|abr|may|jun|jul|ago|sep|sept|oct|nov|dic)', line0, re.IGNORECASE)
            if not fecha_match:
                return None, 1

            dia = int(fecha_match.group(1))
            mes = self.MESES_ES[fecha_match.group(2).lower()]

            # Extraer año de line2 (que comienza con YYYY)
            year_match = re.match(r'^(\d{4})', line2)
            if year_match:
                year = int(year_match.group(1))
            else:
                year = self.year_context

            if not year:
                return None, 3

            fecha = datetime(year, mes, dia).date()

            # Combinar SOLO line0 + line1 + line2 (NO line3 que puede ser siguiente transacción)
            full_text = f"{line0} {line1} {line2}"

            # Detectar tipo de transacción
            tipo = self._detect_tipo(full_text)

            # Extraer todos los importes del texto completo
            importes = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})\s*€', full_text)

            if len(importes) < 2:
                return None, 3

            # Los dos últimos importes son: [cantidad, balance]
            importe_str = importes[-2]
            balance_str = importes[-1]

            # Convertir formato español a float
            importe_value = float(importe_str.replace('.', '').replace(',', '.'))
            balance = float(balance_str.replace('.', '').replace(',', '.'))

            # Extraer descripción
            # Prioridad: línea 0 (después de fecha) o línea 1 (antes de tipo)
            descripcion = ''

            # Opción 1: Descripción en line0 (después de "DD MMM")
            desc_match = re.search(r'^\d{1,2}\s+\w+\s+(.+)', line0)
            if desc_match:
                descripcion = desc_match.group(1).strip()

            # Opción 2: Añadir descripción de line1 (antes de importes)
            # Remover tipo conocido y importes
            line1_clean = line1
            for tipo_kw in self.TIPOS_TRANSFERENCIA + self.TIPOS_TARJETA + self.TIPOS_INVERSION + self.TIPOS_INTERES:
                line1_clean = line1_clean.replace(tipo_kw, '')
            # Remover importes
            for imp in importes:
                line1_clean = line1_clean.replace(imp + ' €', '')
                line1_clean = line1_clean.replace(imp + '€', '')
            line1_clean = line1_clean.strip()

            if line1_clean and not descripcion:
                descripcion = line1_clean
            elif line1_clean:
                descripcion = f"{descripcion} {line1_clean}"

            # Limpiar descripción
            descripcion = re.sub(r'null', '', descripcion, flags=re.IGNORECASE)  # Remover 'null' en cualquier posición
            descripcion = re.sub(r'\s+', ' ', descripcion).strip()  # Normalizar espacios

            # Remover prefijo "Transacción " que agrega Trade Republic
            if descripcion.startswith('Transacción '):
                descripcion = descripcion[12:].strip()  # len('Transacción ') = 12

            if not descripcion:
                descripcion = 'Sin concepto'
            
            # FIX para pagos de interés mensual del PDF:
            # El PDF no extrae el concepto en los pagos de interés (tipo='Interés')
            # El CSV lo tiene como "interest payment" después de normalizar
            # Canonicalizar a "interest payment" para que coincida
            if descripcion == 'Sin concepto' and tipo.lower() in ['interés', 'interest']:
                descripcion = 'interest payment'

            # Determinar signo del importe basado en CAMBIO DEL BALANCE (método robusto)
            # Si balance aumentó → ENTRADA (positivo)
            # Si balance disminuyó → SALIDA (negativo)
            if balance_anterior is not None:
                cambio_balance = balance - balance_anterior
                if cambio_balance > 0:
                    # Balance aumentó → es un ingreso
                    importe = importe_value
                elif cambio_balance < 0:
                    # Balance disminuyó → es un gasto
                    importe = -importe_value
                else:
                    # Balance no cambió (raro, pero mantener positivo)
                    importe = importe_value
            else:
                # Sin balance anterior, usar lógica de palabras clave como fallback
                if any(kw in full_text for kw in ['Incoming transfer', 'Interest payment', 'Interés']):
                    importe = importe_value  # Ingreso: positivo
                elif any(kw in full_text for kw in ['Outgoing transfer', 'con tarjeta', 'Operar', 'Savings plan']):
                    importe = -importe_value  # Gasto: negativo
                else:
                    # Por defecto, asumir positivo
                    importe = importe_value

            # Convertir fecha a string ISO
            fecha_str = fecha.isoformat()

            # Generar hash SHA256: fecha|importe:.2f|descripcion_normalizada|iban
            # CRÍTICO: Normalizar descripción ANTES de calcular hash para que coincida con CSV
            iban = self.iban or 'Trade Republic'
            descripcion_normalizada = normalize_tr_description_for_hash(descripcion)
            hash_input = f"{fecha_str}|{importe:.2f}|{descripcion_normalizada}|{iban}"
            hash_val = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

            return {
                'fecha': fecha_str,  # String ISO, no datetime.date
                'fecha_valor': fecha_str,
                'descripcion': descripcion,   # Campo estándar para pipeline
                'concepto': descripcion,
                'importe': importe,
                'balance': balance,
                'moneda': 'EUR',
                'cuenta': iban,
                'banco': self.BANCO,
                'tipo_operacion': tipo,
                'hash': hash_val,
            }, 3  # Consumir 3 líneas por transacción

        except Exception as e:
            print(f"⚠️  Error parseando transacción en línea {start_idx}: {e}")
            return None, 1

    def _detect_tipo(self, line: str) -> str:
        """
        Detecta el tipo de operación de la línea.

        Args:
            line: Línea de texto

        Returns:
            Tipo de operación
        """
        if any(kw in line for kw in self.TIPOS_TRANSFERENCIA):
            return 'Transferencia'
        elif any(kw in line for kw in self.TIPOS_TARJETA):
            return 'Tarjeta'
        elif any(kw in line for kw in self.TIPOS_INVERSION):
            return 'Inversión'
        elif any(kw in line for kw in self.TIPOS_INTERES):
            return 'Interés'
        else:
            return 'Otro'


def test_parser():
    """Test del parser con el PDF de Trade Republic."""
    parser = TradeRepublicParser()

    file_path = 'input/new/Extracto de cuenta (1).pdf'

    print(f"{'='*60}")
    print(f"Parseando: {Path(file_path).name}")
    print('='*60)

    try:
        transactions = parser.parse(file_path)
        print(f"✅ Transacciones parseadas: {len(transactions)}")

        if transactions:
            print(f"\nIBAN detectado: {parser.iban}")
            print(f"Año contexto: {parser.year_context}")

            print(f"\nPrimeras 5 transacciones:")
            for i, t in enumerate(transactions[:5]):
                print(f"\n  {i+1}. Fecha: {t['fecha']}")
                print(f"     Concepto: {t['concepto'][:60]}")
                print(f"     Tipo: {t['tipo_operacion']}")
                print(f"     Importe: {t['importe']:.2f} {t['moneda']}")
                print(f"     Balance: {t['balance']:.2f} {t['moneda']}")

            print(f"\nÚltima transacción:")
            t = transactions[-1]
            print(f"  Fecha: {t['fecha']}")
            print(f"  Concepto: {t['concepto'][:60]}")
            print(f"  Importe: {t['importe']:.2f} {t['moneda']}")

            print(f"\nResumen:")
            total_ingresos = sum(t['importe'] for t in transactions if t['importe'] > 0)
            total_gastos = sum(t['importe'] for t in transactions if t['importe'] < 0)
            print(f"  Total ingresos: {total_ingresos:.2f} EUR")
            print(f"  Total gastos: {total_gastos:.2f} EUR")
            print(f"  Balance neto: {total_ingresos + total_gastos:.2f} EUR")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_parser()
