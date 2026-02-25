#!/usr/bin/env python3
"""
Script para generar un nuevo maestro CSV (v4) desde finsense.db
manteniendo la estructura del maestro v3, pero incluyendo TODAS las transacciones
actuales de la BD con sus categorías finales.
"""
import sqlite3
import csv
from datetime import datetime

DB_PATH = 'finsense.db'
OUTPUT_PATH = 'validate/Validacion_Categorias_Finsense_MASTER_v4.csv'

def generate_master():
    """Genera el maestro v4 desde finsense.db"""
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener todas las transacciones
    cursor.execute("""
        SELECT 
            fecha,
            importe,
            descripcion,
            banco,
            cuenta,
            tipo,
            cat1,
            cat2,
            hash,
            id
        FROM transacciones
        ORDER BY fecha ASC, id ASC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"📝 Leyendo {len(rows)} transacciones de finsense.db...")
    
    # Escribir CSV con estructura idéntica al maestro v3
    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        
        # Header
        writer.writerow(['Fecha', 'Importe', 'Descripción', 'Banco', 'Cuenta', 'Tipo', 'Cat1', 'Cat2', 'Hash', 'id'])
        
        # Datos
        for row in rows:
            fecha_str = row['fecha']  # Formato ISO YYYY-MM-DD en BD
            
            # Convertir a formato DD/MM/YYYY para el CSV
            if fecha_str and len(fecha_str) == 10:
                año, mes, día = fecha_str.split('-')
                fecha_csv = f"{día}/{mes}/{año}"
            else:
                fecha_csv = fecha_str
            
            # Convertir importe a formato español (con coma decimal y punto de miles)
            importe = float(row['importe']) if row['importe'] else 0
            importe_str = f"{importe:.2f}".replace('.', ',')
            
            writer.writerow([
                fecha_csv,
                importe_str,
                row['descripcion'] or '',
                row['banco'] or '',
                row['cuenta'] or '',
                row['tipo'] or '',
                row['cat1'] or '',
                row['cat2'] or '',
                row['hash'] or '',
                row['id'] or ''
            ])
    
    print(f"✅ Maestro v4 generado: {OUTPUT_PATH}")
    print(f"   Total transacciones: {len(rows)}")
    
    # Estadísticas
    cursor = sqlite3.connect(DB_PATH).cursor()
    cursor.execute("SELECT cat1, COUNT(*) as count FROM transacciones GROUP BY cat1 ORDER BY count DESC LIMIT 10")
    print("\n📊 Top 10 categorías:")
    for cat1, count in cursor.fetchall():
        print(f"   {cat1}: {count}")

if __name__ == '__main__':
    generate_master()
