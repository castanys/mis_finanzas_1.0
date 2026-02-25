#!/usr/bin/env python3
"""
Reconstruye la BBDD desde cero procesando TODOS los ficheros.
"""
import sqlite3
import os
from pipeline import TransactionPipeline
# from internal_transfer_hunter import detect_internal_transfers

def main():
    print("=" * 80)
    print("🔨 RECONSTRUCCIÓN COMPLETA DESDE CERO")
    print("=" * 80)

    # 1. Inicializar pipeline
    print("\n1️⃣  Inicializando pipeline...")
    pipeline = TransactionPipeline('Validación_Categorias_Finsense_04020206_5.csv')

    # 2. Procesar ficheros históricos (input/)
    print("\n2️⃣  Procesando ficheros históricos (input/)...")
    historical_records = []
    input_files = []

    # Recoger todos los ficheros del input/
    for filename in os.listdir('input'):
        if filename.endswith(('.csv', '.xls', '.xlsx', '.pdf')):
            filepath = os.path.join('input', filename)
            input_files.append(filepath)

    print(f"   Encontrados {len(input_files)} ficheros históricos")

    for filepath in sorted(input_files):
        filename = os.path.basename(filepath)
        try:
            records = pipeline.process_file(filepath, classify=True)
            historical_records.extend(records)
            print(f"   ✓ {filename:60s} {len(records):4d} transacciones")
        except Exception as e:
            print(f"   ✗ {filename:60s} ERROR: {e}")

    print(f"\n   Total histórico: {len(historical_records):,} transacciones")

    # 3. Procesar ficheros nuevos (input/new/)
    print("\n3️⃣  Procesando ficheros nuevos (input/new/)...")
    new_records = []
    new_files = []

    if os.path.exists('input/new'):
        for filename in os.listdir('input/new'):
            if filename.endswith(('.csv', '.xls', '.xlsx', '.pdf')):
                filepath = os.path.join('input/new', filename)
                new_files.append(filepath)

        print(f"   Encontrados {len(new_files)} ficheros nuevos")

        for filepath in sorted(new_files):
            filename = os.path.basename(filepath)
            try:
                records = pipeline.process_file(filepath, classify=True)
                new_records.extend(records)
                print(f"   ✓ {filename:60s} {len(records):4d} transacciones")
            except Exception as e:
                print(f"   ✗ {filename:60s} ERROR: {e}")

        print(f"\n   Total nuevo: {len(new_records):,} transacciones")

    # 4. Combinar todo
    all_records = historical_records + new_records
    print(f"\n4️⃣  Total combinado: {len(all_records):,} transacciones")

    # 5. Aplicar recurrent merchants
    print("\n5️⃣  Aplicando recurrent merchants...")
    from classifier.recurrent_merchants import apply_recurrent_merchants
    all_records = apply_recurrent_merchants(all_records, threshold=15)

    # 6. Detectar transferencias internas (emparejamiento)
    # print("\n6️⃣  Detectando transferencias internas...")
    # all_records = detect_internal_transfers(all_records)
    # NOTA: El emparejamiento se puede hacer después con internal_transfer_hunter.py

    # 7. Crear base de datos
    print("\n7️⃣  Creando base de datos finsense.db...")
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Crear tabla
    cursor.execute('DROP TABLE IF EXISTS transacciones')
    cursor.execute('''
        CREATE TABLE transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            importe REAL NOT NULL,
            descripcion TEXT,
            banco TEXT,
            cuenta TEXT,
            tipo TEXT,
            cat1 TEXT,
            cat2 TEXT,
            hash TEXT,
            par_id TEXT,
            par_tipo TEXT,
            source_file TEXT
        )
    ''')

    # Crear índices
    cursor.execute('CREATE INDEX idx_fecha ON transacciones(fecha)')
    cursor.execute('CREATE INDEX idx_tipo ON transacciones(tipo)')
    cursor.execute('CREATE INDEX idx_cat1 ON transacciones(cat1)')
    cursor.execute('CREATE INDEX idx_cat2 ON transacciones(cat2)')
    cursor.execute('CREATE INDEX idx_banco ON transacciones(banco)')

    # Insertar transacciones
    print("   Insertando transacciones...")
    for record in all_records:
        cursor.execute('''
            INSERT INTO transacciones
            (fecha, importe, descripcion, banco, cuenta, tipo, cat1, cat2,
             hash, par_id, par_tipo, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.get('fecha'),
            record.get('importe'),
            record.get('descripcion', ''),
            record.get('banco', ''),
            record.get('cuenta', ''),
            record.get('tipo', ''),
            record.get('cat1', ''),
            record.get('cat2', ''),
            record.get('hash', ''),
            record.get('par_id'),
            record.get('par_tipo'),
            record.get('source_file', '')
        ))

    conn.commit()
    conn.close()

    print(f"   ✅ {len(all_records):,} transacciones insertadas")

    # 8. Estadísticas
    print("\n" + "=" * 80)
    print("📊 ESTADÍSTICAS FINALES")
    print("=" * 80)

    pipeline.print_statistics(all_records)

    print("\n✅ RECONSTRUCCIÓN COMPLETADA")
    print("=" * 80)

if __name__ == '__main__':
    main()
