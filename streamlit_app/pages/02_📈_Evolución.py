"""
Página 2: Evolución Temporal
Tendencias mes a mes, estacionalidad, comparativas
"""
import streamlit as st
import sys
import os
from datetime import datetime, timedelta
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import DB_PATH, COLOR_INGRESO, COLOR_GASTO, COLOR_AHORRO
from components.metrics import format_currency, get_current_month_year, format_date_range
from components.charts import line_chart_evolucion_mensual

st.set_page_config(
    page_title="Evolución",
    page_icon="📈",
    layout="wide"
)

st.markdown("# 📈 Evolución Temporal")
st.markdown("---")

# Sidebar
st.sidebar.markdown("## 🔍 Filtros")

months_back = st.sidebar.slider(
    "Últimos N meses",
    min_value=3,
    max_value=48,
    value=12,
    step=3,
    help="Cuántos meses atrás mostrar en los gráficos"
)

metric_type = st.sidebar.multiselect(
    "Métricas a mostrar",
    ["ingresos", "gastos", "ahorro"],
    default=["gastos", "ahorro"]
)

# ===== Función para obtener datos mensuales =====
@st.cache_data(ttl=3600)
def get_monthly_evolution(months: int) -> list:
    """Obtiene evolución mensual de últimos N meses"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Obtener últimos N meses
        cursor.execute(f"""
            SELECT DISTINCT strftime('%Y-%m', fecha) as periodo
            FROM transacciones
            ORDER BY periodo DESC
            LIMIT ?
        """, (months,))
        
        periodos = sorted([row[0] for row in cursor.fetchall()])
        
        monthly_data = []
        for periodo in periodos:
            # Ingresos
            cursor.execute("""
                SELECT SUM(importe) FROM transacciones
                WHERE tipo = 'INGRESO' AND importe > 0 AND cat1 != 'Bizum'
                AND strftime('%Y-%m', fecha) = ?
            """, (periodo,))
            ingreso = cursor.fetchone()[0] or 0.0
            
            # Gastos
            cursor.execute("""
                SELECT SUM(importe) FROM transacciones
                WHERE tipo = 'GASTO' AND cat1 != 'Bizum'
                AND strftime('%Y-%m', fecha) = ?
            """, (periodo,))
            gasto = cursor.fetchone()[0] or 0.0
            
            # Ahorro
            ahorro = ingreso + gasto
            
            monthly_data.append({
                'periodo': periodo,
                'ingreso_total': ingreso,
                'gasto_total': gasto,
                'ahorro': ahorro
            })
        
        conn.close()
        return monthly_data
    
    except Exception as e:
        st.error(f"Error: {e}")
        return []

# ===== Cargar datos =====
data = get_monthly_evolution(months_back)

if not data:
    st.error("No se pudieron cargar los datos")
    st.stop()

st.markdown(f"## Últimos {len(data)} meses")

# ===== Gráfico principal =====
fig_evolution = line_chart_evolucion_mensual(data, metrics=metric_type)
st.plotly_chart(fig_evolution, use_container_width=True)

st.markdown("---")

# ===== Estadísticas =====
st.markdown("## 📊 Estadísticas")

col1, col2, col3, col4 = st.columns(4)

# Calcular promedios
ingresos_avg = sum(d['ingreso_total'] for d in data) / len(data) if data else 0
gastos_avg = abs(sum(d['gasto_total'] for d in data)) / len(data) if data else 0
ahorro_avg = sum(d['ahorro'] for d in data) / len(data) if data else 0

with col1:
    st.metric("📥 Ingreso Promedio", format_currency(ingresos_avg))

with col2:
    st.metric("📤 Gasto Promedio", format_currency(gastos_avg))

with col3:
    st.metric("💾 Ahorro Promedio", format_currency(ahorro_avg))

with col4:
    # Tasa de ahorro promedio
    tasa_avg = (ahorro_avg / ingresos_avg * 100) if ingresos_avg > 0 else 0
    st.metric("🎯 Tasa Ahorro Promedio", f"{tasa_avg:.1f}%")

st.markdown("---")

# ===== Tabla de datos =====
st.markdown("## 📋 Datos Mensuales")

import pandas as pd

table_data = []
for d in data:
    table_data.append({
        'Mes': d['periodo'],
        'Ingresos': format_currency(d['ingreso_total']),
        'Gastos': format_currency(abs(d['gasto_total'])),
        'Ahorro': format_currency(d['ahorro']),
        'Tasa': f"{(d['ahorro'] / d['ingreso_total'] * 100) if d['ingreso_total'] > 0 else 0:.1f}%"
    })

df = pd.DataFrame(table_data)
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# ===== Análisis de tendencia =====
st.markdown("## 🔮 Tendencia")

if len(data) >= 6:
    # Primeros 3 vs últimos 3
    primeros_3 = sum(d['ahorro'] for d in data[:3]) / 3
    ultimos_3 = sum(d['ahorro'] for d in data[-3:]) / 3
    
    cambio = ultimos_3 - primeros_3
    pct_cambio = (cambio / abs(primeros_3) * 100) if primeros_3 != 0 else 0
    
    if cambio > 0:
        emoji = "📈"
        direccion = "mejorando"
    elif cambio < 0:
        emoji = "📉"
        direccion = "empeorando"
    else:
        emoji = "→"
        direccion = "estable"
    
    st.markdown(f"""
    ### {emoji} Tendencia: {direccion}
    
    Tu ahorro promedio está **{direccion}**.
    
    - Primeros 3 meses: {format_currency(primeros_3)}
    - Últimos 3 meses: {format_currency(ultimos_3)}
    - Cambio: {format_currency(cambio)} ({pct_cambio:+.1f}%)
    """)
else:
    st.info("Se necesitan al menos 6 meses de datos para calcular tendencia")

st.markdown("---")
st.markdown("*Dashboard Finsense | Datos: finsense.db*")
