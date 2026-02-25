#!/usr/bin/env python3
"""
TAREA 1: Verificación del clasificador.
Reprocesa TODAS las transacciones de la BBDD con el clasificador actual
y compara con lo almacenado.
"""
import sqlite3
import csv
from classifier.engine import Classifier


def main():
    print("=" * 80)
    print("TAREA 1: VERIFICACIÓN DEL CLASIFICADOR")
    print("=" * 80)

    # Cargar clasificador
    classifier = Classifier('Validación_Categorias_Finsense_MASTER_NEW.csv')

    # Conectar a BBDD
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Leer TODAS las transacciones
    cursor.execute("""
        SELECT id, fecha, importe, descripcion, banco, tipo, cat1, cat2
        FROM transacciones
        ORDER BY id
    """)

    transacciones = cursor.fetchall()
    total_tx = len(transacciones)

    print(f"\n📊 Total transacciones en BBDD: {total_tx:,}")

    # Contadores
    tipo_match = 0
    cat1_match = 0
    cat2_match = 0
    all_match = 0

    tipo_changes = []
    cat1_changes = []
    cat2_changes = []

    # Reprocesar cada transacción
    print(f"\n🔄 Reprocesando con clasificador actual...")

    for tx_id, fecha, importe, desc, banco, tipo_db, cat1_db, cat2_db in transacciones:
        # Re-clasificar
        result = classifier.classify(
            descripcion=desc,
            banco=banco,
            importe=importe,
            fecha=fecha
        )

        tipo_nuevo = result['tipo']
        cat1_nuevo = result['cat1']
        cat2_nuevo = result['cat2']

        # Comparar
        tipo_ok = (tipo_nuevo == tipo_db)
        cat1_ok = (cat1_nuevo == cat1_db)
        cat2_ok = (cat2_nuevo == cat2_db)

        if tipo_ok:
            tipo_match += 1
        else:
            tipo_changes.append({
                'id': tx_id,
                'fecha': fecha,
                'desc': desc[:50],
                'antes': tipo_db,
                'despues': tipo_nuevo
            })

        if cat1_ok:
            cat1_match += 1
        else:
            cat1_changes.append({
                'id': tx_id,
                'fecha': fecha,
                'desc': desc[:50],
                'antes': cat1_db,
                'despues': cat1_nuevo
            })

        if cat2_ok:
            cat2_match += 1
        else:
            cat2_changes.append({
                'id': tx_id,
                'fecha': fecha,
                'desc': desc[:50],
                'antes': cat2_db,
                'despues': cat2_nuevo
            })

        if tipo_ok and cat1_ok and cat2_ok:
            all_match += 1

    # Calcular porcentajes
    tipo_pct = (tipo_match / total_tx) * 100
    cat1_pct = (cat1_match / total_tx) * 100
    cat2_pct = (cat2_match / total_tx) * 100
    all_pct = (all_match / total_tx) * 100

    # Reportar
    print("\n" + "=" * 80)
    print("RESULTADOS DE LA VERIFICACIÓN")
    print("=" * 80)

    print(f"\n{'Métrica':15s} {'Coinciden':>12s} {'Cambian':>12s} {'% Accuracy':>12s}")
    print("─" * 80)
    print(f"{'Tipo':15s} {tipo_match:>12,d} {len(tipo_changes):>12,d} {tipo_pct:>11.2f}%")
    print(f"{'Cat1':15s} {cat1_match:>12,d} {len(cat1_changes):>12,d} {cat1_pct:>11.2f}%")
    print(f"{'Cat2':15s} {cat2_match:>12,d} {len(cat2_changes):>12,d} {cat2_pct:>11.2f}%")
    print(f"{'TODO':15s} {all_match:>12,d} {total_tx - all_match:>12,d} {all_pct:>11.2f}%")

    # Comparar con el maestro
    print("\n" + "=" * 80)
    print("COMPARACIÓN CON MAESTRO")
    print("=" * 80)

    # Cargar maestro
    master = {}
    with open('Validación_Categorias_Finsense_MASTER_NEW.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['Fecha'], row['Importe'], row['Descripcion'], row['Banco'])
            master[key] = {
                'tipo': row['Tipo'],
                'cat1': row['Cat1'],
                'cat2': row['Cat2']
            }

    # Contar coincidencias con maestro
    master_tipo_match = 0
    master_cat1_match = 0
    master_cat2_match = 0
    master_total = 0

    cursor.execute("""
        SELECT fecha, importe, descripcion, banco, tipo, cat1, cat2
        FROM transacciones
    """)

    for fecha, importe, desc, banco, tipo_db, cat1_db, cat2_db in cursor.fetchall():
        key = (fecha, str(importe), desc, banco)
        if key in master:
            master_total += 1
            if tipo_db == master[key]['tipo']:
                master_tipo_match += 1
            if cat1_db == master[key]['cat1']:
                master_cat1_match += 1
            if cat2_db == master[key]['cat2']:
                master_cat2_match += 1

    if master_total > 0:
        master_tipo_pct = (master_tipo_match / master_total) * 100
        master_cat1_pct = (master_cat1_match / master_total) * 100
        master_cat2_pct = (master_cat2_match / master_total) * 100

        print(f"\nTransacciones en maestro: {master_total:,}")
        print(f"\n{'Métrica':15s} {'% Accuracy vs Maestro':>25s}")
        print("─" * 80)
        print(f"{'Tipo':15s} {master_tipo_pct:>24.2f}%")
        print(f"{'Cat1':15s} {master_cat1_pct:>24.2f}%")
        print(f"{'Cat2':15s} {master_cat2_pct:>24.2f}%")

    # Mostrar cambios de Tipo (primeros 20)
    if tipo_changes:
        print("\n" + "=" * 80)
        print(f"CAMBIOS EN TIPO (primeros 20 de {len(tipo_changes):,})")
        print("=" * 80)
        print(f"\n{'ID':>6s} {'Fecha':10s} {'Antes':15s} {'Después':15s} {'Descripción':40s}")
        print("─" * 80)
        for i, change in enumerate(tipo_changes[:20], 1):
            print(f"{change['id']:>6d} {change['fecha']:10s} {change['antes']:15s} "
                  f"{change['despues']:15s} {change['desc']:40s}")

    # Mostrar cambios de Cat1 (primeros 20)
    if cat1_changes:
        print("\n" + "=" * 80)
        print(f"CAMBIOS EN CAT1 (primeros 20 de {len(cat1_changes):,})")
        print("=" * 80)
        print(f"\n{'ID':>6s} {'Fecha':10s} {'Antes':20s} {'Después':20s} {'Descripción':30s}")
        print("─" * 80)
        for i, change in enumerate(cat1_changes[:20], 1):
            print(f"{change['id']:>6d} {change['fecha']:10s} {change['antes']:20s} "
                  f"{change['despues']:20s} {change['desc']:30s}")

    # Diagnóstico
    print("\n" + "=" * 80)
    print("DIAGNÓSTICO")
    print("=" * 80)

    if tipo_pct >= 99.9 and cat1_pct >= 99.9 and cat2_pct >= 99.0:
        print("\n✅ CLASIFICADOR ESTABLE - Cambios mínimos detectados")
        print("   El clasificador mantiene la clasificación almacenada")
    elif tipo_pct >= 95.0 and cat1_pct >= 95.0:
        print("\n⚠️  CAMBIOS MODERADOS DETECTADOS")
        print(f"   {len(tipo_changes)} cambios en Tipo")
        print(f"   {len(cat1_changes)} cambios en Cat1")
        print(f"   {len(cat2_changes)} cambios en Cat2")
        print("\n   Revisar cambios listados arriba - pueden ser mejoras o regresiones")
    else:
        print("\n🚨 ACCURACY HA BAJADO SIGNIFICATIVAMENTE")
        print(f"   Tipo: {tipo_pct:.1f}% (debería ser >99%)")
        print(f"   Cat1: {cat1_pct:.1f}% (debería ser >99%)")
        print(f"   Cat2: {cat2_pct:.1f}% (debería ser >95%)")
        print("\n   ⚠️  DIAGNÓSTICO NECESARIO - No continuar hasta arreglar")

    print("\n" + "=" * 80)

    conn.close()


if __name__ == '__main__':
    main()
