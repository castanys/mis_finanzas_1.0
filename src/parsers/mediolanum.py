"""
Parser para ficheros XLS de Mediolanum.

Formato XLS:
- Fila 6: Metadatos → "Consulta de extracto de la cuenta | 50010510084831 | | Saldo Inicial: | | 73.9"
- Fila 7: Cabeceras → "Fecha Operación | Concepto | Fecha Valor | Pagos | Ingresos | Saldo"
- Filas 8+: Datos de transacciones
- Columnas:
  * Col 0: Fecha Operación (YYYY-MM-DD)
  * Col 1: Concepto
  * Col 2: Fecha Valor (YYYY-MM-DD)
  * Col 3: Pagos (gastos, sin signo)
  * Col 4: Ingresos (sin signo)
  * Col 5: Saldo
- Importes: formato inglés con punto decimal, SIN signo (columnas separadas)
"""
import xlrd
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class MediolanumParser:
    """Parser para XLS de Mediolanum."""

    BANCO = "Mediolanum"
    CODIGO_BANCO = "0501"

    # Fila donde están los metadatos (número de cuenta)
    METADATA_ROW = 6
    # Fila donde están las cabeceras
    HEADER_ROW = 7
    # Primera fila de datos
    DATA_START_ROW = 8

    def __init__(self, cuentas_config_path: str = 'config/cuentas.json'):
        """
        Inicializa el parser.

        Args:
            cuentas_config_path: Ruta al archivo de configuración de cuentas
        """
        self.cuentas_config_path = cuentas_config_path
        self.cuentas = self._load_cuentas()

    def _load_cuentas(self) -> Dict:
        """Carga el registro de cuentas desde JSON."""
        try:
            with open(self.cuentas_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  No se pudo cargar cuentas.json: {e}")
            return {"cuentas": []}

    def parse(self, file_path: str) -> List[Dict]:
        """
        Parsea un XLS de Mediolanum.

        Args:
            file_path: Ruta al archivo XLS

        Returns:
            Lista de transacciones parseadas
        """
        workbook = xlrd.open_workbook(file_path)
        sheet = workbook.sheet_by_index(0)

        # Extraer número de cuenta de la fila de metadatos
        numero_cuenta = self._extract_numero_cuenta(sheet)
        if not numero_cuenta:
            raise ValueError(f"No se pudo extraer número de cuenta del archivo: {file_path}")

        # Buscar IBAN correspondiente en cuentas.json
        cuenta_info = self._find_cuenta_info(numero_cuenta)
        iban = cuenta_info.get('iban') if cuenta_info else None

        # Si no hay IBAN, construir IBAN Mediolanum standard (ES2501 + número de cuenta)
        if not iban:
            iban = f"ES2501{numero_cuenta}"
        
        cuenta_id = iban

        transactions = []

        # Parsear filas de datos
        for row_idx in range(self.DATA_START_ROW, sheet.nrows):
            transaction = self._parse_transaction_row(sheet, row_idx, workbook.datemode, cuenta_id)
            if transaction:
                transactions.append(transaction)

        return transactions

    def _extract_numero_cuenta(self, sheet) -> Optional[str]:
        """
        Extrae el número de cuenta de la fila de metadatos.

        Formato: "Consulta de extracto de la cuenta | 50010510084831.0 | ..."

        Args:
            sheet: Hoja de Excel

        Returns:
            Número de cuenta (sin decimales) o None
        """
        if sheet.nrows <= self.METADATA_ROW:
            return None

        # La cuenta está en col 1 de la fila 6
        cell = sheet.cell(self.METADATA_ROW, 1)
        cuenta_str = str(cell.value).strip()

        # Remover .0 si es float
        if cuenta_str.endswith('.0'):
            cuenta_str = cuenta_str[:-2]

        # Validar que sea numérico
        if cuenta_str and cuenta_str.replace('.', '').isdigit():
            return cuenta_str.replace('.', '')

        return None

    def _find_cuenta_info(self, numero_cuenta: str) -> Optional[Dict]:
        """
        Busca la información de cuenta en cuentas.json.

        Args:
            numero_cuenta: Número de cuenta a buscar

        Returns:
            Dict con info de la cuenta o None
        """
        for cuenta in self.cuentas.get('cuentas', []):
            if cuenta.get('numero_cuenta') == numero_cuenta:
                return cuenta
        return None

    def _parse_transaction_row(self, sheet, row_idx: int, datemode: int, cuenta_id: str) -> Optional[Dict]:
        """
        Parsea una fila de transacción.

        Args:
            sheet: Hoja de Excel
            row_idx: Índice de la fila
            datemode: Modo de fecha de Excel
            cuenta_id: ID de la cuenta (IBAN o número)

        Returns:
            Dict con transacción parseada o None
        """
        try:
            # Col 0: Fecha Operación
            fecha_cell = sheet.cell(row_idx, 0)
            if fecha_cell.ctype == xlrd.XL_CELL_DATE:
                date_tuple = xlrd.xldate_as_tuple(fecha_cell.value, datemode)
                fecha = datetime(*date_tuple[:3]).date()
            elif fecha_cell.ctype == xlrd.XL_CELL_TEXT:
                # Intentar parsear como texto YYYY-MM-DD
                fecha = datetime.strptime(fecha_cell.value.strip(), '%Y-%m-%d').date()
            else:
                return None

            # Col 1: Concepto
            concepto = str(sheet.cell(row_idx, 1).value).strip()
            if not concepto or concepto == '':
                concepto = 'Sin concepto'

            # Col 2: Fecha Valor
            fecha_valor = None
            fecha_valor_cell = sheet.cell(row_idx, 2)
            if fecha_valor_cell.ctype == xlrd.XL_CELL_DATE:
                date_tuple = xlrd.xldate_as_tuple(fecha_valor_cell.value, datemode)
                fecha_valor = datetime(*date_tuple[:3]).date()
            elif fecha_valor_cell.ctype == xlrd.XL_CELL_TEXT and fecha_valor_cell.value.strip():
                try:
                    fecha_valor = datetime.strptime(fecha_valor_cell.value.strip(), '%Y-%m-%d').date()
                except:
                    pass

            # Col 3: Pagos (gastos, sin signo negativo)
            pagos_cell = sheet.cell(row_idx, 3)
            pagos = 0.0
            if pagos_cell.ctype in (xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_TEXT):
                try:
                    pagos_str = str(pagos_cell.value).strip()
                    if pagos_str and pagos_str != '':
                        pagos = float(pagos_str)
                except:
                    pass

            # Col 4: Ingresos (sin signo)
            ingresos_cell = sheet.cell(row_idx, 4)
            ingresos = 0.0
            if ingresos_cell.ctype in (xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_TEXT):
                try:
                    ingresos_str = str(ingresos_cell.value).strip()
                    if ingresos_str and ingresos_str != '':
                        ingresos = float(ingresos_str)
                except:
                    pass

            # Col 5: Saldo
            saldo_cell = sheet.cell(row_idx, 5)
            saldo = None
            if saldo_cell.ctype in (xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_TEXT):
                try:
                    saldo_str = str(saldo_cell.value).strip()
                    if saldo_str and saldo_str != '':
                        saldo = float(saldo_str)
                except:
                    pass

            # Calcular importe (pagos son negativos, ingresos positivos)
            importe = ingresos - pagos

            # Saltar si no hay movimiento
            if importe == 0.0:
                return None

            return {
                'fecha': fecha,
                'fecha_valor': fecha_valor,
                'concepto': concepto,
                'importe': importe,
                'balance': saldo,
                'moneda': 'EUR',
                'cuenta': cuenta_id,
                'banco': self.BANCO,
            }

        except Exception as e:
            print(f"⚠️  Error parseando fila {row_idx}: {e}")
            return None


def test_parser():
    """Test del parser con el fichero XLS."""
    parser = MediolanumParser()

    file_path = 'input/new/tmp1520873390.xls'

    print(f"{'='*60}")
    print(f"Parseando: {Path(file_path).name}")
    print('='*60)

    try:
        transactions = parser.parse(file_path)
        print(f"✅ Transacciones parseadas: {len(transactions)}")

        if transactions:
            print(f"\nPrimera transacción:")
            t = transactions[0]
            print(f"  Fecha: {t['fecha']}")
            print(f"  Concepto: {t['concepto'][:60]}")
            print(f"  Importe: {t['importe']:.2f} {t['moneda']}")
            print(f"  Balance: {t['balance']:.2f} {t['moneda']}")
            print(f"  Banco: {t['banco']}")
            print(f"  Cuenta: {t['cuenta']}")

            print(f"\nÚltima transacción:")
            t = transactions[-1]
            print(f"  Fecha: {t['fecha']}")
            print(f"  Concepto: {t['concepto'][:60]}")
            print(f"  Importe: {t['importe']:.2f} {t['moneda']}")
            print(f"  Balance: {t['balance']:.2f} {t['moneda']}")

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
