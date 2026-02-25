"""
Página 5: Gestión de Suscripciones y Gastos Recurrentes
"""
import streamlit as st
import sys
import os
import sqlite3
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config import DB_PATH
from components.metrics import format_currency

st.set_page_config(
    page_title="Recurrentes",
    page_icon="💳",
    layout="wide"
)

st.markdown("# 💳 Suscripciones y Gastos Recurrentes")
st.markdown("Controla tus gastos fijos y recurrentes")
st.markdown("---")

# ===== Función para detectar recurrentes =====
@st.cache_data(ttl=3600)
def get_recurrentes() -> dict:
    """Detecta gastos recurrentes"""
    try:
        from src.query_engine import QueryEngine
        engine = QueryEngine(DB_PATH)
        result = engine.recibos_recurrentes()
        engine.close()
        return result
    except Exception as e:
        st.error(f"Error: {e}")
        return {'recurrentes': []}

# ===== Cargar datos =====
data = get_recurrentes()
recurrentes = data.get('recurrentes', [])

# ===== Estadísticas =====
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "📋 Gastos Recurrentes",
        len(recurrentes)
    )

with col2:
    total_mensual = data.get('total_mensual_recurrente', 0)
    st.metric(
        "📅 Mensual Recurrente",
        format_currency(abs(total_mensual))
    )

with col3:
    total_anual = data.get('total_anual_recurrente', 0)
    st.metric(
        "📊 Anual Estimado",
        format_currency(abs(total_anual))
    )

st.markdown("---")

# ===== Tabla de recurrentes =====
st.markdown("## 📝 Listado de Gastos Recurrentes")

if recurrentes:
    # Preparar datos para tabla
    table_data = []
    for rec in recurrentes:
        table_data.append({
            'Descripción': rec.get('descripcion', '(sin nombre)')[:40],
            'Categoría': f"{rec.get('cat1', 'N/A')}",
            'Frecuencia': rec.get('frecuencia', 'N/A'),
            'Importe': format_currency(abs(rec.get('importe_medio', 0))),
            'Último cargo': rec.get('ultimo_cargo', 'N/A'),
            'Próximo cargo': rec.get('proximo_estimado', 'N/A'),
            'Anual': format_currency(abs(rec.get('total_anual_estimado', 0)))
        })
    
    df = pd.DataFrame(table_data)
    
    # Ordenar por próximo cargo
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # ===== Alertas de próximos cargos =====
    st.markdown("---")
    st.markdown("## 🔔 Próximos Cargos")
    
    today = datetime.now().date()
    proximamente = []
    
    for rec in recurrentes:
        proximo = datetime.strptime(rec.get('proximo_estimado', '2099-01-01'), '%Y-%m-%d').date()
        dias_restantes = (proximo - today).days
        
        if 0 <= dias_restantes <= 7:
            proximamente.append({
                'desc': rec.get('descripcion', '(sin nombre)')[:40],
                'dias': dias_restantes,
                'fecha': rec.get('proximo_estimado', ''),
                'importe': rec.get('importe_medio', 0)
            })
    
    proximamente.sort(key=lambda x: x['dias'])
    
    if proximamente:
        for item in proximamente:
            if item['dias'] == 0:
                emoji = "🔴"
                texto = "HOY"
            else:
                emoji = "🟡"
                texto = f"en {item['dias']} días"
            
            st.warning(f"{emoji} **{item['desc']}**: {format_currency(abs(item['importe']))} {texto}")
    else:
        st.success("✅ Sin cargos próximos en los próximos 7 días")
    
    # ===== Análisis por categoría =====
    st.markdown("---")
    st.markdown("## 📊 Análisis por Categoría")
    
    # Agrupar por categoría
    categorias_recurrentes = {}
    for rec in recurrentes:
        cat = rec.get('cat1', 'Otros')
        if cat not in categorias_recurrentes:
            categorias_recurrentes[cat] = {
                'cantidad': 0,
                'total_mensual': 0,
                'total_anual': 0
            }
        
        categorias_recurrentes[cat]['cantidad'] += 1
        categorias_recurrentes[cat]['total_mensual'] += rec.get('importe_medio', 0)
        categorias_recurrentes[cat]['total_anual'] += rec.get('total_anual_estimado', 0)
    
    # Crear tabla de categorías
    cat_data = []
    for cat, stats in sorted(categorias_recurrentes.items(), 
                             key=lambda x: x[1]['total_anual'], 
                             reverse=True):
        cat_data.append({
            'Categoría': cat,
            'Cantidad': stats['cantidad'],
            'Mensual': format_currency(abs(stats['total_mensual'])),
            'Anual': format_currency(abs(stats['total_anual']))
        })
    
    if cat_data:
        df_cat = pd.DataFrame(cat_data)
        st.dataframe(df_cat, use_container_width=True, hide_index=True)

else:
    st.info("No se detectaron gastos recurrentes en la base de datos")
    st.markdown("""
    Los gastos recurrentes se detectan automáticamente buscando transacciones
    que se repiten con periodicidad similar.
    
    Criterios:
    - Mínimo 3 ocurrencias
    - Periodicidad regular (variación máxima de 15 días)
    """)

st.markdown("---")

# ===== Consejos =====
st.markdown("## 💡 Consejos")

st.markdown("""
1. **Audita regularmente**: Revisa tus suscripciones mensualmente
2. **Cancela lo que no uses**: Cada servicio cancelado es dinero ahorrado
3. **Busca alternativas**: Algunos servicios tienen planes más baratos
4. **Renegocia**: Contacta proveedores para obtener mejores tarifas
5. **Agrupa servicios**: Algunos proveedores ofrecen bundles más económicos

**Tu objetivo FIRE 🔥**: Cada € ahorrado en recurrentes es dinero que te acerca
""")

st.markdown("---")
st.markdown("*Dashboard Finsense | Datos: finsense.db*")
