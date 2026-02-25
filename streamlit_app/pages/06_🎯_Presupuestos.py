"""
Página 6: Presupuestos y Seguimiento
MVP: Barras de progreso por categoría + edición de presupuestos + calendario de cargos extraordinarios
"""
import streamlit as st
import sys
import os
from datetime import datetime, date
import sqlite3
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import DB_PATH, COLOR_INGRESO, COLOR_GASTO, COLOR_AHORRO
from components.metrics import (
    format_currency, format_percentage, get_current_month_year,
    format_date_range, get_trend_indicator, days_remaining_in_month
)

# Configurar página
st.set_page_config(
    page_title="Presupuestos",
    page_icon="🎯",
    layout="wide"
)

st.markdown("# 🎯 Presupuestos y Seguimiento")
st.markdown("---")

# ===== FUNCIÓN: Obtener presupuestos =====
@st.cache_data(ttl=3600)
def get_presupuestos():
    """Obtiene todos los presupuestos activos"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, cat1, cat2, importe_mensual, activo, updated_at
            FROM presupuestos
            WHERE activo = 1
            ORDER BY cat1, cat2
        """)
        
        presupuestos = []
        for row in cursor.fetchall():
            presupuestos.append({
                'id': row[0],
                'cat1': row[1],
                'cat2': row[2],
                'importe_mensual': row[3],
                'activo': row[4],
                'updated_at': row[5]
            })
        
        conn.close()
        return presupuestos
    
    except Exception as e:
        st.error(f"Error cargando presupuestos: {e}")
        return []

# ===== FUNCIÓN: Obtener gasto actual del mes por categoría =====
def get_gastos_mes_actual():
    """Obtiene gastos actuales del mes en curso por categoría"""
    try:
        year, month = get_current_month_year()
        periodo = f"{year}-{month:02d}"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT cat1, cat2, SUM(importe) as total, COUNT(*) as num_tx
            FROM transacciones
            WHERE tipo = 'GASTO' 
              AND strftime('%Y-%m', fecha) = '{periodo}'
              AND cat1 != 'Bizum'
            GROUP BY cat1, cat2
            ORDER BY cat1, cat2
        """)
        
        gastos = {}
        for row in cursor.fetchall():
            cat1, cat2, total, num_tx = row
            key = f"{cat1}|{cat2}"
            gastos[key] = {
                'cat1': cat1,
                'cat2': cat2,
                'total': abs(total),  # Convertir a positivo
                'num_tx': num_tx
            }
        
        conn.close()
        return gastos
    
    except Exception as e:
        st.error(f"Error cargando gastos: {e}")
        return {}

# ===== FUNCIÓN: Obtener cargos extraordinarios =====
@st.cache_data(ttl=3600)
def get_cargos_extraordinarios():
    """Obtiene todos los cargos extraordinarios activos"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, mes, dia, descripcion, importe_estimado, dias_aviso, activo, created_at
            FROM cargos_extraordinarios
            WHERE activo = 1
            ORDER BY mes, dia
        """)
        
        cargos = []
        for row in cursor.fetchall():
            cargos.append({
                'id': row[0],
                'mes': row[1],
                'dia': row[2],
                'descripcion': row[3],
                'importe_estimado': row[4],
                'dias_aviso': row[5],
                'activo': row[6],
                'created_at': row[7]
            })
        
        conn.close()
        return cargos
    
    except Exception as e:
        st.error(f"Error cargando cargos extraordinarios: {e}")
        return []

# ===== FUNCIÓN: Actualizar presupuesto =====
def actualizar_presupuesto(id_pres, nuevo_importe):
    """Actualiza el importe de un presupuesto"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE presupuestos
            SET importe_mensual = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (nuevo_importe, id_pres))
        
        conn.commit()
        conn.close()
        
        st.cache_data.clear()
        st.success(f"✅ Presupuesto actualizado")
    
    except Exception as e:
        st.error(f"Error actualizando presupuesto: {e}")

# ===== CARGAR DATOS =====
presupuestos = get_presupuestos()
gastos_mes = get_gastos_mes_actual()
cargos_extraordinarios = get_cargos_extraordinarios()

year, month = get_current_month_year()

# ===== SECCIÓN 1: PRESUPUESTOS Y PROGRESO =====
st.markdown("## 💰 Presupuestos del Mes")
st.markdown(f"*Mes actual: {format_date_range(year, month)}*")

if not presupuestos:
    st.warning("⚠️ No hay presupuestos configurados")
else:
    # Tabla interactiva de presupuestos
    tab1, tab2 = st.tabs(["📊 Vista Gráfica", "✏️ Edición"])
    
    with tab1:
        # Vista gráfica con barras de progreso
        for pres in presupuestos:
            cat_key = f"{pres['cat1']}|{pres['cat2']}"
            gasto_actual = gastos_mes.get(cat_key, {}).get('total', 0)
            presupuesto = pres['importe_mensual']
            
            # Calcular porcentaje
            pct = (gasto_actual / presupuesto * 100) if presupuesto > 0 else 0
            
            # Determinar color según estado
            if pct < 80:
                color_estado = "🟢"
                estado = "En plan"
            elif pct < 100:
                color_estado = "🟡"
                estado = "Aproximándose"
            else:
                color_estado = "🔴"
                estado = "Superado"
            
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.write(f"**{pres['cat1']} → {pres['cat2']}**")
            
            with col2:
                st.write(f"{format_currency(gasto_actual)} / {format_currency(presupuesto)}")
            
            with col3:
                st.write(f"{pct:.1f}%")
            
            with col4:
                st.write(f"{color_estado} {estado}")
            
            # Barra de progreso
            st.progress(min(pct / 100, 1.0), text=f"{pct:.0f}%")
    
    with tab2:
        st.write("**Editar Presupuestos**")
        
        # Crear forma de edición
        cols = st.columns([2, 1, 1])
        
        with cols[0]:
            st.write("Categoría")
        
        with cols[1]:
            st.write("Presupuesto Actual")
        
        with cols[2]:
            st.write("Nuevo Presupuesto")
        
        for pres in presupuestos:
            cols = st.columns([2, 1, 1])
            
            with cols[0]:
                st.write(f"{pres['cat1']} → {pres['cat2']}")
            
            with cols[1]:
                st.write(format_currency(pres['importe_mensual']))
            
            with cols[2]:
                nuevo_importe = st.number_input(
                    f"Presupuesto para {pres['cat1']}|{pres['cat2']}",
                    min_value=0.0,
                    value=pres['importe_mensual'],
                    step=10.0,
                    label_visibility="collapsed",
                    key=f"presupuesto_{pres['id']}"
                )
                
                if nuevo_importe != pres['importe_mensual']:
                    if st.button("Guardar", key=f"guardar_{pres['id']}"):
                        actualizar_presupuesto(pres['id'], nuevo_importe)

st.markdown("---")

# ===== SECCIÓN 2: CALENDARIO DE CARGOS EXTRAORDINARIOS =====
st.markdown("## 📅 Cargos Extraordinarios Próximos")

if not cargos_extraordinarios:
    st.info("ℹ️ No hay cargos extraordinarios configurados")
else:
    # Obtener mes actual
    year, month = get_current_month_year()
    meses_nombres = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    
    # Agrupar cargos por mes
    cargos_por_mes = {}
    for cargo in cargos_extraordinarios:
        mes = cargo['mes']
        if mes not in cargos_por_mes:
            cargos_por_mes[mes] = []
        cargos_por_mes[mes].append(cargo)
    
    # Mostrar calendarios de próximos 6 meses
    for offset in range(6):
        mes_objetivo = month + offset
        año_objetivo = year
        
        if mes_objetivo > 12:
            mes_objetivo -= 12
            año_objetivo += 1
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**{meses_nombres[mes_objetivo - 1]} {año_objetivo}**")
        
        if mes_objetivo in cargos_por_mes:
            total_mes = sum(c['importe_estimado'] for c in cargos_por_mes[mes_objetivo])
            
            with col2:
                st.write(f"**Total: {format_currency(total_mes)}**")
            
            for cargo in cargos_por_mes[mes_objetivo]:
                fecha_str = ""
                if cargo['dia']:
                    fecha_str = f"Día {cargo['dia']}"
                else:
                    fecha_str = "Fecha variable"
                
                st.write(f"""
                - **{cargo['descripcion']}**
                  - {fecha_str}
                  - Importe: {format_currency(cargo['importe_estimado'])}
                  - Aviso: {cargo['dias_aviso']} días antes
                """)
        else:
            st.write("*Sin cargos extraordinarios*")
        
        st.markdown("---")

st.markdown("---")

# ===== RESUMEN MENSUAL =====
st.markdown("## 📊 Resumen del Mes")

# Calcular totales
total_presupuesto = sum(p['importe_mensual'] for p in presupuestos)
total_gasto = sum(g['total'] for g in gastos_mes.values())
diferencia = total_presupuesto - total_gasto

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Presupuesto Total",
        format_currency(total_presupuesto),
        delta=None
    )

with col2:
    st.metric(
        "Gasto Real",
        format_currency(total_gasto),
        delta=None
    )

with col3:
    diferencia_pct = (diferencia / total_presupuesto * 100) if total_presupuesto > 0 else 0
    delta_text = f"{abs(diferencia_pct):.1f}% {'restante' if diferencia >= 0 else 'exceso'}"
    
    st.metric(
        "Diferencia",
        format_currency(diferencia),
        delta=delta_text
    )

st.markdown("---")

# ===== FOOTER =====
st.markdown("""
*Dashboard construido con Streamlit | Datos: SQLite finsense.db*
""")
