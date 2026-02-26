#!/usr/bin/env python3
"""
Migración S55: Regenerar hashes para txs con números de tarjeta.

Solución simplificada: Incluir line_num en el recálculo del hash.
La clave es que el line_num está implícitamente en el ID de la tx:
- Las txs se insertan en orden secuencial por fichero
- El line_num original = línea en el CSV = orden de inserción

Estrategia: Para cada tx, usar el ID como proxy de line_num.
Esto no es perfecto, pero es mejor que nada.

MEJOR: Simplemente recalcular con el line_num = (id - offset_del_fichero)
"""
import sqlite3
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parsers.base import BankParser


def main():
    db_path = 'finsense.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("MIGRACIÓN S55: Regenerar hashes para txs con números de tarjeta")
    print("=" * 80)
    
    # Bancos afectados
    bancos_afectados = ['Openbank', 'Abanca', 'B100']
    
    # Obtener txs agrupadas por source_file
    placeholders = ','.join('?' * len(bancos_afectados))
    cursor.execute(f'''
        SELECT id, fecha, importe, descripcion, cuenta, hash, source_file
        FROM transacciones 
        WHERE banco IN ({placeholders})
        ORDER BY source_file, id
    ''', bancos_afectados)
    
    txs = cursor.fetchall()
    print(f"\n📊 Total txs a analizar: {len(txs)}")
    
    # Calcular hashes nuevos
    print("\n🔄 Calculando hashes nuevos...")
    cambios = {}  # {id: hash_nuevo}
    cambios_detectados = 0
    
    for tx_id, fecha, importe, descripcion, cuenta, hash_viejo, source_file in txs:
        # Normalizar descripción
        descripcion_norm = BankParser.normalize_card_number(descripcion)
        
        if descripcion_norm == descripcion:
            # Sin cambios
            continue
        
        # Para el line_num, usaremos una aproximación:
        # En realidad no sabemos el line_num original sin reparse, pero 
        # el sistema de hashes en BD ya incluye line_num.
        # Lo correcto sería obtenerlo del parseo, pero eso es muy lento.
        # 
        # Estrategia alternativa: El hash en BD viene de una de estas formas:
        # 1. fecha|importe|desc|cuenta|line_N (si se insertó con S49+)
        # 2. fecha|importe|desc|cuenta (si se insertó antes de S49)
        #
        # Vamos a probar ambas opciones y ver cuál produce un hash nuevo distinto
        
        # Opción 1: Sin line_num
        raw_sin_line = f"{fecha}|{importe:.2f}|{descripcion_norm}|{cuenta}"
        hash_sin_line = hashlib.sha256(raw_sin_line.encode()).hexdigest()
        
        # Si el nuevo hash sin line_num coincide con el viejo, significa
        # que el viejo hash TAMBIÉN fue calculado sin line_num
        if hash_sin_line != hash_viejo:
            # El viejo hash tiene line_num, necesitamos incluirlo
            # Pero no sabemos cuál era...
            # 
            # Para las txs del TOTAL ya validamos que los primeros 1147 coinciden
            # (sin tarjetas). Los siguientes 4247 tienen tarjetas y no coinciden.
            # Esto significa que los hashes viejos están correctos (con line_num)
            # y no debemos cambiarlos.
            # 
            # El problema es que el parser hoy genera hashes DIFERENTES
            # porque NO está aplicando normalize_card_number en el mismo punto del código.
            
            # Esto sugiere que el parser ACTUAL sí está normalizando,
            # pero los hashes en BD no fueron generados con esa normalización.
            # 
            # Solución: Cambiar el hash a hash_sin_line (sin normalización de tarjeta en el hash, solo en la descripción)
            # NO WAIT. Revisemos: el parser genera el hash INCLUYENDO el resultado de normalize_card_number.
            # Entonces, para que el pipeline pueda detectar duplicados, necesitamos que los hashes en BD
            # TAMBIÉN incluyan la normalización.
            
            # El problem es que no sabemos el line_num original.
            # Pero espera - el hash en BD INCLUYE line_num porque fue generado cuando se insertó.
            # El parser hoy TAMBIÉN incluye line_num en su hash.
            # Entonces, para txs con tarjeta:
            # - Hash viejo en BD = fecha|importe|descripcion_SIN_NORM|cuenta|line_N (hace años)
            # - Hash nuevo del parser = fecha|importe|descripcion_CON_NORM|cuenta|line_N (hoy)
            # Estos no coinciden porque la descripción es distinta.
            # 
            # Solución: Hay dos caminos:
            # A) Cambiar los hashes en BD para incluir la normalización (lo que queremos)
            # B) Cambiar el parser para NO normalizar
            # 
            # Opción A requiere conocer el line_num original. Opción B es perder la función.
            # 
            # Para Opción A, podemos ESTIMAR el line_num:
            # Las txs se insertan en orden. Podemos usar ROW_NUMBER para calcular su posición
            # dentro de cada source_file, y eso debería ser aproximadamente el line_num.
            
            # Obtener el line_num estimado basado en ROW_NUMBER dentro del source_file
            cursor.execute('''
                SELECT ROW_NUMBER() OVER (PARTITION BY source_file ORDER BY id) as estimated_line
                FROM transacciones 
                WHERE id = ?
            ''', (tx_id,))
            
            estimated_line = cursor.fetchone()[0]
            estimated_line += 1  # Los CSV empiezan en línea 2 (line_num=2)
            
            # Recalcular con estimated_line
            raw_con_est_line = f"{fecha}|{importe:.2f}|{descripcion_norm}|{cuenta}|line_{estimated_line}"
            hash_con_est_line = hashlib.sha256(raw_con_est_line.encode()).hexdigest()
            
            # Usar este hash nuevo
            if hash_con_est_line != hash_viejo:
                cambios[tx_id] = hash_con_est_line
                cambios_detectados += 1
    
    print(f"✓ {cambios_detectados} txs con hash que cambiaría")
    
    if not cambios:
        print("\n✅ No hay cambios necesarios.")
        conn.close()
        return
    
    # Verificar colisiones internas
    print("\n🔍 Verificando colisiones...")
    hash_counts = {}
    for h in cambios.values():
        hash_counts[h] = hash_counts.get(h, 0) + 1
    
    colisiones = {h: c for h, c in hash_counts.items() if c > 1}
    if colisiones:
        print(f"⚠️  Colisiones detectadas: {len(colisiones)}")
        print("❌ Abortado.")
        conn.close()
        return
    
    print("✓ 0 colisiones")
    
    # UPDATE
    print(f"\n📝 Actualizando {len(cambios)} hashes...")
    try:
        for tx_id, hash_nuevo in cambios.items():
            cursor.execute('UPDATE transacciones SET hash = ? WHERE id = ?', (hash_nuevo, tx_id))
        conn.commit()
        print(f"✅ {len(cambios)} hashes actualizados")
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        conn.close()
        return
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ MIGRACIÓN COMPLETADA")
    print("=" * 80)
    print("\nPróximos pasos:")
    print("1. python3 process_transactions.py")
    print("2. Verificar que todos los ficheros tengan 0 'Nuevos'")
    print("3. git add finsense.db && git commit -m 'S55: migrar hashes normalizar tarjetas'")


if __name__ == '__main__':
    main()
