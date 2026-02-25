"""
Página 7: Dashboard Geográfico
Análisis de gastos por ubicación del merchant usando Google Places data
Incluye: mapa mundial, tabla de países, mapa de puntos individuales con PyDeck
"""
import streamlit as st
import sys
import os
from datetime import datetime, date
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import DB_PATH, COLOR_GASTO, COLOR_AHORRO
from components.metrics import (
    format_currency, format_percentage, get_current_month_year,
    format_date_range
)
from components.charts import (
    pie_chart_gastos_por_categoria,
    bar_chart_top_gastos
)

# Importar funciones del advisor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from advisor import get_resumen_geografico, get_gastos_por_ubicacion, get_merchants_para_mapa

# Configurar página
st.set_page_config(
    page_title="Geografía",
    page_icon="🗺️",
    layout="wide"
)

st.markdown("# 🗺️ Geografía")
st.markdown("Análisis de gastos por ubicación geográfica del merchant")
st.markdown("---")

# ===== SIDEBAR: Selector de período y filtros =====
st.sidebar.markdown("## 📅 Filtros")

view_type = st.sidebar.radio(
    "Tipo de vista",
    ["Mes actual", "Mes específico", "Año completo", "Todo"],
    index=3  # Por defecto "Todo" porque el mes actual (Feb 2026) tiene pocos datos
)

year_current, month_current = get_current_month_year()
fecha_inicio = None
fecha_fin = None

if view_type == "Mes actual":
    year = year_current
    month = month_current
    period_label = f"Mes actual ({format_date_range(year, month)})"
    fecha_inicio = f"{year}-{month:02d}-01"
    # Último día del mes
    if month == 12:
        fecha_fin = f"{year}-12-31"
    else:
        fecha_fin = f"{year}-{month+1:02d}-01"
        
elif view_type == "Mes específico":
    year = st.sidebar.number_input("Año", min_value=2004, max_value=2099, value=year_current)
    month = st.sidebar.slider("Mes", 1, 12, month_current)
    period_label = format_date_range(year, month)
    fecha_inicio = f"{year}-{month:02d}-01"
    if month == 12:
        fecha_fin = f"{year}-12-31"
    else:
        fecha_fin = f"{year}-{month+1:02d}-01"
        
elif view_type == "Año completo":
    year = st.sidebar.number_input("Año", min_value=2004, max_value=2099, value=year_current)
    month = None
    period_label = str(year)
    fecha_inicio = f"{year}-01-01"
    fecha_fin = f"{year}-12-31"
else:  # Todo
    period_label = "Todos los tiempos"

st.sidebar.markdown(f"**Período**: {period_label}")

# ===== OBTENER DATOS =====
@st.cache_data(ttl=3600)
def get_geo_resumen(fecha_inicio=None, fecha_fin=None):
    """Obtiene resumen geográfico completo"""
    return get_resumen_geografico(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

# Cargar datos
geo_data = get_geo_resumen(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

if not geo_data['paises']:
    st.warning("⚠️ No hay datos geográficos disponibles para el período seleccionado")
    st.stop()

# ===== SECCIÓN 1: KPIs RÁPIDOS =====
st.markdown("## 📊 Resumen Geográfico")

col1, col2, col3, col4 = st.columns(4)

num_paises = len(geo_data['paises'])
num_ciudades = sum(p['num_ciudades'] for p in geo_data['paises'])
total_gasto = geo_data['total_gasto']
gasto_españa = sum(p['gasto'] for p in geo_data['paises'] if p['country'] == 'Spain')
gasto_internacional = total_gasto - gasto_españa
pct_internacional = (gasto_internacional / total_gasto * 100) if total_gasto > 0 else 0

with col1:
    st.metric("🌍 Países", num_paises)

with col2:
    st.metric("🏙️ Ciudades", num_ciudades)

with col3:
    st.metric("💰 Gasto Internacional", format_currency(gasto_internacional))

with col4:
    st.metric("📈 % Internacional", f"{pct_internacional:.1f}%")

st.markdown("---")

# ===== SECCIÓN 2: MAPA MUNDIAL INTERACTIVO CON ZOOM =====
st.markdown("## 🌐 Mapa Mundial Interactivo")
st.markdown("**Zoom progresivo**: Haz zoom hacia países → ciudades → comercios individuales")

# Obtener merchants para mapa
@st.cache_data(ttl=3600)
def cargar_merchants(fecha_inicio=None, fecha_fin=None):
    """Carga merchants con coords para mapa"""
    return get_merchants_para_mapa(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

merchants_data = cargar_merchants(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

if not merchants_data:
    st.warning("⚠️ Sin merchants con coordenadas para el período seleccionado")
else:
    # Definir colores por categoría
    cat_colors = {
        'Alimentación': '#FF6B35',
        'Compras': '#004E89',
        'Restauración': '#F24236',
        'Transporte': '#1B998B',
        'Ocio y Cultura': '#2E294E',
        'Viajes': '#FFD23F',
        'Vivienda': '#3D5941',
        'Deportes': '#E63946',
        'Salud y Belleza': '#F1FAEE',
        'Impuestos': '#A8DADC',
        'Efectivo': '#457B9D',
        'Recibos': '#1D3557',
        'Finanzas': '#14213D',
        'Servicios Consultoría': '#00B4D8',
        'Suscripciones': '#90E0EF',
        'Ropa y Calzado': '#CAF0F8',
        'Seguros': '#006E90',
        'Ingreso': '#51CF66',
        'Nómina': '#40C057',
        'Liquidación': '#69DB7C',
        'Inversión': '#05668D',
        'Wallapop': '#C9184A',
        'Transferencia': '#FB5607',
        'Cuenta Común': '#FFBE0B'
    }
    
    # Extraer datos del mapa
    import numpy as np
    
    merchants_lats = [m['lat'] for m in merchants_data]
    merchants_lngs = [m['lng'] for m in merchants_data]
    merchants_gastos = [m['gasto'] for m in merchants_data]
    merchants_cat1 = [m['cat1'] for m in merchants_data]
    merchants_texts = [
        f"<b>{m['name']}</b><br>" +
        f"<b>📍</b> {m['city']}, {m['country']}<br>" +
        f"<b>💰</b> €{m['gasto']:.2f}<br>" +
        f"<b>🏷️</b> {m['cat1']} / {m['cat2']}<br>" +
        f"<b>📊</b> {m['num_tx']} transacciones"
        for m in merchants_data
    ]
    
    # Calcular tamaño con escala logarítmica
    gastos_array = np.array(merchants_gastos, dtype=float)
    gastos_log = np.log10(gastos_array + 1)
    log_min, log_max = gastos_log.min(), gastos_log.max()
    
    if log_max > log_min:
        sizes_norm = (gastos_log - log_min) / (log_max - log_min)
        sizes = [5.0 + 45.0 * float(s) for s in sizes_norm]
    else:
        sizes = [25.0] * len(merchants_gastos)
    
    # Crear figura con trazas agrupadas por categoría
    fig_mapa = go.Figure()
    categorias = sorted(set(merchants_cat1))
    
    for cat in categorias:
        cat_indices = [i for i, m_cat in enumerate(merchants_cat1) if m_cat == cat]
        
        if cat_indices:
            fig_mapa.add_trace(go.Scattermap(
                lon=[merchants_lngs[i] for i in cat_indices],
                lat=[merchants_lats[i] for i in cat_indices],
                mode='markers',
                marker=dict(
                    size=[sizes[i] for i in cat_indices],
                    color=cat_colors.get(cat, '#808080'),
                    opacity=0.8
                ),
                text=[merchants_texts[i] for i in cat_indices],
                hovertemplate='%{text}<extra></extra>',
                name=cat,
                legendgroup=cat,
                showlegend=True
            ))
    
    fig_mapa.update_layout(
        title="Gastos por Merchant (Zoom progresivo: Global → País → Ciudad → Negocio)<br><sub>Tamaño ∝ gasto, Color = categoría</sub>",
        mapbox=dict(
            style='open-street-map',
            center=dict(lat=40, lon=0),
            zoom=2
        ),
        height=600,
        hovermode='closest',
        margin=dict(l=0, r=0, t=80, b=0),
        legend=dict(
            x=1.05,
            y=1,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='gray',
            borderwidth=1
        )
    )
    
    st.plotly_chart(fig_mapa, use_container_width=True)

st.markdown("---")

# ===== SECCIÓN 3: TABLA DE PAÍSES =====
st.markdown("## 📋 Ranking de Países")

# Preparar DataFrame para tabla
tabla_paises = []
for p in geo_data['paises']:
    pct = (p['gasto'] / total_gasto * 100) if total_gasto > 0 else 0
    tabla_paises.append({
        'País': p['country'],
        'Ciudades': p['num_ciudades'],
        'Merchants': p['num_merchants'],
        'Transacciones': p['num_tx'],
        'Total (€)': f"{p['gasto']:.2f}",
        '% del Total': f"{pct:.1f}%"
    })

df_tabla = pd.DataFrame(tabla_paises)
st.dataframe(df_tabla, use_container_width=True, hide_index=True)

st.markdown("---")

# ===== SECCIÓN 4: DETALLE DEL PAÍS SELECCIONADO =====
st.markdown("## 🔍 Detalle por País")

pais_seleccionado = st.selectbox(
    "Selecciona un país para ver detalle:",
    [p['country'] for p in geo_data['paises']],
    index=0  # Por defecto Spain
)

# Obtener datos del país seleccionado
pais_data = next((p for p in geo_data['paises'] if p['country'] == pais_seleccionado), None)

if pais_data:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Gasto Total", format_currency(pais_data['gasto']))
    with col2:
        st.metric("Transacciones", pais_data['num_tx'])
    with col3:
        st.metric("Merchants", pais_data['num_merchants'])
    
    # Top merchants del país
    st.markdown(f"### Top Merchants en {pais_seleccionado}")
    
    @st.cache_data(ttl=3600)
    def get_top_merchants_pais(country):
        """Obtiene top merchants de un país"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    t.merchant_name,
                    m.address,
                    m.city,
                    SUM(ABS(t.importe)) as total,
                    COUNT(*) as num_tx
                FROM transacciones t
                LEFT JOIN merchants m ON t.merchant_name = m.merchant_name
                WHERE t.tipo = 'GASTO'
                  AND m.country = ?
                  AND t.merchant_name IS NOT NULL
                GROUP BY t.merchant_name
                ORDER BY total DESC
                LIMIT 15
            """
            
            cursor.execute(query, (country,))
            merchants = []
            for row in cursor.fetchall():
                merchant_name, address, city, total, num_tx = row
                merchants.append({
                    'Merchant': merchant_name or '(sin nombre)',
                    'Ciudad': city or '(sin ciudad)',
                    'Dirección': address or '(sin dirección)',
                    'Total (€)': f"{total:.2f}",
                    'Transacciones': num_tx
                })
            
            conn.close()
            return merchants
        except Exception as e:
            st.error(f"Error: {e}")
            return []
    
    merchants_pais = get_top_merchants_pais(pais_seleccionado)
    
    if merchants_pais:
        df_merchants = pd.DataFrame(merchants_pais)
        st.dataframe(df_merchants, use_container_width=True, hide_index=True)
    else:
        st.info("Sin merchants detallados para este país")
    
    st.markdown("---")
    
    # Desglose por categoría
    st.markdown(f"### Desglose por Categoría en {pais_seleccionado}")
    
    @st.cache_data(ttl=3600)
    def get_cat_pais(country, fecha_inicio=None, fecha_fin=None):
        """Obtiene desglose de categorías por país"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            where_clauses = ["t.tipo = 'GASTO'", "m.country = ?", "m.merchant_name IS NOT NULL"]
            params = [country]
            
            if fecha_inicio:
                where_clauses.append("t.fecha >= ?")
                params.append(fecha_inicio)
            
            if fecha_fin:
                where_clauses.append("t.fecha <= ?")
                params.append(fecha_fin)
            
            where_sql = " AND ".join(where_clauses)
            
            query = f"""
                SELECT t.cat1, t.cat2, SUM(ABS(t.importe)) as total, COUNT(*) as num_tx
                FROM transacciones t
                LEFT JOIN merchants m ON t.merchant_name = m.merchant_name
                WHERE {where_sql}
                GROUP BY t.cat1, t.cat2
                ORDER BY total DESC
            """
            
            cursor.execute(query, params)
            
            categorias = []
            for row in cursor.fetchall():
                cat1, cat2, total, num_tx = row
                categorias.append({
                    'cat1': cat1,
                    'cat2': cat2,
                    'gasto': total,
                    'num_tx': num_tx
                })
            
            conn.close()
            return categorias
        except Exception as e:
            st.error(f"Error: {e}")
            return []
    
    cat_pais = get_cat_pais(pais_seleccionado, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
    
    if cat_pais:
        # Pie chart por categoría
        cat_data_pie = []
        for c in cat_pais:
            label = f"{c['cat1']} / {c['cat2']}" if c['cat2'] else c['cat1']
            cat_data_pie.append({
                'label': label,
                'valor': c['gasto']
            })
        
        if cat_data_pie:
            fig_pie = go.Figure(data=[go.Pie(
                labels=[c['label'] for c in cat_data_pie],
                values=[c['valor'] for c in cat_data_pie],
                hovertemplate='<b>%{label}</b><br>€%{value:.2f}<br>%{percent}<extra></extra>'
            )])
            
            fig_pie.update_layout(
                title=f"Desglose de Gasto en {pais_seleccionado}",
                height=400
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
    
    st.markdown("---")
    
    # Mapa de puntos individuales con PyDeck
    st.markdown(f"### 🗺️ Mapa de Puntos en {pais_seleccionado}")
    
    @st.cache_data(ttl=3600)
    def get_puntos_pais(country, fecha_inicio=None, fecha_fin=None):
        """Obtiene puntos individuales (lat/lng) de transacciones en un país"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            where_clauses = [
                "t.tipo = 'GASTO'",
                "m.country = ?",
                "m.merchant_name IS NOT NULL",
                "m.lat IS NOT NULL",
                "m.lng IS NOT NULL",
                "m.lat != 0",
                "m.lng != 0"
            ]
            params = [country]
            
            if fecha_inicio:
                where_clauses.append("t.fecha >= ?")
                params.append(fecha_inicio)
            
            if fecha_fin:
                where_clauses.append("t.fecha <= ?")
                params.append(fecha_fin)
            
            where_sql = " AND ".join(where_clauses)
            
            query = f"""
                SELECT 
                    m.lat, m.lng, t.merchant_name, m.city, m.address,
                    ABS(t.importe) as importe, t.cat1, t.fecha
                FROM transacciones t
                LEFT JOIN merchants m ON t.merchant_name = m.merchant_name
                WHERE {where_sql}
                ORDER BY t.fecha DESC
            """
            
            cursor.execute(query, params)
            
            puntos = []
            for row in cursor.fetchall():
                lat, lng, merchant, city, address, importe, cat1, fecha = row
                
                # Color según categoría (simplificado)
                cat_colors = {
                    'Alimentación': [255, 100, 0],
                    'Compras': [100, 200, 255],
                    'Restauración': [255, 50, 50],
                    'Transporte': [50, 200, 50],
                    'Ocio y Cultura': [200, 50, 200],
                    'Viajes': [255, 255, 0]
                }
                
                color = cat_colors.get(cat1, [150, 150, 150])
                
                puntos.append({
                    'lat': lat,
                    'lon': lng,
                    'name': merchant or '(sin merchant)',
                    'city': city or '(sin ciudad)',
                    'address': address or '(sin dirección)',
                    'importe': importe,
                    'cat1': cat1,
                    'fecha': fecha,
                    'color': color,
                    'size': max(50, min(300, importe * 5))  # Tamaño según importe
                })
            
            conn.close()
            return puntos
        except Exception as e:
            st.error(f"Error: {e}")
            return []
    
    puntos = get_puntos_pais(pais_seleccionado, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
    
    if puntos:
        # Crear mapa PyDeck
        layer = pdk.Layer(
            'ScatterplotLayer',
            data=puntos,
            get_position=['lon', 'lat'],
            get_color='color',
            get_radius='size',
            pickable=True,
            auto_highlight=True,
        )
        
        # Centro del mapa: promedio de los puntos
        lat_centro = sum(p['lat'] for p in puntos) / len(puntos) if puntos else 0
        lng_centro = sum(p['lon'] for p in puntos) / len(puntos) if puntos else 0
        
        view = pdk.ViewState(
            longitude=lng_centro,
            latitude=lat_centro,
            zoom=5,
            pitch=45,
        )
        
        # Tooltip
        tooltip = {
            "html": "<b>{name}</b><br>€{importe:.2f}<br>{cat1}<br>{fecha}",
            "style": {
                "backgroundColor": "steelblue",
                "color": "white",
                "fontFamily": "Arial",
                "z-index": "10000"
            }
        }
        
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip=tooltip,
            map_style='mapbox://styles/mapbox/light-v10'
        )
        
        st.pydeck_chart(deck)
        
        st.info(f"📍 {len(puntos)} transacciones geolocalizadas en {pais_seleccionado}")
    else:
        st.warning(f"⚠️ Sin datos de ubicación exacta para {pais_seleccionado}")
