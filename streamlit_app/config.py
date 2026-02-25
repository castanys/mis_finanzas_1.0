"""
Configuración para Finsense Analytics Dashboard
"""
import os

# Database
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'finsense.db')

# App
APP_TITLE = 'Finsense Analytics'
APP_ICON = '💰'
THEME = 'dark'
LAYOUT = 'wide'

# Colores (tema)
COLOR_INGRESO = '#10B981'  # Verde
COLOR_GASTO = '#EF4444'    # Rojo
COLOR_AHORRO = '#3B82F6'   # Azul
COLOR_NEUTRAL = '#6B7280'  # Gris

# Categorías (Cat1)
CATEGORIAS = [
    'Alimentación', 'Compras', 'Deportes', 'Efectivo', 'Finanzas',
    'Impuestos', 'Ocio y Cultura', 'Recibos', 'Restauración',
    'Ropa y Calzado', 'Salud y Belleza', 'Seguros', 'Servicios Consultoría',
    'Suscripciones', 'Transporte', 'Viajes', 'Vivienda', 'Wallapop',
    'Ingreso', 'Nómina', 'Liquidación', 'Transferencia', 'Inversión'
]

# Parámetros por defecto
DEFAULT_MONTHS_HISTORICO = 12
DEFAULT_FIRE_OBJETIVO = 400000.0
DEFAULT_FIRE_RENTABILIDAD = 0.07
DEFAULT_FIRE_GASTOS_ANUALES = 24000.0
