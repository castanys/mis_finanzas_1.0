# SPEC: Clasificador de Transacciones Bancarias v1.0

## Contexto

Pablo tiene 15,641 transacciones bancarias históricas clasificadas manualmente en un CSV maestro. Necesita un clasificador que, dada una descripción bancaria + banco + importe, devuelva Cat1 y Cat2 correctos.

El clasificador NO usa ML. Es un sistema de reglas por capas, derivado al 100% de los datos reales del CSV maestro.

---

## Arquitectura: 5 Capas en orden de prioridad

El clasificador evalúa cada transacción pasando por las capas en orden. La primera capa que produce un resultado gana. Si ninguna capa matchea, se devuelve `SIN_CLASIFICAR`.

```
Capa 1: Exact Match (descripción exacta ya vista)
  ↓ no match
Capa 2: Merchant Lookup (keyword en descripción → merchant conocido)
  ↓ no match
Capa 3: Transfer Detection (detectar transferencias internas/externas/bizum)
  ↓ no match
Capa 4: Token Heurístico (tokens discriminantes → categoría probable)
  ↓ no match
Capa 5: SIN_CLASIFICAR (cola de revisión manual)
```

**IMPORTANTE**: La Capa 2 (Merchants) va ANTES de la Capa 3 (Transferencias). Esto resuelve el problema de prioridad que Pablo describió: "si tengo compra Amazon -250€ y una transferencia de 250€, pesa más el gasto en Amazon". Si la descripción contiene "AMAZON", la Capa 2 la clasifica como Compras|Amazon y nunca llega a la Capa 3.

---

## Combinaciones Cat1|Cat2 VÁLIDAS (whitelist)

El clasificador SOLO puede devolver combinaciones que existen en los datos reales. Esto evita que se inventen categorías imposibles (el problema del ML).

```python
VALID_COMBINATIONS = {
    "Alimentación": ["Mercadona", "Lidl", "Carnicería", "Carrefour", "Cash & Carry",
        "Otros", "Frutería", "Eroski", "Bodega", "Supermercado", "Higinio",
        "Mercado", "Panadería", "Pescadería", "Hipermercado", "Dia", "Aldi",
        "Alcampo", "Consum", "Café", "GM Cash"],
    "Aportación": [""],
    "Bizum": [""],
    "Bonificación familia numerosa": [""],
    "Cashback": [""],
    "Comisiones": ["", "Retenciones", "Custodia"],
    "Compras": ["Amazon", "Otros", "El Corte Inglés", "Ajustes", "Online",
        "Regularización", "Leroy Merlin", "Decathlon", "Estancos", "Aliexpress",
        "Tecnología", "Ropa y Calzado", "Deportes", "Loterías", "Casa", "Hogar",
        "Electrónica", "Bazar", "Bazar chino", "Bodega", "Vino", "Juguetería",
        "Informática", "eCommerce", "Papelería", "Librería", "Mascotas"],
    "Cripto": ["Nexo", "Binance", "MEXC", "Bit2Me", "RAMP", ""],
    "Cuenta Común": ["", "Entrante"],
    "Deportes": ["Pádel", "Equipo deportivo", "Gimnasio", "Club"],
    "Depósitos": [""],
    "Devoluciones": ["Comisiones", "", "Regularización", "IRPF", "Hacienda"],
    "Dividendos": [""],
    "Divisas": [""],
    "Efectivo": ["Retirada cajero", "", "Ingreso cajero"],
    "Externa": [""],
    "Finanzas": ["Ahorro", "Hipoteca", "Préstamos", "Liquidación", "Paternidad",
        "Gastos de gestión", "Gestoría", "Tasaciones", "Donaciones"],
    "Fondos": ["Venta"],
    "Impuestos": ["Retenciones", "Autónomos", "AEAT", "IRPF", "Circulación",
        "IBI", "Pasarela/Vado", "Seguridad Social"],
    "Intereses": ["", "Trade Republic"],
    "Interna": [""],
    "Liquidación": [""],
    "Nómina": [""],
    "Ocio y Cultura": ["Cines", "Juegos", "Entradas", "Cultura", "Teatro",
        "Deportes", "Museos", "Turismo"],
    "Otros": [""],
    "Recibos": ["Otros", "Telefonía e Internet", "Gimnasio", "Luz", "Seguro Casa",
        "Agua", "Alarma", "Gas", "Asesoría", "Donaciones", "Fotovoltaica"],
    "Renta Variable": ["Compra", "Venta"],
    "Restauración": ["Otros", "Bar", "Heladería", "Bares", "Cafeterías", "Cafetería",
        "Mesón", "Churrería", "Pizzería", "Cervecería", "Asador", "Sushi",
        "Kiosco", "Tapería", "Pub", "Pastelería", "Takos", "Taberna",
        "Fast food", "Hamburguesería", "Kebab", "Bodega"],
    "Ropa y Calzado": ["Ropa y Accesorios", "Otros", "Springfield", "El Ganso",
        "Cortefiel"],
    "Salud y Belleza": ["Farmacia", "Peluquería", "Óptica", "Perfumería", "Médico",
        "Fisioterapia", "Clínica dental", "Clínica capilar", "Spa", "Láser",
        "Nutrición"],
    "Seguros": ["", "Vida", "Indemnización"],
    "Servicios Consultoría": ["", "Otros"],
    "Suscripciones": ["Audible", "Waylet", "Música", "Apple", "Software/Desarrollo",
        "Streaming", "Cloud/Backup", "Software/IA", "IA", "Otros"],
    "Transporte": ["Combustible", "Peajes", "Parking", "Aparcamiento/Peajes",
        "Metro/Tranvía", "Taxi", "Tren", "Transporte público",
        "Taller/Automoción", "Taller", "ITV", "Taxi/VTC", "Autobús"],
    "Viajes": ["Alojamiento", "Vuelos", "Aeropuerto/Duty Free", "Actividades",
        "Bus", "Transporte", "Servicios Camino"],
    "Vivienda": ["Limpieza", "Mantenimiento"],
    "Wallapop": [""],
}
```

**Regla estricta**: Si el clasificador intenta devolver una combinación Cat1+Cat2 que no está en VALID_COMBINATIONS, debe forzar Cat2="" (vacío) o Cat2="Otros" según lo que exista para esa Cat1.

---

## Capa 1: Exact Match

Construir un diccionario `{descripción_exacta: (Cat1, Cat2)}` a partir del CSV maestro.

**Gestión de colisiones**: Solo hay 18 descripciones (de 10,606 únicas) con múltiples Cat1. Para estas, usar la clasificación MÁS FRECUENTE. Las colisiones son:

- `OPERACION TELEBANCO` → Efectivo (246) vs Interna (1) → **Efectivo|Retirada cajero**
- `COMPRAS Y OPERACIONES CON TARJETA 4B` → Compras (217) vs Devoluciones (2) → **Compras|Ajustes**
- `Transferencia` → Interna (6) vs Externa (2) → **Interna|**
- `Transf. Concepto no especificado` → Interna (24) vs Externa (3) vs Cripto (2) → **Interna|**

Para las demás colisiones, resolver por frecuencia (mayoría gana).

**Cobertura esperada**: ~37.7% de transacciones (las que tienen descripción repetida).

---

## Capa 2: Merchant Lookup

Buscar keywords en la descripción (case-insensitive). El ORDEN importa: reglas más específicas primero.

### 2A: Extracción de merchant name

Antes de buscar keywords, extraer el nombre del merchant de la descripción según el formato del banco:

```python
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
```

El merchant extraído se busca TAMBIÉN en la tabla de Capa 2, no solo la descripción completa.

### 2B: Tabla de merchants conocidos

Cada regla tiene: keyword, Cat1, Cat2, y opcionalmente condiciones extra.

```python
MERCHANT_RULES = [
    # ===== ALIMENTACIÓN =====
    ("MERCADONA", "Alimentación", "Mercadona"),
    ("LIDL", "Alimentación", "Lidl"),
    ("EROSKI", "Alimentación", "Eroski"),
    ("CARREFOUR ZARAICHE", "Alimentación", "Carrefour"),  # Carrefour en Murcia, alimentación
    ("CARREFOUR", "Alimentación", "Carrefour"),
    ("ALCAMPO", "Alimentación", "Alcampo"),
    ("ALDI", "Alimentación", "Aldi"),
    ("DIA %", "Alimentación", "Dia"),  # % = word boundary
    ("CONSUM", "Alimentación", "Consum"),  # Supermercado real (cadena valenciana)
    ("TRANSGOURMET", "Alimentación", "Cash & Carry"),
    ("GROS MERCAT", "Alimentación", "Mercado"),
    ("GM CASH", "Alimentación", "GM Cash"),
    ("CARNICAS CAMPILLO", "Alimentación", "Carnicería"),
    ("CARNICERIA HIGINIO", "Alimentación", "Higinio"),
    ("CARNICERIA", "Alimentación", "Carnicería"),  # genérico después de específicos
    ("MUHAMMAD IMRAN", "Alimentación", "Frutería"),
    ("FRUTERIA", "Alimentación", "Frutería"),
    ("PANADERIA", "Alimentación", "Panadería"),
    ("PESCADERIA", "Alimentación", "Pescadería"),
    
    # ===== COMPRAS =====
    ("AMAZON", "Compras", "Amazon"),
    ("AMZN", "Compras", "Amazon"),
    ("CORTE INGLES", "Compras", "El Corte Inglés"),
    ("LEROY MERLIN", "Compras", "Leroy Merlin"),
    ("MERLIN", "Compras", "Leroy Merlin"),
    ("DECATHLON", "Compras", "Decathlon"),
    ("ALIEXPRESS", "Compras", "Aliexpress"),
    ("MIRAVIA", "Compras", "eCommerce"),
    ("MEDIA MARK", "Compras", "Tecnología"),
    ("MEDIAMARKT", "Compras", "Tecnología"),
    ("EBAY", "Compras", "Online"),
    ("ESTANCO", "Compras", "Estancos"),
    ("LOTERIAS Y APUESTAS", "Compras", "Loterías"),
    ("GVB SPINNERIJ", "Compras", "GVB SPINNERIJ"),
    ("MASSIMO DUTTI", "Compras", "Ropa y Calzado"),
    ("SPRINGFIELD", "Compras", "Ropa y Calzado"),
    ("CORTEFIEL", "Compras", "Ropa y Calzado"),
    ("EL GANSO", "Ropa y Calzado", "El Ganso"),
    ("FNAC", "Compras", "Librería"),
    ("TOYS", "Compras", "Juguetería"),
    ("JUGUETILANDIA", "Compras", "Juguetería"),
    ("BAZAR", "Compras", "Bazar"),
    
    # ===== EFECTIVO =====
    ("CAJERO", "Efectivo", "Retirada cajero"),
    ("DISPOSICION EN CAJERO", "Efectivo", "Retirada cajero"),
    ("DISPOSICIÓN EN CAJERO", "Efectivo", "Retirada cajero"),
    ("TELEBANCO", "Efectivo", "Retirada cajero"),
    ("REINTEGRO", "Efectivo", "Retirada cajero"),
    
    # ===== TRANSPORTE =====
    ("AUTOPISTAS DEL SURESTE", "Transporte", "Peajes"),
    ("AUTOPISTA DEL SURESTE", "Transporte", "Peajes"),
    ("AUTPTA", "Transporte", "Peajes"),
    ("AUSURMONTESINOS", "Transporte", "Peajes"),
    ("AUTOPISTAS", "Transporte", "Peajes"),
    ("AUTOPISTA", "Transporte", "Peajes"),
    ("PEAJE", "Transporte", "Peajes"),
    ("GM OIL", "Transporte", "Combustible"),
    ("EASYGAS", "Transporte", "Combustible"),
    ("AUCOSTA", "Transporte", "Combustible"),
    ("REPSOL", "Transporte", "Combustible"),
    ("CEPSA", "Transporte", "Combustible"),
    ("E.S.", "Transporte", "Combustible"),  # Estaciones de servicio
    ("GASOLINERA", "Transporte", "Combustible"),
    ("EYSA", "Transporte", "Parking"),
    ("PKAENA", "Transporte", "Parking"),
    ("PARKING", "Transporte", "Parking"),
    ("METRO DE MADRID", "Transporte", "Metro/Tranvía"),
    ("RENFE", "Tren", "Tren"),  # NOTA: verificar Cat1
    ("GATWICK EXPRESS", "Transporte", "Tren"),
    ("ITV", "Transporte", "ITV"),  # CUIDADO: substring
    ("TUV RHEINLAND", "Transporte", "ITV"),
    
    # ===== RECIBOS =====
    ("VODAFONE", "Recibos", "Telefonía e Internet"),
    ("SIMYO", "Recibos", "Telefonía e Internet"),
    ("ORANGE", "Recibos", "Telefonía e Internet"),  # verificar en datos
    ("HIDROGEA", "Recibos", "Agua"),
    ("IBERDROLA", "Recibos", "Luz"),
    ("ENDESA", "Recibos", "Luz"),
    ("NATURGY", "Recibos", "Gas"),
    ("SECURITAS DIRECT", "Recibos", "Alarma"),
    ("ASOCIACION", "Recibos", "Donaciones"),
    
    # ===== SALUD Y BELLEZA =====
    ("FARMACIA CRESPO", "Salud y Belleza", "FARMACIA CRESPO GALVEZ"),
    ("MARIA DOLORES CRESPO", "Salud y Belleza", "MARIA DOLORES CRESPO GAL"),
    ("FARMACIA", "Salud y Belleza", "Farmacia"),
    ("PELUQUERIA JAVIER CONESA", "Salud y Belleza", "Peluquería"),
    ("PELUQUERIA", "Salud y Belleza", "Peluquería"),
    ("VISIONLAB", "Salud y Belleza", "Óptica"),
    ("OPTICA", "Salud y Belleza", "Óptica"),
    ("LDO.PEDRO ANGEL", "Salud y Belleza", "Médico"),
    ("ORTO NOVA", "Salud y Belleza", "Clínica dental"),
    ("FISIOTERAPI", "Salud y Belleza", "Fisioterapia"),
    ("PERFUMERIA", "Salud y Belleza", "Perfumería"),
    
    # ===== RESTAURACIÓN (merchants específicos) =====
    ("A LA BARRA GASTROBAR", "Restauración", "A LA BARRA GASTROBAR"),
    ("AVALON CARTAGENA", "Restauración", "AVALON CARTAGENA"),
    ("NEOCINE", "Ocio y Cultura", "Cines"),
    ("CAFETERIA PROA", "Restauración", "CAFETERIA PROA"),
    ("MESON EL GALGO", "Restauración", "Mesón"),
    ("DELANTE BAR", "Restauración", "Bar"),
    ("BAR LA PAZ", "Restauración", "BAR LA PAZ"),
    ("HELADERIA LA JIJONENCA", "Restauración", "Heladería"),
    ("GESTIPRAT", "Restauración", "Otros"),
    ("SUPERMERCADO UPPER", "Restauración", "SUPERMERCADO UPPER 948"),
    ("KIOSCO MIGUEL", "Restauración", "Kiosco Miguel"),
    
    # ===== SUSCRIPCIONES =====
    ("AUDIBLE", "Suscripciones", "Audible"),
    ("WAYLET", "Suscripciones", "Waylet"),
    ("SPOTIFY", "Suscripciones", "Música"),
    ("APPLE.COM/BILL", "Suscripciones", "Apple"),
    ("DISNEY", "Suscripciones", "Streaming"),
    ("NETFLIX", "Suscripciones", "Streaming"),
    
    # ===== OCIO Y CULTURA =====
    ("MANDARACHE", "Ocio y Cultura", "Cines"),
    ("CINES", "Ocio y Cultura", "Cines"),
    
    # ===== FINANZAS =====
    ("SAVE", "Finanzas", "Ahorro"),  # B100 Off to save
    ("OFF TO SAVE", "Finanzas", "Ahorro"),
    ("MOVE TO SAVE", "Finanzas", "Ahorro"),
    ("PRÉSTAMO", "Finanzas", "Hipoteca"),
    ("PRESTAMO", "Finanzas", "Hipoteca"),
    
    # ===== IMPUESTOS =====
    ("HACIENDA", "Impuestos", "Retenciones"),
    ("RETENCION", "Impuestos", "Retenciones"),
    ("AUTONOMO", "Impuestos", "Autónomos"),
    ("TGSS", "Impuestos", "Seguridad Social"),
    
    # ===== NÓMINA =====
    ("NOMINA", "Nómina", ""),
    
    # ===== SEGUROS =====
    ("GENERALI", "Seguros", "Vida"),
    
    # ===== CASHBACK =====
    ("BONIFICACION", "Cashback", ""),
    ("DEVOLUCION RECIBOS", "Cashback", ""),
    ("DOMICILIADOS", "Cashback", ""),
    
    # ===== INVERSIÓN =====
    ("NEXO", "Cripto", "Nexo"),
    ("BINANCE", "Cripto", "Binance"),
    ("BIT2ME", "Cripto", "Bit2Me"),
    ("PLAN DE INVERSION", "Renta Variable", "Compra"),
    
    # ===== WALLAPOP =====
    ("WALLAPOP", "Wallapop", ""),
    
    # ===== VIAJES =====
    ("HOTEL", "Viajes", "Alojamiento"),
    ("HOSTAL", "Viajes", "Alojamiento"),
    ("BOOKING", "Viajes", "Alojamiento"),
    ("RYANAIR", "Viajes", "Vuelos"),
    ("VUELING", "Viajes", "Vuelos"),
    ("IBERIA", "Viajes", "Vuelos"),
    ("EASYJET", "Viajes", "Vuelos"),
    ("DUTY FREE", "Viajes", "Aeropuerto/Duty Free"),
    
    # ===== SERVICIOS CONSULTORÍA =====
    ("MCR BUSINESS", "Servicios Consultoría", ""),
]
```

**Notas de implementación:**
- Las reglas se evalúan en ORDEN. Poner reglas más específicas ANTES de las genéricas.
- `CARREFOUR ZARAICHE` antes de `CARREFOUR`.
- `FARMACIA CRESPO` antes de `FARMACIA`.
- `PELUQUERIA JAVIER CONESA` antes de `PELUQUERIA`.
- La keyword `CONSUM` necesita word boundary check para no colisionar con "consumo".
- La keyword `E.S.` (estación de servicio) es ambigua. Considerar usar `E.S. ` (con espacio) o solo en combinación con banco Openbank.
- La keyword `ITV` es corta y puede generar falsos positivos. Usar con cuidado.

**Cobertura esperada**: ~40-50% adicional sobre lo que no cubre la Capa 1.

---

## Capa 3: Transfer Detection

Esta capa detecta transferencias (internas, externas, Bizum). Solo se aplica si las Capas 1 y 2 no han producido resultado.

### 3A: Bizum

```python
def is_bizum(desc, banco):
    desc_upper = desc.upper()
    if "BIZUM" in desc_upper:
        return True
    # Trade Republic: Bizum via "Outgoing/Incoming transfer for <nombre> (+34-...)"
    if banco == "Trade Republic" and re.search(r'transfer for .+\(\+34-', desc):
        return True
    return False
```

Si es Bizum → Cat1="Bizum", Cat2="".

### 3B: Interna

```python
def is_internal_transfer(desc, banco, importe):
    desc_upper = desc.upper()
    
    # Patrones explícitos de transferencia interna
    internal_patterns = [
        "TRASPASO INTERNO",
        "ORDEN TRASPASO INTERNO",
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
    
    # Openbank: transferencias donde el destino es otra cuenta propia
    # Patrón: "TRANSFERENCIA A FAVOR DE FERNANDEZ CASTANYS ORTIZ DE VILLAJOS PAB"
    # (Pablo a sí mismo, diferentes cuentas)
    if banco == "Openbank" and "FERNANDEZ CASTANYS ORTIZ DE VILLAJOS PAB" in desc_upper:
        return True
    
    # Concepto no especificado: mayoritariamente interna (24 de 29 = 83%)
    if "CONCEPTO NO ESPECIFICADO" in desc_upper:
        return True  # Marcar como interna por defecto
    
    return False
```

Si es interna → Cat1="Interna", Cat2="".

### 3C: Cuenta Común

```python
def is_cuenta_comun(desc, banco):
    desc_upper = desc.upper()
    # Yolanda Arroyo Varo = ex-pareja, transferencias de cuenta común
    if "ARROYO VARO" in desc_upper:
        if "RECIBIDA" in desc_upper:
            return ("Cuenta Común", "Entrante")
        return ("Cuenta Común", "")
    return None
```

### 3D: Externa (fallback para transferencias)

Si la descripción contiene keywords de transferencia pero no matchea interna ni bizum ni cuenta común:

```python
TRANSFER_KEYWORDS = ["TRANSFERENCIA", "TRANSF.", "TRASPASO", "STICHTING"]

def is_transfer(desc):
    return any(kw in desc.upper() for kw in TRANSFER_KEYWORDS)
```

Si es transferencia pero no interna/bizum/cuenta común → Cat1="Externa", Cat2="".

---

## Capa 4: Token Heurístico

Para transacciones que no matchean nada anterior. Buscar tokens discriminantes en la descripción.

```python
TOKEN_RULES = [
    # Restauración (tokens genéricos)
    ("BAR ", "Restauración", "Otros"),       # espacio para evitar "BARCELONA", "BARBERÍA"
    ("RESTAURANTE", "Restauración", "Otros"),
    ("CAFETERIA", "Restauración", "Cafeterías"),
    ("CERVECERIA", "Restauración", "Cervecería"),
    ("CHURRERIA", "Restauración", "Churrería"),
    ("MESON", "Restauración", "Mesón"),
    ("TABERNA", "Restauración", "Taberna"),
    ("PIZZ", "Restauración", "Pizzería"),
    ("HELADERIA", "Restauración", "Heladería"),
    ("ASADOR", "Restauración", "Asador"),
    ("PASTELERIA", "Restauración", "Pastelería"),
    ("HAMBURGUES", "Restauración", "Hamburguesería"),
    ("KEBAB", "Restauración", "Kebab"),
    ("GASTROBAR", "Restauración", "Otros"),
    ("TAPAS", "Restauración", "Tapería"),
    ("PUB ", "Restauración", "Pub"),
    
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
]
```

**IMPORTANTE sobre "BAR "**: El espacio después es crucial para evitar falsos positivos como "BARCELONA", "BARBERÍA", etc. En la implementación, usar word boundary: `re.search(r'\bBAR\b', desc)`.

**Cobertura esperada de Capa 4**: ~5-10% adicional.

---

## Capa 5: SIN_CLASIFICAR

Todo lo que no matchea → `Cat1="SIN_CLASIFICAR"`, `Cat2=""`.

Estas transacciones van a una "cola de revisión" que Pablo revisa manualmente (estimación: <5% del total, ~10 minutos/semana para transacciones nuevas).

**Cuando Pablo clasifica una transacción SIN_CLASIFICAR**, se añade al diccionario de Exact Match (Capa 1) y opcionalmente se crea una nueva regla de Merchant (Capa 2) si el merchant se va a repetir.

---

## Tipo de Transacción

Además de Cat1/Cat2, clasificar el `Tipo`:

```python
def determine_tipo(cat1, importe):
    if cat1 in ("Interna", "Externa", "Bizum", "Cuenta Común"):
        return "TRANSFERENCIA"
    if cat1 in ("Renta Variable", "Fondos", "Cripto", "Aportación", "Depósitos"):
        return "INVERSION"
    if float(importe) > 0:
        # Positivo: ingreso o devolución
        if cat1 in ("Nómina", "Intereses", "Dividendos", "Cashback",
                     "Bonificación familia numerosa", "Servicios Consultoría"):
            return "INGRESO"
        if cat1 == "Devoluciones":
            return "INGRESO"
        return "INGRESO"
    return "GASTO"
```

---

## Datos Específicos por Banco

### Formato de descripción

| Banco | Patrón de descripción de gastos |
|-------|--------------------------------|
| Openbank | `COMPRA EN <MERCHANT>, CON LA TARJETA : ...` o `Apple Pay: COMPRA EN <MERCHANT>, ...` o texto libre |
| Trade Republic | `Transacción <MERCHANT> con tarjeta` |
| Revolut | Nombre del merchant directo (ej: `Mercadona`, `Sushi Haiku`) |
| Mediolanum | Nombre o razón social directa |
| B100 | `OFF TO SAVE`, `Move to save`, `AHORRO PARA HUCHA` o texto libre |
| Abanca | `<código> <MERCHANT> \<CIUDAD>\<IBAN>` |
| MyInvestor | Nombre del fondo o `Aportacion a mi cartera` o `COM. GESTION` |

### Reglas específicas por banco

**MyInvestor**: Casi todo es inversión. Reglas:
- `Aportacion a mi cartera` → Renta Variable|Compra
- `Transferencia desde MyInvestor` → Interna
- `COM. GESTION` / `IVA COM. GESTION` → Comisiones
- `EFECTIVO-EUR @ 0` → Comisiones
- Nombres de fondos (ISHARES, VANGUARD, MSCI, S&P 500) → Renta Variable|Compra/Venta (según signo importe)
- `PERIODO` → Intereses

**B100**: Principalmente ahorro:
- `SAVE` / `OFF TO SAVE` / `Move to save` / `AHORRO PARA HUCHA` → Finanzas|Ahorro
- Transferencias con nombre propio → Interna

**Trade Republic**: Importante por volumen (920 txs). El merchant se extrae con `Transacción (.+?) con tarjeta`. Luego se aplican las reglas normales de Capa 2.

---

## Implementación: Estructura del Código

```
finsense/
├── classifier/
│   ├── __init__.py
│   ├── engine.py          # Orquestador: aplica capas en orden
│   ├── exact_match.py     # Capa 1: diccionario de exact matches
│   ├── merchants.py       # Capa 2: tabla de merchant keywords
│   ├── transfers.py       # Capa 3: detección de transferencias
│   ├── tokens.py          # Capa 4: tokens heurísticos
│   └── valid_combos.py    # Whitelist de combinaciones válidas
├── extractors/
│   ├── __init__.py
│   └── merchant_name.py   # Extracción de merchant name por banco
├── data/
│   └── master.csv         # CSV maestro (fuente de verdad)
├── tests/
│   └── test_classifier.py # Tests contra CSV maestro
├── classify.py            # CLI: python classify.py "descripción" "banco" importe
└── build_rules.py         # Genera exact_match dict desde master.csv
```

### engine.py (pseudocódigo)

```python
class Classifier:
    def __init__(self, master_csv_path):
        self.exact_match = build_exact_match(master_csv_path)
        self.merchants = MERCHANT_RULES
        self.transfer_rules = TransferDetector()
        self.token_rules = TOKEN_RULES
        self.valid_combos = VALID_COMBINATIONS
    
    def classify(self, descripcion, banco, importe):
        desc_upper = descripcion.upper()
        
        # Extraer merchant name si es posible
        merchant_name = extract_merchant(descripcion, banco)
        
        # Capa 1: Exact Match
        result = self.exact_match.get(descripcion)
        if result:
            return self._validate(*result)
        
        # Capa 2: Merchant Lookup (buscar en desc completa Y en merchant extraído)
        for keyword, cat1, cat2 in self.merchants:
            if keyword.upper() in desc_upper:
                return self._validate(cat1, cat2)
            if merchant_name and keyword.upper() in merchant_name.upper():
                return self._validate(cat1, cat2)
        
        # Capa 3: Transferencias
        if self.transfer_rules.is_bizum(descripcion, banco):
            return ("Bizum", "", "TRANSFERENCIA")
        
        cc = self.transfer_rules.is_cuenta_comun(descripcion, banco)
        if cc:
            return (*cc, "TRANSFERENCIA")
        
        if self.transfer_rules.is_internal(descripcion, banco, importe):
            return ("Interna", "", "TRANSFERENCIA")
        
        if self.transfer_rules.is_transfer(descripcion):
            return ("Externa", "", "TRANSFERENCIA")
        
        # Capa 4: Tokens heurísticos
        for token, cat1, cat2 in self.token_rules:
            if re.search(r'\b' + re.escape(token.strip()) + r'\b', desc_upper):
                return self._validate(cat1, cat2)
        
        # Capa 5: Sin clasificar
        return ("SIN_CLASIFICAR", "", "")
    
    def _validate(self, cat1, cat2):
        """Valida que la combinación Cat1+Cat2 sea válida."""
        if cat1 in self.valid_combos:
            if cat2 not in self.valid_combos[cat1]:
                # Forzar Cat2 válido
                cat2 = "Otros" if "Otros" in self.valid_combos[cat1] else ""
        tipo = determine_tipo(cat1, importe)
        return (cat1, cat2, tipo)
```

---

## Testing y Criterios de Éxito

### Test principal: clasificar las 15,641 transacciones del CSV maestro

```bash
python test_classifier.py --master data/master.csv
```

**Métricas**:

| Métrica | Objetivo | Aceptable |
|---------|----------|-----------|
| Cat1 accuracy (clasificadas) | >95% | >92% |
| Cat1+Cat2 accuracy (clasificadas) | >85% | >80% |
| % clasificadas (no SIN_CLASIFICAR) | >90% | >85% |
| Cat1 accuracy total (incl. SIN_CLASIFICAR como error) | >85% | >80% |

### Test de regresión: transacciones conocidas difíciles

Crear un archivo `tests/hard_cases.csv` con los edge cases:
- Transferencias de Revolut vía Apple Pay → Interna
- "SIN CONCEPTO" de Abanca → Interna  
- "BAR" que no es restaurante (ej: BARBERÍA)
- "CONSUM" que no es supermercado (ej: "consumo eléctrico")
- Descripciones genéricas: "Transferencia", "Transf. Concepto no especificado"
- Merchants de Restauración sin keywords de restauración (GESTIPRAT, AVALON, etc.)

### Test de nuevas transacciones (simulación)

Tomar las últimas 500 transacciones del CSV maestro, NO incluirlas en el exact match, y ver qué porcentaje clasifica correctamente solo con Capas 2-4.

---

## Notas para Claude Code / Sonnet

1. **No uses ML.** Este clasificador es 100% reglas deterministas.
2. **No inventes reglas.** Cada regla debe ser verificable contra el CSV maestro.
3. **Prioridad = orden.** Las reglas más específicas van primero.
4. **La whitelist es sagrada.** Nunca devolver una combinación Cat1+Cat2 que no esté en VALID_COMBINATIONS.
5. **SIN_CLASIFICAR es éxito, no fallo.** Es mejor decir "no sé" que inventar una clasificación incorrecta.
6. **Normalizar "GASTO" vs "Gasto".** En el CSV maestro hay inconsistencia. Usar siempre MAYÚSCULAS para Tipo.
7. **El CSV maestro tiene datos desde 2004.** Algunos formatos de Openbank han cambiado con los años. Las reglas deben funcionar para todos los períodos.

---

## Fase 1B — Enriquecimiento con Google Places (NO IMPLEMENTAR HASTA CERRAR FASE 1A)

**Prerequisito**: Fase 1A cerrada con >95% Cat1 accuracy. Solo entonces.

**Objetivo**: Reducir el % de SIN_CLASIFICAR consultando Google Places API para merchants desconocidos.

**Flujo**:
1. Transacción llega a Capa 5 (SIN_CLASIFICAR)
2. Extraer merchant name de la descripción (usando extractores de Capa 2A)
3. Consultar caché local (SQLite): ¿ya consulté este merchant?
   - Sí → usar resultado cacheado
   - No → consultar Google Places API con ámbito geográfico
4. Mapear el `type` de Google Places a Cat1/Cat2

**Ámbito geográfico (en orden de prioridad)**:
1. Cartagena, Murcia (radio ~10km) — default para la mayoría de transacciones
2. España — si no hay resultado en Cartagena
3. Europa — si no hay resultado en España
4. Global — si no hay resultado en Europa (viajes a Colombia, etc.)

**Detección de ámbito**: Si la transacción tiene fecha en un periodo donde Pablo estaba de viaje (podría inferirse por acumulación de merchants desconocidos en fechas cercanas), ampliar ámbito directamente a global.

**Caché** (SQLite tabla `merchant_cache`):
```sql
CREATE TABLE merchant_cache (
    merchant_name TEXT PRIMARY KEY,
    google_place_type TEXT,
    google_place_name TEXT,
    mapped_cat1 TEXT,
    mapped_cat2 TEXT,
    confidence TEXT,  -- 'high', 'medium', 'low'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- Caché NO expira (un bar es siempre un bar).
- Si Google Places no devuelve resultado → cachear como `NULL` para no repetir la consulta.
- Mapeo de Google Places types a Cat1/Cat2 (ejemplos):
  - `restaurant`, `bar`, `cafe` → Restauración
  - `supermarket`, `grocery_store` → Alimentación
  - `gas_station` → Transporte|Combustible
  - `pharmacy` → Salud y Belleza|Farmacia
  - `clothing_store` → Compras|Ropa y Calzado
  - `lodging` → Viajes|Alojamiento

**Coste estimado**: Google Places API tiene 0€ para los primeros ~$200/mes (crédito gratuito). Con caché, las consultas serán mínimas tras el primer mes.

**NO IMPLEMENTAR HASTA QUE FASE 1A ESTÉ CERRADA Y VALIDADA.**

---

## Crecimiento del clasificador

Cuando Pablo revisa transacciones SIN_CLASIFICAR y las clasifica:

1. Se añade al diccionario de Exact Match (automático).
2. Si el merchant se va a repetir, Pablo puede añadir una regla a MERCHANT_RULES.
3. La whitelist VALID_COMBINATIONS se actualiza si aparece una nueva combinación Cat1+Cat2 legítima.

Esto es un loop manual pero controlado. NO se necesita reentrenar ningún modelo. Solo editar un archivo de configuración.

---

## Errores conocidos a resolver

De la simulación inicial (con ~50 reglas básicas):

| Error | Causa | Solución |
|-------|-------|----------|
| RECIBO clasificado como Compras|Online (165x) | "RECIBO" matchea antes que el merchant real | Asegurar que merchant-specific rules van ANTES de token genérico "RECIBO" |
| BAR clasificado como Transporte|Combustible (31x) | "BAR" en nombre de gasolinera? | Usar word boundary `\bBAR\b` y verificar estos casos |
| CONSUM clasificado como Alimentación (25x erróneo) | Colisión con "consumo préstamo" en datos | CONSUM es supermercado legítimo. Verificar si los 25 errores reales eran por otra causa |
| CARREFOUR → Alimentación cuando es Ropa (15x) | Dato incorrecto en CSV maestro: Carrefour Zaraiche es alimentación | Corregido: CARREFOUR ZARAICHE → Alimentación|Carrefour |

Estos errores están documentados para que Claude Code los resuelva durante implementación.
