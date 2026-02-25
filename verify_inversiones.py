#!/usr/bin/env python3
"""
TAREA 1: Verificación de reglas INVERSION.
Reprocesa las 413 transacciones del maestro clasificadas como INVERSION
y compara con el clasificador actual.
"""
import csv
from collections import Counter
from classifier.engine import Classifier


def main():
    print("=" * 80)
    print("TAREA 1: VERIFICACIÓN REGLAS INVERSION")
    print("=" * 80)

    # Cargar clasificador
    classifier = Classifier('Validación_Categorias_Finsense_MASTER_NEW.csv')

    # Leer maestro y filtrar INVERSION
    inversiones = []

    with open('Validación_Categorias_Finsense_MASTER_NEW.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Tipo'] == 'INVERSION':
                inversiones.append({
                    'fecha': row['Fecha'],
                    'importe': float(row['Importe']),
                    'descripcion': row.get('Descripción') or row.get('Descripcion', ''),
                    'banco': row['Banco'],
                    'tipo_maestro': row['Tipo'],
                    'cat1_maestro': row['Cat1'],
                    'cat2_maestro': row['Cat2']
                })

    total = len(inversiones)
    print(f"\n📊 Total transacciones INVERSION en maestro: {total}")

    # Distribucion Cat1 en maestro
    cat1_dist = Counter([inv['cat1_maestro'] for inv in inversiones])
    print(f"\n📋 Distribución Cat1 en maestro:")
    for cat1, count in cat1_dist.most_common():
        print(f"   • {cat1}: {count}")

    # Distribución por banco
    banco_dist = Counter([inv['banco'] for inv in inversiones])
    print(f"\n🏦 Distribución por banco:")
    for banco, count in banco_dist.most_common():
        print(f"   • {banco}: {count}")

    # Reprocesar con clasificador actual
    print(f"\n🔄 Reprocesando con clasificador actual...")

    tipo_match = 0
    cat1_match = 0
    tipo_errors = []
    cat1_errors = []

    for inv in inversiones:
        result = classifier.classify(
            descripcion=inv['descripcion'],
            banco=inv['banco'],
            importe=inv['importe'],
            fecha=inv['fecha']
        )

        tipo_actual = result['tipo']
        cat1_actual = result['cat1']

        # Comparar Tipo
        if tipo_actual == inv['tipo_maestro']:
            tipo_match += 1
        else:
            tipo_errors.append({
                'fecha': inv['fecha'],
                'banco': inv['banco'],
                'desc': inv['descripcion'][:60],
                'maestro': inv['tipo_maestro'],
                'actual': tipo_actual,
                'cat1_maestro': inv['cat1_maestro']
            })

        # Comparar Cat1 (solo si Tipo=INVERSION)
        if tipo_actual == 'INVERSION':
            if cat1_actual == inv['cat1_maestro']:
                cat1_match += 1
            else:
                cat1_errors.append({
                    'fecha': inv['fecha'],
                    'banco': inv['banco'],
                    'desc': inv['descripcion'][:60],
                    'maestro': inv['cat1_maestro'],
                    'actual': cat1_actual,
                })

    # Calcular accuracy
    tipo_pct = (tipo_match / total) * 100
    cat1_pct = (cat1_match / tipo_match) * 100 if tipo_match > 0 else 0

    # Reportar
    print("\n" + "=" * 80)
    print("RESULTADOS")
    print("=" * 80)
    print(f"\n{'Métrica':20s} {'Coinciden':>12s} {'Fallan':>12s} {'% Accuracy':>12s}")
    print("─" * 80)
    print(f"{'Tipo=INVERSION':20s} {tipo_match:>12,d} {len(tipo_errors):>12,d} {tipo_pct:>11.2f}%")
    print(f"{'Cat1 (si INVERSION)':20s} {cat1_match:>12,d} {len(cat1_errors):>12,d} {cat1_pct:>11.2f}%")

    # Mostrar errores de Tipo (primeros 30)
    if tipo_errors:
        print("\n" + "=" * 80)
        print(f"ERRORES DE TIPO (primeros 30 de {len(tipo_errors)})")
        print("=" * 80)

        # Agrupar por Cat1 maestro para ver qué tipos de inversión fallan
        tipo_by_cat1 = {}
        for err in tipo_errors:
            cat1 = err['cat1_maestro']
            if cat1 not in tipo_by_cat1:
                tipo_by_cat1[cat1] = []
            tipo_by_cat1[cat1].append(err)

        print(f"\n📊 Errores por Cat1 (maestro):")
        for cat1, errors in sorted(tipo_by_cat1.items(), key=lambda x: -len(x[1])):
            print(f"\n   {cat1}: {len(errors)} errores")
            for err in errors[:5]:  # Mostrar primeros 5 de cada cat1
                print(f"      {err['fecha']:10s} {err['banco']:15s} → {err['actual']:15s}")
                print(f"         {err['desc']}")

    # Mostrar errores de Cat1 (primeros 30)
    if cat1_errors:
        print("\n" + "=" * 80)
        print(f"ERRORES DE CAT1 (primeros 30 de {len(cat1_errors)})")
        print("=" * 80)

        # Agrupar por Cat1 maestro
        cat1_by_maestro = {}
        for err in cat1_errors:
            maestro = err['maestro']
            if maestro not in cat1_by_maestro:
                cat1_by_maestro[maestro] = []
            cat1_by_maestro[maestro].append(err)

        print(f"\n📊 Errores por Cat1 maestro:")
        for cat1_m, errors in sorted(cat1_by_maestro.items(), key=lambda x: -len(x[1])):
            actual_dist = Counter([e['actual'] for e in errors])
            print(f"\n   {cat1_m}: {len(errors)} errores")
            print(f"      Se clasifica como: {dict(actual_dist)}")
            for err in errors[:3]:  # Mostrar primeros 3 ejemplos
                print(f"         {err['fecha']:10s} {err['banco']:15s}")
                print(f"         {err['desc']}")

    # Diagnóstico
    print("\n" + "=" * 80)
    print("DIAGNÓSTICO")
    print("=" * 80)

    if tipo_pct >= 95.0:
        print(f"\n✅ TIPO INVERSION: {tipo_pct:.1f}% accuracy - BUENO")
    else:
        print(f"\n⚠️  TIPO INVERSION: {tipo_pct:.1f}% accuracy - NECESITA MEJORAS")
        print(f"   {len(tipo_errors)} transacciones NO se detectan como INVERSION")

    if cat1_pct >= 90.0:
        print(f"✅ CAT1: {cat1_pct:.1f}% accuracy - BUENO")
    else:
        print(f"⚠️  CAT1: {cat1_pct:.1f}% accuracy - NECESITA MEJORAS")
        print(f"   {len(cat1_errors)} transacciones tienen Cat1 incorrecta")

    print("\n📝 Próximos pasos:")
    print("   1. Revisar errores agrupados por Cat1 maestro")
    print("   2. Implementar reglas que falten en classifier/investments.py")
    print("   3. Priorizar las Cat1 con más errores")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
