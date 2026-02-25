"""
Whitelist de combinaciones válidas Cat1|Cat2.
Solo se pueden devolver combinaciones que existen en los datos reales.
"""

VALID_COMBINATIONS = {
    "Alimentación": ["Alcampo", "Aldi", "Alimentación", "Bodega", "Café", "Carnicería", "Carrefour", "Cash & Carry", "Consum", "Conveniencia", "Dia", "Eroski", "Frutería", "GM Cash", "Higinio", "Lidl", "Mercado", "Mercadona", "Otros", "Panadería", "Pescadería", "Supermercado", "Vinos"],
    "Aportación": [""],
    "Bizum": [""],
    "Bonificación familia numerosa": [""],
    "Cashback": [""],
    "Comisiones": ["", "Custodia", "Retenciones"],
    "Compras": ["Agencia de viajes", "Aliexpress", "Amazon", "Bazar", "Centro comercial", "Cines", "Colegio", "Combustible", "Decathlon", "Deportes", "Devoluciones", "El Corte Inglés", "Electrónica", "Estancos", "Estética", "Ferretería", "Gimnasio", "Hogar", "Hospital", "Joyería", "Juguetería", "Lavado", "Leroy Merlin", "Libros", "Loterías", "Muebles", "Museos", "Online", "Otros", "Panadería", "Parques", "PayPal", "Peluquería", "Regalos", "Ropa y Calzado", "Spa", "Taller", "Tecnología", "Transporte público", "Videojuegos", "eCommerce"],
    "Cripto": ["Binance", "Bit2Me", "MEXC", "MRCR", "Nexo", "Otros", "RAMP"],
     "Cuenta Común": ["", "Hogar"],
    "Deportes": ["Club", "Pádel"],
    "Depósitos": [""],
    "Dividendos": [""],
    "Divisas": [""],
    "Efectivo": ["Ingreso", "Regularización", "Retirada", "Retirada cajero"],
    "Externa": [""],
    "Finanzas": ["Ahorro", "Gestoría", "Hipoteca", "Liquidación", "Otros", "Préstamos", "Tarjeta Crédito"],
    "Fondos": [""],
    "Impuestos": ["AEAT", "Autónomos", "Circulación", "IBI", "IRPF", "IVA", "Retenciones", "Seguridad Social"],
    "Ingreso": ["Devoluciones", "Intereses", "Otros", "Prestación", "Retrocesión", "Seguros"],
    "Interna": [""],
    "Inversión": ["Intereses", "Rebalanceo"],
    "Liquidación": [""],
    "Nómina": [""],
    "Ocio y Cultura": ["Cines", "Conciertos", "Donaciones", "Entradas", "Entretenimiento", "Juegos", "Museos", "Otros"],
     "Otros": ["", "Devoluciones", "Extraordinario", "Prestación", "Retrocesión", "Seguros"],
    "Recibos": ["Agua", "Alarma", "Asesoría", "Devoluciones", "Donaciones", "Fotovoltaica", "Gas", "Gimnasio", "Luz", "Otros", "Telefonía e Internet"],
    "Renta Variable": ["Compra", "Venta"],
    "Restauración": ["", "Bar", "Bares", "Bodega", "Cafetería", "Churrería", "Fast food", "Heladería", "Japonés", "Kiosco", "Mesón", "Otros", "Restaurante", "SUPERMERCADO UPPER 948", "Takos"],
    "Ropa y Calzado": ["CARREFOUR ZARAICHE", "El Ganso", "Otros", "Ropa y Accesorios", "Ropa y Calzado"],
    "Salud y Belleza": ["Clínica capilar", "Clínica dental", "Farmacia", "Fisioterapia", "Médico", "Otros", "Peluquería", "Perfumería", "Óptica"],
    "Seguros": ["Casa", "Otros", "Salud", "Seguros Generales", "Seguros Vida", "Viajes/General", "Vida"],
    "Servicios Consultoría": [""],
    "Suscripciones": ["Apple", "Audible", "Música", "Otros", "Streaming", "Waylet"],
    "Transporte": ["Aparcamiento/Peajes", "Combustible", "Devoluciones", "ITV", "Metro/Tranvía", "Otros", "Parking", "Peajes", "Taller", "Taxi", "Transporte público", "Tren"],
    "Viajes": ["Aeropuerto/Duty Free", "Alojamiento", "Otros", "Vuelos"],
    "Vivienda": ["Comunidad", "Limpieza", "Mantenimiento", "Otros", "Reformas"],
    "Wallapop": [""],
}


def validate_combination(cat1, cat2):
    """
    Valida que una combinación Cat1+Cat2 sea válida.
    Si no lo es, intenta forzar Cat2 válido.
    """
    if cat1 not in VALID_COMBINATIONS:
        return cat1, cat2  # Cat1 desconocido, dejar pasar

    if cat2 in VALID_COMBINATIONS[cat1]:
        return cat1, cat2  # Combinación válida

    # Intentar forzar Cat2 válido
    if "Otros" in VALID_COMBINATIONS[cat1]:
        return cat1, "Otros"
    elif "" in VALID_COMBINATIONS[cat1]:
        return cat1, ""
    else:
        # Usar el primero disponible
        return cat1, VALID_COMBINATIONS[cat1][0]
