"""
Motor del clasificador: orquesta las 5 capas en orden de prioridad.
"""
import json
import os
import sqlite3
from typing import Optional, Dict, Tuple
from .exact_match import build_exact_match_dict, lookup_exact
from .merchants import lookup_merchant, GOOGLE_PLACES_MERCHANTS, FULLNAME_MERCHANTS
from .transfers import detect_transfer
from .tokens import match_token
from .valid_combos import validate_combination
from extractors import extract_merchant


def refine_cat2_by_description(cat1, cat2, descripcion):
    """
    Refina Cat2 basándose en keywords específicos en la descripción.
    Estas son reglas prioritarias que sobrescriben clasificaciones previas.

    Args:
        cat1: Categoría 1 actual
        cat2: Categoría 2 actual
        descripcion: Descripción de la transacción

    Returns:
        cat2 refinado
    """
    desc_upper = descripcion.upper()

    # Solo aplicar refinamientos a Restauración
    if cat1 == 'Restauración':
        # RESTAURANTE o ARROCERIA → Otros (usuario quiere eliminar esta subcat genérica)
        if ('RESTAURANTE' in desc_upper or 'ARROCERIA' in desc_upper) and 'GRANADINA' not in desc_upper:
            return 'Otros'
        # CHURRERIA → Churrería
        elif 'CHURRERIA' in desc_upper or 'CHURRERÍA' in desc_upper:
            return 'Churrería'

    # KIOSKO/QUIOSCO → Kiosco (puede estar en cualquier categoría)
    if 'KIOSKO' in desc_upper or 'QUIOSCO' in desc_upper:
        return 'Kiosco'

    # Si no hay refinamiento, devolver cat2 original
    return cat2


def determine_tipo(cat1, importe, descripcion=""):
    """
    Determina el tipo de transacción según Cat1, importe y descripción.

    Args:
        cat1: Categoría 1
        importe: Importe de la transacción
        descripcion: Descripción de la transacción (opcional)

    Returns:
        Tipo de transacción: TRANSFERENCIA, INVERSION, INGRESO o GASTO
    """
    if cat1 in ("Interna", "Externa", "Bizum", "Cuenta Común"):
        return "TRANSFERENCIA"

    # INVERSION: Cat1 relacionadas con actividad financiera/inversión
    if cat1 in ("Renta Variable", "Fondos", "Cripto", "Aportación", "Depósitos",
                "Dividendos", "Comisiones", "Divisas"):
        return "INVERSION"

    try:
        importe_float = float(importe)
    except (ValueError, TypeError):
        importe_float = 0

    if importe_float > 0:
        # Ingresos reales (positivos)
        if cat1 in ("Nómina", "Bonificación familia numerosa", "Servicios Consultoría",
                   "Finanzas", "Dividendos", "Wallapop", "Intereses", "Cashback", "Otros"):
            return "INGRESO"

        # Devoluciones (positivas en cualquier categoría de gasto) = GASTO
        if cat1 in ("Compras", "Alimentación", "Restauración", "Transporte", "Vivienda",
                   "Salud y Belleza", "Ocio y Cultura", "Ropa y Calzado", "Recibos",
                   "Suscripciones", "Viajes", "Deportes"):
            return "GASTO"

        # Default para positivos: INGRESO
        return "INGRESO"

    return "GASTO"


def lookup_merchant_from_db(merchant_name: str) -> Optional[Tuple[str, str]]:
    """
    Consulta la tabla 'merchants' en finsense.db por merchant_name.
    Mapea google_type a (cat1, cat2) usando GOOGLE_TYPE_TO_CAT1_CAT2.
    
    Solo devuelve resultado si:
    1. Existe entrada en tabla merchants
    2. Tiene google_type con mapeo válido
    3. El mapeo produce (cat1, cat2) válidos
    
    Args:
        merchant_name: Nombre del merchant a buscar
        
    Returns:
        Tupla (cat1, cat2) si encuentra, None en otro caso
    """
    if not merchant_name:
        return None
    
    try:
        # Importar aquí para evitar importación circular
        from src.enrichment.google_places import GOOGLE_TYPE_TO_CAT1_CAT2
        
        db_path = 'finsense.db'
        if not os.path.exists(db_path):
            return None
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Buscar merchant en BD
        cursor.execute("""
            SELECT merchant_name, google_type, cat1, cat2 
            FROM merchants 
            WHERE merchant_name = ?
        """, (merchant_name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        merchant_name_db, google_type_json, cat1_db, cat2_db = row
        
        # Si ya tiene cat1/cat2 válidos en la BD, usarlos
        if cat1_db and cat2_db:
            return (cat1_db, cat2_db)
        
        # Si no, intentar mapear desde google_type
        if google_type_json:
            import json
            try:
                google_types = json.loads(google_type_json) if isinstance(google_type_json, str) else google_type_json
                if isinstance(google_types, list):
                    # Buscar el primer tipo que tenga mapeo
                    for gtype in google_types:
                        gtype_lower = gtype.lower() if gtype else None
                        if gtype_lower in GOOGLE_TYPE_TO_CAT1_CAT2:
                            cat1, cat2 = GOOGLE_TYPE_TO_CAT1_CAT2[gtype_lower]
                            return (cat1, cat2)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return None
    
    except Exception:
        # En caso de error en BD, retornar None silenciosamente
        return None


def build_result(cat1: str, cat2: str, tipo: str, capa, merchant_name: Optional[str] = None) -> Dict:
    """
    Constructor de diccionarios de resultado de clasificación.
    Incluye merchant_name si está disponible.
    
    Args:
        cat1: Categoría 1
        cat2: Categoría 2
        tipo: Tipo de transacción
        capa: Capa en que se clasificó
        merchant_name: Nombre del merchant (opcional)
        
    Returns:
        Diccionario con resultado de clasificación
    """
    result = {
        'cat1': cat1,
        'cat2': cat2,
        'tipo': tipo,
        'capa': capa
    }
    if merchant_name:
        result['merchant_name'] = merchant_name
    return result


class Classifier:
    """
    Clasificador de transacciones bancarias basado en reglas.
    """

    def __init__(self, master_csv_path):
        """
        Inicializa el clasificador.

        Args:
            master_csv_path: Ruta al CSV maestro
        """
        self.exact_match_dict = build_exact_match_dict(master_csv_path)
        print(f"✓ Cargadas {len(self.exact_match_dict)} descripciones únicas en Exact Match")

        # Cargar excepciones (opcionales)
        self.excepciones = []
        excepciones_path = 'excepciones_clasificacion.json'
        if os.path.exists(excepciones_path):
            with open(excepciones_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.excepciones = data.get('excepciones', [])
            print(f"✓ Cargadas {len(self.excepciones)} excepciones de clasificación")

    def check_excepcion(self, fecha: str, importe: float, banco: str) -> Optional[Dict]:
        """
        Chequea si una transacción está en las excepciones.

        Args:
            fecha: Fecha de la transacción (YYYY-MM-DD)
            importe: Importe de la transacción
            banco: Nombre del banco

        Returns:
            Dict con cat1, cat2 si es excepción, None si no
        """
        for exc in self.excepciones:
            if (exc['fecha'] == fecha and
                abs(exc['importe'] - importe) < 0.01 and
                exc['banco'] == banco):
                return {
                    'cat1': exc['cat1'],
                    'cat2': exc.get('cat2', ''),
                }
        return None

    def classify(self, descripcion, banco, importe, fecha=None, cuenta=None):
        """
        Clasifica una transacción aplicando las 5 capas en orden.

        Args:
            descripcion: Descripción de la transacción
            banco: Nombre del banco
            importe: Importe de la transacción
            fecha: Fecha de la transacción (opcional, para excepciones)
            cuenta: Número de cuenta IBAN (opcional, para reglas específicas por cuenta)

        Returns:
            Diccionario con cat1, cat2, tipo, merchant_name (si es extraíble)
        """
        # Extraer merchant name al inicio (se usa en todos los retornos)
        merchant_name = extract_merchant(descripcion, banco)
        
        # === CAPA 0: Excepciones manuales ===
        if fecha:
            exc = self.check_excepcion(fecha, importe, banco)
            if exc:
                cat2_refined = refine_cat2_by_description(exc['cat1'], exc['cat2'], descripcion)
                tipo = determine_tipo(exc['cat1'], importe, descripcion)
                return {
                    'cat1': exc['cat1'],
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }

        # === REGLAS PRIORITARIAS (antes de Exact Match) ===
        desc_upper = descripcion.upper()

        # REGLA #69: AEAT/Devoluciones Tributarias → INGRESO/Impuestos/IRPF (S51)
        # Detecta: "DEVOLUCIONES TRIBUTARIAS" o "AEAT APL" (incluso si importe>0)
        if ("DEVOLUCIONES TRIBUTARIAS" in desc_upper or "AEAT APL" in desc_upper):
            cat2_refined = refine_cat2_by_description("Impuestos", "IRPF", descripcion)
            tipo = determine_tipo("Impuestos", importe, descripcion)
            return {
                'cat1': 'Impuestos',
                'cat2': cat2_refined,
                'tipo': 'INGRESO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #70: Mangopay → INGRESO/Wallapop (S51)
        # Detecta: Mangopay + Wallapop = ventas en Wallapop
        if ("MANGOPAY" in desc_upper and "WALLAPOP" in desc_upper):
            tipo = determine_tipo("Wallapop", importe, descripcion)
            return {
                'cat1': 'Wallapop',
                'cat2': 'Venta',
                'tipo': 'INGRESO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #71: Mangopay en TR (solo "from Mangopay") → INGRESO/Wallapop (S51)
        # Para los Bizums truncados que solo dicen "from Mangopay" sin Wallapop explícito
        if (banco == "Trade Republic" and "FROM MANGOPAY" in desc_upper and 
            "WALLAPOP" not in desc_upper):
            tipo = determine_tipo("Wallapop", importe, descripcion)
            return {
                'cat1': 'Wallapop',
                'cat2': 'Venta',
                'tipo': 'INGRESO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA PRIORITARIA: Detectar devoluciones explícitas (importe positivo + keywords)
        # Esto se aplica ANTES de capas normales para forzar Cat2='Devoluciones'
        try:
            importe_float = float(importe)
        except (ValueError, TypeError):
            importe_float = 0

        if importe_float > 0:
            refund_keywords = ["DEVOLUCIÓN", "DEVOLUCION", "DEVOLUCIO", "REEMBOLSO",
                              "REFUND", "RETURN", "REVERSAL"]
            amazon_keywords = ["AMAZON", "AMZN"]
            
            # Amazon refunds
            if any(kw in desc_upper for kw in amazon_keywords):
                return {
                    'cat1': 'Compras',
                    'cat2': 'Amazon',
                    'tipo': determine_tipo("Compras", importe, descripcion),
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            
            # Devoluciones explícitas en descripción
            if any(kw in desc_upper for kw in refund_keywords):
                categorias_gasto_devolucion = [
                    "Compras", "Alimentación", "Restauración", "Transporte", "Vivienda",
                    "Salud y Belleza", "Ocio y Cultura", "Ropa y Calzado", "Recibos", 
                    "Suscripciones", "Viajes"
                ]
                # Primero intentar detectar la categoría original del merchant
                merchant_result = lookup_merchant(descripcion, merchant_name)
                if merchant_result:
                    cat1, _ = merchant_result
                    if cat1 in categorias_gasto_devolucion:
                        cat2_refined = refine_cat2_by_description(cat1, "Devoluciones", descripcion)
                        tipo = determine_tipo(cat1, importe, descripcion)
                        return {
                            'cat1': cat1,
                            'cat2': cat2_refined,
                            'tipo': tipo,
                            'capa': 0,
                            'merchant_name': merchant_name
                        }
                # Si no hay merchant, intentar con exact match
                exact_result = lookup_exact(descripcion, self.exact_match_dict)
                if exact_result:
                    cat1, _ = exact_result
                    if cat1 in categorias_gasto_devolucion:
                        cat2_refined = refine_cat2_by_description(cat1, "Devoluciones", descripcion)
                        tipo = determine_tipo(cat1, importe, descripcion)
                        return {
                            'cat1': cat1,
                            'cat2': cat2_refined,
                            'tipo': tipo,
                            'capa': 0,
                            'merchant_name': merchant_name
                        }
                # Default a Compras/Devoluciones si no se identifica la categoría
                cat2_refined = refine_cat2_by_description("Compras", "Devoluciones", descripcion)
                tipo = determine_tipo("Compras", importe, descripcion)
                return {
                    'cat1': 'Compras',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }

        # REGLA #0B: Corrección de combinación inválida Compras/Alojamiento → Viajes/Alojamiento
        # Esto es un error semántico: Alojamiento pertenece SOLO a Viajes
        # (Esta regla no se ejecutará en nuevas transacciones porque el clasificador no generará esta combo,
        # pero se incluye para ser explícito y para capas posteriores que pudieran heredar esta categoría)
        # En reclassify_all.py, las transacciones existentes con esta combo simplemente no cambiarán
        # porque el clasificador ya no las genera. Esta regla es un safety net.

        # REGLA #1: B100 Health/Save/Traspaso → SIEMPRE Interna (no override con Exact Match)
        if banco == "B100":
            b100_internal_keywords = ["HEALTH", "SAVE", "TRASPASO", "AHORRO PARA HUCHA", "MOVE TO SAVE"]
            if any(kw in desc_upper for kw in b100_internal_keywords):
                cat2_refined = refine_cat2_by_description("Interna", '', descripcion)
                tipo = determine_tipo("Interna", importe, descripcion)
                return {
                    'cat1': 'Interna',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0  # Capa 0 para indicar regla prioritaria
                }

        # REGLA #1B: Cuentas Abanca ES66 (SAVE) y ES95 (HEALTH) → TRANSFERENCIA/Interna
        # Excepto si la descripción contiene INTERESES (esos sí son ingresos reales)
        if cuenta in ("ES66208001000130433834434", "ES95208001000830433834442"):
            if "INTERESES" not in desc_upper:
                cat2_refined = refine_cat2_by_description("Interna", '', descripcion)
                tipo = determine_tipo("Interna", importe, descripcion)
                return {
                    'cat1': 'Interna',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0  # Capa 0 para indicar regla prioritaria
                }

        # REGLA #2: MyInvestor "Movimiento sin concepto" importe=0 → INVERSION/Renta Variable
        # Los movimientos con importe=0 son traslados de valores (compras/ventas sin efectivo)
        # Los movimientos con importe!=0 son transferencias de dinero (se detectan en Capa 3)
        if banco == "MyInvestor" and descripcion == "Movimiento sin concepto" and abs(importe) < 0.01:
            cat2_refined = refine_cat2_by_description("Renta Variable", "Compra", descripcion)
            tipo = determine_tipo("Renta Variable", importe, descripcion)
            return {
                'cat1': 'Renta Variable',
                'cat2': 'Compra',
                'tipo': tipo,
                'capa': 0  # Regla prioritaria
            }

        # REGLA #3: "TRANSFERENCIA INTERNA/EXTERNA" explícita → TRANSFERENCIA (no override con merchants)
        # Previene que palabras como "NOMINA" en descripción lo clasifiquen como gasto
        if 'TRANSFERENCIA INTERNA' in desc_upper:
            cat2_refined = refine_cat2_by_description("Interna", '', descripcion)
            tipo = determine_tipo("Interna", importe, descripcion)
            return {
                'cat1': 'Interna',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0  # Regla prioritaria
            }
        if 'TRANSFERENCIA EXTERNA' in desc_upper:
            cat2_refined = refine_cat2_by_description("Externa", '', descripcion)
            tipo = determine_tipo("Externa", importe, descripcion)
            return {
                'cat1': 'Externa',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0  # Regla prioritaria
            }

        # REGLA #4: Tatiana Santallana → GASTO/Vivienda/Limpieza (no transferencia externa)
        # Pagos por servicio de limpieza del hogar
        if 'TATIANA' in desc_upper and 'SANTALLANA' in desc_upper:
            cat2_refined = refine_cat2_by_description("Vivienda", "Limpieza", descripcion)
            tipo = determine_tipo("Vivienda", importe, descripcion)
            return {
                'cat1': 'Vivienda',
                'cat2': 'Limpieza',
                'tipo': tipo,
                'capa': 0  # Regla prioritaria
            }

        # REGLA #5: Alejandro Fernández-Castanys (hermano) → GASTO/Finanzas/Préstamos
        # Devolución de préstamo al hermano. Solo pagos grandes (>€500)
        # Pagos pequeños son Bizums normales que se detectan en capa 3
        if 'ALEJANDRO' in desc_upper and importe < -500:
            # Verificar que es el hermano (apellidos)
            if any(surname in desc_upper for surname in ['FERNÁNDEZ', 'FERNANDEZ', 'FDEZCASTANYS', 'CASTANYS']):
                cat2_refined = refine_cat2_by_description("Finanzas", "Préstamos", descripcion)
                tipo = determine_tipo("Finanzas", importe, descripcion)
                return {
                    'cat1': 'Finanzas',
                    'cat2': 'Préstamos',
                    'tipo': tipo,
                    'capa': 0  # Regla prioritaria
                }

        # REGLA #6: Depósito a ADVCASH para cripto (2021-12-07 -3000€ Openbank + Mediolanum hacia ADVCASH)
        # Detecta: "TRANSFERENCIA A FAVOR DE Pablo Fernández-Castanys" en 2021-12-07 por -3000€
        if (fecha == "2021-12-07" and banco == "Openbank" and abs(importe - (-3000.0)) < 0.01 and
            'PABLO' in desc_upper and 'FERNÁNDEZ' in desc_upper):
            cat2_refined = refine_cat2_by_description("Cripto", "ADVCASH", descripcion)
            tipo = determine_tipo("Cripto", importe, descripcion)
            return {
                'cat1': 'Cripto',
                'cat2': 'ADVCASH',
                'tipo': tipo,
                'capa': 0  # Regla prioritaria
            }

        # REGLA #7: Depósito a BINANCE para cripto (2021-12-09 -2000€ Mediolanum hacia BINANCE)
        # Detecta: "Transferencia" en 2021-12-09 por -2000€ en Mediolanum
        if (fecha == "2021-12-09" and banco == "Mediolanum" and abs(importe - (-2000.0)) < 0.01 and
            'TRANSFERENCIA' in desc_upper):
            cat2_refined = refine_cat2_by_description("Cripto", "Binance", descripcion)
            tipo = determine_tipo("Cripto", importe, descripcion)
            return {
                'cat1': 'Cripto',
                'cat2': 'Binance',
                'tipo': tipo,
                'capa': 0  # Regla prioritaria
            }

        # REGLA #8: Depósito a ADVCASH para cripto (2022-05-12 -1000€ Openbank "Funding of Pablo...")
        # Detecta: "TRANSFERENCIA A FAVOR DE Pablo Fernandez CONCEPTO: E 7634 06 06 5448 Funding of..."
        if (fecha == "2022-05-12" and banco == "Openbank" and abs(importe - (-1000.0)) < 0.01 and
            'FUNDING' in desc_upper):
            cat2_refined = refine_cat2_by_description("Cripto", "ADVCASH", descripcion)
            tipo = determine_tipo("Cripto", importe, descripcion)
            return {
                'cat1': 'Cripto',
                'cat2': 'ADVCASH',
                'tipo': tipo,
                'capa': 0  # Regla prioritaria
            }

        # REGLA #30: Transporte en patrón "COMPRA EN" — PRIMERO (evita falsos positivos con BAR, BARRIO, etc.)
        if "COMPRA EN" in desc_upper:
            cat2 = None
            if any(keyword in desc_upper for keyword in ["TAXI", "TAXIS"]):
                cat2 = "Taxi"
            elif any(keyword in desc_upper for keyword in ["TREN", "SBB", "SPANAIR", "TAQUILLAS"]):
                cat2 = "Transporte público"
            elif any(keyword in desc_upper for keyword in ["APARC", "PARKING", "GLORIETA"]):
                cat2 = "Parking"
            elif any(keyword in desc_upper for keyword in ["EESS", "TAMOIL", "COMBUSTIBLE", "REPSOL", "GASOLINERA"]):
                cat2 = "Combustible"
            
            if cat2:
                cat2_refined = refine_cat2_by_description("Transporte", cat2, descripcion)
                tipo = determine_tipo("Transporte", importe, descripcion)
                return {
                    'cat1': 'Transporte',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }

        # REGLA #29: Restauración en patrón "COMPRA EN" (BAR, CERVECER, TERRAZA, TABERNA, TAPAS, CAFE, BODEGA)
        # Evitar "BARRIO" = keyword BAR
        if "COMPRA EN" in desc_upper and any(keyword in desc_upper for keyword in ["CERVECER", "TERRAZA", "TABERNA", "TAPAS", "TAPER", "CAFE", "BODEGA", " BAR ", "BAR,"]):
            cat2_refined = refine_cat2_by_description("Restauración", "Bar", descripcion)
            tipo = determine_tipo("Restauración", importe, descripcion)
            return {
                'cat1': 'Restauración',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #31: Otros en patrón "COMPRA EN" (ROPA, TEATRO, FARMAC, CLINIC, SUPERMERCADO)
        if "COMPRA EN" in desc_upper:
             if any(keyword in desc_upper for keyword in ["STRADIVARIUS", "JACK&JONES", "ROPA", "CALZADO"]):
                 cat1, cat2 = "Ropa y Calzado", "Ropa y Accesorios"
             elif any(keyword in desc_upper for keyword in ["TEATRO", "CIRCO", "VOYAGER"]):
                 cat1, cat2 = "Ocio y Cultura", "Entradas"
             elif any(keyword in desc_upper for keyword in ["FARMAC", "CLINIC"]) and "ORTONOVA" not in desc_upper:
                 cat1, cat2 = "Salud y Belleza", "Farmacia"
             elif any(keyword in desc_upper for keyword in ["SUPERMERCADO", "SUPERDUMBO"]):
                 cat1, cat2 = "Alimentación", "Supermercado"
             else:
                 cat1, cat2 = None, None
             
             if cat1 and cat2:
                 cat2_refined = refine_cat2_by_description(cat1, cat2, descripcion)
                 tipo = determine_tipo(cat1, importe, descripcion)
                 return {
                     'cat1': cat1,
                     'cat2': cat2_refined,
                     'tipo': tipo,
                     'capa': 0,
                     'merchant_name': merchant_name
                 }

        # REGLA #32: Vinos (Vinoseleccion) → ALIMENTACION/Vinos
        if any(keyword in desc_upper for keyword in ["VINOSELECCION"]):
            cat1, cat2 = "Alimentación", "Vinos"
            tipo = determine_tipo(cat1, importe, descripcion)
            return {
                'cat1': cat1,
                'cat2': cat2,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #33: RevPoints con Redondeo (Revolut cashback/rewards) → INGRESO/Cashback
        if "RevPoints con Redondeo" in descripcion:
            cat1, cat2 = "Cashback", ""
            tipo = "INGRESO"
            return {
                'cat1': cat1,
                'cat2': cat2,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #34: Aeropuerto o Tienda Travel (WH SMITH AEROPUERTO, LILIENTHAL BERLIN) → VIAJES/Tienda de Viaje
        if any(keyword in desc_upper for keyword in ["AEROPUERTO", "LILIENTHAL", "BERLIN"]):
            cat1, cat2 = "Viajes", "Tienda de Viaje"
            tipo = determine_tipo(cat1, importe, descripcion)
            return {
                'cat1': cat1,
                'cat2': cat2,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #35: "COMPRAS Y OPERACIONES CON TARJETA 4B" positivas → COMPRAS/Devoluciones
        # Patrón de devoluciones/reembolsos con importe positivo en banco antiguo (6 txs)
        if ("COMPRAS Y OPERACIONES CON TARJETA" in desc_upper and importe_float > 0):
            cat2_refined = refine_cat2_by_description("Compras", "Devoluciones", descripcion)
            tipo = determine_tipo("Compras", importe, descripcion)
            return {
                'cat1': 'Compras',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #36: Transporte/Taxi en "COMPRA EN" (BOLT, UBER, CABIFY, BLABLACAR) → TRANSPORTE/Taxi (12 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["BOLT", "UBER", "CABIFY", "BLABLACAR"]):
            cat2_refined = refine_cat2_by_description("Transporte", "Taxi", descripcion)
            tipo = determine_tipo("Transporte", importe, descripcion)
            return {
                'cat1': 'Transporte',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #37: Transporte/Combustible en "COMPRA EN" (ESTAC, ANDAMUR, BALLENOIL, AREA DE SERVICIO) (16 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["ESTAC", "ANDAMUR", "BALLENOIL", "AREA DE SERVICIO"]):
            cat2_refined = refine_cat2_by_description("Transporte", "Combustible", descripcion)
            tipo = determine_tipo("Transporte", importe, descripcion)
            return {
                'cat1': 'Transporte',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #38: Restauración en "COMPRA EN" (PIZZA, ASADOR, RESTAUR, BRASERIA, CHIRINGUITO) (20 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["PIZZA", "ASADOR", "RESTAUR", "BRASERIA", "CHIRINGUITO"]):
            cat2_refined = refine_cat2_by_description("Restauración", "Otros", descripcion)
            tipo = determine_tipo("Restauración", importe, descripcion)
            return {
                'cat1': 'Restauración',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #39: Deportes en "COMPRA EN" (SPORT, PADEL, NAUTIC, CICLOS) (20 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["SPORT", "PADEL", "NAUTIC", "CICLOS"]):
            cat2_refined = refine_cat2_by_description("Deportes", "Club", descripcion)
            tipo = determine_tipo("Deportes", importe, descripcion)
            return {
                'cat1': 'Deportes',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #40: Compras/Libros en "COMPRA EN" (Kindle, XBOX, ELESPANOL) (17 txs)
        # User decision: Libros digitales → Compras/Libros (no Suscripciones/Streaming)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["KINDLE", "XBOX", "ELESPANOL"]):
            cat2_refined = refine_cat2_by_description("Compras", "Libros", descripcion)
            tipo = determine_tipo("Compras", importe, descripcion)
            return {
                'cat1': 'Compras',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #41: Vivienda/Reformas en "COMPRA EN" (FERRETERI, PARQUET, ALUMINIO, PINTURA) (8 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["FERRETERI", "PARQUET", "ALUMINIO", "PINTURA"]):
            cat2_refined = refine_cat2_by_description("Vivienda", "Reformas", descripcion)
            tipo = determine_tipo("Vivienda", importe, descripcion)
            return {
                'cat1': 'Vivienda',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #42: Viajes/Alojamiento en "COMPRA EN" (AIRBNB, CAMPING, HOTEL) (2 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["AIRBNB", "CAMPING", "HOTEL"]):
            cat2_refined = refine_cat2_by_description("Viajes", "Alojamiento", descripcion)
            tipo = determine_tipo("Viajes", importe, descripcion)
            return {
                'cat1': 'Viajes',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #43: Viajes/Aeropuerto en "COMPRA EN" (AEROPORT, AER.) (2 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["AEROPORT", "AER."]):
            cat2_refined = refine_cat2_by_description("Viajes", "Aeropuerto", descripcion)
            tipo = determine_tipo("Viajes", importe, descripcion)
            return {
                'cat1': 'Viajes',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #44: Impuestos/Municipales en "COMPRA EN" (AYTO, EXCMO, AJUNTAMENT) (4 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["AYTO", "EXCMO", "AJUNTAMENT"]):
            cat2_refined = refine_cat2_by_description("Impuestos", "Municipales", descripcion)
            tipo = determine_tipo("Impuestos", importe, descripcion)
            return {
                'cat1': 'Impuestos',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #45: Vivienda/Mantenimiento en "COMPRA EN" (GARDEN, JARDIN) (2 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["GARDEN", "JARDIN"]):
            cat2_refined = refine_cat2_by_description("Vivienda", "Mantenimiento", descripcion)
            tipo = determine_tipo("Vivienda", importe, descripcion)
            return {
                'cat1': 'Vivienda',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
             }

        # REGLA #46: Restauración/Restaurante - Keywords restaurantes (PIZZERIA, KEBAB, etc.) (~15 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["PIZZERIA", "KEBAB", "GOIKO", "CERVERZA", "CARBONERIA", "CHURRERIA"]):
            cat2_refined = refine_cat2_by_description("Restauración", "Restaurante", descripcion)
            tipo = determine_tipo("Restauración", importe, descripcion)
            return {
                'cat1': 'Restauración',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #47: Transporte/Combustible - Estaciones de servicio adicionales (~11 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["PETROPRIX", "EST SERV", "EST.SERV", "PLENOIL", "EE.SS", "BALLENOIL"]):
            cat2_refined = refine_cat2_by_description("Transporte", "Combustible", descripcion)
            tipo = determine_tipo("Transporte", importe, descripcion)
            return {
                'cat1': 'Transporte',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #48: Transporte/Público - Ferrocarriles internacionales (~15 txs)
        if any(kw in desc_upper for kw in ["BUNDESBAHN", "SCHIPHOL", "GVB", "PKP", "OMIO", "RAILW", "FGW SELF", "PERSONENVERVOER"]) or \
           (any(city in desc_upper for city in ["SANTIAGO", "PONTEVEDR", "CALDAS", "VIGO"]) and any(time_pattern in descripcion for time_pattern in ["08:", "09:", "10:", "11:", "12:", "13:", "14:", "15:", "16:", "17:", "18:", "19:", "20:", "21:"])):
            cat2_refined = refine_cat2_by_description("Transporte", "Público", descripcion)
            tipo = determine_tipo("Transporte", importe, descripcion)
            return {
                'cat1': 'Transporte',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #49: Compras/Alimentación - Productos alimentación específicos (PESCADOS, CARNES, LONJA) (~12 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["PESCADOS", "CARNES", "CARNISSERIA", "LONJA"]):
            cat2_refined = refine_cat2_by_description("Compras", "Alimentación", descripcion)
            tipo = determine_tipo("Compras", importe, descripcion)
            return {
                'cat1': 'Compras',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #50: Vivienda/Bricolaje - Tiendas bricolaje exclusión (BRICO excluyendo ya clasificadas) (~4 txs)
        if "COMPRA EN" in desc_upper and "BRICO" in desc_upper and "BRICOFIRE" not in desc_upper and "BRICO HOUSE" not in desc_upper:
            cat2_refined = refine_cat2_by_description("Vivienda", "Bricolaje", descripcion)
            tipo = determine_tipo("Vivienda", importe, descripcion)
            return {
                'cat1': 'Vivienda',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #51: Vivienda/Decoración - Tiendas muebles y decoración (KAVE HOME, ESPACIO CASA, etc.) (~5 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["KAVE HOME", "ESPACIO CASA", "MODREGO", "HORIZONTALIA"]):
            cat2_refined = refine_cat2_by_description("Vivienda", "Decoración", descripcion)
            tipo = determine_tipo("Vivienda", importe, descripcion)
            return {
                'cat1': 'Vivienda',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #52: Ocio y Cultura/Espectáculos - Ticketerías (TICKETMASTER, KINEPOLIS, etc.) (~6 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["TICKETMASTER", "KINEPOLIS", "CROCANT", "ROCKOLA", "GEODA"]):
            cat2_refined = refine_cat2_by_description("Ocio y Cultura", "Espectáculos", descripcion)
            tipo = determine_tipo("Ocio y Cultura", importe, descripcion)
            return {
                'cat1': 'Ocio y Cultura',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #53: Suscripciones/Software - Software y herramientas SaaS (OPENAI, NORDVPN, etc.) (~7 txs)
        if "COMPRA EN" in desc_upper and any(kw in desc_upper for kw in ["OPENAI", "NORDVPN", "KINOMAP", "GODADDY", "SPACE DESIGNER", "BRAINTREE"]):
            cat2_refined = refine_cat2_by_description("Suscripciones", "Software", descripcion)
            tipo = determine_tipo("Suscripciones", importe, descripcion)
            return {
                'cat1': 'Suscripciones',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #54: Transferencias a Cuenta Común (Yolanda Arroyo) → TRANSFERENCIA/Cuenta Común
        # Detecta: transferencias recurrentes a cuentas de terceros para gastos compartidos
        if 'YOLANDA ARROYO' in desc_upper or 'YOLANDA arroyo' in descripcion:
            tipo = determine_tipo("Cuenta Común", importe, descripcion)
            return {
                'cat1': 'Cuenta Común',
                'cat2': '',  # Hogar removed (S51) - redundant descriptor
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #55: MCR Solutions Business (Bankinter) → SERVICIOS CONSULTORÍA/Honorarios
        # Pagos de honorarios como autónomo a empresa propia (importes 6k-11k negativos)
        if banco == "Bankinter" and "MCR SOLUTIONS BUSINESS" in desc_upper:
            cat2_refined = refine_cat2_by_description("Servicios Consultoría", "Honorarios", descripcion)
            tipo = determine_tipo("Servicios Consultoría", importe, descripcion)
            return {
                'cat1': 'Servicios Consultoría',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #56: TRIBUTO (Bankinter) → IMPUESTOS/Otros
        # Pagos de tributos fiscales directos (TRIBUTO 1003900006191X)
        if banco == "Bankinter" and "TRIBUTO" in desc_upper and "1003900006191X" in descripcion:
            cat2_refined = refine_cat2_by_description("Impuestos", "Otros", descripcion)
            tipo = determine_tipo("Impuestos", importe, descripcion)
            return {
                'cat1': 'Impuestos',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #57: LIQ. PROPIA CTA. (Bankinter) → INGRESO/Intereses (cat2 vacío)
        # Liquidación de intereses de la propia cuenta (importes muy pequeños, positivos)
        if banco == "Bankinter" and "LIQ. PROPIA CTA." in desc_upper:
            tipo = determine_tipo("Intereses", importe, descripcion)
            return {
                'cat1': 'Intereses',
                'cat2': '',
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #58: RECTIF. LIQ. CTA. (Bankinter) → INGRESO/Intereses (cat2 vacío)
        # Rectificación de liquidación de intereses
        if banco == "Bankinter" and "RECTIF. LIQ. CTA." in desc_upper:
            tipo = determine_tipo("Intereses", importe, descripcion)
            return {
                'cat1': 'Intereses',
                'cat2': '',
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #59: BARBERIA CARLOS CONDE (Bankinter) → SALUD Y BELLEZA/Peluquería
        # Servicios de barbería/peluquería
        if banco == "Bankinter" and "BARBERIA CARLOS CONDE" in desc_upper:
            cat2_refined = refine_cat2_by_description("Salud y Belleza", "Peluquería", descripcion)
            tipo = determine_tipo("Salud y Belleza", importe, descripcion)
            return {
                'cat1': 'Salud y Belleza',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #60: CENTRO DEP. ZONA SUR (Bankinter) → DEPORTES/Gimnasio
        # Centro deportivo / gimnasio
        if banco == "Bankinter" and "CENTRO DEP. ZONA SUR" in desc_upper:
            cat2_refined = refine_cat2_by_description("Deportes", "Gimnasio", descripcion)
            tipo = determine_tipo("Deportes", importe, descripcion)
            return {
                'cat1': 'Deportes',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #61: HOUSE DECORACION (Bankinter) → VIVIENDA/Decoración
        # Tienda de decoración del hogar
        if banco == "Bankinter" and "HOUSE DECORACION" in desc_upper:
            cat2_refined = refine_cat2_by_description("Vivienda", "Decoración", descripcion)
            tipo = determine_tipo("Vivienda", importe, descripcion)
            return {
                'cat1': 'Vivienda',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #62: INGRESO EN TARJ.CREDITO (Bankinter) → FINANZAS/Tarjeta Crédito
        # Pago/ingreso a tarjeta de crédito
        if banco == "Bankinter" and "INGRESO EN TARJ.CREDITO" in desc_upper:
            cat2_refined = refine_cat2_by_description("Finanzas", "Tarjeta Crédito", descripcion)
            tipo = determine_tipo("Finanzas", importe, descripcion)
            return {
                'cat1': 'Finanzas',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #63: TRANSF OTR /tiendadelasalarmas (Bankinter) → COMPRAS/Otros
        # Transferencia a tienda (compra online o prepago)
        if banco == "Bankinter" and "TRANSF OTR" in desc_upper and "TIENDADELASALARMAS" in desc_upper:
            cat2_refined = refine_cat2_by_description("Compras", "Otros", descripcion)
            tipo = determine_tipo("Compras", importe, descripcion)
            return {
                'cat1': 'Compras',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #64: COMIS. MANT. (Bankinter) → COMISIONES
        # Comisión de mantenimiento de cuenta bancaria
        if banco == "Bankinter" and "COMIS. MANT." in desc_upper:
            cat2_refined = refine_cat2_by_description("Comisiones", "", descripcion)
            tipo = determine_tipo("Comisiones", importe, descripcion)
            return {
                'cat1': 'Comisiones',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #65B: Recibos Ayuntamiento con referencia de impuesto específico
        # Detecta por patrón de mandato en descripción
        if "AYUNTAMIENTO" in desc_upper and "RECIBO" in desc_upper and "MANDATO" in desc_upper:
            # IBI (Impuesto sobre Bienes Inmuebles) — REF. MANDATO 011-...
            if "MANDATO 011-" in descripcion:
                cat2_refined = refine_cat2_by_description("Impuestos", "IBI", descripcion)
                tipo = determine_tipo("Impuestos", importe, descripcion)
                return {
                    'cat1': 'Impuestos',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            
            # Impuesto de Matriculación (IVTM) — REF. MANDATO 040-...
            if "MANDATO 040-" in descripcion:
                cat2_refined = refine_cat2_by_description("Impuestos", "IVTM", descripcion)
                tipo = determine_tipo("Impuestos", importe, descripcion)
                return {
                    'cat1': 'Impuestos',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }

        # REGLA #65: Recibos SEPA Direct Debit (reclasificar por tipo de pago)
        # Patrón: "Recibos Sepa Direct Debit transfer to <EMPRESA>"
        # Estos SON recibos/domiciliaciones, no transferencias externas reales
        # Reclasificar según el acreedor (telefónica, gimnasio, agua, etc.)
        if "SEPA DIRECT DEBIT TRANSFER" in desc_upper:
            # DIGI SPAIN TELECOM → RECIBOS/Telefonía
            if "DIGI SPAIN TELECOM" in desc_upper:
                cat2_refined = refine_cat2_by_description("Recibos", "Telefonía", descripcion)
                tipo = determine_tipo("Recibos", importe, descripcion)
                return {
                    'cat1': 'Recibos',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            
            # FELITONA SERVICIOS Y GESTIONES → RECIBOS/Gimnasio (recibo de gimnasio)
            if "FELITONA" in desc_upper:
                cat2_refined = refine_cat2_by_description("Recibos", "Gimnasio", descripcion)
                tipo = determine_tipo("Recibos", importe, descripcion)
                return {
                    'cat1': 'Recibos',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            
            # HIDROGEA S.A. / AGUA → RECIBOS/Agua (ya está correctamente clasificado, pero asegurar)
            if "HIDROGEA" in desc_upper or "AGUA" in desc_upper:
                cat2_refined = refine_cat2_by_description("Recibos", "Agua", descripcion)
                tipo = determine_tipo("Recibos", importe, descripcion)
                return {
                    'cat1': 'Recibos',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            
            # AYUNTAMIENTO → RECIBOS/Plan de pago personalizado
            # Pago mensual unificado de todas las obligaciones municipales (IBI, IVTM, etc.)
            if "AYUNTAMIENTO" in desc_upper or "EXCMO" in desc_upper:
                cat2_refined = refine_cat2_by_description("Recibos", "Plan de pago personalizado", descripcion)
                tipo = determine_tipo("Recibos", importe, descripcion)
                return {
                    'cat1': 'Recibos',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            
            # ASOCIACION ESPAÑOLA CONTRA EL... → RECIBOS/Donaciones (ya está, pero asegurar)
            if "ASOCIACION" in desc_upper:
                cat2_refined = refine_cat2_by_description("Recibos", "Donaciones", descripcion)
                tipo = determine_tipo("Recibos", importe, descripcion)
                return {
                    'cat1': 'Recibos',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }

        # REGLA #66: Trade Republic PayOut to transit → TRANSFERENCIA/Externa
        # "PayOut to transit" son transferencias salientes de TR a cuentas externas
        # Negativas, variados importes, sin destinatario específico → Externa
        if "PAYOUT TO TRANSIT" in desc_upper:
            tipo = determine_tipo("Externa", importe, descripcion)
            return {
                'cat1': 'Externa',
                'cat2': 'PayOut',
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #67: Trade Republic Bizum cortos truncados (sin "Outgoing/Incoming transfer")
        # Patrón: "for <nombre>" o "from <nombre>" (sin "Outgoing/Incoming transfer" al inicio)
        # Estos son Bizums donde el PDF parser truncó la descripción
        # NOTA: Eliminada cat2='Bizum P2P' (S51) - redundante con cat1=Bizum
        if banco == "Trade Republic" and (desc_upper.startswith("FOR ") or desc_upper.startswith("FROM ")):
            # Skip Wallapop Bizums - they're handled in REGLA #71
            if "WALLAPOP" not in desc_upper:
                tipo = determine_tipo("Bizum", importe, descripcion)
                return {
                    'cat1': 'Bizum',
                    'cat2': '',
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }

         # REGLA #6: Patrón "COMPRA EN" (histórico de Openbank, pero aplicar a todos)
         # Detecta transacciones en formato: "COMPRA EN <MERCHANT>, CON LA TARJETA..."
        # Si extract_merchant() logró extraer un merchant, procesa aquí.
        # Nuevo: Buscar primero en GOOGLE_PLACES_MERCHANTS, luego en MERCHANT_RULES/lookup_merchant (sobre merchant_name), después fallback.
        if merchant_name and ("COMPRA EN" in desc_upper or "Apple pay: COMPRA EN" in desc_upper):
            # 1. Google Places enriched
            if merchant_name in GOOGLE_PLACES_MERCHANTS:
                merchant_data = GOOGLE_PLACES_MERCHANTS[merchant_name]
                cat1 = merchant_data['cat1']
                cat2 = merchant_data['cat2']
            else:
                # 2. Buscar en MERCHANT_RULES
                merchant_result = lookup_merchant(merchant_name, merchant_name)
                if merchant_result:
                    cat1, cat2 = merchant_result
                else:
                    # 3. Fallback genérico
                    cat1 = "Compras"
                    cat2 = "Otros"
            cat2_refined = refine_cat2_by_description(cat1, cat2, descripcion)
            tipo = determine_tipo(cat1, importe, descripcion)
            return {
                'cat1': cat1,
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0  # Regla prioritaria para evitar que Exact Match/Merchant override
            }

        # REGLA #7: PayPal (RECIBO PayPal o COMPRA EN PAYPAL) → COMPRAS/PayPal
        # Las domiciliaciones de PayPal deben clasificarse como compras online, no como recibos
        # Esta regla prioritaria se aplica ANTES de Exact Match para override
        if 'PAYPAL' in desc_upper or 'RECIBO PAYPAL' in desc_upper:
            cat2_refined = refine_cat2_by_description("Compras", "PayPal", descripcion)
            tipo = determine_tipo("Compras", importe, descripcion)
            return {
                'cat1': 'Compras',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0  # Regla prioritaria para override de Exact Match
            }

        # REGLA #8: IVA AUTOLIQUIDACION → IMPUESTOS/IVA
        # Domiciliaciones de IVA trimestral de autónomos
        if 'AUTOLIQUIDACION' in desc_upper and 'I.V.A.' in desc_upper:
            cat2_refined = refine_cat2_by_description("Impuestos", "IVA", descripcion)
            tipo = determine_tipo("Impuestos", importe, descripcion)
            return {
                'cat1': 'Impuestos',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0  # Regla prioritaria para override de Exact Match
            }

        # REGLA #9: Recibos mal clasificados (ONEY, WIZINK, CITIBANK, etc.) → FINANZAS/Préstamos
        # Domiciliaciones de préstamos/créditos mal etiquetadas como Recibos
        # ONEY: cuotas de préstamo personal
        # WIZINK: crédito de banco digital
        # CITIBANK: cuotas de tarjeta de crédito
        financiero_keywords = ['ONEY', 'WIZINK', 'CITIBANK']
        if 'RECIBO' in desc_upper and any(kw in desc_upper for kw in financiero_keywords):
            cat2_refined = refine_cat2_by_description("Finanzas", "Préstamos", descripcion)
            tipo = determine_tipo("Finanzas", importe, descripcion)
            return {
                'cat1': 'Finanzas',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0  # Regla prioritaria
            }

        # REGLA #9B: Patrón "Otros Transacción [MERCHANT] con tarjeta" → extraer merchant
        # Este patrón viene de bancos antiguos que etiquetaban transacciones como "Otros Transacción"
        # Ejemplo: "Otros Transacción JOKER con tarjeta" → buscar JOKER en MERCHANT_RULES
        if "Otros Transacción" in descripcion or "Otros t Transacción" in descripcion:
            import re
            # Extraer el merchant entre "Transacción" y "con tarjeta"
            match = re.search(r'Transacción\s+(.+?)\s+con\s+tarjeta', descripcion, re.IGNORECASE)
            if match:
                extracted_merchant = match.group(1).strip()
                # Buscar en MERCHANT_RULES (lookup_merchant ya está importado al inicio)
                merchant_result = lookup_merchant(extracted_merchant, extracted_merchant)
                if merchant_result:
                    cat1, cat2 = merchant_result
                    cat2_refined = refine_cat2_by_description(cat1, cat2, descripcion)
                    tipo = determine_tipo(cat1, importe, descripcion)
                    return {
                        'cat1': cat1,
                        'cat2': cat2_refined,
                        'tipo': tipo,
                        'capa': 0  # Regla prioritaria
                    }

        # REGLA #10B: Seguros específicos
        if 'SANITAS' in desc_upper or 'SEGURCAIXA' in desc_upper:
            cat2_refined = refine_cat2_by_description("Seguros", "Salud", descripcion)
            tipo = determine_tipo("Seguros", importe, descripcion)
            return {
                'cat1': 'Seguros',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }
        
        if 'LINEA DIRECTA' in desc_upper or 'IATI SEGUROS' in desc_upper:
            cat2_refined = refine_cat2_by_description("Seguros", "Viajes/General", descripcion)
            tipo = determine_tipo("Seguros", importe, descripcion)
            return {
                'cat1': 'Seguros',
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #10: Recibos especiales (vinos, grandes almacenes, gimnasios, etc.)
        # Reclasificar basándose en keywords específicos
        if 'RECIBO' in desc_upper:
            if 'VINOSELECCION' in desc_upper:
                cat2_refined = refine_cat2_by_description("Alimentación", "Vinos", descripcion)
                tipo = determine_tipo("Alimentación", importe, descripcion)
                return {
                    'cat1': 'Alimentación',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            elif 'GRANDES ALMACENES' in desc_upper:
                cat2_refined = refine_cat2_by_description("Compras", "Grandes Almacenes", descripcion)
                tipo = determine_tipo("Compras", importe, descripcion)
                return {
                    'cat1': 'Compras',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            elif 'JAVISA SPORT' in desc_upper or 'BODY FACTORY' in desc_upper:
                cat2_refined = refine_cat2_by_description("Ocio y Cultura", "Deporte", descripcion)
                tipo = determine_tipo("Ocio y Cultura", importe, descripcion)
                return {
                    'cat1': 'Ocio y Cultura',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            elif 'ENERGIA XXI' in desc_upper:
                cat2_refined = refine_cat2_by_description("Recibos", "Gas", descripcion)
                tipo = determine_tipo("Recibos", importe, descripcion)
                return {
                    'cat1': 'Recibos',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            elif 'CONTRIB' in desc_upper:
                cat2_refined = refine_cat2_by_description("Impuestos", "Municipales", descripcion)
                tipo = determine_tipo("Impuestos", importe, descripcion)
                return {
                    'cat1': 'Impuestos',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            elif 'ASOC' in desc_upper and 'DEPORTIVA' in desc_upper:
                cat2_refined = refine_cat2_by_description("Ocio y Cultura", "Deporte", descripcion)
                tipo = determine_tipo("Ocio y Cultura", importe, descripcion)
                return {
                    'cat1': 'Ocio y Cultura',
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 0,
                    'merchant_name': merchant_name
                }

        # REGLA #11: Ingresos especiales (INGRESO/Otros con subcategoría)
        if importe > 0:
            if 'PENSION' in desc_upper or 'ABONO' in desc_upper:
                if 'PENSION' in desc_upper or 'ABONO PENSION' in desc_upper:
                    return {
                        'cat1': 'Otros',
                        'cat2': 'Prestación',
                        'tipo': 'INGRESO',
                        'capa': 0,
                        'merchant_name': merchant_name
                    }
            
            if 'RETROCESION' in desc_upper:
                return {
                    'cat1': 'Otros',
                    'cat2': 'Devoluciones',
                    'tipo': 'INGRESO',
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            
            if 'SINIESTRO' in desc_upper or ('GENERALI' in desc_upper and 'SEGUROS' in desc_upper):
                return {
                    'cat1': 'Otros',
                    'cat2': 'Seguros',
                    'tipo': 'INGRESO',
                    'capa': 0,
                    'merchant_name': merchant_name
                }
            
            if desc_upper.strip() in ['DONACIoN', 'DONACION']:
                return {
                    'cat1': 'Otros',
                    'cat2': 'Extraordinario',
                    'tipo': 'INGRESO',
                    'capa': 0,
                    'merchant_name': merchant_name
                }

        # REGLA #12: Brokers y plataformas de inversión → TRANSFERENCIA/Interna
        # Transf erencias a/desde brokers (DeGiro, Auriga, etc.) y bancos alternativos (Revolut)
        # son movimientos internos del usuario, no transferencias externas reales
        if 'DEGIRO' in desc_upper or 'STICHTING' in desc_upper:
            # DeGiro es un bróker holandés, todas sus transferencias son internas
            return {
                'cat1': 'Interna',
                'cat2': '',
                'tipo': 'TRANSFERENCIA',
                'capa': 0,
                'merchant_name': merchant_name
            }
        
        if 'AURIGA' in desc_upper and 'INVESTOR' in desc_upper:
            # Auriga Global Investors - asesor de inversión
            return {
                'cat1': 'Interna',
                'cat2': '',
                'tipo': 'TRANSFERENCIA',
                'capa': 0,
                'merchant_name': merchant_name
            }
        
        if ('Transferencia' in descripcion and 'Revolut' in descripcion) or \
           ('Transferencia a un cliente de Revolut' in descripcion) or \
           ('Transferencia Incoming transfer' in descripcion and 'Revolut' in descripcion):
             # Transferencias con Revolut (banco digital) - son internas
             return {
                 'cat1': 'Interna',
                 'cat2': '',
                 'tipo': 'TRANSFERENCIA',
                 'capa': 0,
                 'merchant_name': merchant_name
             }
        
        # REGLA #13: Recibos de comunidad/garaje (C.P. EDIFICIO) → VIVIENDA/Comunidad
        if 'C.P. EDIFICIO' in desc_upper and 'RECIBO' in desc_upper:
            return {
                'cat1': 'Vivienda',
                'cat2': 'Comunidad',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }
        
        # REGLA #14: Recibos de seguros de vida (AXA AURORA) → SEGUROS/Seguros Vida
        if 'AXA AURORA VIDA' in desc_upper and 'RECIBO' in desc_upper:
            return {
                'cat1': 'Seguros',
                'cat2': 'Seguros Vida',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }
        
        # REGLA #15: Recibos de tarjetas de crédito (BANCOPOPULAR) → FINANZAS/Tarjeta Crédito
        if 'BANCOPOPULAR' in desc_upper and 'RECIBO' in desc_upper and 'TARJETA' in desc_upper:
            return {
                'cat1': 'Finanzas',
                'cat2': 'Tarjeta Crédito',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }
        
        # REGLA #16: Donaciones (Fundación Polaris, Golf, Rugby, etc.) → GASTO/Ocio y Cultura/Donaciones
        if any(keyword in desc_upper for keyword in ['POLARIS WORLD', 'REAL FED ESPAÑOLA DE GOLF', 
                                                       'CLUB DE RUGBY', 'EUROPOLIS']):
            if 'DONACION' in desc_upper or 'PAGO RECIBO DE' in desc_upper:
                return {
                    'cat1': 'Ocio y Cultura',
                    'cat2': 'Donaciones',
                    'tipo': 'GASTO',
                    'capa': 0,
                    'merchant_name': merchant_name
                }
        
        # REGLA #17: Retrocesión de gastos duplicados (Capgemini) → INGRESO/Otros/Retrocesión
        if 'CAPGEMINI' in desc_upper and 'RETROCESION' in desc_upper:
            return {
                'cat1': 'Retrocesión',
                'cat2': 'Retrocesión',
                'tipo': 'INGRESO',
                'capa': 0,
                'merchant_name': merchant_name
            }
        
        # REGLA #18: Recibos de seguros genéricos antiguos → SEGUROS/Seguros Generales
        if descripcion.strip() == 'RECIBO SEGURO':
            # Recibos muy antiguos (2004-2007) sin más información que "RECIBO SEGURO"
            return {
                'cat1': 'Seguros',
                'cat2': 'Seguros Generales',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }
        
        # REGLA #19: Restaurantes y bares específicos → RESTAURACION/Cat2
        restaurantes_keywords = {
            'REST CASA AUGUSTO': ('Restaurante', 'Restauración'),
            'BODEGAS BAIGORRI': ('Bodega', 'Restauración'),
            'BAR EL PERCHAS': ('Bar', 'Restauración'),
            'DELANTE BAR': ('Bar', 'Restauración'),
            'EL PURGATORIO BAR': ('Bar', 'Restauración'),
            'HENRYÛS DELIZIE': ('Restaurante', 'Restauración'),
            'RESATAURANTE BELLAVISTA': ('Restaurante', 'Restauración'),
            'ARTISAR': ('Restaurante', 'Restauración'),
            'TITIRIT': ('Restaurante', 'Restauración'),
            'SIETE RIOS SL': ('Restaurante', 'Restauración'),
            'LA MARINA I': ('Restaurante', 'Restauración'),
        }
        for keyword, (cat2, cat1_value) in restaurantes_keywords.items():
            if keyword in desc_upper:
                return {
                    'cat1': cat1_value,
                    'cat2': cat2,
                    'tipo': 'GASTO',
                    'capa': 0,
                    'merchant_name': merchant_name
                }

        # REGLA #20: Alcampo y Aldi específicos → ALIMENTACION/Alcampo o Aldi
        if 'ALCAMPO' in desc_upper:
            return {
                'cat1': 'Alimentación',
                'cat2': 'Alcampo',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }
        if 'ALDI' in desc_upper:
            return {
                'cat1': 'Alimentación',
                'cat2': 'Aldi',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #21: Museos y conciertos → OCIO/Museos o OCIO/Conciertos
        if 'TIENDA MUSEO' in desc_upper or 'MUSEO' in desc_upper:
            return {
                'cat1': 'Ocio y Cultura',
                'cat2': 'Museos',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }
        if 'GIRA' in desc_upper or 'CONCIERTO' in desc_upper:
            return {
                'cat1': 'Ocio y Cultura',
                'cat2': 'Conciertos',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #22: Tiendas de ropa específicas → ROPA Y CALZADO/Ropa y Accesorios
        tiendas_ropa = ['CORTEFIEL', 'ZARA', 'H&M', 'MANGO', 'PRIMARK']
        if any(tienda in desc_upper for tienda in tiendas_ropa):
            return {
                'cat1': 'Ropa y Calzado',
                'cat2': 'Ropa y Accesorios',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #23: Obras y reformas de vivienda → VIVIENDA/Reformas
        # Patrón: "Talón" o "Cheque" + empresa de construcción/obras
        if any(keyword in desc_upper for keyword in ['TALON', 'TALÓN', 'CHEQUE']) and any(x in desc_upper for x in ['SOLUCIONE', 'OBRAS', 'REFORMA', 'CONSTRUCCION']):
            return {
                'cat1': 'Vivienda',
                'cat2': 'Reformas',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #24: Capgemini Salary → INGRESO/Nómina (salario por formato transferencia)
        # Transferencias de Capgemini Spain SL con concepto SALARY son nóminas por transferencia
        if 'CAPGEMINI' in desc_upper and 'SALARY' in desc_upper and importe_float > 0:
            return {
                'cat1': 'Nómina',
                'cat2': '',
                'tipo': 'INGRESO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #25: Torreblanca del Mediterráneo Sol → INGRESO/Nómina (salario empresa)
        # Transferencias mensuales de nómina de Torreblanca del Mediterráneo Sol
        if 'TORREBLANCA' in desc_upper and 'MEDITERRANEO' in desc_upper and importe_float > 0:
            return {
                'cat1': 'Nómina',
                'cat2': '',
                'tipo': 'INGRESO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #26: Streye Smart Devices → INGRESO/Nómina (nómina de consultoría)
        # Transferencias de nómina por trabajo de consultoría con Streye Smart Devices
        if 'STREYE' in desc_upper and importe_float > 0:
            return {
                'cat1': 'Nómina',
                'cat2': '',
                'tipo': 'INGRESO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #27: Intereses cobrados → INGRESO/Intereses (cat2 vacío)
        # Keywords: INTERESES CTA., Interest payment, Your interest payment (Trade Republic, Abanca)
        if 'INTERESES' in desc_upper or 'INTEREST PAYMENT' in desc_upper or 'YOUR INTEREST PAYMENT' in desc_upper:
            if importe_float > 0:  # Intereses cobrados son siempre positivos
                return {
                    'cat1': 'Intereses',
                    'cat2': '',
                    'tipo': 'INGRESO',
                    'capa': 0,
                    'merchant_name': merchant_name
                }

        # REGLA #28: Patrón histórico "RETR. COMPRA RENTA VARIABLE" (2004) → RENTA VARIABLE
        # Caso único: transacción de 2004 con descripción única
        if 'RETR. COMPRA RENTA VARIABLE' in desc_upper:
            return {
                'cat1': 'Renta Variable',
                'cat2': 'Compra',
                'tipo': 'INVERSION',
                'capa': 0,
                'merchant_name': merchant_name
            }


        # REGLA #29: Namecheap (NAME-CHEAP/NAMECHEAP) → Suscripciones/Dominios
        # Prioridad: antes del token EXCHANGE para evitar confundir con divisas
        if 'NAME-CHEAP' in desc_upper or 'NAMECHEAP' in desc_upper:
            return {
                'cat1': 'Suscripciones',
                'cat2': 'Dominios',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # REGLA #30: GitHub desde Trade Republic → Suscripciones
        # Prioridad: antes del token EXCHANGE para evitar confundir con divisas
        if 'GITHUB' in desc_upper and banco == 'Trade Republic':
            return {
                'cat1': 'Suscripciones',
                'cat2': 'Otros',
                'tipo': 'GASTO',
                'capa': 0,
                'merchant_name': merchant_name
            }

        # === CAPA 1: Exact Match ===
        # IMPORTANTE: Skip Exact Match para Bizums - deben detectarse en Capa 3
        # para garantizar que SIEMPRE se clasifiquen como Bizum, no como Interna
        if 'BIZUM' not in desc_upper:
            result = lookup_exact(descripcion, self.exact_match_dict)
            if result:
                cat1, cat2 = validate_combination(*result)
                cat2_refined = refine_cat2_by_description(cat1, cat2, descripcion)
                tipo = determine_tipo(cat1, importe, descripcion)
                return {
                    'cat1': cat1,
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 1,
                    'merchant_name': merchant_name
                }

        # === CAPA 2: Merchant Lookup ===
        # IMPORTANTE: Skip Merchant Lookup para Bizums - deben detectarse en Capa 3
        if 'BIZUM' not in desc_upper:
            result = lookup_merchant(descripcion, merchant_name)
            if result:
                cat1, cat2 = validate_combination(*result)
                cat2_refined = refine_cat2_by_description(cat1, cat2, descripcion)
                tipo = determine_tipo(cat1, importe, descripcion)
                return {
                    'cat1': cat1,
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': 2,
                    'merchant_name': merchant_name
                }

        # === CAPA 2.5: Merchant Database Lookup (Google Places) ===
        # Consulta la tabla 'merchants' usando google_type para mapear a (cat1, cat2) válidos.
        # Solo aplica si merchant_name está extraído y tenemos entrada en BD.
        # Prioridad: Solo si resultado de capas previas no fue conclusivo.
        if merchant_name and 'BIZUM' not in desc_upper:
            result = lookup_merchant_from_db(merchant_name)
            if result:
                cat1, cat2 = validate_combination(*result)
                cat2_refined = refine_cat2_by_description(cat1, cat2, descripcion)
                tipo = determine_tipo(cat1, importe, descripcion)
                return {
                    'cat1': cat1,
                    'cat2': cat2_refined,
                    'tipo': tipo,
                    'capa': '2.5'
                }

        # === CAPA 3: Transfer Detection ===
        result = detect_transfer(descripcion, banco, importe)
        if result:
            cat1, cat2 = validate_combination(*result)
            cat2_refined = refine_cat2_by_description(cat1, cat2, descripcion)
            tipo = determine_tipo(cat1, importe, descripcion)
            return {
                'cat1': cat1,
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 3,
                'merchant_name': merchant_name
            }

        # === CAPA 4: Token Heurístico ===
        # Primero: reglas específicas por banco
        from classifier.tokens import match_bank_specific
        result = match_bank_specific(descripcion, banco, importe)
        if result:
            cat1, cat2 = validate_combination(*result)
            cat2_refined = refine_cat2_by_description(cat1, cat2, descripcion)
            tipo = determine_tipo(cat1, importe, descripcion)
            return {
                'cat1': cat1,
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 4,
                'merchant_name': merchant_name
            }

        # Segundo: tokens heurísticos generales
        result = match_token(descripcion)
        if result:
            cat1, cat2 = validate_combination(*result)
            cat2_refined = refine_cat2_by_description(cat1, cat2, descripcion)
            tipo = determine_tipo(cat1, importe, descripcion)
            return {
                'cat1': cat1,
                'cat2': cat2_refined,
                'tipo': tipo,
                'capa': 4,
                'merchant_name': merchant_name
            }

        # === CAPA 5: SIN_CLASIFICAR ===
        return {
            'cat1': 'SIN_CLASIFICAR',
            'cat2': '',
            'tipo': '',
            'capa': 5,
            'merchant_name': merchant_name
        }
