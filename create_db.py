#!/usr/bin/env python3
"""
Crea la base de datos SQLite y carga las transacciones desde CSV.
"""
import sqlite3
import csv
import sys


def create_database(db_path='finsense.db'):
    """Crea la base de datos y la tabla de transacciones."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Eliminar tabla si existe (para recarga limpia)
    cursor.execute('DROP TABLE IF EXISTS transacciones')

    # Crear tabla
    cursor.execute('''
        CREATE TABLE transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            importe REAL NOT NULL,
            descripcion TEXT,
            banco TEXT,
            cuenta TEXT,
            tipo TEXT,          -- GASTO, INGRESO, TRANSFERENCIA, INVERSION
            cat1 TEXT,
            cat2 TEXT,
            hash TEXT,
            par_id TEXT,         -- NULL si no emparejada
            par_tipo TEXT,       -- emparejada_HIGH/MEDIUM/LOW, interna_sin_pareja, etc.
            source_file TEXT
        )
    ''')

    # Crear índices
    cursor.execute('CREATE INDEX idx_fecha ON transacciones(fecha)')
    cursor.execute('CREATE INDEX idx_tipo ON transacciones(tipo)')
    cursor.execute('CREATE INDEX idx_cat1 ON transacciones(cat1)')
    cursor.execute('CREATE INDEX idx_cat2 ON transacciones(cat2)')
    cursor.execute('CREATE INDEX idx_banco ON transacciones(banco)')
    cursor.execute("CREATE INDEX idx_year_month ON transacciones(strftime('%Y-%m', fecha))")

    conn.commit()
    return conn


def load_transactions(conn, csv_path='output/transacciones_con_pares.csv'):
    """Carga transacciones desde CSV a SQLite."""
    cursor = conn.cursor()

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0

        for row in reader:
            # Extraer campos
            fecha = row.get('fecha')
            importe = float(row.get('importe', 0))
            descripcion = row.get('descripcion', '')
            banco = row.get('banco', '')
            cuenta = row.get('cuenta', '')
            tipo = row.get('tipo', '')
            cat1 = row.get('cat1', '')
            cat2 = row.get('cat2', '')
            hash_val = row.get('hash', '')
            par_id = row.get('par_id', '') or None  # NULL si vacío
            par_tipo = row.get('par_tipo', '') or None
            source_file = row.get('source_file', '')

            cursor.execute('''
                INSERT INTO transacciones
                (fecha, importe, descripcion, banco, cuenta, tipo, cat1, cat2,
                 hash, par_id, par_tipo, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (fecha, importe, descripcion, banco, cuenta, tipo, cat1, cat2,
                  hash_val, par_id, par_tipo, source_file))

            count += 1

            if count % 1000 == 0:
                print(f"  Cargadas {count:,} transacciones...", end='\r')

    conn.commit()
    print(f"\n✅ {count:,} transacciones cargadas en la base de datos")
    return count


def verify_database(conn):
    """Verifica que la base de datos tiene datos coherentes."""
    cursor = conn.cursor()

    print("\n📊 Verificación de la base de datos:")

    # Total transacciones
    cursor.execute('SELECT COUNT(*) FROM transacciones')
    total = cursor.fetchone()[0]
    print(f"   Total transacciones: {total:,}")

    # Por tipo
    cursor.execute('''
        SELECT tipo, COUNT(*) as count, SUM(importe) as total
        FROM transacciones
        GROUP BY tipo
        ORDER BY count DESC
    ''')
    print("\n   Por tipo:")
    for row in cursor.fetchall():
        tipo, count, total_importe = row
        print(f"     {tipo:20s}: {count:6,} tx | €{total_importe:15,.2f}")

    # Por Cat1
    cursor.execute('''
        SELECT cat1, COUNT(*) as count
        FROM transacciones
        WHERE cat1 != ''
        GROUP BY cat1
        ORDER BY count DESC
        LIMIT 10
    ''')
    print("\n   Top 10 Cat1:")
    for row in cursor.fetchall():
        cat1, count = row
        print(f"     {cat1:20s}: {count:6,}")

    # Rango de fechas
    cursor.execute('SELECT MIN(fecha), MAX(fecha) FROM transacciones')
    min_fecha, max_fecha = cursor.fetchone()
    print(f"\n   Rango de fechas: {min_fecha} → {max_fecha}")

    # Transacciones emparejadas
    cursor.execute('''
        SELECT par_tipo, COUNT(*) as count
        FROM transacciones
        WHERE par_tipo IS NOT NULL
        GROUP BY par_tipo
    ''')
    print("\n   Transacciones con pares:")
    for row in cursor.fetchall():
        par_tipo, count = row
        print(f"     {par_tipo:30s}: {count:6,}")


def main():
    print("=" * 60)
    print("   CREACIÓN DE BASE DE DATOS FINSENSE")
    print("=" * 60)
    print()

    # Crear base de datos
    print("📦 Creando base de datos SQLite...")
    conn = create_database('finsense.db')
    print("✅ Base de datos creada: finsense.db")

    # Cargar transacciones
    print("\n📂 Cargando transacciones desde CSV...")
    count = load_transactions(conn, 'output/transacciones_con_pares.csv')

    # Verificar
    verify_database(conn)

    conn.close()

    print("\n" + "=" * 60)
    print("✅ BASE DE DATOS CREADA Y VERIFICADA")
    print("=" * 60)


if __name__ == '__main__':
    main()
