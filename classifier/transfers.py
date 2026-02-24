"""
Capa 3: Transfer Detection
Detecta transferencias (internas, externas, Bizum, cuenta común).
"""
import re


TRANSFER_KEYWORDS = [
    "TRANSFERENCIA", "TRASNFERENCIA", "TRANSF.", "TRANSF ", "TRANSF/", 
    "TRANS /", "TRANS ", "TRASPASO", "STICHTING", "TRANSFER",
    "TRANSF OTR"
]


def is_bizum(descripcion, banco):
    """
    Detecta si es un Bizum.

    Args:
        descripcion: Descripción de la transacción
        banco: Nombre del banco

    Returns:
        True si es Bizum, False si no
    """
    desc_upper = descripcion.upper()

    if "BIZUM" in desc_upper:
        return True

    # Trade Republic: Bizum via "Outgoing/Incoming transfer for <nombre> (+34-...)"
    # Formato: "Outgoing transfer for NOMBRE (+34-XXX)" o "Incoming transfer from NOMBRE (+34-XXX)"
    if banco == "Trade Republic" and re.search(r'\(\+34-\d+\)', descripcion):
        return True

    # Trade Republic: Patrón genérico for/from <Nombre> (sin teléfono)
    # Ejemplo: "Outgoing transfer for Diego Bruno", "Incoming transfer from JuanCar Bombero"
    # Nota: Las transferencias internas usan "Outgoing/Incoming transfer for/from NOMBRE COMPLETO"
    # Los Bizums usan "Outgoing transfer for/from <Nombre corto/apodo>"
    if banco == "Trade Republic":
        # Patrón: (Outgoing|Incoming) transfer (for|from) <Nombre> (sin números de teléfono)
        # Este patrón captura Bizums sin teléfono
        if re.search(r'(?:Outgoing|Incoming)\s+transfer\s+(?:for|from)\s+[A-Za-záéíóúñÁÉÍÓÚÑ\s]+$', descripcion, re.IGNORECASE):
            return True

    # Personas conocidas que usan Bizum (confirmadas por Pablo)
    bizum_people = [
        "JUAN CARLOS DE JUAN",
        "DIEGO BRUNO VELASCO",
        "CHRISTOPHER FREDERICK EDEN",
        "CHRISTOPHER EDEN",
        "JESUS MUNOZ URREA",
        "JESÚS MUÑOZ URREA",
    ]
    if any(person in desc_upper for person in bizum_people):
        return True

    return False


def is_cuenta_comun(descripcion, banco):
    """
    Detecta transferencias de/hacia cuenta común.

    Args:
        descripcion: Descripción de la transacción
        banco: Nombre del banco

    Returns:
        Tupla (Cat1, Cat2) si es cuenta común, None si no
    """
    desc_upper = descripcion.upper()

    # Yolanda Arroyo Varo = ex-pareja, transferencias de cuenta común
    if "ARROYO VARO" in desc_upper:
        if "RECIBIDA" in desc_upper:
            return ("Cuenta Común", "Entrante")
        return ("Cuenta Común", "")

    return None


def is_internal_transfer(descripcion, banco, importe):
    """
    Detecta si es una transferencia interna.

    Args:
        descripcion: Descripción de la transacción
        banco: Nombre del banco
        importe: Importe de la transacción

    Returns:
        True si es transferencia interna, False si no
    """
    desc_upper = descripcion.upper()

    # Patrones explícitos de transferencia interna
    internal_patterns = [
        "TRASPASO INTERNO",
        "ORDEN TRASPASO INTERNO",
        "TRANSFERENCIA INTERNA NOMINA",  # Abanca - transferencia de nómina a otra cuenta
        "MOVIMIENTO MYINVESTOR",
        "RECARGA DE APPLE PAY",
        "RECARGA DE *",
        "UNA RECARGA DE",
        "TRANSFERENCIA ENVIADA",  # B100
        "APORTACION A MI CARTERA",  # MyInvestor
        "TRANSFERENCIA DESDE MYINVESTOR",  # MyInvestor
    ]
    if any(pat in desc_upper for pat in internal_patterns):
        return True

    # Abanca: "SIN CONCEPTO" → siempre interna en datos históricos
    if banco == "Abanca" and "SIN CONCEPTO" in desc_upper:
        return True

    # Nombre propio del titular (CASTANYS) pero NO familiares
    if "CASTANYS" in desc_upper:
        # Familiares → NO es interna
        family = ["JUAN ANTONIO", "LAURA FERNANDEZ-CASTANYS", "ALEJANDRO"]
        if any(name in desc_upper for name in family):
            return False  # Es externa
        # DeGiro/Stichting → NO es interna (inversión)
        if "STICHTING" in desc_upper or "GIRO" in desc_upper:
            return False
        return True

    # B100: transferencias del titular
    if banco == "B100" and "FERNANDEZ CASTANYS" in desc_upper:
        return True

    # Mediolanum: "Transf.de FERNANDEZ CASTANYS"
    if banco == "Mediolanum" and "FERNANDEZ CASTANYS" in desc_upper:
        return True

    # Revolut: recargas
    if banco == "Revolut" and ("APPLE PAY" in desc_upper or "RECARGA" in desc_upper):
        return True

    # Bankinter: transferencias del titular (nombre propio truncado, con variaciones y typos)
    if banco == "Bankinter":
        # Patrones exactos
        bankinter_own_patterns = [
            "PABLO FERNANDEZ-CASTANY",
            "PABLO FERNANDEZ CASTANY",
            "PABLO FERNANDEZ-CASTANYS",  # variante con 's'
            "P. FERNANDEZ",
            "CUENTA PROFESIONAL",        # TRANSF INT /Cuenta Profesional
            "CUENTA CORRIENTE DIGITA",   # TRANS /Cuenta Corriente Digita
            "TRANSF OTRAS /PABLO FERNANDEZ",  # variante sin guion
        ]
        if any(pat in desc_upper for pat in bankinter_own_patterns):
            return True
        
        # Patrón flexible para nombres con typos/truncamientos/acentos: PABLO FERNANDEZ* (sin CASTANY completo)
        # Captura: "PABLO FERNANDEZ-CASTAN" (falta 'y'), "PABLO FERNÁNDEZ-Castan" (acento+typo), "PABLO FERNANDEZ-Castna" (typo)
        import re
        if re.search(r'PABLO\s+FERN[ÁA]NDEZ', desc_upper, re.IGNORECASE):
            # Asegurar que NO es una persona tercera (MARIA, YOLANDA, etc.)
            if not any(name in desc_upper for name in ["MARIA", "YOLANDA", "ALEJANDRO", "JUAN", "CRUSOL"]):
                return True

    # Openbank: transferencias donde el destino es otra cuenta propia
    # Patrón: "TRANSFERENCIA A FAVOR DE FERNANDEZ CASTANYS ORTIZ DE VILLAJOS PAB"
    if banco == "Openbank" and "FERNANDEZ CASTANYS ORTIZ DE VILLAJOS PAB" in desc_upper:
        return True

    # Concepto no especificado: mayoritariamente interna (24 de 29 = 83%)
    if "CONCEPTO NO ESPECIFICADO" in desc_upper:
        return True  # Marcar como interna por defecto

    # Trade Republic: transferencias a/desde Pablo o cuentas propias
    # Formato: "Incoming/Outgoing transfer from/for FERNANDEZ CASTANYS ORTIZ DE VILLAJOS PABLO"
    if banco == "Trade Republic":
        if "FERNANDEZ CASTANYS ORTIZ DE VILLAJOS PABLO" in desc_upper or \
           "FERNANDEZ-CASTANYS ORTIZ DE VILLAJOS PABLO" in desc_upper or \
           "PABLO FERNANDEZ-CASTANYS" in desc_upper or \
           "PABLO FERNANDEZ CASTANYS" in desc_upper:
            return True

        # También cuentas propias por IBAN (desde cuentas.json)
        own_ibans = [
            "ES3600730100550435513660",  # Openbank
            "ES8015860001420977164411",  # Trade Republic mismo
            "ES2501865001680510084831",  # Mediolanum
            "ES6001288700180105753633",  # Bankinter (cta cerrada oct 2024)
            "ES6001288700160105752044",  # Bankinter (cta cerrada sep 2024)
        ]
        if any(iban in descripcion for iban in own_ibans):
            return True

    return False


def is_transfer(descripcion):
    """
    Detecta si la descripción contiene keywords de transferencia.

    Args:
        descripcion: Descripción de la transacción

    Returns:
        True si contiene keywords de transferencia, False si no
    """
    desc_upper = descripcion.upper()
    return any(kw in desc_upper for kw in TRANSFER_KEYWORDS)


def is_loan_alejandro(descripcion):
    """
    Detecta si es una transferencia a/desde Alejandro (hermano).

    Args:
        descripcion: Descripción de la transacción

    Returns:
        True si es transferencia a/desde Alejandro, False si no
    """
    desc_upper = descripcion.upper()

    # Patrones para Alejandro Fernández Castanys
    alejandro_patterns = [
        "ALEJANDRO FERNANDEZ CASTANYS",
        "ALEJANDRO FERNANDEZ-CASTANYS",
        "ALEJANDRO FERNÁNDEZ CASTANYS",
        "ALEJANDRO FERNÁNDEZ-CASTANYS",
    ]

    return any(pat in desc_upper for pat in alejandro_patterns)


def detect_transfer(descripcion, banco, importe):
    """
    Detecta el tipo de transferencia.

    Args:
        descripcion: Descripción de la transacción
        banco: Nombre del banco
        importe: Importe de la transacción

    Returns:
        Tupla (Cat1, Cat2) si es transferencia, None si no
    """
    # 0. REGLA B100: Traspasos internos Health/Save/Ahorro
    # Banco puede ser "B100" (parser B100) o "Abanca" (parser Enablebanking)
    if banco in ("B100", "Abanca"):
        desc_upper = descripcion.upper()
        b100_internal_keywords = [
            "HEALTH", "SAVE", "TRASPASO", "AHORRO PARA HUCHA", "MOVE TO SAVE",
            "APERTURA CUENTA", "OFF TO SAVE"
        ]
        if any(kw in desc_upper for kw in b100_internal_keywords):
            return ("Interna", "")

    # 1. Bizum
    if is_bizum(descripcion, banco):
        return ("Bizum", "")

    # 2. Préstamos a/desde Alejandro (hermano) - solo si NO es Bizum
    if is_loan_alejandro(descripcion):
        return ("Préstamos", "Préstamo hermano")

    # 3. Cuenta común
    cc = is_cuenta_comun(descripcion, banco)
    if cc:
        return cc

    # 4. Interna
    if is_internal_transfer(descripcion, banco, importe):
        return ("Interna", "")

    # 5. Externa (si tiene keywords de transferencia)
    if is_transfer(descripcion):
        return ("Externa", "")

    return None
