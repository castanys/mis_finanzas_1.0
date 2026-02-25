"""
Capa 4: Token Heurístico
Busca tokens discriminantes en la descripción.
"""
import re


# Cada regla: (token, Cat1, Cat2)
TOKEN_RULES = [
    # Restauración (tokens genéricos)
    ("BAR", "Restauración", "Otros"),  # word boundary se aplica en la búsqueda
    ("RESTAURANTE", "Restauración", "Otros"),
    ("CAFETERIA", "Restauración", "Cafeterías"),
    ("CERVECERIA", "Restauración", "Cervecería"),
    ("CHURRERIA", "Restauración", "Churrería"),
    ("TABERNA", "Restauración", "Taberna"),
    ("PIZZ", "Restauración", "Pizzería"),
    ("ASADOR", "Restauración", "Asador"),
    ("PASTELERIA", "Restauración", "Pastelería"),
    ("HAMBURGUES", "Restauración", "Hamburguesería"),
    ("KEBAB", "Restauración", "Kebab"),
    ("GASTROBAR", "Restauración", "Otros"),
    ("TAPAS", "Restauración", "Tapería"),
    ("PUB", "Restauración", "Pub"),

    # Recibos (genérico - solo si tiene RECIBO en desc)
    ("RECIBO", "Recibos", "Otros"),

    # Seguros
    ("SEGURO", "Seguros", ""),

    # Deportes
    ("PADEL", "Deportes", "Pádel"),
    ("GIMNASIO", "Deportes", "Gimnasio"),

    # Comisiones
    ("COMISION", "Comisiones", ""),
    ("COMISIÓN", "Comisiones", ""),
    ("CUSTODIA", "Comisiones", "Custodia"),

    # Intereses
    ("INTERESES", "Intereses", ""),
    ("PERIODO", "Intereses", ""),  # MyInvestor intereses periódicos
    ("INTEREST PAYMENT", "Intereses", ""),  # Trade Republic

    # Cashback
    ("SAVEBACK", "Cashback", ""),  # Trade Republic
    ("CASH REWARD", "Cashback", ""),  # Trade Republic

    # Devoluciones
    ("DEVOLUCION", "Devoluciones", ""),
    ("DEVOLUCIÓN", "Devoluciones", ""),

    # Renta Variable
    ("ISHARES", "Renta Variable", "Compra"),
    ("VANGUARD", "Renta Variable", "Compra"),
    ("MSCI", "Renta Variable", "Compra"),
    ("S&P 500", "Renta Variable", "Compra"),

    # Divisas (Revolut)
    ("EXCHANGED", "Divisas", ""),
    ("EXCHANGE", "Divisas", ""),

    # Liquidación
    ("LIQUIDACION", "Comisiones", ""),  # Liquidación de cuenta

    # Suscripciones
    ("TIDAL", "Suscripciones", "Música"),  # Tidal streaming

    # Transferencias a Revolut (recarga)
    ("REVOLUT RAMP", "Interna", ""),
    ("REVOLUT**", "Interna", ""),

    # Eventos
    ("TCB 2025 GIRA", "Ocio y Cultura", "Eventos"),

    # Salud
    ("CLINICA ORTONOVA", "Salud y Belleza", "Clínica dental"),

    # Compras específicas
    ("VENTA GARCERAN", "Compras", "Otros"),
    ("RESERVES.PALAUDEGEL.AD", "Viajes", "Alojamiento"),
    ("ARCE ASISTENCIA", "Transporte", "Taller"),
]


def match_bank_specific(descripcion, banco, importe):
    """
    Reglas específicas por banco para casos especiales.

    Args:
        descripcion: Descripción de la transacción
        banco: Nombre del banco
        importe: Importe de la transacción

    Returns:
        Tupla (Cat1, Cat2) si hay match, None si no
    """
    desc_upper = descripcion.upper()
    desc_lower = descripcion.lower()

    # MyInvestor: "Movimiento sin concepto" o descripción vacía
    if banco == "MyInvestor":
        if "MOVIMIENTO SIN CONCEPTO" in desc_upper or descripcion.strip() == "":
            # Si importe = 0 → Rebalanceo de fondos
            try:
                importe_float = float(importe)
                if abs(importe_float) < 0.01:  # Importe = 0
                    return ("Renta Variable", "Rebalanceo")
                else:
                    # Importe ≠ 0 → Interna (compra/venta fondos)
                    return ("Interna", "")
            except (ValueError, TypeError):
                return ("Interna", "")

    # Abanca: "Movimiento Abanca" → siempre Interna
    if banco == "Abanca":
        if "MOVIMIENTO ABANCA" in desc_upper or "SIN CONCEPTO" in desc_upper:
            return ("Interna", "")

    # Mediolanum: descripción "NA" o vacía → Interna
    if banco == "Mediolanum":
        if descripcion.strip() in ["NA", "", "N/A"]:
            return ("Interna", "")

    return None


def match_token(descripcion):
    """
    Busca tokens heurísticos en la descripción.

    Args:
        descripcion: Descripción de la transacción

    Returns:
        Tupla (Cat1, Cat2) si hay match, None si no
    """
    desc_upper = descripcion.upper()

    for token, cat1, cat2 in TOKEN_RULES:
        token_upper = token.upper()

        # Casos especiales que requieren word boundary
        if token in ["BAR", "PUB"]:
            if re.search(r'\b' + re.escape(token_upper) + r'\b', desc_upper):
                return (cat1, cat2)
        else:
            # Búsqueda normal (substring)
            if token_upper in desc_upper:
                return (cat1, cat2)

    return None
