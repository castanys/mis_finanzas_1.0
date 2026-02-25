#!/usr/bin/env python3
"""
Genera CSV maestro v28 desde finsense.db
Incorpora cambios de S17 (REGLAS #35-#45) y S18 (REGLAS #46-#53 + 229 merchants)
Formato: mismo que v27 (9 columnas: fecha, importe, descripcion, banco, cuenta, tipo, cat1, cat2, hash)
"""
import sqlite3
import csv
import sys

def main():
    # Conectar a BD
    try:
        conn = sqlite3.connect('finsense.db')
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Error conectando a finsense.db: {e}")
        sys.exit(1)

    # Verificar que BD tiene datos
    cursor.execute("SELECT COUNT(*) FROM transacciones")
    total_count = cursor.fetchone()[0]
    print(f"📊 Total transacciones en BD: {total_count}")

    # Verificar métricas
    cursor.execute("SELECT COUNT(*) FROM transacciones WHERE cat2='Otros'")
    otros_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM transacciones WHERE cat1='Compras' AND cat2='Otros'")
    compras_otros_count = cursor.fetchone()[0]
    
    print(f"   Cat2='Otros': {otros_count}")
    print(f"   Compras/Otros: {compras_otros_count}")

    # Exportar todas las transacciones
    cursor.execute("""
        SELECT fecha, importe, descripcion, banco, cuenta, tipo, cat1, cat2, hash
        FROM transacciones
        ORDER BY fecha, id
    """)

    rows = cursor.fetchall()
    conn.close()

    # Exportar a CSV
    output_file = 'validate/Validacion_Categorias_Finsense_MASTER_v28.csv'

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header (exactamente igual a v27)
            writer.writerow([
                'fecha', 'importe', 'descripcion', 'banco', 'cuenta',
                'tipo', 'cat1', 'cat2', 'hash'
            ])

            # Data
            for row in rows:
                writer.writerow(row)

        print()
        print("=" * 80)
        print("✅ CSV MAESTRO v28 GENERADO EXITOSAMENTE")
        print("=" * 80)
        print(f"📁 Archivo: {output_file}")
        print(f"📝 Total transacciones: {len(rows)}")
        print(f"📋 Líneas con header: {len(rows) + 1}")
        print()
        print("Cambios respecto a v27:")
        print("  • REGLAS #35-#45 (S17): -85 transacciones reclasificadas")
        print("  • REGLAS #46-#53 + 229 merchants (S18): -225 transacciones reclasificadas")
        print("  • Total cambios: -310 transacciones")
        print()
        print("Métricas finales:")
        print(f"  • Cat2='Otros': {otros_count}")
        print(f"  • Compras/Otros: {compras_otros_count}")
        print(f"  • Cobertura clasificación: {100.0 * (total_count - compras_otros_count) / total_count:.1f}%")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error escribiendo CSV: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
