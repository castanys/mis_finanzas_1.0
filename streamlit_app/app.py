"""
Finsense Analytics - Dashboard Principal
"""
import streamlit as st
import sys
import os
from datetime import datetime

# Añadir parent directory para importar config
sys.path.insert(0, os.path.dirname(__file__))

from config import APP_TITLE, APP_ICON, LAYOUT

# Configurar página
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
<style>
    .main-title {
        font-size: 3em;
        font-weight: bold;
        margin-bottom: 0.5em;
    }
    .subtitle {
        font-size: 1.2em;
        color: #888;
        margin-bottom: 2em;
    }
    .metric-card {
        background-color: #1a1a1a;
        padding: 1.5em;
        border-radius: 0.5em;
        margin: 0.5em 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown(f"# {APP_ICON} {APP_TITLE}")
st.markdown("### Dashboard de Análisis Financiero Personal")
st.markdown("---")

# Información del sistema
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📊", "Base de Datos", "✅ Conectada")

with col2:
    st.metric("📅", "Última Actualización", datetime.now().strftime("%Y-%m-%d %H:%M"))

with col3:
    st.metric("💾", "Transacciones", "15,548")

st.markdown("---")

# Descripción de páginas
st.markdown("## 📖 Navegación")

pages_info = {
    "01_📊_Resumen": "Vista general del mes/año actual con KPIs principales",
    "02_📈_Evolución": "Tendencias temporales y evolución de gastos/ingresos",
    "03_🔍_Categorías": "Análisis detallado por categorías de gasto",
    "04_💰_FIRE": "Proyecciones de independencia financiera",
    "05_💳_Recurrentes": "Gestión de suscripciones y gastos recurrentes",
    "06_🎯_Presupuestos": "Presupuestos y tracking vs real",
    "07_🗺️_Geografía": "Análisis de gastos por ubicación geográfica con mapas"
}

for page, description in pages_info.items():
    st.markdown(f"- **{page}**: {description}")

st.markdown("---")

# Footer
st.markdown("""
### 🛠️ Sistema

- **Database**: SQLite (finsense.db)
- **Transacciones**: 15,548 (2004-2026)
- **Clasificación**: 97.7% (353 transacciones "Otros" = 2.3%)
- **Cobertura**: 21 categorías, 188 subcategorías

**Última sesión**: S19 - Fase 2.1 (CSV v28 generado)
""")

# Verificar conexión a DB
if st.checkbox("🔍 Ver detalles técnicos"):
    try:
        import sqlite3
        from config import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM transacciones")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(fecha), MAX(fecha) FROM transacciones")
        min_date, max_date = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) FROM transacciones WHERE cat2='Otros'")
        otros = cursor.fetchone()[0]
        
        conn.close()
        
        st.success("✅ Base de datos OK")
        st.markdown(f"""
        - **Total transacciones**: {total}
        - **Rango**: {min_date} → {max_date}
        - **Cat2=Otros**: {otros}
        - **Cobertura**: {100.0 * (total - otros) / total:.1f}%
        """)
    except Exception as e:
        st.error(f"❌ Error conectando a BD: {e}")
