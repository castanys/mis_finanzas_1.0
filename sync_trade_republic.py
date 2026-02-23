#!/usr/bin/env python3
"""
Sincronizador de Trade Republic para mis_finanzas_1.0

Descarga PDFs de extracto de cuenta desde Trade Republic usando pytr,
detecta nuevos, los procesa y reporta resultados.

Uso:
    python3 sync_trade_republic.py              # Ejecución normal
    python3 sync_trade_republic.py --debug      # Con logs detallados
    python3 sync_trade_republic.py --dry-run    # Solo simular, no mover archivos

Integración en bot:
    from sync_trade_republic import sync_trade_republic
    result = sync_trade_republic()
    print(f"Estado: {result['estado']}, TXs nuevas: {result['nuevas_txs']}")
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import json
import logging
import argparse

# Configurar logger
def setup_logger(debug=False):
    """Configurar logger para sync."""
    level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger('sync_tr')
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(handler)
    
    return logger


# Constantes
PROJECT_ROOT = Path(__file__).parent
INPUT_DIR = PROJECT_ROOT / "input"
TR_DOWNLOAD_DIR = INPUT_DIR / "tr_download"
PROCESSED_DIR = INPUT_DIR / "procesados"
PYTR_TIMEOUT = 120

# Ruta a pytr en el venv
VENV_DIR = PROJECT_ROOT / "venv"
PYTR_BIN = VENV_DIR / "bin" / "pytr"


class TradeRepublicSyncError(Exception):
    """Error durante sincronización de Trade Republic."""
    pass


class AuthenticationError(TradeRepublicSyncError):
    """Error de autenticación con Trade Republic."""
    pass


class PytrNotInstalledError(TradeRepublicSyncError):
    """pytr no está instalado."""
    pass


def check_pytr_installed(logger):
    """Verificar que pytr está instalado en el venv."""
    try:
        # Buscar pytr en el venv
        pytr_path = PYTR_BIN if PYTR_BIN.exists() else "pytr"
        
        result = subprocess.run(
            [str(pytr_path), "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            raise PytrNotInstalledError("pytr retornó código de error")
        logger.debug(f"pytr {result.stdout.strip()} detectado en {pytr_path}")
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise PytrNotInstalledError(f"pytr no disponible: {e}")


def download_trade_republic_docs(logger, dry_run=False):
    """
    Ejecutar 'pytr dl_docs' para descargar documentos de Trade Republic.
    
    Returns:
        bool: True si tuvo éxito
        
    Raises:
        AuthenticationError: Si falta autenticación
        TradeRepublicSyncError: Si falla la descarga
    """
    if not dry_run:
        # Crear directorio si no existe
        TR_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Descargando documentos TR a {TR_DOWNLOAD_DIR}...")
    else:
        logger.info(f"[DRY-RUN] Descargando documentos TR a {TR_DOWNLOAD_DIR}...")
    
    if dry_run:
        logger.debug("[DRY-RUN] Saltando descarga real")
        return True
    
    try:
        # Buscar pytr en el venv
        pytr_path = PYTR_BIN if PYTR_BIN.exists() else "pytr"
        
        result = subprocess.run(
            [str(pytr_path), "dl_docs", str(TR_DOWNLOAD_DIR), "--last_days", "2"],
            capture_output=True,
            text=True,
            timeout=PYTR_TIMEOUT
        )
        
        if result.returncode != 0:
            stderr = result.stderr.lower()
            
            # Detectar errores de autenticación (frases específicas para evitar falsos positivos)
            auth_error_phrases = ["login required", "session expired", "device reset", "please login", "not authenticated", "unauthorized"]
            if any(phrase in stderr for phrase in auth_error_phrases):
                logger.error("Auth error detectado en pytr stderr")
                raise AuthenticationError(f"pytr requiere reautenticación (ejecutar: pytr login)")
            
            # Otros errores
            raise TradeRepublicSyncError(f"pytr falló: {result.stderr[:200]}")
        
        logger.info("✓ Documentos descargados correctamente")
        logger.debug(f"stdout: {result.stdout[:300]}")
        return True
        
    except subprocess.TimeoutExpired:
        raise TradeRepublicSyncError(f"pytr timeout después de {PYTR_TIMEOUT}s")


def find_new_account_statements(logger, dry_run=False):
    """
    Detectar PDFs de extracto de cuenta en tr_download/.
    
    Estrategia:
    1. Listar todos los PDFs en tr_download/ recursivamente
    2. Filtrar: nombre contiene "Extracto de cuenta"
    3. Devolver todos (el pipeline deduplicará automáticamente por hash SHA256)
    
    Returns:
        list[Path]: Rutas a PDFs encontrados en tr_download/
    """
    new_pdfs = []
    
    if not TR_DOWNLOAD_DIR.exists():
        logger.debug(f"No hay directorio {TR_DOWNLOAD_DIR}, sin PDFs")
        return new_pdfs
    
    # Listar todos los PDFs descargados
    all_pdfs = list(TR_DOWNLOAD_DIR.rglob("*.pdf"))
    logger.debug(f"Total PDFs en tr_download/: {len(all_pdfs)}")
    
    if not all_pdfs:
        logger.info("No hay PDFs en tr_download/")
        return new_pdfs
    
    # Filtrar: solo "Extracto de cuenta"
    statement_pdfs = [p for p in all_pdfs if "Extracto de cuenta" in p.name]
    logger.debug(f"PDFs de extracto de cuenta: {len(statement_pdfs)}")
    
    if not statement_pdfs:
        logger.info("No hay PDFs de extracto de cuenta en tr_download/")
        return new_pdfs
    
    # Devolver todos los PDFs encontrados
    # La deduplicación por hash se hace en el pipeline
    for pdf in statement_pdfs:
        logger.info(f"✓ PDF detectado: {pdf.name}")
        new_pdfs.append(pdf)
    
    logger.info(f"Total PDFs encontrados: {len(new_pdfs)}")
    return new_pdfs


def move_pdfs_to_input(logger, new_pdfs, dry_run=False):
    """
    Mover PDFs nuevos de tr_download/ a input/.
    
    Args:
        new_pdfs: list[Path]
        dry_run: bool
        
    Returns:
        list[Path]: Rutas en input/ donde se movieron
    """
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    moved = []
    
    for pdf in new_pdfs:
        dest = INPUT_DIR / pdf.name
        
        if dry_run:
            logger.info(f"[DRY-RUN] Copiar {pdf.name} → input/")
        else:
            try:
                shutil.copy2(pdf, dest)
                logger.info(f"✓ Movido: {pdf.name} → input/")
                moved.append(dest)
            except Exception as e:
                logger.error(f"✗ Error moviendo {pdf.name}: {e}")
                continue
    
    return moved


def process_with_pipeline(logger, pdfs_procesados=0, dry_run=False):
    """
    Ejecutar process_transactions.py sobre input/ y capturar resultados.
    
    Args:
        logger: Logger instance
        pdfs_procesados: Número de PDFs que se movieron a input/ (para reportar en resultado)
        dry_run: bool
    
    Returns:
        dict: {"nuevas_txs": int, "pdfs_procesados": int}
    """
    if dry_run:
        logger.info("[DRY-RUN] Ejecutar process_transactions.py")
        return {"nuevas_txs": 0, "pdfs_procesados": 0}
    
    logger.info("Procesando PDFs con pipeline...")
    
    try:
        result = subprocess.run(
            [sys.executable, "process_transactions.py", "--input-dir", "input/"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"process_transactions.py falló: {result.stderr[:300]}")
            return {"nuevas_txs": 0, "pdfs_procesados": 0}
        
        # Parsear output para extraer "Nuevos: X"
        stdout = result.stdout
        logger.debug(f"Pipeline output:\n{stdout[:500]}")
        
        # Buscar patron "Nuevos: X" o similar
        nuevas_txs = 0
        for line in stdout.split('\n'):
            if 'Nuevos:' in line or 'nuevos' in line.lower():
                # Intentar extraer número
                try:
                    parts = line.split(':')
                    if len(parts) > 1:
                        num_str = parts[1].strip().split()[0]
                        nuevas_txs = int(num_str)
                        logger.debug(f"Extractadas {nuevas_txs} nuevas txs del output")
                        break
                except (ValueError, IndexError):
                    pass
        
        logger.info(f"✓ Pipeline completado. Nuevas transacciones: {nuevas_txs}")
        return {"nuevas_txs": nuevas_txs, "pdfs_procesados": pdfs_procesados}
        
    except subprocess.TimeoutExpired:
        logger.error("process_transactions.py timeout (>300s)")
        return {"nuevas_txs": 0, "pdfs_procesados": 0}
    except Exception as e:
        logger.error(f"Error ejecutando pipeline: {e}")
        return {"nuevas_txs": 0, "pdfs_procesados": 0}


def sync_trade_republic(logger=None, dry_run=False):
    """
    Sincronización completa de Trade Republic.
    
    Workflow:
    1. Verificar pytr instalado
    2. Descargar documentos con pytr dl_docs
    3. Detectar PDFs nuevos de extracto de cuenta
    4. Mover a input/
    5. Ejecutar process_transactions.py
    6. Retornar resultado
    
    Args:
        logger: Logger customizado (opcional, se crea si no se pasa)
        dry_run: bool - Solo simular sin cambios
        
    Returns:
        dict: {
            "estado": "ok" | "sin_novedades" | "pytr_no_instalado" | 
                      "auth_required" | "timeout" | "error",
            "nuevas_txs": int,
            "pdfs_descargados": int,
            "pdfs_procesados": int,
            "error": str (opcional)
        }
    """
    if logger is None:
        logger = setup_logger(debug=False)
    
    result = {
        "estado": "ok",
        "nuevas_txs": 0,
        "pdfs_descargados": 0,
        "pdfs_procesados": 0,
        "error": None,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # 1. Verificar pytr
        logger.info("=" * 60)
        logger.info("Iniciando sincronización Trade Republic")
        logger.info("=" * 60)
        
        check_pytr_installed(logger)
        
        # 2. Descargar documentos
        download_trade_republic_docs(logger, dry_run=dry_run)
        
        # 3. Detectar PDFs nuevos
        new_pdfs = find_new_account_statements(logger)
        result["pdfs_descargados"] = len(new_pdfs)
        
        if not new_pdfs:
            logger.info("✓ Sin novedades (no hay PDFs nuevos)")
            result["estado"] = "sin_novedades"
            return result
        
        # 4. Mover a input/
        moved_pdfs = move_pdfs_to_input(logger, new_pdfs, dry_run=dry_run)
        result["pdfs_procesados"] = len(moved_pdfs)
        
        # 5. Procesar con pipeline
        if moved_pdfs or dry_run:
            pipeline_result = process_with_pipeline(logger, pdfs_procesados=len(moved_pdfs), dry_run=dry_run)
            result["nuevas_txs"] = pipeline_result["nuevas_txs"]
            logger.info(f"✓ Sincronización completada: {result['nuevas_txs']} nuevas transacciones")
        
        return result
        
    except AuthenticationError as e:
        logger.error(f"✗ Error de autenticación: {e}")
        result["estado"] = "auth_required"
        result["error"] = str(e)
        return result
        
    except PytrNotInstalledError as e:
        logger.error(f"✗ pytr no disponible: {e}")
        result["estado"] = "pytr_no_instalado"
        result["error"] = str(e)
        return result
        
    except TradeRepublicSyncError as e:
        logger.error(f"✗ Error de sync: {e}")
        result["estado"] = "error"
        result["error"] = str(e)
        return result
        
    except Exception as e:
        logger.error(f"✗ Error inesperado: {e}")
        result["estado"] = "error"
        result["error"] = str(e)
        return result
    
    finally:
        logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sincronizar Trade Republic con mis_finanzas"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Modo debug (logs detallados)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sin hacer cambios"
    )
    
    args = parser.parse_args()
    
    logger = setup_logger(debug=args.debug)
    result = sync_trade_republic(logger=logger, dry_run=args.dry_run)
    
    print("\n" + "=" * 60)
    print("RESULTADO FINAL:")
    print(f"Estado: {result['estado']}")
    print(f"PDFs descargados: {result['pdfs_descargados']}")
    print(f"PDFs procesados: {result['pdfs_procesados']}")
    print(f"Nuevas transacciones: {result['nuevas_txs']}")
    if result['error']:
        print(f"Error: {result['error']}")
    print("=" * 60)
    
    # Exit code para scripting
    sys.exit(0 if result["estado"] in ("ok", "sin_novedades") else 1)
