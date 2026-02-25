#!/usr/bin/env python3
"""
Script para rellenar city/country en merchants que tienen place_id pero sin ubicación.
Usa Google Places Details API.
"""
import sqlite3
import os
import time
import logging
from typing import Tuple
from src.enrichment.google_places import get_place_details

# Configuración
DB_PATH = 'finsense.db'
API_KEY = os.getenv('GOOGLE_PLACES_API_KEY', 'AIzaSyClEVVWiHTjMJE7Wr4AuAVTch-InPDTmwI')
RATE_LIMIT_SECONDS = 0.1  # 100ms entre llamadas
LOG_FILE = 'logs/fill_merchant_locations.log'

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


def fill_merchant_locations_from_place_id() -> Tuple[int, int]:
    """
    Rellena city/country para merchants que tienen place_id pero no ubicación.
    
    Returns:
        Tupla (rellenados, errores)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    logger.info("🌍 Rellenando city/country desde Google Places Details...")
    
    # Obtener merchants con place_id pero sin city/country
    cursor.execute("""
        SELECT merchant_name, place_id 
        FROM merchants 
        WHERE place_id IS NOT NULL 
          AND (city IS NULL OR country IS NULL)
        ORDER BY merchant_name
    """)
    
    rows = cursor.fetchall()
    total = len(rows)
    logger.info(f"   Encontrados {total} merchants sin city/country")
    
    filled = 0
    errors = 0
    
    for idx, (merchant_name, place_id) in enumerate(rows):
        try:
            result = get_place_details(place_id, API_KEY)
            if result:
                cursor.execute("""
                    UPDATE merchants SET 
                        address = ?, city = ?, country = ?, lat = ?, lng = ?
                    WHERE merchant_name = ?
                """, (
                    result['formatted_address'],
                    result['city'],
                    result['country'],
                    result['lat'],
                    result['lng'],
                    merchant_name
                ))
                filled += 1
                logger.debug(f"   ✅ {merchant_name} → {result['city']}, {result['country']}")
            else:
                logger.debug(f"   ⏭️  {merchant_name} (place_id: {place_id}) → sin detalles")
        except Exception as e:
            errors += 1
            logger.warning(f"   ⚠️  {merchant_name} → error: {e}")
        
        # Rate limiting
        time.sleep(RATE_LIMIT_SECONDS)
        
        # Commit y progreso cada 50 merchants
        if (idx + 1) % 50 == 0:
            conn.commit()
            logger.info(f"   Progreso: {idx + 1}/{total} (✅ {filled}, ⚠️  {errors})")
    
    conn.commit()
    logger.info(f"✅ Rellenados {filled}/{total} merchants")
    logger.info(f"   Errores: {errors}\n")
    
    conn.close()
    
    return filled, errors


def get_merchant_location_statistics() -> dict:
    """Obtiene estadísticas de cobertura de ubicación en merchants."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM merchants WHERE city IS NOT NULL")
    stats['with_city'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM merchants WHERE country IS NOT NULL")
    stats['with_country'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM merchants WHERE place_id IS NOT NULL AND (city IS NULL OR country IS NULL)")
    stats['place_id_without_location'] = cursor.fetchone()[0]
    
    conn.close()
    return stats


if __name__ == '__main__':
    try:
        logger.info("=" * 60)
        logger.info("RELLENO DE UBICACIÓN DE MERCHANTS - INICIO")
        logger.info("=" * 60 + "\n")
        
        # Estadísticas iniciales
        logger.info("📊 Estado inicial:")
        stats_before = get_merchant_location_statistics()
        logger.info(f"   Merchants con city: {stats_before['with_city']}")
        logger.info(f"   Merchants con country: {stats_before['with_country']}")
        logger.info(f"   Merchants con place_id pero sin ubicación: {stats_before['place_id_without_location']}\n")
        
        # Ejecutar relleno
        filled, errors = fill_merchant_locations_from_place_id()
        
        # Estadísticas finales
        logger.info("📊 Estado final:")
        stats_after = get_merchant_location_statistics()
        logger.info(f"   Merchants con city: {stats_after['with_city']} (Δ +{stats_after['with_city'] - stats_before['with_city']})")
        logger.info(f"   Merchants con country: {stats_after['with_country']} (Δ +{stats_after['with_country'] - stats_before['with_country']})")
        logger.info(f"   Merchants con place_id pero sin ubicación: {stats_after['place_id_without_location']} (Δ {stats_after['place_id_without_location'] - stats_before['place_id_without_location']})\n")
        
        logger.info("=" * 60)
        logger.info("✅ RELLENO COMPLETADO")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        exit(1)
