"""
Capa 1: Exact Match
Diccionario de descripciones exactas → (Cat1, Cat2).
"""
import csv
from collections import Counter


def build_exact_match_dict(csv_path):
    """
    Construye el diccionario de exact match desde el CSV maestro.
    Gestiona colisiones usando la clasificación más frecuente.

    Args:
        csv_path: Ruta al CSV maestro

    Returns:
        Diccionario {descripcion: (cat1, cat2)}
    """
    # Primero, recopilar todas las clasificaciones por descripción
    desc_classifications = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            desc = row.get('Descripción') or row.get('Descripcion', '')
            cat1 = row.get('Cat1', '')
            cat2 = row.get('Cat2', '')
            
            if not desc or not cat1:
                continue

            if desc not in desc_classifications:
                desc_classifications[desc] = []

            desc_classifications[desc].append((cat1, cat2))

    # Construir diccionario final: para cada descripción, usar la clasificación más frecuente
    exact_match = {}

    for desc, classifications in desc_classifications.items():
        # Contar frecuencia de cada combinación (cat1, cat2)
        counter = Counter(classifications)
        most_common = counter.most_common(1)[0][0]  # (cat1, cat2) más frecuente

        exact_match[desc] = most_common

    return exact_match


def lookup_exact(descripcion, exact_match_dict):
    """
    Busca una descripción en el diccionario de exact match.

    Args:
        descripcion: Descripción de la transacción
        exact_match_dict: Diccionario de exact match

    Returns:
        Tupla (Cat1, Cat2) si hay match, None si no
    """
    return exact_match_dict.get(descripcion)
