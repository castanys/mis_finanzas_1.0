"""
Orquestador de enriquecimiento Cat2.
Extrae merchant → busca en caché → busca en Google Places → mapea → asigna Cat2.
"""
import re
from typing import Optional, List, Dict


def extract_merchant_name(descripcion: str, banco: str) -> Optional[str]:
    """
    Extrae el nombre del merchant de la descripción bancaria.

    Args:
        descripcion: Descripción de la transacción
        banco: Nombre del banco

    Returns:
        Nombre del merchant o None si no se puede extraer
    """
    if banco == "Openbank":
        # "COMPRA EN MERCADONA PROLONGACION AN, CON LA TARJETA..."
        # "Apple pay: COMPRA EN MERCADONA..., CON LA TARJETA..."
        match = re.search(r'(?:Apple [Pp]ay: )?COMPRA EN ([^,]+),', descripcion)
        if match:
            return match.group(1).strip()

    elif banco == "Trade Republic":
        # "Transacción MERCHANT con tarjeta"
        match = re.search(r'Transacci[oó]n (.+?) con tarjeta', descripcion)
        if match:
            return match.group(1).strip()

    elif banco == "Abanca":
        # "767003239036 MERCHANT \\CIUDAD\\..."
        match = re.search(r'\d+ (.+?)\\\\', descripcion)
        if match:
            return match.group(1).strip()

    # Fallback: usar descripción completa (limpia)
    return descripcion.strip()


def identify_candidates(transactions: List[Dict]) -> List[Dict]:
    """
    Identifica transacciones candidatas para enriquecimiento.

    Criterios:
    - Cat1 de comercio físico (Restauración, Compras, Alimentación, etc.)
    - Cat2 vacío o "Otros"

    Args:
        transactions: Lista de transacciones

    Returns:
        Lista de transacciones candidatas
    """
    TARGET_CAT1 = {
        'Restauración',
        'Compras',
        'Alimentación',
        'Ropa y Calzado',
        'Transporte',
        'Salud y Belleza',
        'Ocio y Cultura',
        'Viajes',
    }

    candidates = []
    for tx in transactions:
        cat1 = tx.get('cat1', '')
        cat2 = tx.get('cat2', '')

        if cat1 in TARGET_CAT1 and (not cat2 or cat2 == 'Otros'):
            candidates.append(tx)

    return candidates


def extract_unique_merchants(candidates: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Extrae merchants únicos de las candidatas.

    Args:
        candidates: Lista de transacciones candidatas

    Returns:
        Dict {merchant_name: [transacciones con ese merchant]}
    """
    merchants = {}

    for tx in candidates:
        merchant = extract_merchant_name(tx.get('descripcion', ''), tx.get('banco', ''))
        if merchant:
            if merchant not in merchants:
                merchants[merchant] = []
            merchants[merchant].append(tx)

    return merchants


def enrich_cat2(
    transactions: List[Dict],
    cache,
    api_key: Optional[str] = None,
    dry_run: bool = False
) -> tuple:
    """
    Enriquece Cat2 de transacciones usando Google Places API.

    Args:
        transactions: Lista de transacciones
        cache: Instancia de MerchantCache
        api_key: API key de Google Places (requerida si no es dry_run)
        dry_run: Si True, solo muestra qué haría sin llamar a la API

    Returns:
        Tupla (transactions_actualizadas, stats)
    """
    from .google_places import search_places_by_scope
    import time

    # 1. Identificar candidatas
    candidates = identify_candidates(transactions)
    print(f"Candidatas para enriquecimiento: {len(candidates)}")

    # 2. Extraer merchants únicos
    merchants_dict = extract_unique_merchants(candidates)
    unique_merchants = list(merchants_dict.keys())
    print(f"Merchants únicos a consultar: {len(unique_merchants)}")

    if dry_run:
        print("\n=== MODO DRY-RUN ===")
        print("No se llamará a la API de Google Places.")
        print(f"Se consultarían {len(unique_merchants)} merchants únicos.")
        print("\nTop 20 merchants a consultar:")
        for i, merchant in enumerate(unique_merchants[:20], 1):
            tx_count = len(merchants_dict[merchant])
            print(f"  {i}. {merchant} ({tx_count} tx)")
        return transactions, {
            'candidates': len(candidates),
            'unique_merchants': len(unique_merchants),
            'enriched': 0,
            'api_calls': 0,
        }

    if not api_key:
        raise ValueError("API key requerida para modo no-dry-run")

    # 3. Para cada merchant único: buscar en caché o API
    api_calls = 0
    cache_hits = 0

    for i, merchant in enumerate(unique_merchants, 1):
        print(f"[{i}/{len(unique_merchants)}] {merchant}...", end=' ', flush=True)

        # Check caché
        cached = cache.get_any_location(merchant)
        if cached:
            print(f"✓ caché ({cached['confidence']})")
            cache_hits += 1
            continue

        # Buscar por ámbitos
        result = search_places_by_scope(merchant, api_key)

        # Guardar en caché
        cache.save(merchant, result['search_location'], result)

        confidence = result['confidence']
        cat2 = result['mapped_cat2'] or 'N/A'
        print(f"✓ {result['search_location'][:4]} ({confidence}) → {cat2}")

        api_calls += 1

        # Rate limiting
        time.sleep(0.1)

    # 4. Aplicar Cat2 enriquecido
    enriched_count = 0
    for tx in candidates:
        merchant = extract_merchant_name(tx.get('descripcion', ''), tx.get('banco', ''))
        if not merchant:
            continue

        cached = cache.get_any_location(merchant)
        if cached and cached['mapped_cat2'] and cached['confidence'] != 'no_result':
            tx['cat2'] = cached['mapped_cat2']
            enriched_count += 1

    print(f"\n✅ Transacciones enriquecidas: {enriched_count}/{len(candidates)}")
    print(f"📊 Cache hits: {cache_hits}, API calls: {api_calls}")

    return transactions, {
        'candidates': len(candidates),
        'unique_merchants': len(unique_merchants),
        'enriched': enriched_count,
        'api_calls': api_calls,
        'cache_hits': cache_hits,
    }
