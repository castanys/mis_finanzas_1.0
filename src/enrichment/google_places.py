"""
Google Places API integration — query-first strategy con extracción de ubicación.
Busca merchants sin scope previo, luego amplía geográficamente si es necesario.
Devuelve address, city, country, lat, lng junto con cat2.
"""
import os
import requests
import re
from typing import Optional, Dict, List, Tuple


# Scopes como estrategia de desambiguación (no como limitador primario)
SEARCH_SCOPES = [
    {
        'name': 'cartagena',
        'context': 'Cartagena Murcia Spain',
        'lat': 37.6057,
        'lng': -0.9913,
        'radius': 10000,
    },
    {
        'name': 'murcia',
        'context': 'Murcia Spain',
        'lat': 37.9922,
        'lng': -1.1307,
        'radius': 15000,
    },
    {
        'name': 'spain',
        'context': 'Spain',
        'lat': 40.4168,
        'lng': -3.7038,
        'radius': 500000,
    },
    {
        'name': 'europe',
        'context': 'Europe',
        'lat': 48.8566,
        'lng': 2.3522,
        'radius': 2000000,
    },
    {
        'name': 'global',
        'context': '',
        'lat': None,
        'lng': None,
        'radius': None,
    },
]


# Mapeo directo de tipos de Google Places → (Cat1, Cat2)
# Solo incluye combinaciones válidas según valid_combos.py
GOOGLE_TYPE_TO_CAT1_CAT2 = {
    # Restauración
    'restaurant': ('Restauración', 'Restaurante'),
    'bar': ('Restauración', 'Bar'),
    'cafe': ('Restauración', 'Cafetería'),
    'bakery': ('Restauración', 'Panadería'),
    'meal_delivery': ('Restauración', 'Otros'),  # no existe "Comida a domicilio" en taxonomía
    'meal_takeaway': ('Restauración', 'Otros'),  # no existe "Comida para llevar" en taxonomía
    'night_club': ('Restauración', 'Otros'),  # no existe "Ocio nocturno" en Restauración
    'food': ('Restauración', 'Otros'),  # genérico, usar fallback

    # Alimentación
    'supermarket': ('Alimentación', 'Supermercado'),
    'grocery_or_supermarket': ('Alimentación', 'Supermercado'),
    'market': ('Alimentación', 'Mercado'),

    # Transporte
    'gas_station': ('Transporte', 'Combustible'),
    'parking': ('Transporte', 'Parking'),
    'car_repair': ('Transporte', 'Taller'),
    'car_wash': ('Transporte', 'Lavado'),
    'transit_station': ('Transporte', 'Transporte público'),
    'airport': ('Transporte', 'Aeropuerto/Peajes'),  # "Aeropuerto" no existe en Transporte, usar fallback
    
    # Compras
    'clothing_store': ('Compras', 'Ropa y Calzado'),
    'shoe_store': ('Compras', 'Ropa y Calzado'),
    'jewelry_store': ('Compras', 'Joyería'),
    'electronics_store': ('Compras', 'Electrónica'),
    'furniture_store': ('Compras', 'Hogar'),
    'home_goods_store': ('Compras', 'Hogar'),
    'hardware_store': ('Compras', 'Ferretería'),
    'book_store': ('Compras', 'Libros'),
    'pet_store': ('Compras', 'Otros'),  # "Mascotas" no existe en Compras
    'shopping_mall': ('Compras', 'Centro comercial'),
    'department_store': ('Compras', 'Centro comercial'),  # "Grandes almacenes" no existe, usar Centro comercial
    'convenience_store': ('Alimentación', 'Conveniencia'),  # también podría ser Compras

    # Salud y Belleza
    'pharmacy': ('Salud y Belleza', 'Farmacia'),
    'dentist': ('Salud y Belleza', 'Clínica dental'),
    'doctor': ('Salud y Belleza', 'Médico'),
    'hospital': ('Salud y Belleza', 'Hospital'),
    'hair_care': ('Salud y Belleza', 'Peluquería'),
    'beauty_salon': ('Salud y Belleza', 'Estética'),
    'spa': ('Compras', 'Spa'),  # "Spa" está en Compras, no en Salud y Belleza
    'physiotherapist': ('Salud y Belleza', 'Fisioterapia'),
    'veterinary_care': ('Salud y Belleza', 'Otros'),  # "Veterinario" no existe en Salud y Belleza

    # Ocio y Cultura
    'movie_theater': ('Ocio y Cultura', 'Cines'),
    'museum': ('Ocio y Cultura', 'Museos'),
    'amusement_park': ('Ocio y Cultura', 'Parques'),
    'gym': ('Ocio y Cultura', 'Gimnasio'),  # también podría ser Compras/Gimnasio
    'stadium': ('Ocio y Cultura', 'Entradas'),  # "Eventos" no existe en Ocio, usar Entradas
    'bowling_alley': ('Ocio y Cultura', 'Otros'),  # "Bolera" no existe

    # Viajes
    'lodging': ('Viajes', 'Alojamiento'),
    'hotel': ('Viajes', 'Alojamiento'),
    'campground': ('Viajes', 'Alojamiento'),
}

# Mapeo heredado (deprecado, solo para compatibilidad)
GOOGLE_TYPE_TO_CAT2 = {v[1]: v[0] for k, v in GOOGLE_TYPE_TO_CAT1_CAT2.items()}


def extract_address_parts(formatted_address: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae city y country de formatted_address (ej: "C. Junterones 4, 30008 Murcia, Spain").
    Heurística: el último componente es country, el penúltimo es city/región.
    Limpia códigos postales numéricos del componente de city.
    Normaliza country a nombres completos (ej. "CA" → "United States", "ES" → "Spain").
    """
    if not formatted_address:
        return None, None
    
    parts = [p.strip() for p in formatted_address.split(',')]
    
    country_raw = parts[-1] if len(parts) > 0 else None
    
    # Normalizar country: códigos de 2 letras a nombres completos
    COUNTRY_MAPPING = {
        'ES': 'Spain',
        'GB': 'United Kingdom',
        'US': 'United States',
        'CA': 'Canada',
        'FR': 'France',
        'DE': 'Germany',
        'IT': 'Italy',
        'PT': 'Portugal',
        'BE': 'Belgium',
        'NL': 'Netherlands',
        'AT': 'Austria',
        'CH': 'Switzerland',
        'SE': 'Sweden',
        'NO': 'Norway',
        'DK': 'Denmark',
        'PL': 'Poland',
        'CZ': 'Czech Republic',
        'SK': 'Slovakia',
        'HU': 'Hungary',
        'RO': 'Romania',
        'BG': 'Bulgaria',
        'HR': 'Croatia',
        'SI': 'Slovenia',
        'GR': 'Greece',
        'CY': 'Cyprus',
        'MT': 'Malta',
        'IE': 'Ireland',
        'LU': 'Luxembourg',
        'MX': 'Mexico',
        'CO': 'Colombia',
        'AR': 'Argentina',
        'BR': 'Brazil',
        'CL': 'Chile',
        'PE': 'Peru',
        'JP': 'Japan',
        'CN': 'China',
        'IN': 'India',
        'AU': 'Australia',
        'NZ': 'New Zealand',
        'SG': 'Singapore',
        'HK': 'Hong Kong',
        'AE': 'United Arab Emirates',
        'SA': 'Saudi Arabia',
    }
    
    country = COUNTRY_MAPPING.get(country_raw, country_raw) if country_raw else None
    
    # Extraer penúltimo componente como city
    city_raw = parts[-2] if len(parts) > 1 else None
    
    # Limpiar city: eliminar códigos postales numéricos
    # Patrones: "30008 Murcia" → "Murcia", "30008" → None
    if city_raw:
        # Si comienza con números (código postal), intentar extraer la parte de texto
        match = re.search(r'([A-Za-záéíóúàèìòùäëïöüÑñ\s\-]+)$', city_raw)
        if match:
            city = match.group(1).strip()
            # Si solo queda vacío o es demasiado corto, usar city_raw
            if not city or len(city) < 2:
                city = city_raw
        else:
            city = city_raw
    else:
        city = None
    
    return city, country


def map_google_types_to_cat1_cat2(google_types: List[str]) -> Tuple[Optional[str], Optional[str], str]:
    """
    Mapea lista de tipos de Google Places a (cat1, cat2, confidence).
    Prioriza tipos específicos sobre genéricos.
    
    Solo devuelve combinaciones válidas según valid_combos.py.
    """
    if not google_types:
        return None, None, 'low'
    
    # Definir prioridades
    SPECIFIC_TYPES = {
        'restaurant', 'supermarket', 'grocery_or_supermarket', 'bar', 'cafe', 
        'bakery', 'pharmacy', 'hotel', 'lodging', 'gas_station', 'parking',
        'car_repair', 'gym', 'movie_theater', 'museum', 'clothing_store',
        'electronics_store', 'furniture_store', 'hardware_store', 'book_store',
        'pet_store', 'hair_care', 'beauty_salon', 'spa', 'dentist', 'doctor',
        'hospital', 'airport', 'campground', 'jewelry_store', 'shoe_store',
        'department_store', 'shopping_mall', 'convenience_store', 'market',
        'meal_delivery', 'meal_takeaway', 'night_club', 'amusement_park',
        'stadium', 'bowling_alley', 'car_wash', 'transit_station', 'veterinary_care',
        'physiotherapist'
    }
    
    GENERIC_TYPES = {'establishment', 'point_of_interest', 'store', 'food'}
    
    # Buscar tipos específicos primero
    for gtype in google_types:
        gtype_lower = gtype.lower()
        if gtype_lower in SPECIFIC_TYPES and gtype_lower in GOOGLE_TYPE_TO_CAT1_CAT2:
            cat1, cat2 = GOOGLE_TYPE_TO_CAT1_CAT2[gtype_lower]
            return cat1, cat2, 'high'
    
    # Si no hay específicos, buscar genéricos
    for gtype in google_types:
        gtype_lower = gtype.lower()
        if gtype_lower in GOOGLE_TYPE_TO_CAT1_CAT2:
            cat1, cat2 = GOOGLE_TYPE_TO_CAT1_CAT2[gtype_lower]
            confidence = 'high' if gtype_lower in SPECIFIC_TYPES else 'medium'
            return cat1, cat2, confidence
    
    return None, None, 'low'


def infer_cat1_from_cat2(cat2: str) -> Optional[str]:
    """
    Infiere Cat1 desde Cat2 usando heurísticas simples.
    """
    cat2_lower = cat2.lower()
    
    if any(x in cat2_lower for x in ['restaurante', 'bar', 'cafetería', 'comida', 'panadería']):
        return 'Restauración'
    elif any(x in cat2_lower for x in ['supermercado', 'mercado', 'alimentación']):
        return 'Alimentación'
    elif any(x in cat2_lower for x in ['combustible', 'parking', 'taller', 'lavado', 'aeropuerto']):
        return 'Transporte'
    elif any(x in cat2_lower for x in ['ropa', 'calzado', 'joyería', 'electrónica', 'hogar', 'ferretería']):
        return 'Compras'
    elif any(x in cat2_lower for x in ['farmacia', 'médico', 'dentista', 'peluquería', 'estética', 'spa']):
        return 'Salud y Belleza'
    elif any(x in cat2_lower for x in ['cines', 'museos', 'parques', 'gimnasio', 'eventos']):
        return 'Ocio y Cultura'
    elif any(x in cat2_lower for x in ['alojamiento', 'hotel']):
        return 'Viajes'
    
    return None


def search_place_with_scope(merchant_name: str, scope: Dict, api_key: str) -> Optional[Dict]:
    """
    Busca un merchant usando Google Places Text Search con un scope específico.
    Retorna dict con place_id, name, address, lat, lng, types, search_scope.
    """
    base_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
    
    # Construir query con contexto del scope
    if scope['context']:
        query = f"{merchant_name} {scope['context']}"
    else:
        query = merchant_name
    
    params = {
        'query': query,
        'key': api_key,
    }
    
    # Añadir ubicación y radio si está definido
    if scope['lat'] is not None and scope['lng'] is not None:
        params['location'] = f"{scope['lat']},{scope['lng']}"
        params['radius'] = scope['radius']
    
    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'OK' or not data.get('results'):
            return None
        
        result = data['results'][0]
        
        return {
            'place_id': result.get('place_id'),
            'place_name': result.get('name'),
            'formatted_address': result.get('formatted_address'),
            'lat': result.get('geometry', {}).get('location', {}).get('lat'),
            'lng': result.get('geometry', {}).get('location', {}).get('lng'),
            'types': result.get('types', []),
            'search_scope': scope['name'],
        }
    except Exception as e:
        print(f"   ⚠️  Error buscando '{merchant_name}' en scope {scope['name']}: {e}")
        return None


def search_place_cascade(merchant_name: str, api_key: str) -> Optional[Dict]:
    """
    Busca un merchant de forma escalada: global primero, luego scopes locales si confidence es baja.
    Estrategia query-first: sin ubicación al principio, luego añade contexto.
    """
    # Intenta primero globalmente sin contexto
    global_scope = next(s for s in SEARCH_SCOPES if s['name'] == 'global')
    result = search_place_with_scope(merchant_name, global_scope, api_key)
    
    if result:
        return result
    
    # Si no encuentra, intenta con scopes locales (cartagena → murcia → spain → europe)
    for scope in SEARCH_SCOPES:
        if scope['name'] == 'global':
            continue
        
        result = search_place_with_scope(merchant_name, scope, api_key)
        if result:
            return result
    
    return None


def get_place_details(place_id: str, api_key: str) -> Optional[Dict]:
    """
    Obtiene detalles de un lugar usando su place_id (Google Places Details API).
    Útil para enriquecer merchants que ya tienen place_id pero sin city/country.
    
    Args:
        place_id: Google Place ID
        api_key: Clave API de Google Places
    
    Returns:
        Dict con formatted_address, city, country, lat, lng, types. None si falla.
    """
    base_url = 'https://maps.googleapis.com/maps/api/place/details/json'
    
    params = {
        'place_id': place_id,
        'fields': 'formatted_address,geometry,types',
        'key': api_key,
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'OK':
            return None
        
        result = data['result']
        
        # Extraer city y country
        city, country = extract_address_parts(result.get('formatted_address', ''))
        
        return {
            'formatted_address': result.get('formatted_address'),
            'city': city,
            'country': country,
            'lat': result.get('geometry', {}).get('location', {}).get('lat'),
            'lng': result.get('geometry', {}).get('location', {}).get('lng'),
            'types': result.get('types', []),
        }
    except Exception as e:
        print(f"   ⚠️  Error obteniendo detalles del place {place_id}: {e}")
        return None


def enrich_merchant(merchant_name: str, api_key: str) -> Optional[Dict]:
    """
    Enriquece un merchant consultando Google Places.
    Retorna dict con: cat1, cat2, place_id, place_name, address, city, country, lat, lng, confidence, search_scope.
    """
    result = search_place_cascade(merchant_name, api_key)
    
    if not result:
        return None
    
    # Extraer city y country
    city, country = extract_address_parts(result['formatted_address'])
    
    # Mapear tipos a cat1/cat2
    cat1, cat2, confidence = map_google_types_to_cat1_cat2(result['types'])
    
    return {
        'merchant_name': merchant_name,
        'place_id': result['place_id'],
        'place_name': result['place_name'],
        'formatted_address': result['formatted_address'],
        'city': city,
        'country': country,
        'lat': result['lat'],
        'lng': result['lng'],
        'cat1': cat1,
        'cat2': cat2,
        'google_type': result['types'][0] if result['types'] else None,
        'confidence': confidence,
        'search_scope': result['search_scope'],
    }
