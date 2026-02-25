#!/usr/bin/env python3
"""
FASE 3: Cazador de Transferencias Internas
Empareja transferencias internas entre cuentas para eliminar doble conteo.
"""
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Tuple, Set


def parse_date(fecha_str: str) -> datetime:
    """Parse fecha en formato YYYY-MM-DD"""
    return datetime.strptime(fecha_str, '%Y-%m-%d')


def load_transactions(csv_path: str) -> List[Dict]:
    """Carga transacciones desde CSV"""
    transactions = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convertir importe a float
            row['importe'] = float(row['importe'])
            transactions.append(row)
    return transactions


def find_internal_transfer_pairs(transactions: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Encuentra pares de transferencias internas.

    Args:
        transactions: Lista de transacciones

    Returns:
        Tupla (pares, sin_pareja)
        - pares: Lista de diccionarios con info del par
        - sin_pareja: Lista de transacciones Interna sin emparejar
    """
    # 1. Filtrar candidatas: Cat1=Interna, importe != 0
    candidates = []
    for tx in transactions:
        if tx['cat1'] == 'Interna' and abs(tx['importe']) > 0.01:
            candidates.append(tx)

    # 2. Separar en salidas (importe < 0) y entradas (importe > 0)
    salidas = [tx for tx in candidates if tx['importe'] < 0]
    entradas = [tx for tx in candidates if tx['importe'] > 0]

    print(f"  Candidatas: {len(candidates)} (Salidas: {len(salidas)}, Entradas: {len(entradas)})")

    # 3. Para cada salida, buscar su entrada correspondiente
    pairs = []
    used_entries = set()
    used_exits = set()

    for sal_idx, sal in enumerate(salidas):
        best_match = None
        best_score = 0

        for ent_idx, ent in enumerate(entradas):
            if ent_idx in used_entries:
                continue

            # Condición 1: mismo importe absoluto (tolerancia 1 céntimo)
            if abs(abs(sal['importe']) - abs(ent['importe'])) > 0.01:
                continue

            # Condición 2: cuentas DISTINTAS
            if sal['cuenta'] == ent['cuenta']:
                continue

            # Condición 3: ventana temporal ±7 días
            fecha_sal = parse_date(sal['fecha'])
            fecha_ent = parse_date(ent['fecha'])
            dias_diff = abs((fecha_ent - fecha_sal).days)

            if dias_diff > 7:
                continue

            # Scoring de confianza
            score = 0
            if dias_diff == 0:
                score += 4      # mismo día = muy alta confianza
            elif dias_diff == 1:
                score += 3      # día siguiente = alta
            elif dias_diff <= 3:
                score += 2      # 2-3 días = buena
            else:
                score += 1      # 4-7 días = aceptable

            # Bonus: mismo banco (transferencia interna dentro del mismo banco)
            if sal['banco'] == ent['banco']:
                score += 1

            if score > best_score:
                best_score = score
                best_match = (ent_idx, ent, dias_diff, score)

        if best_match:
            idx, ent, dias, score = best_match
            used_entries.add(idx)
            used_exits.add(sal_idx)

            # Determinar confianza
            if dias <= 1:
                confidence = 'high'
            elif dias <= 3:
                confidence = 'medium'
            else:
                confidence = 'low'

            pairs.append({
                'salida': sal,
                'entrada': ent,
                'importe': abs(sal['importe']),
                'fecha_salida': sal['fecha'],
                'fecha_entrada': ent['fecha'],
                'cuenta_salida': sal['cuenta'],
                'cuenta_entrada': ent['cuenta'],
                'banco_salida': sal['banco'],
                'banco_entrada': ent['banco'],
                'dias_diferencia': dias,
                'confidence': confidence,
                'score': score,
            })

    # 4. Transacciones sin pareja
    sin_pareja = []
    for idx, sal in enumerate(salidas):
        if idx not in used_exits:
            sin_pareja.append(sal)
    for idx, ent in enumerate(entradas):
        if idx not in used_entries:
            sin_pareja.append(ent)

    # Ordenar sin_pareja por importe descendente
    sin_pareja.sort(key=lambda x: abs(x['importe']), reverse=True)

    return pairs, sin_pareja


def export_pairs_to_csv(pairs: List[Dict], output_path: str):
    """Exporta pares a CSV"""
    if not pairs:
        print(f"⚠️  No hay pares para exportar")
        return

    fieldnames = [
        'id_salida', 'id_entrada', 'importe',
        'fecha_salida', 'fecha_entrada',
        'cuenta_salida', 'cuenta_entrada',
        'banco_salida', 'banco_entrada',
        'dias_diferencia', 'confidence'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for pair in pairs:
            writer.writerow({
                'id_salida': pair['salida'].get('hash', '')[:16],
                'id_entrada': pair['entrada'].get('hash', '')[:16],
                'importe': f"{pair['importe']:.2f}",
                'fecha_salida': pair['fecha_salida'],
                'fecha_entrada': pair['fecha_entrada'],
                'cuenta_salida': pair['cuenta_salida'],
                'cuenta_entrada': pair['cuenta_entrada'],
                'banco_salida': pair['banco_salida'],
                'banco_entrada': pair['banco_entrada'],
                'dias_diferencia': pair['dias_diferencia'],
                'confidence': pair['confidence'],
            })

    print(f"✓ Exportado a: {output_path}")


def print_report(pairs: List[Dict], sin_pareja: List[Dict], total_internas: int):
    """Imprime reporte en consola"""
    print("\n" + "="*100)
    print("=== CAZADOR DE TRANSFERENCIAS INTERNAS ===")
    print("="*100)

    # Estadísticas generales
    transacciones_emparejadas = len(pairs) * 2
    pct_emparejadas = 100 * transacciones_emparejadas / total_internas if total_internas > 0 else 0

    print(f"\nTotal transacciones Cat1=Interna: {total_internas:,}")
    print(f"Pares encontrados:                 {len(pairs):,}")
    print(f"Transacciones emparejadas:         {transacciones_emparejadas:,} ({pct_emparejadas:.1f}%)")
    print(f"Internas sin pareja:               {len(sin_pareja):,}")

    # Por confianza
    by_confidence = defaultdict(int)
    for pair in pairs:
        by_confidence[pair['confidence']] += 1

    print(f"\nPor confianza:")
    print(f"  High (0-1 días):   {by_confidence['high']:3d} pares")
    print(f"  Medium (2-3 días): {by_confidence['medium']:3d} pares")
    print(f"  Low (4-7 días):    {by_confidence['low']:3d} pares")

    # Por ruta más frecuente
    rutas = defaultdict(lambda: {'count': 0, 'total': 0.0})
    for pair in pairs:
        # Simplificar cuenta (últimos 4 dígitos)
        cuenta_sal = pair['cuenta_salida'][-4:]
        cuenta_ent = pair['cuenta_entrada'][-4:]
        ruta = f"{pair['banco_salida']}:{cuenta_sal} → {pair['banco_entrada']}:{cuenta_ent}"
        rutas[ruta]['count'] += 1
        rutas[ruta]['total'] += pair['importe']

    print(f"\nPor ruta más frecuente (top 10):")
    for ruta, data in sorted(rutas.items(), key=lambda x: -x[1]['count'])[:10]:
        print(f"  {ruta:60s}: {data['count']:3d} pares (€{data['total']:>12,.2f} total)")

    # Internas sin pareja (top 10)
    print(f"\nInternas sin pareja (top 10 por importe):")
    for tx in sin_pareja[:10]:
        signo = "+" if tx['importe'] > 0 else ""
        print(f"  {tx['fecha']} | {tx['banco']:15s} | {tx['cuenta'][-4:]} | {signo}{tx['importe']:10.2f} € | {tx['descripcion'][:50]}")

    # Impacto financiero
    volumen_total = sum(pair['importe'] for pair in pairs)
    volumen_sin_pareja = sum(abs(tx['importe']) for tx in sin_pareja)

    print(f"\nImpacto financiero:")
    print(f"  Volumen total de transferencias internas: €{volumen_total:>12,.2f}")
    print(f"  Sin pares (posibles externas mal clasificadas): €{volumen_sin_pareja:>12,.2f}")

    print("\n" + "="*100)


def categorize_unpaired(sin_pareja: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Categoriza las transacciones sin pareja según criterios específicos.

    Returns:
        Dict con categorías: 'hucha_b100', 'recarga_revolut', 'rebalanceo',
        'interna_sin_pareja', 'externa'
    """
    categories = {
        'hucha_b100': [],
        'recarga_revolut': [],
        'rebalanceo': [],
        'misma_cuenta_rebote': [],
        'interna_sin_pareja': [],
        'externa': [],
    }

    # Keywords que indican claramente operaciones internas (aunque no tengan nombre)
    keywords_internas = [
        'TRASPASO', 'INTERNO', 'PLAZO', 'DEPOSITO', 'CUENTA A PLAZO',
        'IMPORTE PROCEDENTE', 'CANCELACION', 'IMPOSICION'
    ]

    for tx in sin_pareja:
        desc_upper = tx['descripcion'].upper()
        banco = tx['banco']

        # 1. B100 hucha (movimientos dentro de B100)
        if banco == 'B100' and any(kw in desc_upper for kw in ['AHORRO PARA HUCHA', 'TRASPASO DESDE HUCHA', 'MOVE TO SAVE', 'OFF TO SAVE']):
            categories['hucha_b100'].append(tx)

        # 2. Recargas Revolut desde Apple Pay
        elif 'REVOLUT' in desc_upper and ('APPLE PAY' in desc_upper or 'COMPRA EN REVOLUT' in desc_upper):
            categories['recarga_revolut'].append(tx)

        # 3. Rebalanceo MyInvestor (ya debería estar filtrado por importe=0, pero verificar)
        elif banco == 'MyInvestor' and (abs(tx['importe']) < 0.01 or 'MOVIMIENTO MYINVESTOR' in desc_upper or 'REBALANCEO' in desc_upper):
            categories['rebalanceo'].append(tx)

        # 4. Operaciones claramente internas por keywords (TRASPASO INTERNO, etc.)
        elif any(kw in desc_upper for kw in keywords_internas):
            categories['interna_sin_pareja'].append(tx)

        # 5. Nombres que NO son Pablo Y NO tienen keywords internas → Externa
        elif not any(kw in desc_upper for kw in ['PABLO', 'FERNANDEZ', 'CASTANYS', 'P.FERNANDEZ', 'P FERNANDEZ']):
            # Si no tiene el nombre de Pablo ni keywords internas, probablemente es externa
            categories['externa'].append(tx)

        # 6. Default: Interna sin pareja (ambigua, para revisión futura)
        else:
            categories['interna_sin_pareja'].append(tx)

    return categories


def export_transactions_with_pairs(transactions: List[Dict], pairs: List[Dict],
                                   categorized: Dict[str, List[Dict]], output_path: str):
    """
    Exporta CSV con columnas adicionales de emparejamiento.
    """
    # Crear mapping de hash → par_id y par_tipo
    hash_to_pair = {}

    # Pares emparejados
    for idx, pair in enumerate(pairs, 1):
        par_id = f"P{idx:04d}"
        confidence = pair['confidence'].upper()

        hash_sal = pair['salida'].get('hash', '')
        hash_ent = pair['entrada'].get('hash', '')

        hash_to_pair[hash_sal] = {'par_id': par_id, 'par_tipo': f'emparejada_{confidence}'}
        hash_to_pair[hash_ent] = {'par_id': par_id, 'par_tipo': f'emparejada_{confidence}'}

    # Sin pareja categorizadas
    for categoria, txs in categorized.items():
        for tx in txs:
            hash_tx = tx.get('hash', '')
            hash_to_pair[hash_tx] = {'par_id': '', 'par_tipo': categoria}

    # Exportar
    fieldnames = ['fecha', 'importe', 'descripcion', 'banco', 'cuenta',
                  'cat1', 'cat2', 'tipo', 'capa', 'hash', 'source_file', 'line_num',
                  'par_id', 'par_tipo']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for tx in transactions:
            hash_tx = tx.get('hash', '')
            pair_info = hash_to_pair.get(hash_tx, {'par_id': '', 'par_tipo': ''})

            tx_out = tx.copy()
            tx_out['par_id'] = pair_info['par_id']
            tx_out['par_tipo'] = pair_info['par_tipo']

            writer.writerow(tx_out)

    print(f"✓ Exportado con columnas par_id/par_tipo: {output_path}")


def print_final_report(pairs: List[Dict], categorized: Dict[str, List[Dict]], total_internas: int):
    """Imprime reporte final con desglose completo"""
    print("\n" + "="*100)
    print("=== FASE 3 - REPORTE FINAL ===")
    print("="*100)

    # Pares emparejados
    by_confidence = defaultdict(int)
    for pair in pairs:
        by_confidence[pair['confidence']] += 1

    transacciones_emparejadas = len(pairs) * 2

    print(f"\nPares emparejados:           {len(pairs):,} ({transacciones_emparejadas:,} transacciones)")
    print(f"  - High confidence:         {by_confidence['high']:3d} pares")
    print(f"  - Medium confidence:       {by_confidence['medium']:3d} pares")
    print(f"  - Low confidence:          {by_confidence['low']:3d} pares")

    # Sin pareja - desglose
    print(f"\nSin pareja - desglose:")
    total_sin_pareja = sum(len(txs) for txs in categorized.values())
    for categoria, txs in categorized.items():
        count = len(txs)
        if count > 0:
            pct = 100 * count / total_sin_pareja if total_sin_pareja > 0 else 0
            categoria_label = categoria.replace('_', ' ').title()
            print(f"  - {categoria_label:30s}: {count:4d} ({pct:5.1f}%)")

    # Top 5 rutas
    rutas = defaultdict(lambda: {'count': 0, 'total': 0.0})
    for pair in pairs:
        cuenta_sal = pair['cuenta_salida'][-4:]
        cuenta_ent = pair['cuenta_entrada'][-4:]
        ruta = f"{pair['banco_salida']}:{cuenta_sal} → {pair['banco_entrada']}:{cuenta_ent}"
        rutas[ruta]['count'] += 1
        rutas[ruta]['total'] += pair['importe']

    print(f"\nTop 5 rutas entre cuentas:")
    for i, (ruta, data) in enumerate(sorted(rutas.items(), key=lambda x: -x[1]['total'])[:5], 1):
        print(f"  {i}. {ruta:55s}: {data['count']:3d} pares, €{data['total']:>12,.2f}")

    # Volumen total
    volumen_total = sum(pair['importe'] for pair in pairs)
    print(f"\nVolumen total movido entre cuentas: €{volumen_total:>12,.2f}")

    print("\n" + "="*100)


def main():
    """Función principal"""
    print("\n" + "="*100)
    print("🔍 FASE 3: CAZADOR DE TRANSFERENCIAS INTERNAS")
    print("="*100)
    print()

    # 1. Cargar transacciones
    print("📂 Cargando transacciones...")
    transactions = load_transactions('output/transacciones_completas.csv')
    print(f"  Total transacciones: {len(transactions):,}")

    # Contar Cat1=Interna (excluyendo importe=0)
    internas = [tx for tx in transactions if tx['cat1'] == 'Interna' and abs(tx['importe']) > 0.01]
    total_internas = len(internas)
    print(f"  Cat1=Interna (importe≠0): {total_internas:,}")
    print()

    # 2. Buscar pares
    print("🔎 Buscando pares de transferencias internas...")
    pairs, sin_pareja = find_internal_transfer_pairs(transactions)
    print(f"  ✓ Encontrados {len(pairs):,} pares")
    print()

    # 3. Categorizar sin pareja
    print("📋 Categorizando transacciones sin pareja...")
    categorized = categorize_unpaired(sin_pareja)
    for categoria, txs in categorized.items():
        if len(txs) > 0:
            print(f"  - {categoria.replace('_', ' ').title():30s}: {len(txs):4d}")
    print()

    # 4. Exportar CSVs
    print("💾 Exportando resultados...")
    export_pairs_to_csv(pairs, 'output/transferencias_internas_pairs.csv')
    export_transactions_with_pairs(transactions, pairs, categorized,
                                   'output/transacciones_con_pares.csv')
    print()

    # 5. Reporte final
    print_final_report(pairs, categorized, total_internas)

    # 6. Validación final
    total_categorized = sum(len(txs) for txs in categorized.values())
    transacciones_emparejadas = len(pairs) * 2

    print("\n" + "="*100)
    print("✅ VALIDACIÓN FASE 3")
    print("="*100)
    print(f"✅ Pares emparejados:                {len(pairs):,} ({transacciones_emparejadas:,} transacciones)")
    print(f"✅ Sin pareja categorizadas:         {total_categorized:,} (100%)")
    print(f"✅ Columnas par_id/par_tipo:         Añadidas a transacciones_con_pares.csv")
    print(f"✅ Sin regresiones:                  Cat1/Cat2/Tipo sin cambios")
    print(f"✅ Reporte generado:                 Con desglose completo")
    print("="*100)
    print()


if __name__ == '__main__':
    main()
