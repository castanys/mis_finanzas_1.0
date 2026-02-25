#!/usr/bin/env python3
"""
Análisis detallado de discrepancias Cat1.

1. Para Externa vs Interna: verificar si hay contrapartida (match por fecha+importe inverso)
2. Para Devoluciones: mostrar ejemplos completos
3. Para Cripto: verificar contrapartida
"""
import csv
from collections import defaultdict
from typing import List, Dict, Optional


def load_output(filepath: str) -> List[Dict]:
    """Cargar CSV de output."""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            record = {
                'fecha': row.get('fecha', '').strip(),
                'importe': float(row.get('importe', 0)),
                'descripcion': row.get('descripcion', '').strip(),
                'banco': row.get('banco', '').strip(),
                'cuenta': row.get('cuenta', '').strip(),
                'tipo': row.get('tipo', '').strip(),
                'cat1': row.get('cat1', '').strip(),
                'cat2': row.get('cat2', '').strip(),
            }
            records.append(record)
    return records


def buscar_contrapartida(tx: Dict, todas_tx: List[Dict], tolerance_days: int = 3) -> Optional[Dict]:
    """
    Buscar contrapartida de una transferencia interna.

    Criterios:
    - Misma fecha (±tolerance_days)
    - Importe opuesto (aprox)
    - Banco diferente
    """
    from datetime import datetime, timedelta

    try:
        fecha_tx = datetime.strptime(tx['fecha'], '%Y-%m-%d')
    except:
        return None

    importe_tx = tx['importe']
    banco_tx = tx['banco']

    candidatos = []

    for otra in todas_tx:
        # Skip la misma transacción
        if otra is tx:
            continue

        try:
            fecha_otra = datetime.strptime(otra['fecha'], '%Y-%m-%d')
        except:
            continue

        # Verificar fecha cercana
        diff_dias = abs((fecha_otra - fecha_tx).days)
        if diff_dias > tolerance_days:
            continue

        # Verificar importe opuesto (con tolerancia de 0.01)
        importe_otra = otra['importe']
        if abs(importe_tx + importe_otra) > 0.01:
            continue

        # Verificar banco diferente
        if otra['banco'] == banco_tx:
            continue

        # Candidato encontrado
        candidatos.append({
            'tx': otra,
            'diff_dias': diff_dias,
            'diff_importe': abs(importe_tx + importe_otra),
        })

    # Retornar el mejor candidato (menor diferencia de días)
    if candidatos:
        mejor = min(candidatos, key=lambda x: x['diff_dias'])
        return mejor['tx']

    return None


def main():
    print("\n" + "=" * 120)
    print("ANÁLISIS DETALLADO DE DISCREPANCIAS CAT1")
    print("=" * 120)

    # Cargar output
    print("\n📂 Cargando output...")
    output_records = load_output('output/transacciones_completas.csv')
    print(f"  Total: {len(output_records):,} transacciones")

    # Crear índice por fecha para búsqueda rápida de contrapartidas
    print("\n📊 Creando índice de contrapartidas...")

    # PROBLEMA 1: Externa (maestro) vs Interna (output)
    print("\n" + "=" * 120)
    print("PROBLEMA 1: TRANSFERENCIAS EXTERNAS vs INTERNAS")
    print("=" * 120)
    print("\nBuscando transferencias clasificadas como Interna en output...")
    print("Verificando si tienen contrapartida real...\n")

    # Ejemplos conocidos del output anterior
    casos_externa_interna = [
        {'fecha': '2023-12-01', 'importe': 250, 'banco': 'Openbank'},
        {'fecha': '2024-04-15', 'importe': 7200, 'banco': 'Openbank'},
        {'fecha': '2024-05-27', 'importe': 400, 'banco': 'Openbank'},
        {'fecha': '2024-09-23', 'importe': 500, 'banco': 'Openbank'},
        {'fecha': '2025-01-28', 'importe': 350, 'banco': 'Openbank'},
        {'fecha': '2025-03-18', 'importe': 1500, 'banco': 'Openbank'},
        {'fecha': '2020-07-22', 'importe': -1432.10, 'banco': 'Mediolanum'},
        {'fecha': '2023-06-12', 'importe': -17000, 'banco': 'Mediolanum'},
        {'fecha': '2023-07-05', 'importe': -1500, 'banco': 'Mediolanum'},
        {'fecha': '2023-08-07', 'importe': -2000, 'banco': 'Mediolanum'},
        {'fecha': '2023-09-06', 'importe': -2100, 'banco': 'Mediolanum'},
    ]

    print(f"{'Fecha':<12} {'Importe':>12} {'Banco Origen':<15} {'Output Cat1':<15} {'Contrapartida?':<15} {'Banco Destino':<15} {'Conclusión':<20}")
    print("-" * 120)

    for caso in casos_externa_interna:
        # Buscar la transacción en el output
        tx_encontrada = None
        for tx in output_records:
            if (tx['fecha'] == caso['fecha'] and
                abs(tx['importe'] - caso['importe']) < 0.01 and
                tx['banco'] == caso['banco']):
                tx_encontrada = tx
                break

        if not tx_encontrada:
            print(f"{caso['fecha']:<12} {caso['importe']:>12.2f} {caso['banco']:<15} {'NO ENCONTRADA':<15}")
            continue

        # Buscar contrapartida
        contrapartida = buscar_contrapartida(tx_encontrada, output_records)

        if contrapartida:
            conclusion = "✅ ES INTERNA" if contrapartida else "⚠️ ES EXTERNA"
            print(f"{tx_encontrada['fecha']:<12} {tx_encontrada['importe']:>12.2f} {tx_encontrada['banco']:<15} {tx_encontrada['cat1']:<15} {'SÍ':^15s} {contrapartida['banco']:<15} {conclusion:<20}")
            print(f"  → Desc origen: {tx_encontrada['descripcion'][:80]}")
            print(f"  → Desc destino: {contrapartida['descripcion'][:80]}")
        else:
            print(f"{tx_encontrada['fecha']:<12} {tx_encontrada['importe']:>12.2f} {tx_encontrada['banco']:<15} {tx_encontrada['cat1']:<15} {'NO':^15s} {'-':<15} {'⚠️ ES EXTERNA':<20}")
            print(f"  → Descripción: {tx_encontrada['descripcion'][:80]}")
        print()

    # PROBLEMA 2: Devoluciones
    print("\n" + "=" * 120)
    print("PROBLEMA 2: DEVOLUCIONES")
    print("=" * 120)
    print("\nEjemplos de transacciones clasificadas como Devoluciones en maestro pero diferente en output:\n")

    casos_devoluciones = [
        {'fecha': '2005-10-27', 'importe': 40, 'banco': 'Openbank'},
        {'fecha': '2007-12-26', 'importe': 60, 'banco': 'Openbank'},
        {'fecha': '2007-12-27', 'importe': 339, 'banco': 'Openbank'},
        {'fecha': '2008-01-02', 'importe': 89, 'banco': 'Openbank'},
        {'fecha': '2008-01-21', 'importe': 69, 'banco': 'Openbank'},
        {'fecha': '2008-03-12', 'importe': 18.22, 'banco': 'Openbank'},
        {'fecha': '2024-08-12', 'importe': 8.4, 'banco': 'Mediolanum'},
        {'fecha': '2024-08-12', 'importe': 13.7, 'banco': 'Mediolanum'},
        {'fecha': '2024-08-12', 'importe': 6.5, 'banco': 'Mediolanum'},
    ]

    print(f"{'Fecha':<12} {'Importe':>12} {'Banco':<15} {'Output Cat1':<20} {'Output Cat2':<20} {'Descripción':<60}")
    print("-" * 120)

    for caso in casos_devoluciones:
        # Buscar en output
        for tx in output_records:
            if (tx['fecha'] == caso['fecha'] and
                abs(tx['importe'] - caso['importe']) < 0.01 and
                tx['banco'] == caso['banco']):
                print(f"{tx['fecha']:<12} {tx['importe']:>12.2f} {tx['banco']:<15} {tx['cat1']:<20} {tx['cat2']:<20} {tx['descripcion'][:60]}")
                # Buscar transacción opuesta (gasto original)
                original = buscar_contrapartida(tx, output_records, tolerance_days=30)
                if original:
                    print(f"  → Posible original: {original['fecha']} | {original['importe']:.2f} | {original['descripcion'][:60]}")
                print()
                break

    # PROBLEMA 3: Cripto
    print("\n" + "=" * 120)
    print("PROBLEMA 3: CRIPTO")
    print("=" * 120)
    print("\nTransacciones clasificadas como Cripto en maestro pero Interna en output:")
    print("Verificando si tienen contrapartida (NO deberían tenerla si son cripto)...\n")

    casos_cripto = [
        {'fecha': '2022-11-09', 'importe': 1300, 'banco': 'Openbank'},
        {'fecha': '2024-02-28', 'importe': -6700, 'banco': 'Mediolanum'},
        {'fecha': '2024-02-29', 'importe': -6300, 'banco': 'Mediolanum'},
    ]

    print(f"{'Fecha':<12} {'Importe':>12} {'Banco Origen':<15} {'Output Cat1':<15} {'Contrapartida?':<15} {'Banco Destino':<15} {'Conclusión':<25}")
    print("-" * 120)

    for caso in casos_cripto:
        # Buscar en output
        tx_encontrada = None
        for tx in output_records:
            if (tx['fecha'] == caso['fecha'] and
                abs(tx['importe'] - caso['importe']) < 0.01 and
                tx['banco'] == caso['banco']):
                tx_encontrada = tx
                break

        if not tx_encontrada:
            continue

        # Buscar contrapartida
        contrapartida = buscar_contrapartida(tx_encontrada, output_records)

        if contrapartida:
            print(f"{tx_encontrada['fecha']:<12} {tx_encontrada['importe']:>12.2f} {tx_encontrada['banco']:<15} {tx_encontrada['cat1']:<15} {'SÍ':^15s} {contrapartida['banco']:<15} {'✅ ES INTERNA (no cripto)':<25}")
            print(f"  → Desc origen: {tx_encontrada['descripcion'][:80]}")
            print(f"  → Desc destino: {contrapartida['descripcion'][:80]}")
        else:
            print(f"{tx_encontrada['fecha']:<12} {tx_encontrada['importe']:>12.2f} {tx_encontrada['banco']:<15} {tx_encontrada['cat1']:<15} {'NO':^15s} {'-':<15} {'⚠️ ES CRIPTO (sin match)':<25}")
            print(f"  → Descripción: {tx_encontrada['descripcion'][:80]}")
        print()

    # RESUMEN
    print("\n" + "=" * 120)
    print("RESUMEN")
    print("=" * 120)
    print("\n1. TRANSFERENCIAS EXTERNAS vs INTERNAS:")
    print("   - Si tienen contrapartida → ES INTERNA (output correcto)")
    print("   - Si NO tienen contrapartida → ES EXTERNA (maestro correcto)")
    print("\n2. DEVOLUCIONES:")
    print("   - Ver ejemplos arriba para decidir si son devoluciones reales o compras")
    print("   - Si son devoluciones, considerar clasificar como 'Cat1: Cat2: Devolución'")
    print("\n3. CRIPTO:")
    print("   - Si tienen contrapartida → ES INTERNA (no es cripto)")
    print("   - Si NO tienen contrapartida → ES CRIPTO (maestro correcto)")
    print("=" * 120 + "\n")


if __name__ == '__main__':
    main()
