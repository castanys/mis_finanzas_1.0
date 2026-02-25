"""
Post-procesamiento: Merchants Recurrentes
Sustituye Cat2="Otros" por el nombre del merchant cuando es muy recurrente (15+ transacciones).
"""
import re
from collections import defaultdict
from typing import List, Dict, Optional


def extract_merchant(descripcion: str) -> Optional[str]:
    """
    Extrae el nombre del establecimiento de la descripción.

    Args:
        descripcion: Descripción de la transacción

    Returns:
        Nombre del merchant o None si no se puede extraer
    """
    # Normalizar espacios rotos (ej. "TARJET A" → "TARJETA")
    descripcion_norm = re.sub(r'\s+', ' ', descripcion).strip()
    
    patterns = [
        # COMPRA EN X, CON LA TARJETA (estándar)
        r'COMPRA EN (.+?),?\s*(?:CON LA TARJETA|TARJETA)',
        # Apple Pay: COMPRA EN X
        r'Apple pay:\s*COMPRA EN (.+?),?\s*(?:CON LA TARJETA|TARJETA)',
        # REGULARIZACION COMPRA EN X (para txs antiguas)
        r'REGULARIZACION\s+COMPRA EN (.+?),?\s*(?:CON LA TARJETA|TARJETA)',
        # PAGO RECIBO DE X, NUM (ej. servicios)
        r'PAGO RECIBO DE (.+?),\s*NUM',
        # RECIBO X (genérico)
        r'RECIBO\s+(.+?)(?:\s+Nº|\s*$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, descripcion_norm, re.IGNORECASE)
        if match:
            merchant = match.group(1).strip()
            # Limpiar números de tarjeta (10+ dígitos consecutivos)
            merchant = re.sub(r'\d{10,}', '', merchant).strip()
            # Eliminar "EL 20XX-XX-XX" (fechas)
            merchant = re.sub(r'\s+EL\s+\d{4}-\d{2}-\d{2}', '', merchant, flags=re.IGNORECASE).strip()
            if merchant:
                return merchant

    return None


def normalize_merchant(merchant: str) -> str:
    """
    Normaliza el nombre del merchant para agrupar variantes.

    Args:
        merchant: Nombre raw del merchant

    Returns:
        Nombre normalizado
    """
    # Normalizar PayPal (múltiples variantes)
    if 'PAYPAL' in merchant.upper():
        return 'PayPal'

    # Normalizar A LA BARRA (variantes con/sin GASTROBAR)
    if 'A LA BARRA' in merchant.upper():
        return 'A la Barra'

    # Por defecto, capitalizar primera letra de cada palabra
    return merchant.title()


def build_recurrent_dict(records: List[Dict], threshold: int = 15) -> Dict[str, str]:
    """
    Construye diccionario de merchants recurrentes.
    Solo merchants que aparecen threshold+ veces.

    Args:
        records: Lista de registros de transacciones
        threshold: Umbral mínimo de apariciones (default: 15)

    Returns:
        Diccionario {merchant_raw: merchant_normalizado}
    """
    # Contar apariciones por merchant normalizado
    merchant_counts = defaultdict(list)

    for r in records:
        cat2 = r.get('cat2', '').strip()
        if cat2 == 'Otros':
            merchant = extract_merchant(r.get('descripcion', ''))
            if merchant:
                merchant_norm = normalize_merchant(merchant)
                merchant_counts[merchant_norm].append(merchant)

    # Filtrar recurrentes (threshold+)
    recurrent_dict = {}
    for merchant_norm, raw_variants in merchant_counts.items():
        if len(raw_variants) >= threshold:
            # Mapear todas las variantes raw al nombre normalizado
            for raw in set(raw_variants):
                recurrent_dict[raw] = merchant_norm

    return recurrent_dict


def apply_recurrent_merchants(records: List[Dict], threshold: int = 15) -> List[Dict]:
    """
    Post-procesamiento: sustituye Cat2="Otros" por merchant name si es recurrente.

    Args:
        records: Lista de registros de transacciones
        threshold: Umbral mínimo de apariciones (default: 15)

    Returns:
        Lista de registros con Cat2 actualizado
    """
    # Construir diccionario de recurrentes
    recurrent_dict = build_recurrent_dict(records, threshold)

    print(f"✓ Identificados {len(set(recurrent_dict.values()))} merchants recurrentes ({threshold}+ tx)")

    # Aplicar sustitución
    updated = 0
    for r in records:
        cat2 = r.get('cat2', '').strip()
        if cat2 == 'Otros':
            merchant = extract_merchant(r.get('descripcion', ''))
            if merchant and merchant in recurrent_dict:
                r['cat2'] = recurrent_dict[merchant]
                updated += 1

    if updated > 0:
        print(f"✓ Actualizadas {updated} transacciones con merchants recurrentes")

    return records


def print_recurrent_summary(records: List[Dict], threshold: int = 15):
    """
    Imprime resumen de merchants recurrentes identificados.

    Args:
        records: Lista de registros de transacciones
        threshold: Umbral mínimo de apariciones
    """
    recurrent_dict = build_recurrent_dict(records, threshold)

    # Contar por merchant normalizado
    merchant_counts = defaultdict(int)
    for merchant_norm in recurrent_dict.values():
        merchant_counts[merchant_norm] += 1

    print("\n" + "="*80)
    print(f"MERCHANTS RECURRENTES ({threshold}+ transacciones)")
    print("="*80)

    for merchant, count in sorted(merchant_counts.items(), key=lambda x: -x[1]):
        # Calcular total gastado
        total = sum(float(r['importe']) for r in records
                   if r.get('cat2', '').strip() == merchant)
        print(f"  {merchant:50s}: {count:3d} tx | Total: {total:10.2f} €")

    print("="*80)
