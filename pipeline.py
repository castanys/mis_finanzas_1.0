"""
Pipeline principal: parse → dedup → classify → output

Orquesta el procesamiento de CSVs bancarios:
1. Detecta el banco del archivo
2. Parsea usando el parser específico
3. Deduplica usando hashes
4. Clasifica usando el clasificador de 5 capas
5. Retorna transacciones nuevas clasificadas
"""
import os
from typing import List, Dict, Set, Optional
from pathlib import Path
import json
import csv
import sqlite3
import shutil
from datetime import datetime

from src.logger import get_logger

from parsers import (
    OpenbankParser,
    MyInvestorParser,
    MediolanumParser as MediolanumParserOld,
    RevolutParser,
    TradeRepublicParser as TradeRepublicParserCSV,  # CSV parser de Trade Republic
    B100Parser,
    AbancaParser,
    PreprocessedParser,
    BankinterParser,
)
# Nuevos parsers para ficheros Enablebanking, Mediolanum XLS, Trade Republic PDF, Trade Republic pytr
from src.parsers.enablebanking import EnablebankingParser
from src.parsers.mediolanum import MediolanumParser
from src.parsers.trade_republic import TradeRepublicParser as TradeRepublicParserPDF
from classifier import Classifier
from classifier.engine import determine_tipo
from classifier.normalization import normalize_description
import json


class TransactionPipeline:
    """Main pipeline: parse → dedup → classify → output"""

    def __init__(self, master_csv_path: str, known_hashes: Optional[Dict] = None, db_path: str = 'finsense.db'):
        """
        Initialize pipeline.

        Args:
            master_csv_path: Path to master CSV for exact match layer
            known_hashes: Dict of account -> dict of hashes for same-account deduplication
            db_path: Path to SQLite database
        """
        self.logger = get_logger()
        self.db_path = db_path
        self.known_hashes = known_hashes or {}
        self.parsers = {
            'openbank': OpenbankParser(),
            'myinvestor': MyInvestorParser(),
            'mediolanum': MediolanumParser(),  # Nuevo parser XLS
            'mediolanum_old': MediolanumParserOld(),  # Parser antiguo como fallback
            'revolut': RevolutParser(),
            'trade_republic_csv': TradeRepublicParserCSV(),  # Parser CSV de Trade Republic (formato antiguo)
            'trade_republic_pdf': TradeRepublicParserPDF(),  # Parser PDF de Trade Republic
            'b100': B100Parser(),
            'abanca': AbancaParser(),
            'bankinter': BankinterParser(),  # Nuevo parser Bankinter
            'enablebanking': EnablebankingParser(),  # Nuevo parser Enablebanking (Abanca+Openbank)
            'preprocessed': PreprocessedParser(),
        }
        self.classifier = Classifier(master_csv_path)

        # Cargar excepciones de clasificación
        self.excepciones = []
        excepciones_path = 'excepciones_clasificacion.json'
        if os.path.exists(excepciones_path):
            with open(excepciones_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.excepciones = data.get('excepciones', [])
            self.logger.debug(f"Cargadas {len(self.excepciones)} excepciones de clasificación")

        # Calcular total conocido: sum de counts en todos los hashes de todas las cuentas
        total_known = 0
        for cuenta_hashes in self.known_hashes.values():
            for hash_info in cuenta_hashes.values():
                if isinstance(hash_info, dict):
                    # Nuevo formato: {filename: count}
                    total_known += sum(hash_info.values())
                else:
                    # Formato antiguo (por compatibilidad)
                    total_known += 1
        self.logger.info(f"Pipeline inicializado con {total_known} transacciones conocidas en {len(self.known_hashes)} cuentas")

    def check_excepcion(self, fecha: str, importe: float, banco: str) -> Optional[Dict]:
        """
        Chequea si una transacción está en las excepciones.

        Args:
            fecha: Fecha de la transacción (YYYY-MM-DD)
            importe: Importe de la transacción
            banco: Nombre del banco

        Returns:
            Dict con cat1, cat2 si es excepción, None si no
        """
        for exc in self.excepciones:
            if (exc['fecha'] == fecha and
                abs(exc['importe'] - importe) < 0.01 and
                exc['banco'] == banco):
                return {
                    'cat1': exc['cat1'],
                    'cat2': exc.get('cat2', ''),
                }
        return None

    def detect_bank(self, filepath: str) -> str:
        """
        Detect bank from filename and file content.

        Args:
            filepath: Path to CSV/XLS/PDF file

        Returns:
            Bank identifier (lowercase) or 'unknown'
        """
        filename = os.path.basename(filepath).lower()
        extension = os.path.splitext(filepath)[1].lower()

        # Detectar por extensión primero
        # PDFs: Trade Republic
        if extension == '.pdf':
            if 'extracto' in filename or 'trade' in filename or 'cuenta' in filename:
                return 'trade_republic_pdf'

        # XLS/XLSX: Mediolanum
        if extension in ['.xls', '.xlsx']:
            return 'mediolanum'

        # CSVs: revisar contenido y nombre
        if extension == '.csv':
            # Leer primera línea para detectar por header
            # (utf-8-sig primero, latin-1 como fallback para ficheros con Ñ)
            first_line = ''
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    first_line = f.readline().strip()
            except (UnicodeDecodeError, IOError):
                try:
                    with open(filepath, 'r', encoding='latin-1') as f:
                        first_line = f.readline().strip()
                except Exception:
                    pass

            if first_line:
                # Preprocessed: Fecha,Importe,Descripcion,Banco,Cuenta
                if 'Fecha,Importe,Descripcion,Banco,Cuenta' in first_line:
                    return 'preprocessed'

                # Trade Republic CSV: fecha,importe,concepto,banco,balance
                if 'fecha,importe,concepto,banco' in first_line.lower():
                    return 'trade_republic_csv'

                # Enablebanking formato nuevo: booking_date,value_date,amount,currency,...
                if first_line.startswith('booking_date,value_date,amount,currency'):
                    return 'enablebanking'

                # Enablebanking formato antiguo: booking_datetime,value_datetime,amount,currency,...
                if first_line.startswith('booking_datetime,value_datetime,amount,currency'):
                    return 'enablebanking'

                # Abanca formato banco directo: Fecha ctble;Fecha valor;Concepto;...
                if first_line.startswith('Fecha ctble;Fecha valor;Concepto'):
                    return 'abanca'

                # Abanca formato web/app: Fecha,Concepto,Saldo,Importe,Fecha operación,Fecha valor
                if first_line.startswith('Fecha,Concepto,Saldo,Importe'):
                    return 'abanca'

                # Mediolanum CSV: Fecha Operación;Concepto;Fecha Valor;Pagos;Ingresos;...
                if 'Pagos' in first_line and 'Ingresos' in first_line and 'Fecha Operación' in first_line:
                    return 'mediolanum_old'

                # Openbank formato nuevo (columnas vacías): ;Fecha Operación;;Fecha Valor;;...
                if first_line.startswith(';Fecha Operación;;Fecha Valor;;Concepto'):
                    return 'openbank'

                # Openbank formato TOTAL: Fecha valor;Concepto;Importe;Cuenta;Saldo
                if first_line.startswith('Fecha valor;Concepto;Importe;Cuenta;Saldo'):
                    return 'openbank'

            # Fallback por nombre de fichero
            # enable_abanca_* y enable_openbank_* son siempre Enablebanking
            if filename.startswith('enable_abanca_') or filename.startswith('enable_openbank_'):
                return 'enablebanking'

            # abanca_ESXX... y openbank_ESXX... (enablebanking con booking_datetime)
            if filename.startswith('abanca_es') or filename.startswith('openbank_es'):
                return 'enablebanking'

            if 'openbank' in filename:
                return 'openbank'
            if 'myinvestor' in filename:
                return 'myinvestor'
            if 'mediolanum' in filename:
                return 'mediolanum_old'  # CSV de Mediolanum → parser viejo (CSV con ';')
            if 'revolut' in filename:
                return 'revolut'
            if 'trade' in filename or 'traderepublic' in filename:
                return 'trade_republic_csv'
            if 'b100' in filename or 'movimientosb100' in filename:
                return 'b100'
            if 'abanca' in filename:
                return 'abanca'
            if 'bankinter' in filename:
                return 'bankinter'

        return 'unknown'

    def archive_pdf(self, filepath: str) -> bool:
        """
        Mover un archivo PDF procesado a input/procesados/ con timestamp.
        
        Args:
            filepath: Path al PDF a archivar
            
        Returns:
            True si se movió exitosamente, False en caso contrario
        """
        # Solo aplica a PDFs
        if not filepath.lower().endswith('.pdf'):
            return False
        
        try:
            # Crear directorio de archivados si no existe
            archive_dir = Path('input/procesados')
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Generar nombre con timestamp
            filename = os.path.basename(filepath)
            name_without_ext = os.path.splitext(filename)[0]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_filename = f"{name_without_ext}_{timestamp}.pdf"
            new_filepath = archive_dir / new_filename
            
            # Mover archivo
            shutil.move(filepath, str(new_filepath))
            
            self.logger.info(f"📦 PDF archivado → input/procesados/{new_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error archivando PDF {filepath}: {e}")
            return False

    def process_file(self, filepath: str, classify: bool = True) -> tuple:
        """
        Process a single CSV file.

        Args:
            filepath: Path to CSV file
            classify: Whether to classify transactions (default: True)

        Returns:
            Tuple (records, file_stats) where:
            - records: List of new transactions (already classified if classify=True)
            - file_stats: Dict with {total_original, nuevos, duplicados, dup_origen_por_fichero}
        """
        bank = self.detect_bank(filepath)

        if bank == 'unknown':
            self.logger.error(f"No se pudo detectar el banco del archivo: {filepath}")
            raise ValueError(f"No se pudo detectar el banco del archivo: {filepath}")

        if bank not in self.parsers:
            self.logger.error(f"No hay parser para el banco: {bank}")
            raise ValueError(f"No hay parser para el banco: {bank}")

        # Parse
        records = self.parsers[bank].parse(filepath)
        self.logger.debug(f"Parser {bank} parseó {len(records)} transacciones de {os.path.basename(filepath)}")

        # Deduplication ONLY for same account, cross-file
        # Do NOT deduplicate within the same file
        filename = os.path.basename(filepath)
        
        # Guardar total original ANTES de deduplicación
        total_original = len(records)

        # Guardar source_file en cada registro
        for r in records:
            r['source_file'] = filename

            # Normalize field names (some parsers use 'concepto', others 'descripcion')
            if 'concepto' in r and 'descripcion' not in r:
                r['descripcion'] = r['concepto']
            elif 'descripcion' in r and 'concepto' not in r:
                r['concepto'] = r['descripcion']

            # Generate hash if not present (should use parsers' SHA256, not MD5 fallback)
            if 'hash' not in r or not r['hash']:
                # IMPORTANTE: Los parsers deben SIEMPRE generar SHA256
                # Si faltan hashes, es un problema del parser, no del pipeline
                self.logger.error(f"Parser {r.get('banco')} no generó hash para transacción: {r}")
                raise ValueError(f"Parser {r.get('banco')} no generó hash para transacción: {r}")

        # Extract account from records (all records from same file have same account)
        duplicados_mismo = 0
        duplicados_bd = 0
        dup_origen_contador = {}  # {source_file_origen: cantidad}
        
        if records:
            account = records[0].get('cuenta', '')

            # Initialize account-specific hash dict if needed
            # Store {hash: source_file} to track which file each hash came from
            if account not in self.known_hashes:
                self.known_hashes[account] = {}

            # Deduplicate: BOTH internal (within same file) AND cross-file
            # NEW LOGIC: Usar contador de ocurrencias por hash para permitir txs idénticas legítimas
            filtered_records = []
            file_hash_count = {}  # {hash: contador de ocurrencias en este fichero}
            duplicados_internos = 0
            duplicados_cross = 0
            
            # PASO 1: Contar ocurrencias de cada hash dentro del fichero actual
            for r in records:
                hash_val = r['hash']
                file_hash_count[hash_val] = file_hash_count.get(hash_val, 0) + 1
            
            # PASO 2: Procesar records con lógica de contador
            file_hash_seen_count = {}  # {hash: cuántos hemos visto hasta ahora en este procesamiento}
            
            for r in records:
                hash_val = r['hash']
                
                # ¿Cuántas veces hemos visto este hash hasta ahora en este fichero?
                current_occurrence = file_hash_seen_count.get(hash_val, 0) + 1
                file_hash_seen_count[hash_val] = current_occurrence
                
                # ¿Cuántas veces existe este hash en ficheros anteriores (cross-file)?
                cross_file_count = 0
                cross_file_origin = None
                if hash_val in self.known_hashes[account]:
                    # known_hashes[account][hash] ahora es un dict {filename: count}
                    for fname, count in self.known_hashes[account][hash_val].items():
                        cross_file_count += count
                        if not cross_file_origin:
                            cross_file_origin = fname
                
                # Lógica: si esta es la ocurrencia número N dentro de este fichero,
                # y ya hay M ocurrencias en ficheros anteriores, entonces:
                # - Si N <= M: es un duplicado cross-file
                # - Si N > M: es una transacción genuinamente nueva (duplicado legítimo dentro del mismo fichero)
                if current_occurrence <= cross_file_count:
                    # Duplicado cross-file - SKIP
                    duplicados_cross += 1
                    duplicados_bd += 1
                    dup_origen_contador[cross_file_origin] = dup_origen_contador.get(cross_file_origin, 0) + 1
                    continue
                
                # Hash es nuevo o es una ocurrencia adicional - KEEP
                filtered_records.append(r)
            
            # PASO 3: Actualizar known_hashes SOLO con los hashes que fueron realmente insertados
            # Contar cuántas de cada hash fueron realmente insertadas en filtered_records
            inserted_hash_count = {}
            for r in filtered_records:
                hash_val = r['hash']
                inserted_hash_count[hash_val] = inserted_hash_count.get(hash_val, 0) + 1
            
            for hash_val, count_inserted in inserted_hash_count.items():
                if hash_val not in self.known_hashes[account]:
                    self.known_hashes[account][hash_val] = {}
                self.known_hashes[account][hash_val][filename] = count_inserted
            
            # Debug
            if total_original > 0:
                self.logger.debug(f"  {filename}: parseo={total_original}, internos_dup={duplicados_internos}, cross_dup={duplicados_cross}, result={len(filtered_records)}")

            # ===== ASIGNAR REGISTROS DEDUPLICADOS =====
            # Para todos los bancos: usar filtered_records (deduplicados)
            records = filtered_records

            self.logger.add_stat('duplicados_en_bd', duplicados_bd)

        # Guardar stats de este fichero
        file_stats = {
            'total_original': total_original,
            'nuevos': len(records),
            'duplicados': duplicados_bd,
            'dup_origen_por_fichero': dup_origen_contador
        }

        # Classify
        if classify:
            from collections import Counter
            capas_contador = Counter()
            capas_global = self.logger.stats.get('capas_clasificacion', {})
            
            for r in records:
                # Normalizar descripción ANTES de clasificar (una sola vez, centralizado)
                # Preservamos la original en 'descripcion', usamos normalizada solo para clasificar
                descripcion_original = r['descripcion']
                descripcion_normalizada = normalize_description(descripcion_original)

                # Clasificar usando descripción normalizada (el classifier chequea excepciones internamente)
                result = self.classifier.classify(
                    descripcion=descripcion_normalizada,
                    banco=r['banco'],
                    importe=r['importe'],
                    fecha=r['fecha'],  # Pasar fecha para chequeo de excepciones
                    cuenta=r.get('cuenta')  # Pasar cuenta para reglas específicas por IBAN
                )

                # Guardar resultados de clasificación
                r['cat1'] = result['cat1']
                r['cat2'] = result['cat2']
                r['tipo'] = result['tipo']
                r['capa'] = result['capa']
                
                # Recoger merchant_name si está disponible
                if 'merchant_name' in result and result['merchant_name']:
                    r['merchant_name'] = result['merchant_name']

                # Preservar descripción original (sin normalizar) en el registro
                # La normalizada solo se usó para clasificar
                r['descripcion'] = descripcion_original
                
                # Contar por capa
                capas_contador[result['capa']] += 1
            
            # Log de capas (BLOQUE 3)
            if records:
                self.logger.info(f"  Clasificación por capa:")
                for capa in sorted(capas_contador.keys()):
                    count = capas_contador[capa]
                    pct = 100 * count / len(records)
                    
                    # Nombres descriptivos por capa
                    nombres_capa = {
                        0: "Reglas prioritarias",
                        1: "Exact match",
                        2: "Merchants",
                        3: "Transferencias",
                        4: "Tokens",
                        5: "Sin clasificar"
                    }
                    nombre = nombres_capa.get(capa, f"Capa {capa}")
                    
                    if capa == 5 and count == 0:
                        # Sin clasificar = OK si es 0
                        self.logger.info(f"    Capa {capa} ({nombre:25s}): {count:5d} tx ({pct:5.1f}%) ✓")
                    else:
                        self.logger.info(f"    Capa {capa} ({nombre:25s}): {count:5d} tx ({pct:5.1f}%)")
                
                # Acumular stats de capas globalmente
                for capa, count in capas_contador.items():
                    capas_global[capa] = capas_global.get(capa, 0) + count
                
                self.logger.set_stat('capas_clasificacion', capas_global)

        # Post-procesamiento: merchants recurrentes
        if classify and records:
            from classifier.recurrent_merchants import apply_recurrent_merchants
            records = apply_recurrent_merchants(records, threshold=15)
        
        # Archivar PDF si fue procesado exitosamente
        if records and filepath.lower().endswith('.pdf'):
            self.archive_pdf(filepath)

        return records, file_stats

    def process_directory(self, dirpath: str, classify: bool = True) -> List[Dict]:
        """
        Process all CSV files in a directory.

        Args:
            dirpath: Path to directory containing CSV files
            classify: Whether to classify transactions (default: True)

        Returns:
            List of all new transactions
        """
        all_records = []
        file_stats = {}  # {filename: {total_original, nuevos, duplicados, dup_origen_por_fichero}}

        # Get all CSV files, prioritizing TOTAL files first
        def sort_priority(filename):
            # TOTAL files first, then alphabetically
            if 'TOTAL' in filename:
                return (0, filename)
            else:
                return (1, filename)

        csv_files = sorted(
            [f for f in os.listdir(dirpath) if f.endswith('.csv')],
            key=sort_priority
        )

        # Incluir PDFs también
        pdf_files = sorted([f for f in os.listdir(dirpath) if f.endswith('.pdf')])
        all_files = csv_files + pdf_files

        self.logger.info(f"Encontrados {len(csv_files)} CSVs y {len(pdf_files)} PDFs en {dirpath}")
        self.logger.add_stat('csvs_encontrados', len(csv_files) + len(pdf_files))

        for filename in all_files:
            filepath = os.path.join(dirpath, filename)
            try:
                # Procesar fichero y recibir stats enriquecidos
                records, stats_fichero = self.process_file(filepath, classify=classify)
                
                # Guardar stats por fichero (ahora con datos reales)
                file_stats[filename] = stats_fichero
                
                all_records.extend(records)
                
                # Log por fichero (BLOQUE 2 implementado aquí)
                total = stats_fichero['total_original']
                nuevos = stats_fichero['nuevos']
                duplicados = stats_fichero['duplicados']
                
                # GUARD DE SANIDAD: Verificar que nuevos <= total_original
                if nuevos > total:
                    self.logger.error(
                        f"🚨 SANIDAD FALLIDA en {filename}: "
                        f"nuevos ({nuevos}) > total_original ({total}). "
                        f"ABORTANDO ESTE FICHERO."
                    )
                    # No agregar estos registros a all_records
                    all_records = [r for r in all_records if r.get('source_file') != filename]
                    stats_fichero['sanidad_fallida'] = True
                    file_stats[filename] = stats_fichero
                    self.logger.add_stat('csvs_ignorados', 1)
                    continue
                
                if duplicados == 0:
                    dup_info = "0"
                else:
                    # Mostrar de qué ficheros vinieron los duplicados
                    dup_origen = stats_fichero['dup_origen_por_fichero']
                    dup_sources = ', '.join([f"{v}x {k}" for k, v in sorted(dup_origen.items())])
                    dup_info = f"{duplicados} (de: {dup_sources})"
                
                self.logger.info(
                    f"✓ {filename:45s} | "
                    f"Total: {total:4d} | Nuevos: {nuevos:4d} | Duplic: {dup_info}"
                )
                
                self.logger.add_stat('csvs_procesados', 1)
                self.logger.add_stat('transacciones_leidas', nuevos)
                
            except Exception as e:
                import traceback
                self.logger.error(f"✗ {filename:50s} ERROR: {e}")
                self.logger.debug(traceback.format_exc())
                file_stats[filename] = {
                    'total_original': 0,
                    'nuevos': 0,
                    'duplicados': 0,
                    'dup_origen_por_fichero': {},
                    'error': str(e),
                }
                self.logger.add_stat('csvs_ignorados', 1)

        self.logger.info(f"")
        self.logger.info(f"Total procesado: {len(all_records)} transacciones nuevas")

        # Mostrar ficheros con error si los hay
        ficheros_con_error = {f: s for f, s in file_stats.items() if 'error' in s}
        if ficheros_con_error:
            self.logger.warning(f"")
            self.logger.warning(f"FICHEROS CON ERROR ({len(ficheros_con_error)}) — NO cargados:")
            for fname, s in ficheros_con_error.items():
                self.logger.warning(f"  ✗ {fname}: {s['error']}")

        # Mostrar ficheros con sanidad fallida si los hay
        ficheros_sanidad_fallida = {f: s for f, s in file_stats.items() if s.get('sanidad_fallida')}
        if ficheros_sanidad_fallida:
            self.logger.error(f"")
            self.logger.error(f"🚨 SANIDAD FALLIDA ({len(ficheros_sanidad_fallida)}) — NO cargados:")
            for fname, s in ficheros_sanidad_fallida.items():
                self.logger.error(f"  🚨 {fname}: nuevos ({s['nuevos']}) > total ({s['total_original']})")

        # Guardar stats por fichero en el logger para luego mostrarlas
        self.logger.add_stat('file_stats', file_stats)

        # Post-procesamiento: merchants recurrentes
        if classify and all_records:
            from classifier.recurrent_merchants import apply_recurrent_merchants
            all_records = apply_recurrent_merchants(all_records, threshold=15)

        return all_records

    def export_to_csv(self, records: List[Dict], output_path: str):
        """
        Export records to CSV.

        Args:
            records: List of transaction records
            output_path: Path to output CSV file
        """
        if not records:
            self.logger.warning("No hay transacciones para exportar a CSV")
            return

        # Campos principales + campos opcionales (source_file debe estar incluido)
        fieldnames = ['fecha', 'importe', 'descripcion', 'concepto', 'banco', 'cuenta',
                      'cat1', 'cat2', 'cat3', 'tipo', 'capa', 'hash', 'source_file', 'line_num',
                      'balance', 'fecha_valor', 'moneda', 'tipo_operacion']

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(records)

        self.logger.info(f"Exportado CSV: {output_path}")

    def export_to_json(self, records: List[Dict], output_path: str):
        """
        Export records to JSON.

        Args:
            records: List of transaction records
            output_path: Path to output JSON file
        """
        if not records:
            self.logger.warning("No hay transacciones para exportar a JSON")
            return

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Exportado JSON: {output_path}")

    def get_statistics(self, records: List[Dict]) -> Dict:
        """
        Get statistics about processed transactions.

        Args:
            records: List of transaction records

        Returns:
            Dictionary with statistics
        """
        if not records:
            return {}

        stats = {
            'total': len(records),
            'by_bank': {},
            'by_cat1': {},
            'by_tipo': {},
            'by_capa': {},
            'total_ingreso': 0.0,
            'total_gasto': 0.0,
            'date_range': {
                'min': min(r['fecha'] for r in records),
                'max': max(r['fecha'] for r in records),
            }
        }

        for r in records:
            # Por banco
            banco = r['banco']
            stats['by_bank'][banco] = stats['by_bank'].get(banco, 0) + 1

            # Por categoría
            cat1 = r.get('cat1', 'SIN_CLASIFICAR')
            stats['by_cat1'][cat1] = stats['by_cat1'].get(cat1, 0) + 1

            # Por tipo
            tipo = r.get('tipo', 'DESCONOCIDO')
            stats['by_tipo'][tipo] = stats['by_tipo'].get(tipo, 0) + 1

            # Por capa
            capa = r.get('capa', 0)
            stats['by_capa'][f'Capa {capa}'] = stats['by_capa'].get(f'Capa {capa}', 0) + 1

            # Totales
            importe = r['importe']
            if importe > 0:
                stats['total_ingreso'] += importe
            else:
                stats['total_gasto'] += abs(importe)

        return stats

    def print_statistics(self, records: List[Dict]):
        """
        Print statistics about processed transactions.

        Args:
            records: List of transaction records
        """
        stats = self.get_statistics(records)

        if not stats:
            self.logger.warning("No hay estadísticas para mostrar")
            return

        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("ESTADÍSTICAS DE TRANSACCIONES NUEVAS")
        self.logger.info("=" * 80)

        self.logger.info(f"📅 Periodo: {stats['date_range']['min']} → {stats['date_range']['max']}")
        self.logger.info(f"📝 Total nuevas transacciones: {stats['total']:,}")

        self.logger.info(f"💰 Totales:")
        self.logger.info(f"  Ingresos: +€{stats['total_ingreso']:,.2f}")
        self.logger.info(f"  Gastos:   -€{stats['total_gasto']:,.2f}")
        self.logger.info(f"  Balance:   €{stats['total_ingreso'] - stats['total_gasto']:,.2f}")

        sin_clasificar = stats['by_cat1'].get('SIN_CLASIFICAR', 0)
        if sin_clasificar > 0:
            pct = 100 * sin_clasificar / stats['total']
            self.logger.warning(f"⚠️  {sin_clasificar} transacciones sin clasificar ({pct:.1f}%)")
        else:
            self.logger.info(f"✅ Todas las nuevas transacciones clasificadas correctamente")

        self.logger.info("=" * 80)


def main():
    """Ejemplo de uso del pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description='Procesar CSVs bancarios')
    parser.add_argument('input_dir', help='Directorio con CSVs bancarios')
    parser.add_argument('--master-csv', required=True, help='CSV maestro para exact match')
    parser.add_argument('--output-csv', help='Archivo CSV de salida')
    parser.add_argument('--output-json', help='Archivo JSON de salida')
    parser.add_argument('--no-classify', action='store_true', help='No clasificar (solo parsear)')

    args = parser.parse_args()

    # Inicializar pipeline
    pipeline = TransactionPipeline(master_csv_path=args.master_csv)

    # Procesar directorio
    records = pipeline.process_directory(args.input_dir, classify=not args.no_classify)

    # Exportar
    if args.output_csv:
        pipeline.export_to_csv(records, args.output_csv)

    if args.output_json:
        pipeline.export_to_json(records, args.output_json)

    # Mostrar estadísticas
    pipeline.print_statistics(records)


if __name__ == '__main__':
    main()
