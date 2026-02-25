#!/usr/bin/env python3
"""
Script para recategorizar merchants basándose en sus tipos de Google Places.
Consulta Google Places Details para obtener todos los tipos (no solo el primero).
Aplica la lógica mejorada de map_google_types_to_cat1_cat2.
"""
import sqlite3
import json
import logging
import os
import time
from typing import List, Tuple
from src.enrichment.google_places import map_google_types_to_cat1_cat2, get_place_details

DB_PATH = 'finsense.db'
LOG_FILE = 'logs/fix_merchant_categories.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def fix_merchant_categories():
    """
    Recategoriza merchants consultando Google Places Details para obtener tipos completos.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    API_KEY = os.getenv('GOOGLE_PLACES_API_KEY', 'AIzaSyClEVVWiHTjMJE7Wr4AuAVTch-InPDTmwI')
    
    logger.info("🔧 Recategorizando merchants con Google Places Details...")
    
    # Obtener merchants con place_id pero cat1 vacío
    cursor.execute("""
        SELECT merchant_name, place_id, cat1, cat2
        FROM merchants
        WHERE place_id IS NOT NULL
          AND (cat1 IS NULL OR cat1 = '')
        ORDER BY merchant_name
    """)
    
    rows = cursor.fetchall()
    total = len(rows)
    logger.info(f"   Encontrados {total} merchants para recategorizar")
    
    fixed = 0
    errors = 0
    
    for idx, (merchant_name, place_id, cat1_old, cat2_old) in enumerate(rows):
        try:
            # Consultar Google Places Details para obtener tipos completos
            result = get_place_details(place_id, API_KEY)
            
            if result and result['types']:
                # Mapear tipos a categorías
                cat1_new, cat2_new, confidence = map_google_types_to_cat1_cat2(result['types'])
                
                if cat1_new and cat2_new:
                    # Guardar todos los tipos como JSON
                    types_json = json.dumps(result['types'])
                    
                    cursor.execute("""
                        UPDATE merchants
                        SET cat1 = ?, cat2 = ?, confidence = ?, google_type = ?
                        WHERE merchant_name = ?
                    """, (cat1_new, cat2_new, confidence, types_json, merchant_name))
                    
                    fixed += 1
                    logger.debug(f"   ✅ {merchant_name}: {cat1_old or 'N/A'}/{cat2_old} → {cat1_new}/{cat2_new} (types: {result['types'][:2]}...)")
            else:
                logger.debug(f"   ⏭️  {merchant_name}: sin tipos en Google Places")
            
        except Exception as e:
            errors += 1
            logger.warning(f"   ⚠️  {merchant_name}: {e}")
        
        # Rate limiting
        time.sleep(0.1)
        
        if (idx + 1) % 50 == 0:
            conn.commit()
            logger.info(f"   Progreso: {idx + 1}/{total} ({fixed} corregidos, {errors} errores)")
    
    conn.commit()
    logger.info(f"✅ Recategorizados {fixed}/{total} merchants ({errors} errores)\n")
    conn.close()
    
    return fixed


if __name__ == '__main__':
    try:
        logger.info("=" * 60)
        logger.info("CORRECCIÓN DE CATEGORÍAS DE MERCHANTS")
        logger.info("=" * 60 + "\n")
        
        fixed = fix_merchant_categories()
        
        logger.info("=" * 60)
        logger.info("✅ CORRECCIÓN COMPLETADA")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        exit(1)
