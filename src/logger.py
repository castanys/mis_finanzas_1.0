"""
Logger centralizado para finsense.
Proporciona logging simultáneo en consola y fichero.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


class FinsenseLogger:
    """Logger centralizado con outputs a consola y fichero."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializar logger singleton."""
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = logging.getLogger('finsense')
        self.logger.setLevel(logging.DEBUG)
        
        # Crear directorio logs/ si no existe
        logs_dir = Path(__file__).parent.parent / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        # Timestamp para nombre de archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = logs_dir / f'finsense_{timestamp}.log'
        
        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Handler para fichero
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Agregar handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        self.log_file = log_file
        self.stats = {
            'csvs_encontrados': 0,
            'csvs_procesados': 0,
            'csvs_ignorados': 0,
            'transacciones_leidas': 0,
            'duplicados_mismo_archivo': 0,
            'duplicados_en_bd': 0,
            'nuevas_insertadas': 0,
            'merchants_detectados': 0,
            'transferencias_sin_pareja': [],
            'total_bd': 0,
            'file_stats': {},  # {filename: {total, nuevos, duplicados}}
        }
        
        self.logger.info('=' * 70)
        self.logger.info('INICIANDO FINSENSE')
        self.logger.info('=' * 70)
    
    def get(self):
        """Obtener el logger."""
        return self.logger
    
    def info(self, msg: str):
        """Log INFO."""
        self.logger.info(msg)
    
    def debug(self, msg: str):
        """Log DEBUG."""
        self.logger.debug(msg)
    
    def warning(self, msg: str):
        """Log WARNING."""
        self.logger.warning(msg)
    
    def error(self, msg: str):
        """Log ERROR."""
        self.logger.error(msg)
    
    def critical(self, msg: str):
        """Log CRITICAL."""
        self.logger.critical(msg)
    
    def add_stat(self, key: str, value):
        """Añadir/actualizar estadística."""
        if key in self.stats:
            if isinstance(self.stats[key], int):
                self.stats[key] += value if isinstance(value, int) else 0
            elif isinstance(self.stats[key], list):
                if isinstance(value, list):
                    self.stats[key].extend(value)
                else:
                    self.stats[key].append(value)
            else:
                self.stats[key] = value
    
    def set_stat(self, key: str, value):
        """Establecer estadística directamente."""
        self.stats[key] = value
    
    def print_summary(self):
        """Imprimir resumen de ejecución."""
        self.logger.info('')
        self.logger.info('=' * 80)
        self.logger.info('RESUMEN DE EJECUCIÓN')
        self.logger.info('=' * 80)
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.logger.info(f'Timestamp: {timestamp}')
        self.logger.info(f'Log guardado en: {self.log_file}')
        self.logger.info('')
        
        # Mostrar informe de importación por fichero
        file_stats = self.stats.get('file_stats', {})
        if file_stats:
            self.logger.info('--- INFORME DE IMPORTACIÓN POR FICHERO ---')
            self.logger.info('')
            self.print_file_import_report(file_stats)
            self.logger.info('')
        
        self.logger.info('--- Estadísticas de Procesamiento ---')
        self.logger.info(f"  Ficheros encontrados:           {self.stats['csvs_encontrados']}")
        self.logger.info(f"  Ficheros procesados:            {self.stats['csvs_procesados']}")
        self.logger.info(f"  Ficheros ignorados:             {self.stats['csvs_ignorados']}")
        self.logger.info(f"  Transacciones leídas:           {self.stats['transacciones_leidas']}")
        self.logger.info(f"  Duplicados (mismo archivo):     {self.stats['duplicados_mismo_archivo']}")
        self.logger.info(f"  Duplicados (ya en BD):          {self.stats['duplicados_en_bd']}")
        self.logger.info(f"  Nuevas transacciones insertadas:{self.stats['nuevas_insertadas']}")
        self.logger.info(f"  Merchants únicos detectados:    {self.stats['merchants_detectados']}")
        self.logger.info(f"  Total en BD después:            {self.stats['total_bd']}")
        self.logger.info('')
        
        # Mostrar resumen de clasificación por capas
        capas = self.stats.get('capas_clasificacion', {})
        if capas:
            self.logger.info('--- Clasificación por Capa (global) ---')
            total_clasificadas = sum(capas.values())
            
            nombres_capa = {
                0: "Reglas prioritarias",
                1: "Exact match",
                2: "Merchants",
                3: "Transferencias",
                4: "Tokens",
                5: "Sin clasificar"
            }
            
            for capa in sorted(capas.keys()):
                count = capas[capa]
                pct = 100 * count / total_clasificadas if total_clasificadas > 0 else 0
                nombre = nombres_capa.get(capa, f"Capa {capa}")
                
                if capa == 5 and count == 0:
                    self.logger.info(f"  Capa {capa} ({nombre:25s}): {count:6d} tx ({pct:5.1f}%) ✓")
                else:
                    self.logger.info(f"  Capa {capa} ({nombre:25s}): {count:6d} tx ({pct:5.1f}%)")
            
            self.logger.info('')
        
        if self.stats['transferencias_sin_pareja']:
            self.logger.warning('')
            self.logger.warning('--- ⚠ ADVERTENCIAS: Transferencias Internas sin Pareja ---')
            for tx in self.stats['transferencias_sin_pareja']:
                self.logger.warning(
                    f"  ID: {tx['id']} | Fecha: {tx['fecha']} | "
                    f"Importe: {tx['importe']:>10.2f} | {tx['descripcion']}"
                )
            self.logger.warning(f"  Total sin pareja: {len(self.stats['transferencias_sin_pareja'])}")
            self.logger.warning('')
        
        self.logger.info('=' * 80)
        self.logger.info('FIN DE EJECUCIÓN')
        self.logger.info('=' * 80)
    
    def print_file_import_report(self, file_stats: dict):
        """
        Imprimir reporte tabular de importación por fichero con origen de duplicados.
        
        Args:
            file_stats: Dict {filename: {total_original, nuevos, duplicados, dup_origen_por_fichero}}
        """
        if not file_stats:
            return
        
        # Ancho de columnas
        w_name = 38
        w_num = 7
        w_origen = 30
        
        # Encabezado
        self.logger.info(f"{'Fichero':{w_name}} │ {'Total':>{w_num}} │ {'Nuevos':>{w_num}} │ {'Duplic':>{w_num}} │ {'Origen duplicado':{w_origen}}")
        self.logger.info('─' * (w_name + w_num * 3 + w_origen + 15))
        
        total_total = 0
        total_nuevos = 0
        total_dupes = 0
        
        # Filas
        for filename in sorted(file_stats.keys()):
            stats = file_stats[filename]
            total = stats.get('total_original', 0)
            nuevos = stats.get('nuevos', 0)
            dupes = stats.get('duplicados', 0)
            
            total_total += total
            total_nuevos += nuevos
            total_dupes += dupes
            
            # Abreviar nombre si es muy largo
            display_name = filename if len(filename) <= w_name else filename[:w_name-3] + '..'
            
            # Origen de duplicados
            dup_origen = stats.get('dup_origen_por_fichero', {})
            if dup_origen:
                origen_str = ', '.join([f"{v}x {k[:20]}..." if len(k) > 20 else f"{v}x {k}" 
                                       for k, v in sorted(dup_origen.items())])
            else:
                origen_str = '—'
            
            self.logger.info(f"{display_name:{w_name}} │ {total:>{w_num}} │ {nuevos:>{w_num}} │ {dupes:>{w_num}} │ {origen_str:{w_origen}}")
        
        # Separador y totales
        self.logger.info('─' * (w_name + w_num * 3 + w_origen + 15))
        self.logger.info(f"{'TOTAL':{w_name}} │ {total_total:>{w_num}} │ {total_nuevos:>{w_num}} │ {total_dupes:>{w_num}} │ {' ':>{w_origen}}")
        self.logger.info('')


def get_logger() -> FinsenseLogger:
    """Obtener instancia del logger."""
    return FinsenseLogger()
