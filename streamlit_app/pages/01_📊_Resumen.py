"""
Página 1: Resumen Mensual/Anual
MVP: Vista general con KPIs principales
"""
import streamlit as st
import sys
import os
from datetime import datetime, date
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import DB_PATH, COLOR_INGRESO, COLOR_GASTO, COLOR_AHORRO
from components.metrics import (
    format_currency, format_percentage, get_current_month_year,
    format_date_range, get_trend_indicator, days_remaining_in_month
)
from components.charts import (
    pie_chart_gastos_por_categoria,
    bar_chart_top_gastos,
    line_chart_evolucion_mensual
)

# Configurar página
st.set_page_config(
    page_title="Resumen",
    page_icon="📊",
    layout="wide"
)

st.markdown("# 📊 Resumen")
st.markdown("---")

# ===== SIDEBAR: Selector de período =====
st.sidebar.markdown("## 📅 Filtros")

view_type = st.sidebar.radio(
    "Tipo de vista",
    ["Mes actual", "Mes específico", "Año completo"],
    index=0
)

year_current, month_current = get_current_month_year()

if view_type == "Mes actual":
    year = year_current
    month = month_current
    period_label = f"Mes actual ({format_date_range(year, month)})"
elif view_type == "Mes específico":
    year = st.sidebar.number_input("Año", min_value=2004, max_value=2099, value=year_current)
    month = st.sidebar.slider("Mes", 1, 12, month_current)
    period_label = format_date_range(year, month)
else:  # Año completo
    year = st.sidebar.number_input("Año", min_value=2004, max_value=2099, value=year_current)
    month = None
    period_label = str(year)

st.sidebar.markdown(f"**Período**: {period_label}")

# ===== FUNCIÓN: Obtener datos del mes =====
@st.cache_data(ttl=3600)
def get_resumen_mensual(year: int, month: int = None) -> dict:
    """Obtiene resumen del período seleccionado"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Filtro de fecha
        if month:
            periodo = f"{year}-{month:02d}"
            date_filter = f"AND strftime('%Y-%m', fecha) = '{periodo}'"
        else:
            periodo = str(year)
            date_filter = f"AND strftime('%Y', fecha) = '{year}'"
        
        # Total ingresos
        cursor.execute(f"""
            SELECT SUM(importe) as total FROM transacciones
            WHERE tipo = 'INGRESO' AND importe > 0 AND cat1 != 'Bizum'
            {date_filter}
        """)
        ingreso_total = cursor.fetchone()[0] or 0.0
        
        # Total gastos
        cursor.execute(f"""
            SELECT SUM(importe) as total FROM transacciones
            WHERE tipo = 'GASTO' AND cat1 != 'Bizum'
            {date_filter}
        """)
        gasto_total = cursor.fetchone()[0] or 0.0
        
        # Ahorro
        ahorro = ingreso_total + gasto_total
        tasa_ahorro_pct = (ahorro / ingreso_total * 100) if ingreso_total > 0 else 0
        
        # Gasto por categoría
        cursor.execute(f"""
            SELECT cat1, SUM(importe) as total, COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO' AND cat1 != 'Bizum'
            {date_filter}
            GROUP BY cat1
            ORDER BY total ASC
        """)
        
        categorias = []
        total_gasto_abs = abs(gasto_total)
        
        for row in cursor.fetchall():
            cat1, total, num_tx = row
            pct = (abs(total) / total_gasto_abs * 100) if total_gasto_abs > 0 else 0
            categorias.append({
                'cat1': cat1,
                'total': total,
                'num_tx': num_tx,
                'pct': pct
            })
        
        # Top 10 gastos
        cursor.execute(f"""
            SELECT
                CASE WHEN cat2 != '' THEN cat2 ELSE SUBSTR(descripcion, 1, 40) END as merchant,
                cat1,
                SUM(importe) as total,
                COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO' AND cat1 != 'Bizum'
            {date_filter}
            GROUP BY merchant, cat1
            ORDER BY total ASC
            LIMIT 10
        """)
        
        top_gastos = []
        for row in cursor.fetchall():
            merchant, cat1, total, num_tx = row
            top_gastos.append({
                'merchant': merchant or '(sin merchant)',
                'cat1': cat1,
                'total': total,
                'num_tx': num_tx
            })
        
        conn.close()
        
        return {
            'ingreso_total': ingreso_total,
            'gasto_total': gasto_total,
            'ahorro': ahorro,
            'tasa_ahorro_pct': tasa_ahorro_pct,
            'categorias': categorias,
            'top_gastos': top_gastos,
            'periodo': periodo if month else str(year)
        }
    
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return {}

# ===== CARGAR DATOS =====
data = get_resumen_mensual(year, month)

if not data:
    st.error("❌ No se pudieron cargar los datos")
    st.stop()

# ===== KPIs PRINCIPALES =====
st.markdown("## 💰 KPIs Principales")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "📥 Ingresos",
        format_currency(data['ingreso_total']),
        delta=None
    )

with col2:
    st.metric(
        "📤 Gastos",
        format_currency(abs(data['gasto_total'])),
        delta=None
    )

with col3:
    st.metric(
        "💾 Ahorro",
        format_currency(data['ahorro']),
        delta=format_percentage(data['tasa_ahorro_pct'])
    )

with col4:
    days_left = days_remaining_in_month() if month and year == year_current and month == month_current else 0
    st.metric(
        "📅 Días restantes",
        f"{days_left} días" if days_left > 0 else "Mes terminado",
        delta=None
    )

st.markdown("---")

# ===== GRÁFICOS =====
st.markdown("## 📊 Análisis")

# Fila 1: Pie chart + Top gastos
col1, col2 = st.columns([1, 1])

with col1:
    fig_pie = pie_chart_gastos_por_categoria(data['categorias'])
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    fig_bar = bar_chart_top_gastos(data['top_gastos'], limit=10)
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# ===== TABLA DE CATEGORÍAS =====
st.markdown("## 📋 Desglose por Categoría")

# Preparar datos para tabla
table_data = []
for cat in data['categorias']:
    if cat['total'] < 0:  # Solo gastos
        table_data.append({
            'Categoría': cat['cat1'],
            'Gasto': format_currency(abs(cat['total'])),
            'Transacciones': cat['num_tx'],
            'Porcentaje': f"{cat['pct']:.1f}%"
        })

if table_data:
    # Mostrar tabla
    import pandas as pd
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Sin datos de gastos para este período")

st.markdown("---")

# ===== DETALLES ADICIONALES =====
st.markdown("## ℹ️ Información Adicional")

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    **Período**: {data['periodo']}
    
    **Total Transacciones**: {sum(c['num_tx'] for c in data['categorias'])}
    
    **Categorías con gasto**: {len([c for c in data['categorias'] if c['total'] < 0])}
    """)

with col2:
    if data['ingreso_total'] > 0:
        ratio = abs(data['gasto_total']) / data['ingreso_total'] * 100
        st.markdown(f"""
        **Gasto vs Ingreso**: {ratio:.1f}%
        
        **Tasa de Ahorro**: {data['tasa_ahorro_pct']:.1f}%
        
        **Ahorro por día**: {format_currency(data['ahorro'] / max(28, days_remaining_in_month() or 28))}
        """)
    else:
        st.warning("Sin ingresos este período")

# ===== FOOTER =====
st.markdown("---")
st.markdown("""
*Dashboard construido con Streamlit | Datos: SQLite finsense.db*
""")
