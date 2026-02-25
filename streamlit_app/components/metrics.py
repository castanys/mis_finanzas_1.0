"""
Funciones para cálculo de métricas y KPIs
"""
from typing import Dict, Tuple
from datetime import datetime, date

def format_currency(amount: float) -> str:
    """Formatea cantidad como moneda EUR"""
    return f"€{abs(amount):,.0f}" if amount != 0 else "€0"

def format_percentage(pct: float) -> str:
    """Formatea porcentaje con signo"""
    if pct > 0:
        return f"+{pct:.1f}%"
    elif pct < 0:
        return f"{pct:.1f}%"
    else:
        return "0%"

def get_current_month_year() -> Tuple[int, int]:
    """Devuelve año y mes actual"""
    today = date.today()
    return today.year, today.month

def format_date_range(year: int, month: int = None) -> str:
    """Formatea rango de fechas de forma legible"""
    if month is None:
        return str(year)
    
    meses = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    return f"{meses[month-1]} {year}"

def calculate_variation_pct(current: float, previous: float) -> float:
    """Calcula variación porcentual entre dos valores"""
    if previous == 0:
        return 0 if current == 0 else 100
    return ((current - previous) / abs(previous)) * 100

def get_trend_indicator(variation_pct: float) -> str:
    """Devuelve emoji indicador de tendencia"""
    if variation_pct > 10:
        return "📈"  # Sube mucho
    elif variation_pct > 0:
        return "↗️"  # Sube poco
    elif variation_pct < -10:
        return "📉"  # Baja mucho
    elif variation_pct < 0:
        return "↘️"  # Baja poco
    else:
        return "→"   # Estable

def get_status_emoji(value: float, threshold_positive: bool = True) -> str:
    """Devuelve emoji de estado según valor"""
    if threshold_positive:
        # Para métricas donde positivo es bueno (ahorro, tasa ahorro)
        if value > 0:
            return "✅"
        elif value < 0:
            return "⚠️"
        else:
            return "➖"
    else:
        # Para métricas donde negativo es bueno (gastos)
        if value < 0:
            return "✅"
        elif value > 0:
            return "⚠️"
        else:
            return "➖"

def days_remaining_in_month() -> int:
    """Devuelve días restantes en el mes actual"""
    today = date.today()
    if today.month == 12:
        next_month = datetime(today.year + 1, 1, 1)
    else:
        next_month = datetime(today.year, today.month + 1, 1)
    
    remaining = (next_month - datetime(today.year, today.month, today.day)).days
    return max(remaining, 0)

def project_end_of_month(daily_average: float) -> float:
    """Proyecta gasto/ingreso al final del mes"""
    remaining = days_remaining_in_month()
    if remaining <= 0:
        return daily_average
    
    today = date.today().day
    total_days = today + remaining
    return (daily_average * today) + (daily_average * remaining)
