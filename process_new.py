#!/usr/bin/env python3
"""
Script para procesar ficheros nuevos bancarios con revisión previa.

Este script procesa ficheros nuevos (CSV, XLS, PDF) de varios bancos,
muestra las transacciones detectadas para revisión del usuario, y luego
las inserta en la base de datos finsense.db.

Uso:
    python3 process_new.py input/new/
    python3 process_new.py input/new/ --dry-run
    python3 process_new.py input/new/ --auto-approve
"""
import argparse
import sys
import os
import sqlite3
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from pipeline import TransactionPipeline
from src.query_engine import QueryEngine


def load_existing_hashes(db_path: str = 'finsense.db') -> Dict[str, set]:
    """
    Carga los hashes existentes de la base de datos para deduplicación.

    Args:
        db_path: Ruta a la base de datos

    Returns:
        Dict de cuenta -> set de hashes
    """
    if not os.path.exists(db_path):
        print(f"⚠️  Base de datos {db_path} no existe. Se creará al insertar transacciones.")
        return {}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT cuenta, hash FROM transacciones WHERE hash IS NOT NULL')
    rows = cursor.fetchall()
    conn.close()

    hashes_by_account = {}
    for cuenta, hash_val in rows:
        if cuenta not in hashes_by_account:
            hashes_by_account[cuenta] = {}
        hashes_by_account[cuenta][hash_val] = 'existing'  # Value doesn't matter, just track hash

    return hashes_by_account


def insert_transactions(transactions: List[Dict], db_path: str = 'finsense.db'):
    """
    Inserta transacciones en la base de datos.

    Args:
        transactions: Lista de transacciones a insertar
        db_path: Ruta a la base de datos
    """
    if not transactions:
        print("No hay transacciones para insertar.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Preparar datos para inserción
    inserted = 0
    duplicated = 0

    for trans in transactions:
        try:
            # Generar hash para deduplicación
            import hashlib
            hash_input = f"{trans['fecha']}|{trans.get('concepto', '')}|{trans['importe']:.2f}|{trans['cuenta']}"
            trans_hash = hashlib.md5(hash_input.encode()).hexdigest()

            # Verificar si ya existe
            cursor.execute('SELECT id FROM transacciones WHERE hash = ?', (trans_hash,))
            if cursor.fetchone():
                duplicated += 1
                continue

            # Insertar
            cursor.execute('''
                INSERT INTO transacciones (
                    fecha, descripcion, importe, tipo, cat1, cat2,
                    banco, cuenta, hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trans['fecha'],
                trans.get('descripcion', trans.get('concepto', '')),
                trans['importe'],
                trans.get('tipo', 'GASTO'),
                trans.get('cat1', 'SIN_CLASIFICAR'),
                trans.get('cat2', ''),
                trans.get('banco', ''),
                trans['cuenta'],
                trans_hash
            ))
            inserted += 1

        except Exception as e:
            print(f"⚠️  Error insertando transacción {trans.get('fecha')} {trans.get('concepto', '')[:30]}: {e}")

    conn.commit()
    conn.close()

    print(f"\n✅ Insertadas: {inserted} transacciones")
    if duplicated > 0:
        print(f"⏭️  Duplicadas (omitidas): {duplicated} transacciones")


def print_transaction_summary(transactions: List[Dict]):
    """
    Muestra un resumen de las transacciones procesadas.

    Args:
        transactions: Lista de transacciones
    """
    if not transactions:
        print("\n📭 No hay transacciones nuevas.")
        return

    print(f"\n{'='*80}")
    print(f"RESUMEN DE TRANSACCIONES PROCESADAS")
    print(f"{'='*80}\n")

    # Agrupar por banco
    by_bank = {}
    for t in transactions:
        banco = t.get('banco', 'Desconocido')
        if banco not in by_bank:
            by_bank[banco] = []
        by_bank[banco].append(t)

    for banco, trans in sorted(by_bank.items()):
        print(f"\n📊 {banco}: {len(trans)} transacciones")

        # Rango de fechas
        fechas = sorted([t['fecha'] for t in trans if t.get('fecha')])
        if fechas:
            print(f"   Periodo: {fechas[0]} a {fechas[-1]}")

        # Totales
        ingresos = sum(t['importe'] for t in trans if t['importe'] > 0)
        gastos = sum(t['importe'] for t in trans if t['importe'] < 0)
        print(f"   Ingresos: +€{ingresos:,.2f}")
        print(f"   Gastos:   €{gastos:,.2f}")
        print(f"   Neto:     €{ingresos + gastos:,.2f}")

        # Clasificación
        sin_clasificar = sum(1 for t in trans if t.get('cat1') == 'SIN_CLASIFICAR')
        if sin_clasificar > 0:
            pct = 100 * sin_clasificar / len(trans)
            print(f"   ⚠️  Sin clasificar: {sin_clasificar} ({pct:.1f}%)")
        else:
            print(f"   ✅ Todas clasificadas")

    # Resumen global
    print(f"\n{'='*80}")
    print(f"TOTAL: {len(transactions)} transacciones")
    total_ingresos = sum(t['importe'] for t in transactions if t['importe'] > 0)
    total_gastos = sum(t['importe'] for t in transactions if t['importe'] < 0)
    print(f"Ingresos: +€{total_ingresos:,.2f}")
    print(f"Gastos:   €{total_gastos:,.2f}")
    print(f"Neto:     €{total_ingresos + total_gastos:,.2f}")

    sin_clasificar_total = sum(1 for t in transactions if t.get('cat1') == 'SIN_CLASIFICAR')
    if sin_clasificar_total > 0:
        pct = 100 * sin_clasificar_total / len(transactions)
        print(f"\n⚠️  ATENCIÓN: {sin_clasificar_total} transacciones sin clasificar ({pct:.1f}%)")
    else:
        print(f"\n✅ Todas las transacciones clasificadas correctamente")

    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Procesar ficheros bancarios nuevos (CSV, XLS, PDF) con revisión',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Procesar todos los archivos en input/new/
  %(prog)s input/new/

  # Modo dry-run (solo mostrar, no insertar)
  %(prog)s input/new/ --dry-run

  # Auto-aprobar (sin confirmación)
  %(prog)s input/new/ --auto-approve

  # Procesar un archivo específico
  %(prog)s input/new/abanca_ES5120800823473040166463_EUR_20260213-180352.csv
        """
    )

    parser.add_argument(
        'path',
        help='Directorio con ficheros nuevos o archivo específico'
    )

    parser.add_argument(
        '--master-csv',
        default='Validación_Categorias_Finsense_04020206_5.csv',
        help='CSV maestro para clasificación (default: Validación_Categorias_Finsense_04020206_5.csv)'
    )

    parser.add_argument(
        '--db',
        default='finsense.db',
        help='Ruta a la base de datos (default: finsense.db)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Solo mostrar transacciones, no insertar en DB'
    )

    parser.add_argument(
        '--auto-approve',
        action='store_true',
        help='No pedir confirmación antes de insertar'
    )

    parser.add_argument(
        '--output',
        '-o',
        help='Exportar resultados a CSV antes de insertar'
    )

    args = parser.parse_args()

    # Validar path
    if not os.path.exists(args.path):
        print(f"❌ ERROR: No se encuentra: {args.path}")
        sys.exit(1)

    # Validar master CSV
    if not os.path.exists(args.master_csv):
        print(f"❌ ERROR: No se encuentra el master CSV: {args.master_csv}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("🆕 PROCESAMIENTO DE FICHEROS NUEVOS")
    print("=" * 80)
    print()

    # Cargar hashes existentes para deduplicación
    print("📦 Cargando transacciones existentes para deduplicación...")
    known_hashes = load_existing_hashes(args.db)
    total_known = sum(len(hashes) for hashes in known_hashes.values())
    print(f"   ✓ {total_known} transacciones conocidas en {len(known_hashes)} cuentas\n")

    # Inicializar pipeline
    pipeline = TransactionPipeline(
        master_csv_path=args.master_csv,
        known_hashes=known_hashes
    )

    # Procesar
    all_transactions = []

    if os.path.isfile(args.path):
        # Procesar un solo archivo
        print(f"📄 Procesando archivo: {args.path}\n")
        transactions = pipeline.process_file(args.path, classify=True)
        all_transactions.extend(transactions)
    else:
        # Procesar directorio
        print(f"📁 Procesando directorio: {args.path}\n")

        # Buscar todos los archivos relevantes
        path_obj = Path(args.path)
        files = (
            list(path_obj.glob('*.csv')) +
            list(path_obj.glob('*.xls')) +
            list(path_obj.glob('*.xlsx')) +
            list(path_obj.glob('*.pdf'))
        )

        if not files:
            print(f"❌ No se encontraron archivos CSV/XLS/PDF en {args.path}")
            sys.exit(1)

        print(f"Encontrados {len(files)} archivos:\n")
        for f in files:
            print(f"  • {f.name}")
        print()

        for file_path in sorted(files):
            try:
                print(f"{'─'*80}")
                print(f"Procesando: {file_path.name}")
                print(f"{'─'*80}")

                transactions = pipeline.process_file(str(file_path), classify=True)
                all_transactions.extend(transactions)

                print(f"✓ {len(transactions)} transacciones nuevas de {file_path.name}\n")

            except Exception as e:
                print(f"❌ Error procesando {file_path.name}: {e}\n")
                import traceback
                traceback.print_exc()

    # Mostrar resumen
    print_transaction_summary(all_transactions)

    # Exportar si se solicita
    if args.output and all_transactions:
        pipeline.export_to_csv(all_transactions, args.output)

    # Insertar en DB
    if all_transactions:
        if args.dry_run:
            print("🔍 Modo DRY-RUN activado: no se insertarán transacciones en la base de datos.")
        else:
            if not args.auto_approve:
                print("\n" + "="*80)
                respuesta = input(f"¿Insertar {len(all_transactions)} transacciones en {args.db}? (s/N): ").strip().lower()
                if respuesta not in ('s', 'si', 'sí', 'yes', 'y'):
                    print("❌ Cancelado por el usuario.")
                    sys.exit(0)

            print(f"\n💾 Insertando transacciones en {args.db}...")
            insert_transactions(all_transactions, args.db)

            print(f"\n✅ ¡Proceso completado!\n")
    else:
        print("📭 No hay transacciones nuevas para procesar.\n")


if __name__ == '__main__':
    main()
