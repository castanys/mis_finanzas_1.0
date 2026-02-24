"""
Extracción de nombres de merchants según el formato del banco.
"""
import re


MERCHANT_EXTRACTORS = {
    # Openbank: "COMPRA EN <MERCHANT>, CON LA TARJETA..."
    # También: "Apple Pay: COMPRA EN <MERCHANT>, CON LA TARJETA..."
    "Openbank": r'(?:Apple [Pp]ay: )?COMPRA EN ([^,]+),',

    # Trade Republic: "Transacción <MERCHANT> con tarjeta"
    "Trade Republic": r'Transacción (.+?) con tarjeta',

    # Revolut: merchant name IS the description (for gastos)
    "Revolut": None,  # use description directly

    # Mediolanum: varies, use description directly
    "Mediolanum": None,

    # B100: varies
    "B100": None,

    # Abanca: "767003239036 <MERCHANT> \<CIUDAD>\..."
    "Abanca": r'\d+ (.+?)\\',
}


def extract_merchant(descripcion, banco):
    """
    Extrae el nombre del merchant de la descripción según el formato del banco.

    Args:
        descripcion: Descripción de la transacción
        banco: Nombre del banco

    Returns:
        Nombre del merchant extraído, o None si no se pudo extraer
    """
    if banco not in MERCHANT_EXTRACTORS:
        return None

    pattern = MERCHANT_EXTRACTORS[banco]

    # Si no hay patrón, usar descripción completa
    if pattern is None:
        return descripcion

    # Buscar patrón
    match = re.search(pattern, descripcion)
    if match:
        return match.group(1).strip()

    # Trade Republic: fallback a descripción completa si el patrón no hace match
    # Esto permite capturar restaurantes con descripción pura (ej: "BIERGARTEN")
    if banco == "Trade Republic":
        return descripcion

    return None
