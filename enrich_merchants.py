#!/usr/bin/env python3
"""
Script para enriquecer transacciones con merchant_name y datos de ubicación.
Usa la tabla merchants en finsense.db + Google Places API.
Versión mejorada: sin límites, rate limiting, y reportes detallados.
"""
import sqlite3
import os
import time
import logging
from typing import List, Tuple
from classifier.recurrent_merchants import extract_merchant
from src.enrichment.google_places import enrich_merchant

# Configuración
DB_PATH = 'finsense.db'
API_KEY = os.getenv('GOOGLE_PLACES_API_KEY', 'AIzaSyClEVVWiHTjMJE7Wr4AuAVTch-InPDTmwI')
RATE_LIMIT_SECONDS = 0.1  # 100ms entre llamadas a Google Places
LOG_FILE = 'logs/enrich_merchants.log'

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


def populate_merchant_names(limit: int | None = None) -> int:
    """
    Llena la columna merchant_name en transacciones extrayendo de descripción.
    
    Args:
        limit: Máximo número de transacciones a procesar (None = todas)
    
    Returns:
        Número de transacciones actualizadas
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    logger.info("📝 Poblando merchant_name en transacciones...")
    
    # Obtener txs sin merchant_name
    query = "SELECT id, descripcion FROM transacciones WHERE merchant_name IS NULL"
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    total = len(rows)
    logger.info(f"   Procesando {total} transacciones...")
    
    updated = 0
    for i, (tx_id, descripcion) in enumerate(rows):
        merchant = extract_merchant(descripcion)
        if merchant:
            cursor.execute(
                "UPDATE transacciones SET merchant_name = ? WHERE id = ?",
                (merchant, tx_id)
            )
            updated += 1
        
        # Commit cada 500 txs
        if (i + 1) % 500 == 0:
            conn.commit()
            logger.info(f"   Progreso: {i + 1}/{total} ({updated} actualizadas)")
    
    conn.commit()
    logger.info(f"✅ Actualizadas {updated}/{total} transacciones con merchant_name\n")
    conn.close()
    
    return updated


def enrich_merchants_in_db(batch_size: int | None = None) -> Tuple[int, int]:
    """
    Busca merchants en Google Places y los guarda en tabla merchants.
    Sin límite predefinido de merchants a procesar.
    
    Args:
        batch_size: Número de merchants por batch antes de commit (default: 20)
    
    Returns:
        Tupla (enriquecidos, no_encontrados)
    """
    if batch_size is None:
        batch_size = 20
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    logger.info("🔍 Enriqueciendo merchants desde Google Places (sin límite)...")
    
    # Obtener TODOS los merchants sin place_id
    cursor.execute("""
        SELECT merchant_name FROM merchants 
        WHERE place_id IS NULL AND merchant_name IS NOT NULL 
        ORDER BY merchant_name
    """)
    
    merchants_to_enrich = [row[0] for row in cursor.fetchall()]
    total = len(merchants_to_enrich)
    logger.info(f"   Encontrados {total} merchants sin place_id para enriquecer")
    
    enriched = 0
    not_found = 0
    errors = 0
    
    for idx, merchant_name in enumerate(merchants_to_enrich):
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
            logger.info(f"   Progreso: {idx + 1}/{total} (✅ {enriched}, ⏭️  {not_found}, ⚠️  {errors})")
    
    conn.commit()
    logger.info(f"✅ Enriquecimiento completado:")
    logger.info(f"   - Enriquecidos: {enriched}/{total}")
    logger.info(f"   - No encontrados: {not_found}")
    logger.info(f"   - Errores: {errors}\n")
    
    conn.close()
    
    return enriched, not_found


def get_merchant_statistics() -> dict:
    """
    Obtiene estadísticas de cobertura de merchants.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {}
    
    # Total merchants
    cursor.execute("SELECT COUNT(*) FROM merchants")
    stats['total_merchants'] = cursor.fetchone()[0]
    
    # Con place_id
    cursor.execute("SELECT COUNT(*) FROM merchants WHERE place_id IS NOT NULL")
    stats['with_place_id'] = cursor.fetchone()[0]
    
    # Con city
    cursor.execute("SELECT COUNT(*) FROM merchants WHERE city IS NOT NULL")
    stats['with_city'] = cursor.fetchone()[0]
    
    # Con country
    cursor.execute("SELECT COUNT(*) FROM merchants WHERE country IS NOT NULL")
    stats['with_country'] = cursor.fetchone()[0]
    
    # Transacciones con merchant_name
    cursor.execute("SELECT COUNT(*) FROM transacciones WHERE merchant_name IS NOT NULL")
    stats['txs_with_merchant'] = cursor.fetchone()[0]
    
    # Transacciones sin merchant_name
    cursor.execute("SELECT COUNT(*) FROM transacciones WHERE merchant_name IS NULL")
    stats['txs_without_merchant'] = cursor.fetchone()[0]
    
    conn.close()
    
    return stats


def link_transactions_to_merchants():
    """
    Vincula transacciones a merchants rellenando datos de ubicación desde la tabla merchants.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    logger.info("🔗 Estadísticas de vinculación txs-merchants...")
    
    # Txs con merchant_name que están en tabla merchants con city
    cursor.execute("""
        SELECT COUNT(*) FROM transacciones t 
        JOIN merchants m ON t.merchant_name = m.merchant_name 
        WHERE m.city IS NOT NULL
    """)
    with_city = cursor.fetchone()[0]
    
    # Txs con merchant_name que están en tabla merchants con country
    cursor.execute("""
        SELECT COUNT(*) FROM transacciones t 
        JOIN merchants m ON t.merchant_name = m.merchant_name 
        WHERE m.country IS NOT NULL
    """)
    with_country = cursor.fetchone()[0]
    
    logger.info(f"   ✅ {with_city} transacciones vinculadas con city")
    logger.info(f"   ✅ {with_country} transacciones vinculadas con country\n")
    
    conn.close()


if __name__ == '__main__':
    try:
        logger.info("=" * 60)
        logger.info("ENRIQUECIMIENTO DE MERCHANTS - INICIO")
        logger.info("=" * 60 + "\n")
        
        # Estadísticas iniciales
        logger.info("📊 Estado inicial:")
        stats_before = get_merchant_statistics()
        logger.info(f"   Total merchants: {stats_before['total_merchants']}")
        logger.info(f"   Con place_id: {stats_before['with_place_id']}")
        logger.info(f"   Con city: {stats_before['with_city']}")
        logger.info(f"   Con country: {stats_before['with_country']}")
        logger.info(f"   Txs con merchant_name: {stats_before['txs_with_merchant']}")
        logger.info(f"   Txs sin merchant_name: {stats_before['txs_without_merchant']}\n")
        
        # Ejecutar enriquecimiento
        logger.info("🚀 Iniciando proceso de enriquecimiento...\n")
        
        updated_merchant_names = populate_merchant_names()
        enriched, not_found = enrich_merchants_in_db()
        link_transactions_to_merchants()
        
        # Estadísticas finales
        logger.info("📊 Estado final:")
        stats_after = get_merchant_statistics()
        logger.info(f"   Total merchants: {stats_after['total_merchants']}")
        logger.info(f"   Con place_id: {stats_after['with_place_id']} (Δ +{stats_after['with_place_id'] - stats_before['with_place_id']})")
        logger.info(f"   Con city: {stats_after['with_city']} (Δ +{stats_after['with_city'] - stats_before['with_city']})")
        logger.info(f"   Con country: {stats_after['with_country']} (Δ +{stats_after['with_country'] - stats_before['with_country']})")
        logger.info(f"   Txs con merchant_name: {stats_after['txs_with_merchant']} (Δ +{stats_after['txs_with_merchant'] - stats_before['txs_with_merchant']})\n")
        
        logger.info("=" * 60)
        logger.info("✅ ENRIQUECIMIENTO COMPLETADO")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        exit(1)
