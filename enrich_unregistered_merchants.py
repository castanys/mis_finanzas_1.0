#!/usr/bin/env python3
"""
Script para enriquecer merchants que NO están registrados en la tabla merchants.
Extrae merchants únicos de transacciones que faltan en merchants, los añade,
y los enriquece con Google Places API.
"""
import sqlite3
import os
import time
import logging
from typing import List, Tuple
from src.enrichment.google_places import enrich_merchant

# Configuración
DB_PATH = 'finsense.db'
API_KEY = os.getenv('GOOGLE_PLACES_API_KEY', 'AIzaSyClEVVWiHTjMJE7Wr4AuAVTch-InPDTmwI')
RATE_LIMIT_SECONDS = 0.1  # 100ms entre llamadas a Google Places
LOG_FILE = 'logs/enrich_unregistered.log'

# Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_unregistered_merchants() -> List[str]:
    """
    Obtiene lista de merchants únicos en transacciones que NO están en tabla merchants.
    Returns:
        Lista de nombres de merchants
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT merchant_name 
        FROM transacciones 
        WHERE merchant_name IS NOT NULL 
        AND merchant_name NOT IN (SELECT merchant_name FROM merchants WHERE merchant_name IS NOT NULL)
        ORDER BY merchant_name
    """)
    
    merchants = [row[0] for row in cursor.fetchall()]
    conn.close()
    return merchants


def insert_unregistered_merchants(merchants: List[str]) -> int:
    """
    Inserta merchants no registrados en tabla merchants.
    Returns:
        Número de merchants insertados
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    logger.info(f"📝 Insertando {len(merchants)} merchants no registrados...")
    
    inserted = 0
    for merchant_name in merchants:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO merchants 
                (merchant_name, place_id, place_name, city, country, lat, lng)
                VALUES (?, NULL, ?, ?, ?, NULL, NULL)
            """, (merchant_name, merchant_name, None, None))
            inserted += 1
        except Exception as e:
            logger.warning(f"⚠️  Error insertando {merchant_name}: {e}")
    
    conn.commit()
    logger.info(f"✅ Insertados {inserted}/{len(merchants)} merchants\n")
    conn.close()
    
    return inserted


def enrich_merchants_with_google_places(merchants: List[str], batch_size: int = 50) -> Tuple[int, int, int]:
    """
    Enriquece merchants con Google Places API.
    Returns:
        Tupla (enriquecidos, no_encontrados, errores)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    logger.info(f"🔍 Enriqueciendo {len(merchants)} merchants con Google Places...")
    
    enriched = 0
    not_found = 0
    errors = 0
    
    for idx, merchant_name in enumerate(merchants):
        try:
            result = enrich_merchant(merchant_name, API_KEY)
            if result:
                cursor.execute("""
                    UPDATE merchants SET 
                        place_id = ?, place_name = ?, address = ?, city = ?, country = ?,
                        lat = ?, lng = ?, cat1 = ?, cat2 = ?, 
                        google_type = ?, confidence = ?, search_scope = ?
                    WHERE merchant_name = ?
                """, (
                    result['place_id'], result['place_name'], result['formatted_address'],
                    result['city'], result['country'],
                    result['lat'], result['lng'], result['cat1'], result['cat2'],
                    result['google_type'], result['confidence'], result['search_scope'],
                    merchant_name
                ))
                enriched += 1
                logger.info(f"   ✅ {merchant_name} → {result['city']}, {result['country']}")
            else:
                not_found += 1
                logger.debug(f"   ⏭️  {merchant_name} → no encontrado en Google Places")
        except Exception as e:
            errors += 1
            logger.warning(f"   ⚠️  {merchant_name} → error: {e}")
        
        # Rate limiting
        time.sleep(RATE_LIMIT_SECONDS)
        
        # Commit cada batch_size merchants
        if (idx + 1) % batch_size == 0:
            conn.commit()
            logger.info(f"   Progreso: {idx + 1}/{len(merchants)} (✅ {enriched}, ⏭️  {not_found}, ⚠️  {errors})")
    
    conn.commit()
    logger.info(f"\n✅ Enriquecimiento completado:")
    logger.info(f"   - Enriquecidos: {enriched}/{len(merchants)}")
    logger.info(f"   - No encontrados: {not_found}")
    logger.info(f"   - Errores: {errors}\n")
    
    conn.close()
    
    return enriched, not_found, errors


def main():
    """Flujo principal de enriquecimiento"""
    logger.info("="*60)
    logger.info("ENRIQUECIMIENTO DE MERCHANTS NO REGISTRADOS - INICIO")
    logger.info("="*60)
    
    # Paso 1: Obtener merchants no registrados
    unregistered = get_unregistered_merchants()
    logger.info(f"📊 Encontrados {len(unregistered)} merchants no registrados\n")
    
    if not unregistered:
        logger.info("✅ No hay merchants sin registrar")
        return
    
    # Paso 2: Insertarlos en tabla merchants
    insert_unregistered_merchants(unregistered)
    
    # Paso 3: Enriquecerlos con Google Places
    enriched, not_found, errors = enrich_merchants_with_google_places(unregistered)
    
    logger.info("="*60)
    logger.info("✅ PROCESO COMPLETADO")
    logger.info("="*60)


if __name__ == "__main__":
    main()
