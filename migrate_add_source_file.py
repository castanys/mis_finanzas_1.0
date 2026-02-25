#!/usr/bin/env python3
"""
Script de migración para añadir columna 'source_file' a la tabla transacciones.

Uso:
    python3 migrate_add_source_file.py

El script:
1. Verifica si la columna ya existe
2. Si no existe, la añade
3. Los registros existentes quedarán con source_file = NULL
4. Después de reimportar ficheros, los nuevos registros tendrán source_file rellenado
"""
import sqlite3
import sys
from pathlib import Path

def migrate():
    """Ejecutar migración de esquema."""
    db_path = 'finsense.db'
    
    if not Path(db_path).exists():
        print(f"❌ No se encuentra la BD: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(transacciones)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'source_file' in columns:
            print("✓ La columna 'source_file' ya existe en la tabla 'transacciones'")
            conn.close()
            return True
        
        # Añadir la columna
        print("🔄 Añadiendo columna 'source_file' a la tabla 'transacciones'...")
        cursor.execute("ALTER TABLE transacciones ADD COLUMN source_file TEXT")
        conn.commit()
        
        print("✓ Columna 'source_file' añadida exitosamente")
        
        # Verificar
        cursor.execute("PRAGMA table_info(transacciones)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'source_file' in columns:
            print("✓ Verificación: columna 'source_file' está presente en la tabla")
            conn.close()
            return True
        else:
            print("❌ Verificación fallida: columna no encontrada después de migración")
            conn.close()
            return False
    
    except Exception as e:
        print(f"❌ Error durante migración: {e}")
        conn.rollback()
        conn.close()
        return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
