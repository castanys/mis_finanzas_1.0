# FASE 2D: Enriquecimiento de Cat2 con Google Places API

## Contexto

De las 15,640 transacciones clasificadas, hay ~953 gastos en comercios físicos con Cat2 vacío o "Otros" donde Cat1 ya es correcto (Restauración, Compras, Alimentación, etc.). Google Places API puede decirnos QUÉ tipo de comercio es para asignar un Cat2 específico.

**NO toques el clasificador base ni la clasificación Cat1.** Esta fase SOLO enriquece Cat2 de transacciones que ya tienen Cat1 correcto.

## Arquitectura

```
src/
  enrichment/
    __init__.py
    google_places.py      # Cliente API con búsqueda por ámbitos
    merchant_cache.py      # Caché SQLite
    cat2_enricher.py       # Orquestador: extrae merchant → busca → mapea → asigna Cat2
```

## Paso 1: Extractor de merchant name

La mayoría de las candidatas son Openbank con formato:
```
COMPRA EN <MERCHANT>, CON LA TARJETA : XXXX EL YYYY-MM-DD
Apple pay: COMPRA EN <MERCHANT>, CON LA TARJETA : XXXX EL YYYY-MM-DD
```

Ya existe un extractor en el clasificador (Capa 2A). Reutilízalo o crea uno equivalente:

```python
import re

def extract_merchant_name(descripcion: str, banco: str) -> str:
    """Extrae el nombre del merchant de la descripción bancaria."""
    
    if banco == "Openbank":
        # "COMPRA EN MERCADONA PROLONGACION AN, CON LA TARJETA..."
        # "Apple pay: COMPRA EN MERCADONA..., CON LA TARJETA..."
        match = re.search(r'(?:Apple [Pp]ay: )?COMPRA EN ([^,]+),', descripcion)
        if match:
            return match.group(1).strip()
    
    elif banco == "Trade Republic":
        # "Transacción MERCHANT con tarjeta"
        match = re.search(r'Transacci[oó]n (.+?) con tarjeta', descripcion)
        if match:
            return match.group(1).strip()
    
    elif banco == "Abanca":
        # "767003239036 MERCHANT \CIUDAD\..."
        match = re.search(r'\d+ (.+?)\\', descripcion)
        if match:
            return match.group(1).strip()
    
    # Fallback: usar descripción completa (limpia)
    return descripcion.strip()
```

## Paso 2: Caché SQLite

```sql
CREATE TABLE IF NOT EXISTS merchant_cache (
    merchant_name TEXT NOT NULL,
    search_location TEXT NOT NULL,    -- 'cartagena', 'spain', 'europe', 'global'
    google_place_id TEXT,
    google_place_name TEXT,
    google_place_type TEXT,           -- tipo principal de Google Places
    google_place_types TEXT,          -- todos los tipos, separados por |
    mapped_cat2 TEXT,
    confidence TEXT,                  -- 'high', 'medium', 'low', 'no_result'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (merchant_name, search_location)
);
```

Reglas de caché:
- NO expira (un bar es siempre un bar)
- Si Google no devuelve resultado → guardar con confidence='no_result' para no repetir
- Lookup: primero buscar en caché antes de llamar a la API

## Paso 3: Búsqueda por 4 ámbitos geográficos

Buscar en orden, parar al primer resultado con confianza alta:

```python
SEARCH_LOCATIONS = [
    {
        'name': 'cartagena',
        'query_suffix': 'Cartagena Murcia Spain',
        'lat': 37.6057,
        'lng': -0.9913,
        'radius': 10000,   # 10km
    },
    {
        'name': 'spain', 
        'query_suffix': 'Spain',
        'lat': 40.4168,
        'lng': -3.7038,
        'radius': 500000,  # 500km
    },
    {
        'name': 'europe',
        'query_suffix': 'Europe',
        'lat': 48.8566,
        'lng': 2.3522,
        'radius': 2000000, # 2000km
    },
    {
        'name': 'global',
        'query_suffix': '',
        'lat': None,
        'lng': None,
        'radius': None,    # sin restricción
    },
]
```

Lógica:
1. Buscar "ARROCERIA EL LIMONERO Cartagena Murcia Spain"
2. Si no hay resultado → buscar "ARROCERIA EL LIMONERO Spain"
3. Si no hay resultado → buscar "ARROCERIA EL LIMONERO Europe"
4. Si no hay resultado → buscar "ARROCERIA EL LIMONERO"
5. Si no hay resultado → confidence='no_result', Cat2 queda como está

## Paso 4: Mapeo Google Places types → Cat2

```python
GOOGLE_TYPE_TO_CAT2 = {
    # Restauración
    'restaurant': 'Restaurante',
    'bar': 'Bar',
    'cafe': 'Cafetería',
    'bakery': 'Panadería',
    'meal_delivery': 'Comida a domicilio',
    'meal_takeaway': 'Comida para llevar',
    'night_club': 'Ocio nocturno',
    
    # Alimentación
    'supermarket': 'Supermercado',
    'grocery_or_supermarket': 'Supermercado',
    'food': 'Alimentación',
    
    # Transporte
    'gas_station': 'Combustible',
    'parking': 'Parking',
    'car_repair': 'Taller',
    'car_wash': 'Lavado',
    'transit_station': 'Transporte público',
    'airport': 'Aeropuerto/Duty Free',
    
    # Compras
    'clothing_store': 'Ropa y Calzado',
    'shoe_store': 'Ropa y Calzado',
    'jewelry_store': 'Joyería',
    'electronics_store': 'Electrónica',
    'furniture_store': 'Hogar',
    'home_goods_store': 'Hogar',
    'hardware_store': 'Ferretería',
    'book_store': 'Libros',
    'pet_store': 'Mascotas',
    'shopping_mall': 'Centro comercial',
    'department_store': 'Grandes almacenes',
    'convenience_store': 'Conveniencia',
    
    # Salud y Belleza
    'pharmacy': 'Farmacia',
    'dentist': 'Clínica dental',
    'doctor': 'Médico',
    'hospital': 'Hospital',
    'hair_care': 'Peluquería',
    'beauty_salon': 'Estética',
    'spa': 'Spa',
    'physiotherapist': 'Fisioterapia',
    'veterinary_care': 'Veterinario',
    
    # Ocio y Cultura
    'movie_theater': 'Cines',
    'museum': 'Museos',
    'amusement_park': 'Parques',
    'gym': 'Gimnasio',
    'stadium': 'Eventos',
    'bowling_alley': 'Bolera',
    
    # Viajes
    'lodging': 'Alojamiento',
    'travel_agency': 'Agencia de viajes',
    
    # Educación
    'school': 'Colegio',
    'university': 'Universidad',
}
```

Si Google devuelve múltiples types, usar el primero que tenga mapping. Si ninguno tiene mapping, guardar el type principal y confidence='low'.

## Paso 5: API Key de Google Places

**IMPORTANTE:** El script debe pedir la API key como variable de entorno, NUNCA hardcodeada:

```python
import os
API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')
if not API_KEY:
    raise ValueError("Set GOOGLE_PLACES_API_KEY environment variable")
```

Uso: `GOOGLE_PLACES_API_KEY=xxx python3 enrich_cat2.py`

Google Places API tiene $200/mes de crédito gratuito. Con caché, el coste será mínimo.

## Paso 6: Ejecución en modo batch

```python
# enrich_cat2.py - Script principal

def main():
    # 1. Cargar transacciones clasificadas
    transactions = load_csv('output/transacciones_completas.csv')
    
    # 2. Filtrar candidatas: Cat2 vacío o "Otros" + Cat1 de comercio físico
    candidates = [tx for tx in transactions 
                  if tx['cat1'] in ('Restauración', 'Compras', 'Alimentación', 
                                    'Ropa y Calzado', 'Transporte', 'Salud y Belleza',
                                    'Ocio y Cultura', 'Viajes')
                  and (not tx['cat2'] or tx['cat2'] == 'Otros')]
    
    print(f"Candidatas para enriquecimiento: {len(candidates)}")
    
    # 3. Extraer merchants únicos (no repetir consultas)
    unique_merchants = set()
    for tx in candidates:
        merchant = extract_merchant_name(tx['descripcion'], tx['banco'])
        unique_merchants.add(merchant)
    
    print(f"Merchants únicos a consultar: {len(unique_merchants)}")
    
    # 4. Para cada merchant único:
    cache = MerchantCache('merchant_cache.db')
    
    for merchant in unique_merchants:
        # Check caché
        cached = cache.get(merchant)
        if cached:
            continue
        
        # Buscar por ámbitos
        result = search_places_by_scope(merchant, API_KEY)
        cache.save(merchant, result)
        
        # Rate limiting: Google Places permite 100 QPS pero sé conservador
        time.sleep(0.1)
    
    # 5. Aplicar Cat2 enriquecido
    enriched_count = 0
    for tx in candidates:
        merchant = extract_merchant_name(tx['descripcion'], tx['banco'])
        cached = cache.get(merchant)
        if cached and cached['mapped_cat2'] and cached['confidence'] != 'no_result':
            tx['cat2'] = cached['mapped_cat2']
            enriched_count += 1
    
    print(f"Transacciones enriquecidas: {enriched_count}/{len(candidates)}")
    
    # 6. Guardar
    save_csv(transactions, 'output/transacciones_completas.csv')

if __name__ == '__main__':
    main()
```

## Paso 7: Modo DRY-RUN (sin API key)

El script debe tener un modo --dry-run que:
1. Identifica las candidatas
2. Extrae merchants únicos
3. Muestra cuántas consultas haría a la API
4. NO llama a Google Places
5. Así Pablo puede verificar antes de gastar crédito

```bash
python3 enrich_cat2.py --dry-run    # Solo muestra qué haría
python3 enrich_cat2.py              # Ejecuta con API
```

## Validación

Después del enriquecimiento:

```
=== ENRIQUECIMIENTO Cat2 ===
Candidatas totales:          953
Merchants únicos:            XXX
Encontrados en Google:       XXX (XX%)
Cat2 asignados:              XXX (XX%)
Sin resultado:               XXX
Consultas a API:             XXX (coste estimado: $X.XX)

Antes vs Después:
  Cat2 vacío/Otros:  953 → XXX (-XX%)
  Cat2 accuracy vs maestro: 93.4% → XX.X%

Top Cat2 asignados:
  Restaurante: XXX
  Bar: XXX
  Supermercado: XXX
  ...
```

## Criterios de cierre

| Métrica | Objetivo |
|---------|----------|
| Merchants consultados | 100% de únicos |
| Cat2 enriquecidos | >50% de las 953 candidatas |
| Caché funcional | 0 consultas repetidas |
| Dry-run mode | Funciona sin API key |
| Sin regresiones | Cat1 sin cambios, Cat2 solo mejora |
| Coste API | Documentado |
