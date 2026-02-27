#!/usr/bin/env python3
"""
Script principal para procesar transacciones bancarias.

DOCUMENTACIÓN DE USO:

Ejecución básica (procesa input/, exporta Excel automático):
    python3 process_transactions.py

Especificar directorio de entrada:
    python3 process_transactions.py --input-dir mi_carpeta/

Procesar un solo archivo:
    python3 process_transactions.py --file input/openbank_ES2200.csv

Exportar a CSV/JSON adicionales (el Excel siempre se genera):
    python3 process_transactions.py --output output/mi_salida.csv --output-json output/data.json

Sin clasificar (solo parsear):
    python3 process_transactions.py --no-classify

Usar maestro CSV distinto:
    python3 process_transactions.py --master-csv validate/mi_maestro.csv

Sin estadísticas:
    python3 process_transactions.py --no-stats

Combinaciones útiles:
    # Full output: Excel + CSV + JSON + Logs
    python3 process_transactions.py --output output/tx.csv --output-json output/tx.json

    # Procesar y limpiar archivos antiguos
    python3 process_transactions.py --cleanup

    # Debug mode con logs detallados
    python3 process_transactions.py --debug

OUTPUT:
    - Excel: output/transacciones_YYYYMMDD_HHMMSS.xlsx (automático siempre)
    - Logs: logs/finsense_YYYYMMDD_HHMMSS.log (automático siempre)
    - CSV/JSON: solo si se especifican flags
    - Log en pantalla: resumen de ejecución

IMPORTANTE:
    - El directorio 'logs/' se crea automáticamente
    - Los archivos con >30 días se borran automáticamente
    - Todos los mensajes se loguean simultáneamente en pantalla y fichero
"""
import argparse
import sys
import os
from pathlib import Path
import sqlite3

from pipeline import TransactionPipeline
from src.logger import get_logger
from src.exporter import ExcelExporter, cleanup_old_exports


def create_db_tables(db_path: str = 'finsense.db'):
    """Crear tablas en la BD si no existen."""
    logger = get_logger()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                importe REAL NOT NULL,
                descripcion TEXT NOT NULL,
                banco TEXT NOT NULL,
                cuenta TEXT,
                tipo TEXT,
                cat1 TEXT,
                cat2 TEXT,
                hash TEXT UNIQUE NOT NULL,
                source_file TEXT,
                merchant_name TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS presupuestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cat1 TEXT NOT NULL,
                cat2 TEXT,
                importe_mensual REAL NOT NULL,
                activo INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cargos_extraordinarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mes INTEGER NOT NULL,
                dia INTEGER,
                descripcion TEXT NOT NULL,
                importe_estimado REAL,
                dias_aviso INTEGER DEFAULT 10,
                activo INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS merchants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_name TEXT UNIQUE,
                place_id TEXT,
                place_name TEXT,
                address TEXT,
                city TEXT,
                country TEXT,
                lat REAL,
                lng REAL,
                cat1 TEXT,
                cat2 TEXT,
                google_type TEXT,
                confidence REAL,
                search_scope TEXT
            )
        ''')
        
        # Crear índices para merchants si no existen
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_merchant_name ON merchants(merchant_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_city ON merchants(city)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_country ON merchants(country)')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fondo_caprichos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anio INTEGER NOT NULL,
                mes INTEGER NOT NULL,
                cat1 TEXT NOT NULL,
                presupuesto REAL NOT NULL,
                gasto_real REAL NOT NULL,
                diferencia REAL NOT NULL,
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(anio, mes, cat1)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_estado (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        ''')
        
        conn.commit()
        logger.debug("Tablas de BD creadas/verificadas")
        conn.close()
    except Exception as e:
        logger.error(f"Error creando tablas: {e}")
        raise


def load_known_hashes(db_path: str = 'finsense.db') -> dict:
    """
    Cargar hashes conocidos desde la BD para deduplicación.
    
    Formato compatible con pipeline.py:
    {cuenta: {hash: {source_file: count}}}
    
    Ejemplo:
    {
        'ES3600730100550435513660': {
            'abc123hash': {'bd': 2},  # Este hash aparece 2 veces en la BD
            'def456hash': {'bd': 1}   # Este hash aparece 1 vez en la BD
        }
    }
    
    Returns:
        Dict con estructura anidada para compatible con pipeline
    """
    logger = get_logger()
    known_hashes = {}
    
    if not os.path.exists(db_path):
        logger.debug(f"BD no existe todavía: {db_path}")
        return known_hashes
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Contar cuántas veces aparece cada hash por cuenta
        cursor.execute('''
            SELECT cuenta, hash, COUNT(*) as hash_count
            FROM transacciones
            GROUP BY cuenta, hash
        ''')
        rows = cursor.fetchall()
        
        for cuenta, hash_val, hash_count in rows:
            if cuenta not in known_hashes:
                known_hashes[cuenta] = {}
            # Formato esperado por pipeline: {hash: {source_file: count}}
            # Como proviene de BD, usamos 'bd' como source_file
            known_hashes[cuenta][hash_val] = {'bd': hash_count}
        
        total_hashes = sum(len(h) for h in known_hashes.values())
        logger.debug(f"Cargados {total_hashes} hashes únicos de BD ({len(known_hashes)} cuentas)")
        
        conn.close()
    except Exception as e:
        logger.error(f"Error cargando hashes de BD: {e}")
    
    return known_hashes


def insert_new_transactions(db_path: str, records: list):
    """
    Insertar transacciones nuevas en la BD.
    
    Args:
        db_path: Path a finsense.db
        records: List de dicts con transacciones
    """
    logger = get_logger()
    
    if not records:
        logger.info("No hay transacciones nuevas para insertar")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        inserted = 0
        for r in records:
            # Incluir source_file y merchant_name en la inserción
            source_file = r.get('source_file', None)
            merchant_name = r.get('merchant_name', None)
            
            cursor.execute('''
                INSERT INTO transacciones 
                (fecha, importe, descripcion, banco, cuenta, tipo, cat1, cat2, hash, source_file, merchant_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                r['fecha'], r['importe'], r['descripcion'], r['banco'],
                r['cuenta'], r['tipo'], r['cat1'], r['cat2'], r['hash'], source_file, merchant_name
            ))
            inserted += 1
        
        conn.commit()
        logger.add_stat('nuevas_insertadas', inserted)
        logger.info(f"Insertadas {inserted} nuevas transacciones en BD")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error insertando transacciones: {e}")
    finally:
        conn.close()


def enrich_new_merchants(db_path: str = 'finsense.db'):
    """
    Enriquece merchants no registrados que aparecen en las nuevas transacciones.
    
    Busca merchants en transacciones que NO están en la tabla merchants,
    los inserta, y opcionalmente los enriquece con Google Places (background).
    
    Args:
        db_path: Path a finsense.db
    """
    logger = get_logger()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener merchants únicos en transacciones que no están registrados
        cursor.execute("""
            SELECT DISTINCT merchant_name 
            FROM transacciones 
            WHERE merchant_name IS NOT NULL 
            AND merchant_name NOT IN (SELECT merchant_name FROM merchants WHERE merchant_name IS NOT NULL)
            ORDER BY merchant_name
        """)
        
        unregistered = [row[0] for row in cursor.fetchall()]
        
        if not unregistered:
            logger.debug("No hay merchants nuevos para registrar")
            conn.close()
            return
        
        # Insertar merchants no registrados en tabla merchants
        logger.info(f"Registrando {len(unregistered)} merchants nuevos...")
        for merchant_name in unregistered:
            cursor.execute("""
                INSERT OR IGNORE INTO merchants 
                (merchant_name, place_name, cat1, cat2)
                VALUES (?, ?, NULL, NULL)
            """, (merchant_name, merchant_name))
        
        conn.commit()
        logger.info(f"✓ {len(unregistered)} merchants registrados (enriquecimiento pendiente)")
        logger.add_stat('merchants_nuevos_registrados', len(unregistered))
        
        conn.close()
        
        # Nota: El enriquecimiento con Google Places se hace en background (enrich_background.py)
        # para no bloquear el procesamiento de transacciones
        
    except Exception as e:
        logger.warning(f"Error enriqueciendo merchants nuevos: {e}")


def get_total_in_db(db_path: str = 'finsense.db') -> int:
    """Contar total de transacciones en BD."""
    if not os.path.exists(db_path):
        return 0
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM transacciones')
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except:
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='Procesar CSVs bancarios y clasificar transacciones',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--input-dir',
        default='input',
        help='Directorio con CSVs bancarios (default: input)'
    )

    parser.add_argument(
        '--master-csv',
        default='validate/Validacion_Categorias_Finsense_MASTER_v9.csv',
        help='CSV maestro para exact match'
    )

    parser.add_argument(
        '--db',
        default='finsense.db',
        help='Path a BD SQLite (default: finsense.db)'
    )

    parser.add_argument(
        '--file',
        help='Procesar solo este archivo'
    )

    parser.add_argument(
        '--output',
        '-o',
        help='Exportar resultados a CSV'
    )

    parser.add_argument(
        '--output-json',
        help='Exportar resultados a JSON'
    )

    parser.add_argument(
        '--output-dir',
        default='output',
        help='Directorio de salida para Excel (default: output)'
    )

    parser.add_argument(
        '--no-classify',
        action='store_true',
        help='Solo parsear, sin clasificar'
    )

    parser.add_argument(
        '--no-stats',
        action='store_true',
        help='No mostrar estadísticas'
    )

    parser.add_argument(
        '--no-db-insert',
        action='store_true',
        help='No insertar en BD (solo procesar)'
    )

    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Limpiar archivos con >30 días'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Modo debug (logs detallados)'
    )

    parser.add_argument(
        '--reset-db',
        action='store_true',
        help='Borrar todas las transacciones de BD y reimportar desde cero (requiere todos los CSVs en input/)'
    )

    args = parser.parse_args()
    
    # Inicializar logger
    logger = get_logger()
    
    if args.debug:
        logger.logger.setLevel(__import__('logging').DEBUG)

    logger.info(f"Directorio entrada: {args.input_dir}")
    logger.info(f"Maestro CSV: {args.master_csv}")
    logger.info(f"BD: {args.db}")
    logger.info("")
    
    # Crear tablas si no existen
    create_db_tables(args.db)

    # Validar master CSV
    if not os.path.exists(args.master_csv):
        logger.error(f"No se encuentra maestro CSV: {args.master_csv}")
        sys.exit(1)

    # Manejar --reset-db
    if args.reset_db:
        # Validar que se usa modo directorio, no --file
        if args.file:
            logger.error("No se puede usar --reset-db con --file. Usa --reset-db sin --file para reimportar todo.")
            sys.exit(1)
        
        # Validar que existe el directorio input/
        if not os.path.exists(args.input_dir):
            logger.error(f"No se encuentra directorio: {args.input_dir}")
            sys.exit(1)
        
        # Contar CSVs/PDFs en directorio
        all_files = [f for f in os.listdir(args.input_dir) if f.endswith(('.csv', '.pdf'))]
        if not all_files:
            logger.error(f"No hay CSVs ni PDFs en {args.input_dir}")
            sys.exit(1)
        
        logger.warning("=" * 70)
        logger.warning(f"⚠️  RESET-DB: Se borrarán TODAS las transacciones de {args.db}")
        logger.warning(f"⚠️  Se reimportarán {len(all_files)} ficheros de {args.input_dir}")
        logger.warning(f"⚠️  Las reglas del clasificador son permanentes y no se borran")
        logger.warning("=" * 70)
        logger.info("")
        
        # Borrar todas las transacciones (sin tocar el esquema)
        try:
            conn = sqlite3.connect(args.db)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM transacciones')
            conn.commit()
            conn.close()
            logger.warning(f"✓ Borradas todas las transacciones de {args.db}")
        except Exception as e:
            logger.error(f"Error borrando transacciones: {e}")
            sys.exit(1)
        
        logger.info("")

    # Limpiar archivos antiguos si se pide
    if args.cleanup:
        logger.info("Limpiando archivos con >30 días...")
        cleanup_old_exports(days=30, output_dir=args.output_dir)
        logger.info("Limpieza completada")

    # Cargar hashes conocidos desde BD
    logger.info("Cargando estado de BD...")
    known_hashes = load_known_hashes(args.db)
    total_bd_antes = get_total_in_db(args.db)
    logger.info(f"Total en BD antes: {total_bd_antes}")
    logger.set_stat('total_bd', total_bd_antes)

    # Inicializar pipeline
    logger.info("Inicializando pipeline...")
    pipeline = TransactionPipeline(
        master_csv_path=args.master_csv,
        known_hashes=known_hashes,
        db_path=args.db
    )

    # Procesar
    logger.info("")
    records = []
    
    try:
        if args.file:
            # Procesar un solo archivo
            if not os.path.exists(args.file):
                logger.error(f"No se encuentra archivo: {args.file}")
                sys.exit(1)

            logger.info(f"Procesando archivo: {args.file}")
            records, file_stats = pipeline.process_file(args.file, classify=not args.no_classify)
            
            # Guardar stats de este fichero en el logger
            filename = os.path.basename(args.file)
            logger.add_stat('file_stats', {filename: file_stats})
            
            logger.add_stat('csvs_procesados', 1)

        else:
            # Procesar directorio
            if not os.path.exists(args.input_dir):
                logger.error(f"No se encuentra directorio: {args.input_dir}")
                sys.exit(1)

            logger.info(f"Procesando directorio: {args.input_dir}")
            records = pipeline.process_directory(args.input_dir, classify=not args.no_classify)

    except Exception as e:
        logger.error(f"Error durante procesamiento: {e}")
        sys.exit(1)

    logger.info("")

    # Insertar en BD
    if records and not args.no_db_insert:
        logger.info("Insertando transacciones en BD...")
        insert_new_transactions(args.db, records)
        
        # Registrar merchants nuevos
        enrich_new_merchants(args.db)
        
        total_bd_despues = get_total_in_db(args.db)
        logger.set_stat('total_bd', total_bd_despues)
        logger.info(f"Total en BD después: {total_bd_despues}")

    logger.info("")

    # Exportar Excel (automático siempre)
    if records or True:  # Exportar incluso si no hay nuevas
        try:
            logger.info("Exportando a Excel...")
            exporter = ExcelExporter(args.db)
            excel_file = exporter.export_to_excel(args.output_dir)
            logger.info(f"✓ Excel generado: {excel_file}")
        except Exception as e:
            logger.error(f"Error exportando Excel: {e}")

    # Exportar CSV (si se especifica)
    if args.output:
        if records:
            pipeline.export_to_csv(records, args.output)
        else:
            logger.warning("No hay transacciones nuevas para exportar a CSV")

    # Exportar JSON (si se especifica)
    if args.output_json:
        if records:
            pipeline.export_to_json(records, args.output_json)
        else:
            logger.warning("No hay transacciones nuevas para exportar a JSON")

    # Estadísticas
    if not args.no_stats and records:
        pipeline.print_statistics(records)

    # Mostrar resumen final
    logger.print_summary()


if __name__ == '__main__':
    main()
