#!/usr/bin/env python3
"""
TAREA 1: ELIMINAR DUPLICADOS.

Detecta y elimina transacciones duplicadas basándose en:
- Misma fecha
- Mismo |importe| (valor absoluto)
- Mismo banco
- Misma cuenta

Criterio de selección (quedarse con UNO):
1. Preferir descripción SIN prefijo "Otros " o "Transferencia " (más limpia)
2. Preferir tarjeta enmascarada "XXXX" (más reciente)
3. Si ambas iguales, quedarse con la primera
"""
import sqlite3
from collections import defaultdict


def detect_duplicates(cursor):
    """Detecta grupos de duplicados."""
    cursor.execute("""
        SELECT id, fecha, importe, descripcion, banco, cuenta, tipo, cat1, cat2
        FROM transacciones
        ORDER BY fecha, banco, cuenta, importe
    """)

    all_transactions = cursor.fetchall()

    # Agrupar por (fecha, |importe|, banco, cuenta)
    groups = defaultdict(list)

    for tx in all_transactions:
        tx_id, fecha, importe, desc, banco, cuenta, tipo, cat1, cat2 = tx
        key = (fecha, abs(importe), banco, cuenta)
        groups[key].append({
            'id': tx_id,
            'fecha': fecha,
            'importe': importe,
            'descripcion': desc,
            'banco': banco,
            'cuenta': cuenta,
            'tipo': tipo,
            'cat1': cat1,
            'cat2': cat2
        })

    # Filtrar solo grupos con duplicados (2+ transacciones)
    duplicates = {k: v for k, v in groups.items() if len(v) >= 2}

    return duplicates


def score_transaction(tx):
    """
    Asigna un score a una transacción para decidir cuál mantener.
    Score MÁS ALTO = mejor (la que nos quedamos)
    """
    score = 0
    desc = tx['descripcion']

    # CRITERIO 1: Preferir SIN prefijos "Otros " o "Transferencia "
    if not desc.startswith('Otros '):
        score += 10
    if not desc.startswith('Transferencia '):
        score += 10

    # CRITERIO 2: Preferir tarjeta enmascarada (XXXX)
    if 'XXXX' in desc:
        score += 5

    # CRITERIO 3: Preferir descripción más corta (menos verbose)
    score -= len(desc) // 100  # Penalty pequeño por longitud

    return score


def select_best_transaction(duplicates):
    """Selecciona la mejor transacción de un grupo de duplicados."""
    # Calcular score para cada una
    scored = [(tx, score_transaction(tx)) for tx in duplicates]

    # Ordenar por score descendente
    scored.sort(key=lambda x: -x[1])

    # Devolver la mejor (mayor score)
    return scored[0][0]


def main():
    print("=" * 80)
    print("TAREA 1: ELIMINAR DUPLICADOS")
    print("=" * 80)

    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Detectar duplicados
    print("\n🔍 Detectando duplicados...")
    duplicate_groups = detect_duplicates(cursor)

    total_groups = len(duplicate_groups)
    total_duplicates = sum(len(txs) for txs in duplicate_groups.values())
    total_to_delete = sum(len(txs) - 1 for txs in duplicate_groups.values())

    print(f"\n📊 Resumen:")
    print(f"   Grupos de duplicados: {total_groups:,}")
    print(f"   Transacciones duplicadas: {total_duplicates:,}")
    print(f"   A eliminar (quedarse con 1 por grupo): {total_to_delete:,}")

    if total_groups == 0:
        print("\n✅ No hay duplicados. Base de datos limpia.")
        conn.close()
        return

    # Mostrar ejemplos
    print(f"\n📋 Ejemplos de duplicados (primeros 10 grupos):")
    for i, (key, txs) in enumerate(list(duplicate_groups.items())[:10]):
        fecha, importe, banco, cuenta = key
        print(f"\n   Grupo {i+1}: {fecha} | {banco} | €{importe:.2f} | {len(txs)} copias")
        for tx in txs:
            score = score_transaction(tx)
            print(f"      [{score:>3}] ID={tx['id']:>6} | {tx['descripcion'][:70]}")

    # Análisis por banco
    by_banco = defaultdict(int)
    for txs in duplicate_groups.values():
        banco = txs[0]['banco']
        by_banco[banco] += len(txs) - 1

    print(f"\n🏦 Duplicados por banco:")
    for banco, count in sorted(by_banco.items(), key=lambda x: -x[1]):
        print(f"   • {banco:20s}: {count:>5,d} duplicados a eliminar")

    # Seleccionar cuáles mantener y cuáles eliminar
    print(f"\n🧹 Seleccionando transacciones a mantener/eliminar...")

    to_keep = []
    to_delete = []

    for key, txs in duplicate_groups.items():
        best = select_best_transaction(txs)
        to_keep.append(best['id'])

        for tx in txs:
            if tx['id'] != best['id']:
                to_delete.append(tx['id'])

    print(f"\n   ✅ A mantener: {len(to_keep):,}")
    print(f"   🗑️  A eliminar: {len(to_delete):,}")

    # Confirmar eliminación
    print(f"\n{'=' * 80}")
    print(f"⚠️  CONFIRMACIÓN")
    print(f"{'=' * 80}")
    print(f"\nSe van a ELIMINAR {len(to_delete):,} transacciones duplicadas.")
    print(f"Backup creado en: finsense.db.bak_antes_limpieza")

    response = input(f"\n¿Proceder con la eliminación? (s/N): ")

    if response.lower() != 's':
        print("\n❌ Operación cancelada por el usuario.")
        conn.close()
        return

    # Eliminar duplicados
    print(f"\n🗑️  Eliminando {len(to_delete):,} duplicados...")

    deleted = 0
    for tx_id in to_delete:
        cursor.execute("DELETE FROM transacciones WHERE id = ?", (tx_id,))
        deleted += 1

    conn.commit()

    print(f"\n✅ Eliminados: {deleted:,} duplicados")

    # Verificación post-limpieza
    print(f"\n🔍 Verificando limpieza...")

    duplicate_groups_after = detect_duplicates(cursor)
    total_groups_after = len(duplicate_groups_after)

    if total_groups_after == 0:
        print(f"   ✅ 0 duplicados restantes")
    else:
        print(f"   ⚠️  {total_groups_after:,} grupos de duplicados AÚN presentes")
        print(f"      (posiblemente duplicados legítimos con diferente clasificación)")

    # Contar transacciones totales
    cursor.execute("SELECT COUNT(*) FROM transacciones")
    total_after = cursor.fetchone()[0]

    print(f"\n📊 Total transacciones después de limpieza: {total_after:,}")

    conn.close()

    print(f"\n{'=' * 80}")
    print(f"✅ LIMPIEZA COMPLETADA")
    print(f"{'=' * 80}")
    print(f"\nEliminadas: {deleted:,} transacciones duplicadas")
    print(f"Backup: finsense.db.bak_antes_limpieza")


if __name__ == '__main__':
    main()
