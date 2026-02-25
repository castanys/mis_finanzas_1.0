"""
Taxonomía canónica v2 de Finsense.
Define TODAS las combinaciones válidas de Tipo > Cat1 > Cat2.
Cualquier combinación fuera de esta lista es un ERROR.
"""

TAXONOMIA = {
    "GASTO": {
        "Alimentación": ["Mercadona", "Lidl", "Carnicería", "Carrefour", "Cash & Carry", "Frutería", "Eroski", "Bodega", "Higinio", "Mercado", "Panadería", "Vinos", "Otros", "Devoluciones"],
        "Compras": ["Amazon", "El Corte Inglés", "Leroy Merlin", "Decathlon", "Aliexpress", "Online", "Tecnología", "Hogar", "Estancos", "Loterías", "Bazar", "Deportes", "Ropa y Calzado", "Muebles", "Videojuegos", "Otros", "Devoluciones"],
        "Restauración": ["Restaurante", "Bar", "Cafetería", "Fast food", "Heladería", "Japonés", "Otros", "Devoluciones"],
        "Recibos": ["Telefonía e Internet", "Luz", "Agua", "Gas", "Gimnasio", "Alarma", "Asesoría", "Donaciones", "Fotovoltaica", "Otros", "Devoluciones"],
        "Seguros": ["Casa", "Vida", "Coche", "Otros", "Devoluciones"],
        "Transporte": ["Combustible", "Peajes", "Parking", "Transporte público", "Taxi", "Taller", "Otros", "Devoluciones"],
        "Finanzas": ["Hipoteca", "Préstamos", "Ahorro", "Liquidación", "Gestoría", "Otros", "Devoluciones"],
        "Impuestos": ["IRPF", "Autónomos", "Retenciones", "IBI", "Circulación", "Pasarela/Vado", "Seguridad Social", "AEAT"],
        "Vivienda": ["Limpieza", "Mantenimiento", "Otros", "Devoluciones"],
        "Salud y Belleza": ["Farmacia", "Médico", "Dental", "Óptica", "Peluquería", "Fisioterapia", "Perfumería", "Otros", "Devoluciones"],
        "Ropa y Calzado": ["Carrefour Zaraiche", "Ropa y Accesorios", "Otros", "Devoluciones"],
        "Ocio y Cultura": ["Cines", "Entradas", "Juegos", "Entretenimiento", "Otros", "Devoluciones"],
        "Deportes": ["Pádel", "Gimnasio", "Equipo deportivo", "Club", "Devoluciones"],
        "Suscripciones": ["Streaming", "Música", "Audible", "Software", "Apple", "Waylet", "Otros", "Devoluciones"],
        "Viajes": ["Alojamiento", "Vuelos", "Transporte", "Actividades", "Aeropuerto", "Otros", "Devoluciones"],
        "Efectivo": ["Retirada", "Ingreso", "Regularización"],
        "Cuenta Común": [""],
        "Comisiones": [""],
        "Préstamos": ["Préstamo hermano"],
        "Wallapop": [""],
        "Liquidación": [""],
    },
    "INGRESO": {
        "Nómina": [""],
        "Cashback": [""],
        "Intereses": [""],
        "Wallapop": [""],
        "Bonificación familia numerosa": [""],
        "Servicios Consultoría": [""],
        "Efectivo": [""],
        "Otros": [""],
    },
    "INVERSION": {
        "Renta Variable": ["Compra", "Venta"],
        "Cripto": ["Nexo", "Binance", "MEXC", "Bit2Me", "RAMP", "MRCR", "Otros", ""],
        "Dividendos": [""],
        "Divisas": [""],
        "Comisiones": ["Custodia", "Retenciones", ""],
        "Aportación": [""],
        "Fondos": ["Compra", "Venta", ""],
        "Liquidación": [""],
        "Depósitos": [""],
        "Cashback": [""],
        "Intereses": [""],
    },
    "TRANSFERENCIA": {
        "Interna": [""],
        "Externa": [""],
        "Bizum": [""],
        "Cuenta Común": [""],
    }
}


def validar_taxonomia(tipo, cat1, cat2):
    """
    Valida que una combinación Tipo/Cat1/Cat2 sea válida según la taxonomía.

    Args:
        tipo: Tipo de transacción (GASTO, INGRESO, INVERSION, TRANSFERENCIA)
        cat1: Categoría nivel 1
        cat2: Categoría nivel 2 (puede ser vacío "")

    Returns:
        bool: True si la combinación es válida, False si no
    """
    # Verificar que el tipo existe
    if tipo not in TAXONOMIA:
        return False

    # Verificar que cat1 existe en ese tipo
    if cat1 not in TAXONOMIA[tipo]:
        return False

    # Verificar que cat2 está en la lista de cat2 válidos para esa cat1
    cat2_validos = TAXONOMIA[tipo][cat1]

    # cat2 puede ser None, convertir a string vacío
    cat2_str = cat2 if cat2 is not None else ""

    return cat2_str in cat2_validos


def get_combinaciones_validas():
    """
    Devuelve todas las combinaciones válidas como lista de tuplas.

    Returns:
        List[Tuple[str, str, str]]: Lista de (tipo, cat1, cat2)
    """
    combinaciones = []

    for tipo, cat1_dict in TAXONOMIA.items():
        for cat1, cat2_list in cat1_dict.items():
            for cat2 in cat2_list:
                combinaciones.append((tipo, cat1, cat2))

    return combinaciones


def get_cat2_validos(tipo, cat1):
    """
    Devuelve los Cat2 válidos para un Tipo/Cat1 dado.

    Args:
        tipo: Tipo de transacción
        cat1: Categoría nivel 1

    Returns:
        List[str]: Lista de cat2 válidos, o [] si la combinación no existe
    """
    if tipo not in TAXONOMIA:
        return []

    if cat1 not in TAXONOMIA[tipo]:
        return []

    return TAXONOMIA[tipo][cat1]


if __name__ == '__main__':
    # Test
    print("Taxonomía Finsense v2")
    print("=" * 80)

    total_combinaciones = len(get_combinaciones_validas())
    print(f"\nTotal combinaciones válidas: {total_combinaciones}")

    # Contar por tipo
    for tipo in TAXONOMIA.keys():
        count = sum(len(cat2_list) for cat2_list in TAXONOMIA[tipo].values())
        print(f"  {tipo}: {count} combinaciones")

    # Tests
    print("\n" + "=" * 80)
    print("TESTS")
    print("=" * 80)

    tests = [
        ("GASTO", "Alimentación", "Mercadona", True),
        ("GASTO", "Restauración", "Bar", True),
        ("INGRESO", "Nómina", "", True),
        ("TRANSFERENCIA", "Bizum", "", True),
        ("GASTO", "Alimentación", "Inventado", False),
        ("GASTO", "CategoriaInvalida", "Otros", False),
        ("TIPO_INVALIDO", "Alimentación", "Otros", False),
    ]

    for tipo, cat1, cat2, esperado in tests:
        resultado = validar_taxonomia(tipo, cat1, cat2)
        status = "✅" if resultado == esperado else "❌"
        print(f"{status} {tipo}/{cat1}/{cat2} → {resultado} (esperado: {esperado})")
