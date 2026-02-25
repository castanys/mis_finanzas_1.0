"""
Normalización de descripciones de Trade Republic para generación de hash.
Esto previene duplicados entre CSV y PDF con descripciones diferentes.

CASOS A MANEJAR:
1. CSV vs PDF con prefijos distintos: "Otros ", "Transferencia ", "Interés ", "Bonificación ", "Otros t "
2. Sufijos ruidosos: "null", " con tarjeta", "markup: X.XX%", "Operar ", "quantity: X.XXXXX"
3. IBAN en paréntesis al final: " (ES...)"
4. Espacios extra
5. Tipo de cambio (exchange rate) en transacciones FX — truncar para evitar duplicados CSV/PDF

Ejemplos de normalización:
- CSV: "Savings plan execution IE00B5BMR087 iShares VII plc - iShares Core S&P"
- PDF: "Otros Savings plan execution IE00B5BMR087 iShares VII plc - iShares Core Operar S&P 500 UCITS ETF USD (Acc), quantity: 0.017378"
- Normalizado: "Savings plan execution IE00B5BMR087 iShares VII plc - iShares Core S&P"

- CSV (variante): "Otros Transacción GITHUB, INC., 10,00 $, exchange rate: 0,861, ECB rate: 0,859549596, con tarjeta markup: 0,16874 %"
- PDF (misma tx): "GITHUB, INC., 10,00 $, exchange rate: 0,861, ECB rate: 0,859549596,"
- Normalizado: "GITHUB, INC., 10,00 $" (todo lo demás es ruido FX)

- CSV: "MERCADONA PROLONGACION AN"
- PDF: "Otros Transacción MERCADONA PROLONGACION ANnull con tarjeta"
- Normalizado: "Transacción MERCADONA PROLONGACION AN"
"""
import re

def normalize_tr_description_for_hash(descripcion: str) -> str:
    """
    Normaliza descripción de Trade Republic para hash único.
    
    Elimina ruido que varía entre formatos CSV/PDF pero representa la misma transacción.
    
    PATRONES TRATADOS:
    1. Prefijos que varían entre CSV y PDF:
       - CSV puede añadir: "Transferencia ", "Transferencia t ", "Interés ", "Interés t ", "Otros ", "Otros t ", "Bonificación "
       - PDF puede añadir: mismos prefijos
       - AMBOS se normalizan a la forma sin prefijo
    
    2. Verbos completos vs preposiciones (CSV es más verboso):
       - "Outgoing transfer for X" (CSV) → "for X" (canónico)
       - "Incoming transfer from X" (CSV) → "from X" (canónico)
       - "Your interest payment" (PDF) vs "Interest payment" (CSV) → "interest payment" (canónico)
    
     3. Truncado de tipo de cambio en transacciones FX:
        - CSV y PDF describen el tipo de cambio de formas distintas pero inconsistentes
        - Se trunca desde ", exchange rate:" hacia el final
        - Preserva: "MERCHANT, IMPORTE_DIVISA" (suficiente para identificación única)
     
     4. Sufijos ruidosos:
        - "null", " con tarjeta", "quantity: X.XXXXX", IBAN en paréntesis
     
     Args:
        descripcion: Descripción original
        
    Returns:
        Descripción normalizada para hash
    """
    if not descripcion:
        return descripcion
    
    normalized = descripcion
    
    # ===== FASE 1: Eliminar prefijos de tipo transacción (aplica a CSV y PDF) =====
    # CRÍTICO: Eliminar TODOS los prefijos, no solo el primero
    # porque CSV puede tener: "Transferencia t X" o "Interés t X" etc
    prefixes = [
        'Otros t ',      
        'Otros ',        
        'Transferencia t ',  
        'Transferencia ', 
        'Interés t ',    # NUEVO: prefijo que aparece en CSV
        'Interés ',      
        'Bonificación ', 
    ]
    
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            # NO romper — continuar eliminando si hay otro prefijo
    
    # ===== FASE 2: Canonicalizar frases verbales a formas cortas =====
    # CSV es más verboso que PDF. Canonicalizar a la forma más corta
    
    # "Outgoing transfer for X" → "for X"
    if normalized.startswith('Outgoing transfer for '):
        normalized = 'for ' + normalized[len('Outgoing transfer for '):]
    
    # "Incoming transfer from X" → "from X"
    if normalized.startswith('Incoming transfer from '):
        normalized = 'from ' + normalized[len('Incoming transfer from '):]
    
    # "Your interest payment" → "interest payment" (PDF dice "Your", CSV dice "Interest")
    normalized = normalized.replace('Your interest payment', 'interest payment')
    
    # "Interest payment" → "interest payment" (normalizar caso)
    if normalized.startswith('Interest payment'):
        normalized = 'interest payment' + normalized[len('Interest payment'):]
    
    # ===== FASE 3: Limpiar "Transacción " (PDF de tarjeta) =====
    if normalized.startswith('Transacción '):
        normalized = normalized[len('Transacción '):]
    
    # ===== FASE 3.5: Truncar tipo de cambio en transacciones FX =====
    # CRÍTICO para evitar duplicados CSV vs PDF en Trade Republic
    # CSV: "GITHUB, INC., 10,00 $, exchange rate: 0,861, ECB rate: 0,859549596, con tarjeta markup: 0,16874 %"
    # PDF: "GITHUB, INC., 10,00 $, exchange rate: 0,861, ECB rate: 0,859549596,"
    # Los datos de FX (ECB rate, markup, con tarjeta) varían entre formatos pero representan la misma transacción.
    # Solución: truncar desde ", exchange rate:" en adelante.
    # Resultado: "GITHUB, INC., 10,00 $" (merchant + importe en divisa = identificación única)
    normalized = re.sub(r',\s*exchange rate:.*$', '', normalized)
    
    # ===== FASE 4: Eliminar sufijos y ruido ruidoso =====
    # "null" puede aparecer en cualquier lugar
    normalized = normalized.replace('null', '')
    
    # ", markup: X.XX%" (aparece en transacciones de tarjeta en CSV)
    # Ej: "Transacción GITHUB, INC., ..., markup: 0,29919149 %" → sin markup
    # Patrón: coma seguida de "markup:", valor decimal, espacio, "%"
    normalized = re.sub(r',\s*markup:\s*[\d,\.]+\s*%', '', normalized)
    
    # " con tarjeta" al final (PDF de transacciones con tarjeta)
    normalized = normalized.replace(' con tarjeta', '')
    
    # " Operar " (aparece en descripciones de savings plans)
    # Ej: "iShares Core Operar S&P 500" → "iShares Core S&P 500"
    normalized = re.sub(r'\s+Operar\s+', ' ', normalized)
    
    # "quantity: X.XXXXX" (aparece en savings plans)
    # Ej: "..., quantity: 0.017378" → "..."
    normalized = re.sub(r',\s*quantity:\s*[\d.]+', '', normalized)
    
    # Sufijo de tipo de cambio / FX rate (CSV a veces añade)
    # Ej: "MUHAMMAD IMRAN KHAN 1.86" → "MUHAMMAD IMRAN KHAN"
    # Patrón: espacio seguido de número decimal al final
    normalized = re.sub(r'\s+\d+[.,]\d{2,}$', '', normalized)
    
    # ===== FASE 5: Eliminar IBAN en paréntesis O al final (CSV agrega IBAN del remitente) =====
    # Caso 1: PDF: "Outgoing transfer for FERNANDEZ... (ES3600730100550435513660)" → sin IBAN
    normalized = re.sub(r'\s*\(ES\d{22}\)\s*$', '', normalized)
    
    # Caso 2: CSV: "Ingreso aceptado: ES3600730100550435513660 a DE77502109007012803405" → "... a"
    # El CSV añade IBAN de banco remitente (DE..., GB..., FR..., etc) al final sin paréntesis
    # Casos observados:
    #   - "... a DE775021090" (truncado a ~10 chars)
    #   - "... a DE77502109007012803405" (IBAN completo ~24 chars)
    # Patrón: " a " seguido de código país (2 letras) + dígito de control (2) + dígitos/letras
    normalized = re.sub(r' a [A-Z]{2}\d{2}[A-Z0-9]+$', ' a', normalized)
    
    # ===== FASE 6: Normalizar espacios extra =====
    # Múltiples espacios → uno
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()
