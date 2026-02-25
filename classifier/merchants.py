"""
Capa 2: Merchant Lookup
Tabla de merchants conocidos con keywords.
"""
import json
import os
from typing import Optional

# Cargar merchants de Google Places (enriquecimientos permanentes)
GOOGLE_PLACES_MERCHANTS = {}
places_file = os.path.join(os.path.dirname(__file__), '..', 'merchants_places.json')
if os.path.exists(places_file):
    with open(places_file, 'r', encoding='utf-8') as f:
        GOOGLE_PLACES_MERCHANTS = json.load(f)
    print(f"✓ Cargados {len(GOOGLE_PLACES_MERCHANTS)} merchants de Google Places")

# Cargar merchants por nombre completo (extraídos de patrón COMPRA EN)
FULLNAME_MERCHANTS = {}
fullnames_file = os.path.join(os.path.dirname(__file__), '..', 'merchants_fullnames.json')
if os.path.exists(fullnames_file):
    with open(fullnames_file, 'r', encoding='utf-8') as f:
        FULLNAME_MERCHANTS = json.load(f)
    print(f"✓ Cargados {len(FULLNAME_MERCHANTS)} merchants por nombre completo")

# Cada regla: (keyword, Cat1, Cat2)
# IMPORTANTE: El orden importa - reglas más específicas primero
MERCHANT_RULES = [
    # ===== ALIMENTACIÓN =====
    ("MERCADONA", "Alimentación", "Mercadona"),
    ("LIDL", "Alimentación", "Lidl"),
    ("EROSKI", "Alimentación", "Eroski"),
    ("CARREFOUR ZARAICHE", "Alimentación", "Carrefour"),  # Carrefour en Murcia, alimentación
    ("CARREF CARTA", "Alimentación", "Carrefour"),  # Carrefour Cartagena
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
    ("RAMIZ IQBAL", "Alimentación", "Frutería"),
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
    ("DEPORVILLAGE", "Compras", "Deportes"),  # Limpio (sin NULL)
    ("ALIEXPRESS", "Compras", "Aliexpress"),
    ("MIRAVIA", "Compras", "eCommerce"),
    ("MEDIA MARK", "Compras", "Tecnología"),
    ("MEDIAMARKT", "Compras", "Tecnología"),
    ("TEDITRONIC", "Compras", "Tecnología"),  # Electrónica Cartagena
    ("EBAY", "Compras", "Online"),
    ("MERCA H", "Compras", "Bazar"),  # Merca H&W Cartagena
    ("WWW.CURIOSITE", "Compras", "Regalos"),  # Tienda online de regalos
    ("CURIOSITE", "Compras", "Regalos"),
    ("ESTANCO", "Compras", "Estancos"),
    ("LOTERIAS Y APUESTAS", "Compras", "Loterías"),
    ("MASSIMO DUTTI", "Compras", "Ropa y Calzado"),
    ("SPRINGFIELD", "Compras", "Ropa y Calzado"),
    ("CORTEFIEL", "Compras", "Ropa y Calzado"),
    ("EL GANSO", "Ropa y Calzado", "El Ganso"),
    ("PAYPAL *ACTURUSCAPI", "Ropa y Calzado", "El Ganso"),  # Compras El Ganso via PayPal
    ("FNAC", "Compras", "Librería"),
    ("TOYS", "Compras", "Juguetería"),
    ("JUGUETILANDIA", "Compras", "Juguetería"),
     ("BAZAR", "Compras", "Bazar"),
     ("RECIBO PAYPAL", "Compras", "PayPal"),  # Domiciliaciones RECIBO PayPal Europe
     ("PAYPAL", "Compras", "PayPal"),  # Compras via PayPal
     
     # ===== COMPRAS (mejoras merchants Punto 3) =====
    ("CEDIPSA", "Transporte", "Combustible"),  # Gasolinera CEPSA
    ("PRIMARK", "Compras", "Ropa y Calzado"),
    ("PULL AND BEAR", "Compras", "Ropa y Calzado"),
    ("H&M", "Compras", "Ropa y Calzado"),
    ("MANGO", "Compras", "Ropa y Calzado"),
    ("JYSK", "Compras", "Muebles"),
    ("MAISONS DU MONDE", "Compras", "Muebles"),
    ("IKEA", "Compras", "Muebles"),
    ("TREKKINN", "Compras", "Deportes"),
    ("FORUM SPORT", "Compras", "Deportes"),
    ("PCCOMPONENTES", "Compras", "Tecnología"),
    ("PC BOX", "Compras", "Tecnología"),
    ("STEAM", "Compras", "Videojuegos"),
    ("VINOSELECCION", "Alimentación", "Vinos"),

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
    ("PLENERGY", "Transporte", "Combustible"),  # Limpio (sin NULL ni número de gasolinera)
    ("E.S.", "Transporte", "Combustible"),  # Estaciones de servicio
    ("TPV MURCIA I EL PUNTAL", "Transporte", "Combustible"),  # Gasolinera específica
    ("GASOLINERA", "Transporte", "Combustible"),
    ("EYSA", "Transporte", "Parking"),
    ("PKAENA", "Transporte", "Parking"),
    ("PARKING", "Transporte", "Parking"),
    ("METRO DE MADRID", "Transporte", "Metro/Tranvía"),
    ("RENFE", "Transporte", "Tren"),
    ("GATWICK EXPRESS", "Transporte", "Tren"),
    ("ITV", "Transporte", "ITV"),
    ("TUV RHEINLAND", "Transporte", "ITV"),
    ("REPUESTOS BASI", "Transporte", "Repuestos"),  # Repuestos motos/bicis

     # ===== RECIBOS =====
     ("RECIBO REPSOL", "Recibos", "Luz"),  # REPSOL luz (domiciliaciones periódicas)
     ("VODAFONE", "Recibos", "Telefonía e Internet"),
     ("SIMYO", "Recibos", "Telefonía e Internet"),
     ("DIGI SPAIN", "Recibos", "Telefonía e Internet"),  # DIGI Spain Telecom (telefonía móvil)
     ("ORANGE", "Recibos", "Telefonía e Internet"),
     ("HIDROGEA", "Recibos", "Agua"),
     ("IBERDROLA", "Recibos", "Luz"),
     ("ENDESA", "Recibos", "Luz"),
     ("NATURGY", "Recibos", "Gas"),
     ("SECURITAS DIRECT", "Recibos", "Alarma"),
     ("FELITONA", "Recibos", "Gimnasio"),  # Felitona Servicios y Gestiones (cuota gimnasio)
     ("ASOCIACION", "Recibos", "Donaciones"),
     ("RECIBO ONEY", "Finanzas", "Crédito"),  # ONEY financiero
     ("RECIBO WIZINK", "Finanzas", "Crédito"),  # WIZINK banco digital
     ("RECIBO CITIBANK", "Finanzas", "Crédito"),  # CITIBANK tarjetas crédito
     ("RECIBO GRANDES ALMACENES", "Compras", "Grandes Almacenes"),  # Recibo grandes almacenes
     ("RECIBO VINOSELECCION", "Alimentación", "Vinos"),  # Compra de vinos
     ("RECIBO JAVISA SPORT", "Ocio y Cultura", "Deporte"),  # BODY FACTORY - gimnasio
     ("BODY FACTORY", "Ocio y Cultura", "Deporte"),  # BODY FACTORY gimnasio
     ("RECIBO ENERGIA XXI", "Recibos", "Gas"),  # Energía XXI es gas, no luz
     ("RECIBO CONTRIB", "Impuestos", "Municipales"),  # Contribución municipal
     ("RECIBO ASOC", "Ocio y Cultura", "Deporte"),  # Asociaciones deportivas

    # ===== SALUD Y BELLEZA =====
    ("FARMACIA CRESPO", "Salud y Belleza", "Farmacia"),
    ("MARIA DOLORES CRESPO", "Salud y Belleza", "Farmacia"),
    ("FARMACIA", "Salud y Belleza", "Farmacia"),
    ("ORTONOVA", "Salud y Belleza", "Dental"),  # Clínica dental Ortonova (S51)
    ("HAVANA OLD", "Salud y Belleza", "Peluquería"),
    ("PELUQUERIA JAVIER CONESA", "Salud y Belleza", "Peluquería"),
    ("PELUQUERIA", "Salud y Belleza", "Peluquería"),
    ("VISIONLAB", "Salud y Belleza", "Óptica"),
    ("OPTICA", "Salud y Belleza", "Óptica"),
    ("LDO.PEDRO ANGEL", "Salud y Belleza", "Médico"),
    ("ORTO NOVA", "Salud y Belleza", "Clínica dental"),
    ("FISIOTERAPI", "Salud y Belleza", "Fisioterapia"),
    ("PERFUMERIA", "Salud y Belleza", "Perfumería"),

    # ===== RESTAURACIÓN (merchants específicos) =====
    ("NEOCINE", "Ocio y Cultura", "Cines"),
    ("VENTA EL PALMERAL", "Restauración", "Otros"),  # Restaurante Cartagena
    ("EL CHANQUETE", "Restauración", "Otros"),  # Restaurante mediterráneo Cartagena
    ("CHANQUETE", "Restauración", "Otros"),
    ("DCUATRO", "Restauración", "Otros"),  # Restaurante Murcia
    ("GUEVARA", "Restauración", "Otros"),  # El Corral de Guevara
    ("MIAJA", "Restauración", "Bar"),  # Bar Murcia
    ("IMPERIO ROJO", "Restauración", "Bar"),  # Bar Cartagena
    ("SUPERBAR", "Restauración", "Bar"),
    ("MESON", "Restauración", "Mesón"),
     ("DELANTE BAR", "Restauración", "Bar"),
     ("LA FRONTERA", "Restauración", "Otros"),  # La Frontera (Trade Republic S50)
     ("EL HORNO DE RICOTE", "Restauración", "Otros"),  # El Horno de Ricote (Trade Republic S50)
     ("BIERGARTEN", "Restauración", "Bar"),  # Biergarten (Trade Republic S50)
     ("HELADERIA", "Restauración", "Heladería"),
    ("SUSHI", "Restauración", "Japonés"),  # Mejora Punto 3
    ("BODEGA", "Restauración", "Bodega"),  # Genérico para bodegas

    # ===== SUSCRIPCIONES =====
    ("AUDIBLE", "Suscripciones", "Audible"),
    ("WAYLET", "Suscripciones", "Waylet"),
    ("SPOTIFY", "Suscripciones", "Música"),
    ("APPLE.COM/BILL", "Suscripciones", "Apple"),
    ("DISNEY", "Suscripciones", "Streaming"),
    ("NETFLIX", "Suscripciones", "Streaming"),
    ("ANTHROPIC", "Suscripciones", "Software/IA"),
    ("GITHUB", "Suscripciones", "Software/IA"),  # GitHub Copilot/Pro/suscripciones
    ("OPENROUTER", "Suscripciones", "Software/IA"),  # OpenRouter API (S51)
    ("NAMECHEAP", "Suscripciones", "Dominios"),  # Namecheap domain registrar (S51)
    ("CLAUDE.AI", "Suscripciones", "Software/IA"),  # Limpio (sin NULL)

    # ===== OCIO Y CULTURA =====
    ("D LIO", "Ocio y Cultura", "Bar"),  # Bar/pub nocturno Cartagena
    ("D'LIO", "Ocio y Cultura", "Bar"),
    ("MANDARACHE", "Ocio y Cultura", "Cines"),
    ("CINES", "Ocio y Cultura", "Cines"),
    ("BOWLING", "Ocio y Cultura", "Entretenimiento"),  # Mejora Punto 3

    # ===== FINANZAS =====
    ("OFF TO SAVE", "Finanzas", "Ahorro"),
    ("MOVE TO SAVE", "Finanzas", "Ahorro"),
    ("AHORRO PARA HUCHA", "Finanzas", "Ahorro"),
    ("PRÉSTAMO", "Finanzas", "Hipoteca"),
    ("PRESTAMO", "Finanzas", "Hipoteca"),

     # ===== IMPUESTOS =====
     ("HACIENDA", "Impuestos", "Retenciones"),
     ("RETENCION", "Impuestos", "Retenciones"),
     ("AUTONOMO", "Impuestos", "Autónomos"),
     ("AUTOLIQUIDACION", "Impuestos", "IVA"),  # IVA trimestral autónomos
     ("TGSS", "Impuestos", "Seguridad Social"),

    # ===== NÓMINA =====
    ("TIMESTAMP SOLUTIONS", "Nómina", ""),  # Empresa de Pablo
    ("NOMINA", "Nómina", ""),

    # ===== SEGUROS =====
    ("GENERALI", "Seguros", "Vida"),

    # ===== CASHBACK =====
    ("BONIFICACION", "Cashback", ""),
    ("DEVOLUCION RECIBOS", "Cashback", ""),
    ("DOMICILIADOS", "Cashback", ""),

    # ===== INVERSIÓN =====
    # MyInvestor
    ("ABONO POR TRANSFERENCIA", "Renta Variable", "Compra"),  # MyInvestor - aportación a fondos
    ("CARGO POR TRANSFERENCIA", "Renta Variable", "Venta"),   # MyInvestor - rescate de fondos
    
    ("INTEREST PAYMENT", "Inversión", "Intereses"),  # Trade Republic
    ("INTERÉS", "Inversión", "Intereses"),
    ("INTERESES", "Inversión", "Intereses"),
    ("SIN CONCEPTO", "Inversión", "Rebalanceo"),  # Trade Republic - intereses/rebalanceo
    ("NEXO", "Cripto", "Nexo"),
    ("BINANCE", "Cripto", "Binance"),
    ("BIT2ME", "Cripto", "Bit2Me"),
     ("RAMP SWAPS", "Cripto", "RAMP"),  # Plataforma DeFi
     ("MRCR", "Cripto", "MRCR"),  # Mobile payment Cripto
     ("TRANSF. CONCEPTO NO ESPECIFICADO", "Cripto", "Otros"),  # Transferencias genéricas en Cripto
     ("PLAN DE INVERSION", "Renta Variable", "Compra"),
    ("SAVINGS PLAN EXECUTION", "Renta Variable", "Compra"),  # Trade Republic

    # ===== WALLAPOP =====
    ("MANGOPAY", "Wallapop", ""),  # Payment processor de Wallapop
    ("WALLAPOP", "Wallapop", ""),

    # ===== ABONOS EN TARJETA (Devoluciones/Reembolsos de bancos) =====
    ("ABONO EN LA TARJETA", "Cashback", ""),  # Reembolsos/abonos a tarjeta (sin merchant)
    
    # ===== REGULARIZACIONES Y AJUSTES =====
    ("REGULARIZACION COMPRA EN", "Cashback", ""),  # Regularizaciones de compra sin merchant
    ("REGULARIZACION APPLE", "Suscripciones", "Apple"),  # Regularización Apple pay
    ("RETR. COMPRA RENTA", "Inversión", "Intereses"),  # Retorno de compra de renta variable

    # ===== VIVIENDA =====
    ("TATIANA", "Vivienda", "Limpieza"),
    ("SANTALLANA", "Vivienda", "Limpieza"),

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

     # ===== PATRONES ESPECIALES =====
    # Revolut con formato especial (Revolut**XXXX*)
    ("REVOLUT**", "Transferencia", "Interna"),
    
     # ===== REGLAS GENERADAS AUTOMÁTICAMENTE =====

    # --- Alimentación ---
    ("BODEGA ANTONIO PEREZNULL", "Alimentación", "Bodega"),
    ("CARREF CARTAGENA II", "Alimentación", "Carrefour"),
    ("CARREF CARTANULL", "Alimentación", "Carrefour"),
    ("FROIZ ILLA", "Alimentación", "Supermercado"),
    ("FROIZ PLAZA DEL TORAL", "Alimentación", "Supermercado"),
    ("FRUTA Y VERDURA CARTAGENA", "Alimentación", "Frutería"),
    ("KAFFEKAPSLEN", "Alimentación", "Café"),
    ("LA COLEGIALA", "Alimentación", "Panadería"),
    ("MARKET MOTRIL", "Alimentación", "Supermercado"),
    ("MIGA DE ORO JIMENEZ DE LA", "Alimentación", "Panadería"),
    ("PESCADOS HERMANOS AGUERA", "Alimentación", "Pescadería"),
    ("RAMIZ IQBALNULL", "Alimentación", "Frutería"),
    ("SUPERMERCADOS ULLOA, SL.", "Alimentación", "Supermercado"),
    ("VENTA EL CABEZO", "Alimentación", "Frutería"),
    ("VENTA EL PALMERALNULL", "Alimentación", "Frutería"),
    ("VENTA EL PUERTO 3", "Alimentación", "Frutería"),
    ("VENTA HNOS BLAYA", "Alimentación", "Frutería"),

    # --- Compras ---
    ("ALLTRICKS", "Compras", "Deporte"),
    ("BKT MAD PARK V PREPAGO", "Compras", "Otros"),
    ("CAMINO FACIL", "Compras", "Deporte"),
    ("DEPORTES JSC CAZA Y PESCA", "Compras", "Niños"),
    ("DEPORVILLAGENULL", "Compras", "Deportes"),
    ("DI ZHONG HAI SL", "Compras", "Bazar"),
    ("EXPPREGUNT", "Compras", "Estanco"),
    ("EXPPUERTASDEMURCIA", "Compras", "Estanco"),
    ("GOONSHOP.ES", "Compras", "Deporte"),
    ("HPY*EKOSPORT", "Compras", "Deporte"),
    ("IMPERIO ROJONULL", "Compras", "Bazar"),
    ("KUTPHONE", "Compras", "Electrónica"),
    ("MANZANARES RUIZ SA", "Compras", "Otros"),
    ("MARIA DEL MAR SANCHEZ LOP", "Compras", "Otros"),
    ("MDC CIMALP", "Compras", "Deportes"),
    ("MERCA HYWNULL", "Compras", "Bazar"),
    ("SAN LUCAR DE BARRAMEDA", "Compras", "Estanco"),
    ("SORIA MARINA SL", "Compras", "Otros"),
    ("SP ALL4CYCLING", "Compras", "Deporte"),
    ("SP LILIENTHAL BERLIN", "Compras", "Otros"),
    ("SUPERTREBOL", "Compras", "Otros"),
    ("WE LOVE COOKING S.L.", "Compras", "Hogar"),
    ("WE LOVE COOKING S.L.NULL", "Compras", "Hogar"),
    ("WH SMITH AEROPUERTO MADRI", "Compras", "Otros"),
    ("WWW.CURIOSITE.ESNULL", "Compras", "Curiosite"),
    ("WWW.GROUPON.ES", "Compras", "Groupon"),

    # --- Cripto ---
    ("RAMP SWAPS LTDNULL", "Cripto", "RAMP"),

    # --- Deportes ---
    ("CDE RUGBY ALCORCON", "Deportes", "Club"),
    ("RUGBY", "Deportes", "Club"),  # Mejora Punto 3

    # --- Efectivo ---
    ("CASH LEPE JAMON 296", "Efectivo", "Retirada cajero"),

    # --- Interna ---
    ("130580288", "Interna", ""),

    # --- Ocio y Cultura ---
    ("ENTRADAS CINE", "Ocio y Cultura", "Cines"),
    ("ENTRADAS CINENULL", "Ocio y Cultura", "Cines"),
    ("TCB GIRA 4", "Ocio y Cultura", "Entradas"),

    # --- Restauración ---
    ("1433 / LEVANTE", "Restauración", "Otros"),
    ("A SFUENTIDUENA DEL TAJO", "Restauración", "Otros"),
    ("ALAMBIQUE BARNULL", "Restauración", "Otros"),
    ("ARIZONA RUTA 66 ROCK BARNULL", "Restauración", "Otros"),
    ("AVALON CARTAGENA", "Restauración", "AVALON CARTAGENA"),
    ("BAMBU BEACH", "Restauración", "Bar"),
    ("BOCABEACH", "Restauración", "Otros"),
    ("BODEGAS LA FUENTE", "Restauración", "Bodega"),
    ("CAFESTORE M50 EXTERIOR", "Restauración", "Cafetería"),
    ("CAMPING ENTREROBLES", "Restauración", "Otros"),
    ("CAPRICHO", "Restauración", "Bares"),
    ("CHAMFER", "Restauración", "Chamfer"),
    ("CHAMFER BURGER CENTRO", "Restauración", "Otros"),
    ("CIEN MONTADITOS CARTAG", "Restauración", "Fast food"),
    ("D LIONULL", "Restauración", "Otros"),
    ("DASEBAS URBAN FOOD", "Restauración", "Otros"),
    ("EL MOLI PAN Y CAFE", "Restauración", "Cafetería"),
    ("EL ORIGEN", "Restauración", "Otros"),
    ("EL PURGATORIO BARNULL", "Restauración", "Otros"),
    ("EL ULTIMO PENELOPE", "Restauración", "Bares"),
    ("EL ULTIMO PENELOPENULL", "Restauración", "Bares"),
    ("GRUPO SABORES DEL MAR", "Restauración", "Otros"),
    ("GUEVARANULL", "Restauración", "Bares"),
    ("HOSTELERIA Y OCIO AMS", "Restauración", "Bares"),
    ("HOSTELERIA Y OCIO AMSNULL", "Restauración", "Bares"),
    ("JAVI MIRA", "Restauración", "Bares"),
    ("JIJONENCA CARTAGENA", "Restauración", "Heladería"),
    ("JOKER", "Restauración", "Bares"),
    ("LA GASTROTASQUITA", "Restauración", "Bar"),
    ("LA MARINA", "Restauración", "Otros"),
    ("LA PARADA DE IONUT", "Restauración", "Otros"),
    ("LA POSADA DE LA PUEBLA", "Restauración", "La Posada de la Puebla"),
    ("MASTIACRAFTBEER", "Restauración", "Mastia Craft Beer"),
    ("MIAJANULL", "Restauración", "Bares"),
    ("MIRADOR DA BREA", "Restauración", "Otros"),
    ("NEWREST TRAVEL RETAIL", "Restauración", "Otros"),
    ("O BALCON DAS BRANAS", "Restauración", "Otros"),
    ("PASO DE LA SERRA (LAGUNA", "Restauración", "Otros"),
    ("PETISCOS DO CARDEAL", "Restauración", "Otros"),
    ("PORTOMINO", "Restauración", "Otros"),
    ("PRTA LOS TRISTES/EL PASEO", "Restauración", "Otros"),
    ("PULPERIA LUIS", "Restauración", "Pulpería Luis"),
    ("REST. RUTA DE LAS NIEVES", "Restauración", "Otros"),
    ("SCABETTI", "Restauración", "Scabetti"),
    ("SERVIAREAS 2000", "Restauración", "Otros"),
    ("SUMUP *PROYECTOS MAIARA", "Restauración", "Alpujarras"),
    ("SUPERBARNULL", "Restauración", "Otros"),
    ("TAKOS", "Restauración", "Takos"),
    ("TAKOSNULL", "Restauración", "Takos"),
    ("TIRABUZON", "Restauración", "Bares"),
    ("UPPER", "Restauración", "SUPERMERCADO UPPER 948"),
    ("VIRGINIA ROCA PUESTO 16", "Restauración", "Otros"),

    # --- Ropa y Calzado ---
    ("ASOS.COM", "Ropa y Calzado", "Ropa y Accesorios"),
    ("PAYPAL *ACTURUSCAPINULL", "Ropa y Calzado", "El Ganso"),
    ("SP VIVAMODA.ES", "Ropa y Calzado", "Ropa y Accesorios"),
    ("SP VIVAMODA.ESNULL", "Ropa y Calzado", "Ropa y Accesorios"),
    ("WWW.WOLVERINEWORLDWIDE", "Ropa y Calzado", "Ropa y Accesorios"),
    ("ZARA", "Ropa y Calzado", "CARREFOUR ZARAICHE"),

    # --- Salud y Belleza ---
    ("AIRAM", "Salud y Belleza", "Fisioterapia"),
    ("INPYLUS", "Salud y Belleza", "Clínica capilar"),

    # --- Suscripciones ---
    ("CLAUDE.AI SUBSCRIPTIONNULL", "Suscripciones", "Software/IA"),
    ("COOKIDOO VORWERK INT.", "Suscripciones", "Cocina/Recetas"),
    ("HETZNER ONLINE GMBH", "Suscripciones", "Cloud/Backup"),
    ("HETZNER ONLINE GMBHNULL", "Suscripciones", "Cloud/Backup"),

    # --- Transporte ---
    ("AUTOESCUELA MAC", "Transporte", "Autoescuela"),
    ("ES BP PUEBLA DE SANABRIA", "Transporte", "Combustible"),
    ("EST. SERV. DPM", "Transporte", "Combustible"),
    ("MONFOBUS, S.L.", "Transporte", "Transporte público"),
    ("ORA LOGRO¥O", "Transporte", "Aparcamiento/Peajes"),
    ("PK AEROPUERTO ALICANTE", "Transporte", "Parking"),
    ("PK SAN ANTONIO", "Transporte", "Parking"),
    ("PLENERGY US 147 CARTAGENA", "Transporte", "Combustible"),
    ("PLENERGY US 147 CARTAGENANULL", "Transporte", "Combustible"),
    ("PLENERGY US373 CARTAGENANULL", "Transporte", "Combustible"),
    ("REPUESTOS BASINULL", "Transporte", "Taller"),
    ("REVEPETROL", "Transporte", "Combustible"),
    ("ROYMAGA PETROLEOS S.L", "Transporte", "Combustible"),
    ("TALLERES JUAN PEDRO PEREZ", "Transporte", "Taller"),
    ("TAXI NUM. 1", "Transporte", "Taxi"),
    ("TEDITRONIC SL POLIGONONULL", "Transporte", "Taller"),
    ("US 109 PLENOIL VILANOVA D", "Transporte", "Combustible"),
    ("US147 PLENOIL CARTAGENA I", "Transporte", "Combustible"),

    # --- Viajes ---
    ("ALBERGUE O CRUCEIRO", "Viajes", "Alojamiento"),
    ("CIVITATIS TOURS", "Viajes", "Tour guiado"),

    # --- Vivienda ---
     ("PINTURAS BRIZ CARTAGENA", "Vivienda", "Mantenimiento"),

    # ===== S18: ANÁLISIS EXHAUSTIVO COMPRAS/OTROS =====
    # Agregados 229 merchants del análisis de 578 transacciones Compras/Otros
    # Objetivo: Reducir de 578 → ~243 txs, aumentar cobertura a 98.4%
    # Fuente: análisis exploratorio de merchants duplicados, ALTA/MEDIA confianza
    ("52147 HIPER ENT", "Alimentación", "Supermercado"),
    ("631 - TT AER BCN", "Viajes", "Aeropuerto"),
    ("713 Coop Pronto", "Alimentación", "Supermercado"),
    ("A.S. BASSELLA", "Deportes", "Club"),
    ("A.S. LAS SALINAS", "Deportes", "Club"),
    ("ADC EXECUTIVE CARS", "Transporte", "Taxi"),
    ("ADMON LOTERIA", "Compras", "Otros"),
    ("AEROPORT", "Viajes", "Aeropuerto"),
    ("AGRUPACION DINAMIA", "Restauración", "Cafetería"),
    ("AIRBNB", "Viajes", "Alojamiento"),
    ("ALDEASA", "Viajes", "Aeropuerto"),
    ("ALE HOP", "Compras", "Regalos"),
    ("ALLZONE.ES", "Compras", "Electrónica"),
    ("AP.EST.ALICANTE", "Transporte", "Parking"),
    ("AQUARIO", "Compras", "Mascotas"),
    ("AREAS LA PLANA", "Restauración", "Otros"),
    ("ARISE OPERATING", "Compras", "Electrónica"),
    ("ARO AQUA FITNESS", "Deportes", "Otros"),
    ("ATM-PORTAL INSCRIPCIONES", "Deportes", "Otros"),
    ("AUTOS PABLO SANCHEZ", "Transporte", "Otros"),
    ("Accelevox", "Suscripciones", "Software"),
    ("BAILA FM", "Ocio y Cultura", "Espectáculos"),
    ("BALLENOIL", "Transporte", "Combustible"),
    ("BALNEARIO AIRE", "Salud y Belleza", "Otros"),
    ("BERSHKA", "Ropa y Calzado", "Ropa"),
    ("BEST BUY", "Compras", "Electrónica"),
    ("BICICLETAS M.R.", "Deportes", "Otros"),
    ("BOLUMERCA", "Alimentación", "Supermercado"),
    ("BORDEAUX INTERN", "Viajes", "Aeropuerto"),
    ("BRAINTREECHARGE", "Suscripciones", "Software"),
    ("BRICO HOUSE", "Vivienda", "Bricolaje"),
    ("BRICOFIRE", "Vivienda", "Bricolaje"),
    ("BRICOR", "Vivienda", "Bricolaje"),
    ("BUNDESBAHN", "Transporte", "Público"),
    ("BUSCALIBRE", "Compras", "Libros"),
    ("Bios Personenvervoer", "Transporte", "Público"),
    ("C&A", "Ropa y Calzado", "Ropa"),
    ("C.M. ", "Salud y Belleza", "Otros"),
    ("CAFFETIA VENDING", "Restauración", "Cafetería"),
    ("CAMPING", "Viajes", "Alojamiento"),
    ("CARMEN SALCEDO AGUDO", "Restauración", "Cafetería"),
    ("CARNES", "Compras", "Alimentación"),
    ("CARNES CARTAGEN", "Compras", "Alimentación"),
    ("CARNISSERIA", "Compras", "Alimentación"),
    ("CARTHON FERRIERE", "Vivienda", "Bricolaje"),
    ("CASH CONVERTERS", "Compras", "Otros"),
    ("CERBERU TELEGESTION", "Viajes", "Alojamiento"),
    ("CERVERZA FRIA", "Restauración", "Otros"),
    ("COLINAS GREEN GOLF", "Deportes", "Otros"),
    ("COLLIDUS TROFEOS", "Deportes", "Otros"),
    ("COMFERSA", "Transporte", "Otros"),
    ("CONSERVEIRA BOLHAO", "Alimentación", "Otros"),
    ("CORP.ALIM.GUISSONA", "Alimentación", "Supermercado"),
    ("COSMETICS", "Salud y Belleza", "Otros"),
    ("CROCANTICKETS", "Ocio y Cultura", "Espectáculos"),
    ("CRV*DEPORTIVO SANTA", "Deportes", "Otros"),
    ("CRV*PESCADOS", "Compras", "Alimentación"),
    ("CRV*SP BIOKSAN", "Salud y Belleza", "Farmacia"),
    ("CRV*TOP4RUNNIN", "Deportes", "Otros"),
    ("CRYSTAL MEDIA", "Compras", "Electrónica"),
    ("Coop-1962 GE Serve", "Alimentación", "Supermercado"),
    ("DANIEL GONZALEZ SANCHEZ", "Restauración", "Otros"),
    ("DEVON CARS", "Transporte", "Otros"),
    ("DIAMARKET", "Alimentación", "Supermercado"),
    ("DINASA REPARACIONES", "Transporte", "Otros"),
    ("DIXONS", "Compras", "Electrónica"),
    ("DRINKSANDCO", "Alimentación", "Otros"),
    ("DRUNI", "Salud y Belleza", "Farmacia"),
    ("EE.SS", "Transporte", "Combustible"),
    ("EFECTO 2000", "Compras", "Electrónica"),
    ("EL CANTON DE", "Restauración", "Otros"),
    ("EL CHORRILLO", "Restauración", "Otros"),
    ("EL SUENO DE JEMIK", "Restauración", "Cafetería"),
    ("ELHA LASER", "Salud y Belleza", "Otros"),
    ("ENHARINARTE", "Restauración", "Cafetería"),
    ("ENTERPRISE RENT", "Transporte", "Otros"),
    ("ENVALIA GROUP", "Servicios Consultoría", "Otros"),
    ("ERAMNSA", "Transporte", "Parking"),
    ("ESPACIO CASA", "Vivienda", "Decoración"),
    ("EST SERV", "Transporte", "Combustible"),
    ("EST.SERV", "Transporte", "Combustible"),
    ("FCC MADNESS BUSINESS", "Ocio y Cultura", "Espectáculos"),
    ("FDN ALMEIDA GARRET", "Ocio y Cultura", "Otros"),
    ("FEU VERT", "Transporte", "Otros"),
    ("FGW SELF SERVICE", "Transporte", "Público"),
    ("FOODTOPIA", "Alimentación", "Supermercado"),
    ("FOR RIDERS", "Deportes", "Otros"),
    ("FRANCISCO JOSE DIAZ URAN", "Restauración", "Otros"),
    ("FRANPE PR", "Restauración", "Otros"),
    ("FREENOW", "Transporte", "Taxi"),
    ("FUTBOL CENTER", "Deportes", "Otros"),
    ("GEODA PULPI", "Ocio y Cultura", "Espectáculos"),
    ("GODADDY", "Suscripciones", "Software"),
    ("GOIKO", "Restauración", "Otros"),
    ("GRUPO 4 CARTAGENA", "Restauración", "Cafetería"),
    ("GRUPO MAICAS PEIRO", "Restauración", "Cafetería"),
    ("GVB", "Transporte", "Público"),
    ("Gall & Gall", "Alimentación", "Otros"),
    ("H10", "Viajes", "Alojamiento"),
    ("HC CARNES", "Compras", "Alimentación"),
    ("HIBISCUS TOWN", "Restauración", "Otros"),
    ("HIPER HF", "Alimentación", "Supermercado"),
    ("HNOS SANCHEZ GOMEZ", "Alimentación", "Otros"),
    ("HOBBY MODELISMO", "Compras", "Juguetes"),
    ("HORIZONTALIA", "Vivienda", "Decoración"),
    ("HOSPES", "Viajes", "Alojamiento"),
    ("HOSPITAL", "Salud y Belleza", "Otros"),
    ("HOSTEL", "Viajes", "Alojamiento"),
    ("HOTEL", "Viajes", "Alojamiento"),
    ("IMPORT & EXPORT XINLAN", "Compras", "Otros"),
    ("INFINITY STORE", "Compras", "Electrónica"),
    ("INSTANT GAMING", "Suscripciones", "Streaming"),
    ("INVERSIONES SUAPO", "Restauración", "Otros"),
    ("JET 2", "Viajes", "Aeropuerto"),
    ("JUAN LUIS PEREZ AZNAR", "Restauración", "Otros"),
    ("KAMPAMENTO BASE", "Deportes", "Otros"),
    ("KAVE HOME", "Vivienda", "Decoración"),
    ("KEFIREK", "Alimentación", "Otros"),
    ("KINEPOLIS", "Ocio y Cultura", "Espectáculos"),
    ("KINGNUTRICION", "Salud y Belleza", "Otros"),
    ("KINGUIN", "Suscripciones", "Streaming"),
    ("KINOMAP", "Suscripciones", "Software"),
    ("KOKOHA CHURRERIA", "Restauración", "Cafetería"),
    ("KRIPLUS HYPERMEDIA", "Compras", "Electrónica"),
    ("KUMAR DONER KEBAB", "Restauración", "Otros"),
    ("LA CATA Y AROMAS DEL VINO", "Alimentación", "Otros"),
    ("LA HERRADURA", "Restauración", "Otros"),
    ("LA JIJONENCA", "Restauración", "Cafetería"),
    ("LA LAGUNA DE U¥A", "Viajes", "Alojamiento"),
    ("LACARBONERIA", "Restauración", "Otros"),
    ("LAVI RESTURACION", "Restauración", "Otros"),
    ("LDO PABLO CERVANTES", "Salud y Belleza", "Otros"),
    ("LLAOLLAO", "Restauración", "Cafetería"),
    ("LONJA", "Compras", "Alimentación"),
    ("MANPER E HIJOS", "Alimentación", "Supermercado"),
    ("MANTEIGARIA", "Restauración", "Cafetería"),
    ("MANZANARES RUIZ", "Alimentación", "Otros"),
    ("MARCOS MOTOR", "Transporte", "Otros"),
    ("MARIA DEL MAR SANCHEZ", "Restauración", "Cafetería"),
    ("MARKET VALLADOL", "Alimentación", "Supermercado"),
    ("MC AUTO", "Transporte", "Otros"),
    ("MICROSOFT", "Suscripciones", "Software"),
    ("MODREGO", "Vivienda", "Decoración"),
    ("MUNDO ANIMAL", "Compras", "Mascotas"),
    ("NATURCAMI¥O", "Viajes", "Alojamiento"),
    ("NEGRILLO.ES", "Alimentación", "Otros"),
    ("NEW SOUTHERN RAILW", "Transporte", "Público"),
    ("NORDVPN", "Suscripciones", "Software"),
    ("NOTINO", "Salud y Belleza", "Otros"),
    ("NUEVA BAHIA", "Restauración", "Otros"),
    ("NUEVO MUNDO", "Restauración", "Cafetería"),
    ("NVIDIA", "Compras", "Electrónica"),
    ("NYX*AIRservSpain", "Viajes", "Aeropuerto"),
    ("OFICINA DEL PEREGRINO", "Viajes", "Otros"),
    ("OMIO", "Transporte", "Público"),
    ("ONECLICK GRANADA", "Compras", "Electrónica"),
    ("OPENAI", "Suscripciones", "Software"),
    ("ORTU¥O RUBIO", "Restauración", "Cafetería"),
    ("OUTLET PC", "Compras", "Electrónica"),
    ("One Hundred Restrooms", "Ocio y Cultura", "Otros"),
    ("PABLO FERNANDEZ-PACHECO", "Restauración", "Otros"),
    ("PASTISSERIA LESPIGA", "Restauración", "Cafetería"),
    ("PC EXPANSION", "Compras", "Electrónica"),
    ("PC INFOR RED", "Compras", "Electrónica"),
    ("PEDRO RODRIGUEZ LUQUE", "Restauración", "Otros"),
    ("PESCADOS CABOMAR", "Compras", "Alimentación"),
    ("PESCADOS MARIA", "Compras", "Alimentación"),
    ("PETROPRIX", "Transporte", "Combustible"),
    ("PETROPRIX SALOBRE", "Transporte", "Combustible"),
    ("PF CHANG", "Restauración", "Otros"),
    ("PIC NEGRE VI", "Alimentación", "Otros"),
    ("PIZZERIA", "Restauración", "Otros"),
    ("PIZZERIA ANGELO", "Restauración", "Otros"),
    ("PIZZERIA LARA", "Restauración", "Otros"),
    ("PIZZERIA SAPRI", "Restauración", "Otros"),
    ("PIZZERIA ¥AM ¥AM", "Restauración", "Otros"),
    ("PKP", "Transporte", "Público"),
    ("PLENOIL", "Transporte", "Combustible"),
    ("PP *", "Finanzas", "Comisiones"),
    ("PRICEMINISTER", "Compras", "Otros"),
    ("PROGRAMER", "Compras", "Electrónica"),
    ("PROMOFARMA", "Salud y Belleza", "Farmacia"),
    ("PULL&BEAR", "Ropa y Calzado", "Ropa"),
    ("Pontevedr-Vigo", "Transporte", "Público"),
    ("PullandBear", "Ropa y Calzado", "Ropa"),
    ("RED LOBSTER", "Restauración", "Otros"),
    ("RENTKAYAKS", "Deportes", "Otros"),
    ("REPUESTOS PAGAN", "Transporte", "Otros"),
    ("RESIDENCE", "Viajes", "Alojamiento"),
    ("ROCKOLA SUMMER CLUB", "Ocio y Cultura", "Espectáculos"),
    ("ROYAL DELUXE IMPORT", "Compras", "Otros"),
    ("RTE. FERNANDEZ", "Restauración", "Otros"),
    ("Revolut", "Finanzas", "Comisiones"),
    ("SARAO GOURMET", "Restauración", "Otros"),
    ("SCHIPHOL", "Transporte", "Público"),
    ("SEA VIEW ALBIR", "Restauración", "Otros"),
    ("SEITT R3 R5", "Transporte", "Parking"),
    ("SHELL OIL", "Transporte", "Combustible"),
    ("SP EIFFELTEXTILE", "Ropa y Calzado", "Otros"),
    ("SP OFFICIALRWC", "Deportes", "Otros"),
    ("SP TRAK RACER", "Deportes", "Otros"),
    ("SPACE DESIGNER 3D", "Suscripciones", "Software"),
    ("SPACEFOOT", "Ropa y Calzado", "Calzado"),
    ("SPAZIO MOTOR", "Transporte", "Otros"),
    ("SPRINTER", "Ropa y Calzado", "Calzado"),
    ("SUPER SONIDO", "Compras", "Electrónica"),
    ("Santiago -Caldas", "Transporte", "Público"),
    ("Santiago -Pontevedr", "Transporte", "Público"),
    ("Satelite 20", "Restauración", "Otros"),
    ("SumUp *jesus ripol", "Restauración", "Otros"),
    ("TECTELTIC", "Compras", "Electrónica"),
    ("TESCO METRO", "Alimentación", "Supermercado"),
    ("THE AULD DUBLINER", "Restauración", "Otros"),
    ("TICKETMASTER", "Ocio y Cultura", "Espectáculos"),
    ("TODOHOBBY", "Compras", "Juguetes"),
    ("TOMAS GUILLEN GUILLEN", "Restauración", "Otros"),
    ("Tangem AG", "Compras", "Electrónica"),
    ("USCUSTOMS ESTA", "Viajes", "Otros"),
    ("UZR*Bike 24", "Deportes", "Otros"),
    ("VILA VINITECA", "Alimentación", "Otros"),
    ("VINOS Y MAS", "Alimentación", "Otros"),
    ("Vorwerk International", "Vivienda", "Otros"),
    ("WDFG MADRID", "Viajes", "Aeropuerto"),
    ("WORLD OF DELIGHTS", "Alimentación", "Otros"),
    ("WP *carnespacorosa", "Compras", "Alimentación"),
    ("WZP - Custtomjerseys", "Deportes", "Otros"),
    ("www.wheelstandpro.com", "Deportes", "Otros"),
]


def extract_merchant_from_compra_en(descripcion: str) -> Optional[str]:
    """
    Extrae el nombre del merchant desde el patrón "COMPRA EN [MERCHANT], CON LA TARJETA..."
    
    Ejemplos:
        "Apple pay: COMPRA EN CARTAGO PADEL, CON LA TARJETA : 548913..." → "CARTAGO PADEL"
        "COMPRA EN MADRID, CON LA TARJETA DE CRÉDITO" → "MADRID"
    
    Args:
        descripcion: Descripción de la transacción
    
    Returns:
        Nombre del merchant limpio, o None si no hay patrón
    """
    import re
    # Busca "COMPRA EN X" donde X está entre COMPRA EN y una de estas terminaciones:
    # - ", CON LA TARJETA" (genérico)
    # - ", DE CREDITO" 
    # - final de línea
    match = re.search(
        r'COMPRA EN\s+(.+?)(?:,\s*(?:CON LA TARJETA|DE CREDITO|DE CRÉDITO)|$)',
        descripcion,
        re.IGNORECASE
    )
    
    if match:
        merchant = re.sub(r'\s+', ' ', match.group(1).strip())
        # Limpiar caracteres especiales finales que no son relevantes
        merchant = re.sub(r'\s*[:;]?\s*$', '', merchant)
        return merchant
    
    return None


def lookup_merchant(descripcion, merchant_name=None):
    """
    Busca keywords en la descripción y en el merchant extraído.
    
    Flujo:
    1. Extrae merchant del patrón "COMPRA EN X" si existe
    2. Busca nombre exacto en Google Places merchants (muy específico)
    3. Busca nombre exacto en merchants por nombre completo (nuevo)
    4. Busca keywords dentro del merchant extraído (preciso)
    5. Fallback: busca keywords en descripción completa (genérico)
    
    Args:
        descripcion: Descripción completa de la transacción
        merchant_name: Nombre del merchant extraído (opcional)

    Returns:
        Tupla (Cat1, Cat2) si hay match, None si no
    """
    import re
    
    desc_upper = descripcion.upper()
    
    # 1. Intentar extraer merchant del patrón "COMPRA EN X"
    extracted_merchant = extract_merchant_from_compra_en(descripcion)
    
    # 2. PRIORIDAD MÁXIMA: Buscar en Google Places merchants (exacto)
    candidates = [merchant_name, extracted_merchant]
    for merchant in candidates:
        if merchant and merchant in GOOGLE_PLACES_MERCHANTS:
            merchant_data = GOOGLE_PLACES_MERCHANTS[merchant]
            return (merchant_data['cat1'], merchant_data['cat2'])
    
    # 3. PRIORIDAD ALTA: Buscar en merchants por nombre completo (exacto, new)
    for merchant in candidates:
        if merchant and merchant in FULLNAME_MERCHANTS:
            merchant_data = FULLNAME_MERCHANTS[merchant]
            return (merchant_data['cat1'], merchant_data['cat2'])
    
    # 4. PRIORIDAD MEDIA: Buscar keywords DENTRO del merchant extraído (más preciso)
    search_texts_with_merchant = []
    if extracted_merchant:
        search_texts_with_merchant.append(extracted_merchant.upper())
    if merchant_name:
        search_texts_with_merchant.append(merchant_name.upper())
    
    # Luego descripción completa como fallback
    search_texts_full = search_texts_with_merchant + [desc_upper]
    
    for keyword, cat1, cat2 in MERCHANT_RULES:
        keyword_upper = keyword.upper()
        
        # Caso especial: DIA % requiere word boundary
        if keyword == "DIA %":
            for text in search_texts_full:
                if re.search(r'\bDIA\b', text):
                    return (cat1, cat2)
            continue
        
        # Búsqueda normal: primero en merchants extraídos (más preciso)
        for text in search_texts_with_merchant:
            if keyword_upper in text:
                return (cat1, cat2)
        
        # Luego en descripción completa (fallback)
        if keyword_upper in desc_upper:
            return (cat1, cat2)
    
    return None
