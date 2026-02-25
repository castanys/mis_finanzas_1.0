"""
Normalización centralizada de descripciones.

Esta función se llama UNA vez antes de la Capa 1 del clasificador
para eliminar prefijos genéricos que pueden romper el exact match.

La descripción ORIGINAL se preserva en el campo 'descripcion'.
La descripción NORMALIZADA se usa solo para clasificar.
"""


def normalize_description(descripcion: str) -> str:
    """
    Normaliza una descripción removiendo prefijos genéricos.

    Prefijos removidos (en orden):
    1. 'Apple Pay: COMPRA EN ' (más específico primero)
    2. 'Apple pay: COMPRA EN ' (variante con minúscula)
    3. 'COMPRA EN '
    4. 'Transacción '

    Args:
        descripcion: Descripción original

    Returns:
        Descripción normalizada (sin prefijos genéricos)

    Ejemplos:
        >>> normalize_description('Transacción MERCADONA')
        'MERCADONA'
        >>> normalize_description('Apple Pay: COMPRA EN LIDL, CON LA TARJETA...')
        'LIDL, CON LA TARJETA...'
        >>> normalize_description('COMPRA EN Amazon')
        'Amazon'
    """
    if not descripcion:
        return descripcion

    # Orden importante: más específico primero
    prefixes = [
        'Apple Pay: COMPRA EN ',
        'Apple pay: COMPRA EN ',
        'COMPRA EN ',
        'Transacción ',
    ]

    desc_normalized = descripcion
    for prefix in prefixes:
        if desc_normalized.startswith(prefix):
            desc_normalized = desc_normalized[len(prefix):].strip()
            break  # Solo remover el primer match

    return desc_normalized
