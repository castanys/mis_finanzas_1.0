#!/usr/bin/env python3
"""
Inserta transacciones B100 Health y Save en la BBDD con:
- Clasificación automática
- Detección de pares (contrapartidas)
- Deduplicación por hash
"""
import sys
import sqlite3
import hashlib
from datetime import datetime

sys.path.append('src/parsers')
from enablebanking import EnablebankingParser
from classifier.engine import Classifier


def generate_hash(fecha, importe, descripcion, cuenta):
    """Genera hash único para deduplicación."""
    unique_string = f"{fecha}|{importe:.2f}|{descripcion}|{cuenta}"
    return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()


def detect_pairs(transactions):
    """
    Detecta pares de transferencias internas (contrapartidas).

    Args:
        transactions: Lista de transacciones

    Returns:
        Dict con pares detectados: {hash: par_hash}
    """
    pairs = {}

    # Solo buscar pares en transferencias internas
    internals = [
        tx for tx in transactions
        if tx['tipo'] == 'TRANSFERENCIA' and tx['cat1'] == 'Interna'
    ]

    for i, tx1 in enumerate(internals):
        for tx2 in internals[i+1:]:
            # Mismo día, importes opuestos, diferentes cuentas
            if (tx1['fecha'] == tx2['fecha'] and
                abs(tx1['importe'] + tx2['importe']) < 0.01 and
                tx1['cuenta'] != tx2['cuenta']):

                # Par detectado
                hash1 = tx1['hash']
                hash2 = tx2['hash']
                pairs[hash1] = hash2
                pairs[hash2] = hash1

    return pairs


def main():
    print("=" * 80)
    print("INSERCIÓN B100 HEALTH & SAVE EN FINSENSE.DB")
    print("=" * 80)

    # 1. Parsear archivos
    files = [
        ('input/new/enable_abanca_ES66208001000130433834434_EUR_20260214-221642.csv', 'Health'),
        ('input/new/enable_abanca_ES95208001000830433834442_EUR_20260214-221634.csv', 'Save'),
    ]

    parser = EnablebankingParser()
    classifier = Classifier('Validación_Categorias_Finsense_MASTER_NEW.csv')

    all_transactions = []

    for file_path, account_type in files:
        print(f"\n📁 Parseando {account_type}: {file_path.split('/')[-1][:60]}")

        # Parsear
        transactions = parser.parse(file_path)

        # Clasificar y preparar
        for tx in transactions:
            # Clasificar
            result = classifier.classify(
                descripcion=tx['concepto'],
                banco=tx['banco'],
                importe=tx['importe'],
                fecha=str(tx['fecha'])
            )

            # Agregar clasificación
            tx['tipo'] = result['tipo']
            tx['cat1'] = result['cat1']
            tx['cat2'] = result['cat2']
            tx['capa'] = result['capa']

            # Generar hash
            tx['hash'] = generate_hash(
                str(tx['fecha']),
                tx['importe'],
                tx['concepto'],
                tx['cuenta']
            )

            all_transactions.append(tx)

        print(f"   ✅ {len(transactions)} transacciones parseadas y clasificadas")

    print(f"\n📊 Total transacciones: {len(all_transactions)}")

    # 2. Detectar pares (contrapartidas)
    print(f"\n🔍 Detectando pares de transferencias internas...")
    pairs = detect_pairs(all_transactions)
    print(f"   ✅ {len(pairs) // 2} pares detectados")

    # 3. Conectar a BBDD y verificar duplicados
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    cursor.execute("SELECT hash FROM transacciones")
    existing_hashes = {row[0] for row in cursor.fetchall()}

    # Filtrar duplicados
    new_transactions = [
        tx for tx in all_transactions
        if tx['hash'] not in existing_hashes
    ]

    duplicates = len(all_transactions) - len(new_transactions)

    if duplicates > 0:
        print(f"   ⚠️  {duplicates} duplicados encontrados (serán saltados)")
    else:
        print(f"   ✅ No hay duplicados")

    print(f"\n💾 Insertando {len(new_transactions)} transacciones nuevas...")

    # 4. Insertar transacciones
    insert_count = 0

    for tx in new_transactions:
        # Preparar par_id y par_tipo
        par_hash = pairs.get(tx['hash'])
        par_id = None
        par_tipo = None

        if par_hash:
            # Buscar par_id en transacciones ya insertadas
            cursor.execute("SELECT id FROM transacciones WHERE hash = ?", (par_hash,))
            result = cursor.fetchone()
            if result:
                par_id = result[0]
                # Determinar tipo de par según importe
                par_tipo = 'salida' if tx['importe'] > 0 else 'entrada'

        # Insertar
        cursor.execute("""
            INSERT INTO transacciones (
                fecha, importe, descripcion, banco, cuenta,
                tipo, cat1, cat2, hash, par_id, par_tipo, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(tx['fecha']),
            tx['importe'],
            tx['concepto'],
            tx['banco'],
            tx['cuenta'],
            tx['tipo'],
            tx['cat1'],
            tx['cat2'],
            tx['hash'],
            par_id,
            par_tipo,
            f"enable_{tx['banco'].lower()}_{tx['cuenta']}_2026"
        ))

        insert_count += 1

    conn.commit()
    conn.close()

    print(f"   ✅ {insert_count} transacciones insertadas")

    # 5. Estadísticas finales
    print(f"\n📈 Estadísticas de inserción:")
    print(f"   • Health: 25 transacciones")
    print(f"   • Save: 111 transacciones")
    print(f"   • Pares detectados: {len(pairs) // 2}")
    print(f"   • Duplicados evitados: {duplicates}")
    print(f"   • Total insertado: {insert_count}")

    print("\n" + "=" * 80)
    print("✅ INSERCIÓN COMPLETADA")
    print("=" * 80)
    print("\nPróximos pasos:")
    print("  1. Verificar contrapartidas en B100 Normal:")
    print("     python3 query_cli.py resumen 2026 01")
    print("  2. Validar que los traspasos B100 NO inflan ingresos")


if __name__ == '__main__':
    main()
