"""
Página 3: Drill-Down por Categoría
Análisis detallado de una categoría específica
"""
import streamlit as st
import sys
import os
import sqlite3
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import DB_PATH, CATEGORIAS, COLOR_GASTO
from components.metrics import format_currency, get_current_month_year

st.set_page_config(
    page_title="Categorías",
    page_icon="🔍",
    layout="wide"
)

st.markdown("# 🔍 Análisis por Categoría")
st.markdown("---")

# Sidebar
st.sidebar.markdown("## 🎯 Selecciona una categoría")

# Filtrar solo Cat1 que existen en GASTO
cat1_opciones = [c for c in CATEGORIAS if c not in ['Ingreso', 'Nómina', 'Liquidación', 'Transferencia', 'Inversión']]

cat1_selected = st.sidebar.selectbox(
    "Categoría",
    cat1_opciones,
    index=0
)

year_current, month_current = get_current_month_year()

view_type = st.sidebar.radio("Período", ["Mes actual", "Mes específico", "Año completo"])

if view_type == "Mes actual":
    year = year_current
    month = month_current
elif view_type == "Mes específico":
    year = st.sidebar.number_input("Año", min_value=2004, max_value=2099, value=year_current)
    month = st.sidebar.slider("Mes", 1, 12, month_current)
else:
    year = st.sidebar.number_input("Año", min_value=2004, max_value=2099, value=year_current)
    month = None

# ===== Función para obtener desglose de categoría =====
@st.cache_data(ttl=3600)
def get_categoria_desglose(cat1: str, year: int, month: int = None) -> dict:
    """Obtiene desglose de una categoría"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if month:
            periodo = f"{year}-{month:02d}"
            date_filter = f"AND strftime('%Y-%m', fecha) = '{periodo}'"
        else:
            date_filter = f"AND strftime('%Y', fecha) = '{year}'"
        
        # Total categoría
        cursor.execute(f"""
            SELECT SUM(importe) as total
            FROM transacciones
            WHERE cat1 = ? AND tipo = 'GASTO'
            {date_filter}
        """, (cat1,))
        total_cat = cursor.fetchone()[0] or 0.0
        
        # Desglose por Cat2
        cursor.execute(f"""
            SELECT cat2, SUM(importe) as total, COUNT(*) as num_tx
            FROM transacciones
            WHERE cat1 = ? AND tipo = 'GASTO'
            {date_filter}
            GROUP BY cat2
            ORDER BY total ASC
        """, (cat1,))
        
        subcategorias = []
        for row in cursor.fetchall():
            cat2 = row[0] or '(sin especificar)'
            total = row[1]
            num_tx = row[2]
            pct = (abs(total) / abs(total_cat) * 100) if total_cat != 0 else 0
            
            subcategorias.append({
                'cat2': cat2,
                'total': total,
                'num_tx': num_tx,
                'pct': pct
            })
        
        # Transacciones individuales (últimas 50)
        cursor.execute(f"""
            SELECT fecha, importe, descripcion, cat2
            FROM transacciones
            WHERE cat1 = ? AND tipo = 'GASTO'
            {date_filter}
            ORDER BY fecha DESC
            LIMIT 50
        """, (cat1,))
        
        transacciones = []
        for row in cursor.fetchall():
            transacciones.append({
                'Fecha': row[0],
                'Importe': format_currency(abs(row[1])),
                'Descripción': row[2][:60],
                'Cat2': row[3] or '(genérico)'
            })
        
        conn.close()
        
        return {
            'total': total_cat,
            'subcategorias': subcategorias,
            'transacciones': transacciones
        }
    
    except Exception as e:
        st.error(f"Error: {e}")
        return {}

# ===== Cargar datos =====
data = get_categoria_desglose(cat1_selected, year, month)

if not data:
    st.error("No se pudieron cargar los datos")
    st.stop()

# ===== KPI Principal =====
st.markdown(f"## {cat1_selected}")

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    st.metric(
        "Total Gasto",
        format_currency(abs(data['total'])),
    )

with col2:
    st.metric(
        "Transacciones",
        len(data['transacciones']),
    )

with col3:
    if len(data['transacciones']) > 0:
        ticket_medio = abs(data['total']) / len(data['transacciones'])
        st.metric("Ticket Medio", format_currency(ticket_medio))
    else:
        st.metric("Ticket Medio", "N/A")

st.markdown("---")

# ===== Desglose por Cat2 =====
st.markdown("## 📊 Desglose por Subcategoría")

if data['subcategorias']:
    # Crear tabla
    table_data = []
    for sub in sorted(data['subcategorias'], key=lambda x: x['total']):
        if sub['total'] < 0:
            table_data.append({
                'Subcategoría': sub['cat2'],
                'Gasto': format_currency(abs(sub['total'])),
                'Transacciones': sub['num_tx'],
                'Porcentaje': f"{sub['pct']:.1f}%"
            })
    
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Sin gastos en esta categoría")
else:
    st.info("Sin gastos en esta categoría")

st.markdown("---")

# ===== Transacciones individuales =====
st.markdown("## 📝 Últimas Transacciones")

if data['transacciones']:
    df_tx = pd.DataFrame(data['transacciones'])
    
    # Filtro de descripción (opcional)
    search_desc = st.text_input("Buscar en descripción", "")
    
    if search_desc:
        df_tx = df_tx[df_tx['Descripción'].str.contains(search_desc, case=False, na=False)]
    
    st.dataframe(df_tx, use_container_width=True, hide_index=True)
    
    st.info(f"Mostrando {len(df_tx)} transacciones")
else:
    st.info("Sin transacciones en este período")

st.markdown("---")
st.markdown("*Dashboard Finsense | Datos: finsense.db*")
