"""
Funciones para generar gráficos con Plotly
"""
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Optional
from config import COLOR_GASTO, COLOR_INGRESO, COLOR_AHORRO, COLOR_NEUTRAL

def pie_chart_gastos_por_categoria(data: List[Dict]) -> go.Figure:
    """
    Gráfico de torta: gastos por categoría (Cat1)
    
    Args:
        data: Lista de dicts con 'cat1', 'total', 'pct'
    
    Returns:
        Plotly Figure
    """
    # Filtrar solo gastos (negativo)
    data_filtrado = [d for d in data if d.get('total', 0) < 0]
    
    if not data_filtrado:
        return go.Figure().add_annotation(text="Sin datos")
    
    # Ordenar por total
    data_filtrado = sorted(data_filtrado, key=lambda x: x['total'])
    
    labels = [d['cat1'] for d in data_filtrado]
    values = [abs(d['total']) for d in data_filtrado]
    pcts = [d.get('pct', 0) for d in data_filtrado]
    
    # Crear hover text
    hover_text = [
        f"{label}<br>€{val:,.0f}<br>{pct:.1f}%"
        for label, val, pct in zip(labels, values, pcts)
    ]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hovertext=hover_text,
        hoverinfo='text',
        marker=dict(line=dict(color='white', width=2)),
        textposition='auto',
        textinfo='label+percent'
    )])
    
    fig.update_layout(
        title="Gastos por Categoría",
        height=500,
        showlegend=True,
        template='plotly_dark'
    )
    
    return fig

def bar_chart_top_gastos(data: List[Dict], limit: int = 10) -> go.Figure:
    """
    Gráfico de barras: top N gastos
    
    Args:
        data: Lista de dicts con 'merchant', 'cat1', 'total'
        limit: Número máximo de resultados
    
    Returns:
        Plotly Figure
    """
    # Filtrar negativos y ordenar
    data_filtrado = [d for d in data[:limit] if d.get('total', 0) < 0]
    data_filtrado = sorted(data_filtrado, key=lambda x: x['total'])
    
    merchants = [d.get('merchant', 'Unknown')[:30] for d in data_filtrado]  # Truncar
    amounts = [abs(d['total']) for d in data_filtrado]
    categories = [d.get('cat1', 'N/A') for d in data_filtrado]
    
    fig = go.Figure(data=[go.Bar(
        x=amounts,
        y=merchants,
        orientation='h',
        marker=dict(
            color=amounts,
            colorscale='Reds',
            showscale=True,
            colorbar=dict(title="€")
        ),
        hovertemplate="%{y}<br>€%{x:,.0f}<extra></extra>"
    )])
    
    fig.update_layout(
        title=f"Top {limit} Gastos",
        xaxis_title="Importe (€)",
        yaxis_title="",
        height=400,
        showlegend=False,
        template='plotly_dark',
        margin=dict(l=200)
    )
    
    return fig

def line_chart_evolucion_mensual(monthly_data: List[Dict], metrics: List[str] = None) -> go.Figure:
    """
    Gráfico de línea: evolución temporal
    
    Args:
        monthly_data: Lista de dicts con 'periodo', 'gasto_total', 'ingreso_total', 'ahorro'
        metrics: Qué métricas mostrar ('gastos', 'ingresos', 'ahorro')
    
    Returns:
        Plotly Figure
    """
    if metrics is None:
        metrics = ['gastos', 'ahorro']
    
    if not monthly_data:
        return go.Figure().add_annotation(text="Sin datos")
    
    # Preparar data
    periodos = [d.get('periodo', '') for d in monthly_data]
    
    fig = go.Figure()
    
    if 'ingresos' in metrics:
        ingresos = [d.get('ingreso_total', 0) for d in monthly_data]
        fig.add_trace(go.Scatter(
            x=periodos, y=ingresos,
            mode='lines+markers',
            name='Ingresos',
            line=dict(color=COLOR_INGRESO, width=2),
            hovertemplate="Ingresos: €%{y:,.0f}<extra></extra>"
        ))
    
    if 'gastos' in metrics:
        gastos = [abs(d.get('gasto_total', 0)) for d in monthly_data]
        fig.add_trace(go.Scatter(
            x=periodos, y=gastos,
            mode='lines+markers',
            name='Gastos',
            line=dict(color=COLOR_GASTO, width=2),
            hovertemplate="Gastos: €%{y:,.0f}<extra></extra>"
        ))
    
    if 'ahorro' in metrics:
        ahorros = [d.get('ahorro', 0) for d in monthly_data]
        fig.add_trace(go.Scatter(
            x=periodos, y=ahorros,
            mode='lines+markers',
            name='Ahorro',
            line=dict(color=COLOR_AHORRO, width=2),
            hovertemplate="Ahorro: €%{y:,.0f}<extra></extra>"
        ))
    
    fig.update_layout(
        title="Evolución Mensual",
        xaxis_title="Mes",
        yaxis_title="Importe (€)",
        height=400,
        hovermode='x unified',
        template='plotly_dark'
    )
    
    return fig

def bar_chart_categoria_breakdown(category_data: List[Dict], cat_name: str) -> go.Figure:
    """
    Gráfico de barras: desglose de una categoría por Cat2
    
    Args:
        category_data: Lista de dicts con 'cat2', 'total', 'num_tx'
        cat_name: Nombre de la categoría
    
    Returns:
        Plotly Figure
    """
    if not category_data:
        return go.Figure().add_annotation(text="Sin datos")
    
    # Filtrar negativos
    data_filtrado = [d for d in category_data if d.get('total', 0) < 0]
    data_filtrado = sorted(data_filtrado, key=lambda x: x['total'])
    
    subcats = [d.get('cat2', 'Otros')[:30] for d in data_filtrado]
    amounts = [abs(d['total']) for d in data_filtrado]
    
    fig = go.Figure(data=[go.Bar(
        x=subcats,
        y=amounts,
        marker=dict(color=COLOR_GASTO),
        hovertemplate="%{x}<br>€%{y:,.0f}<extra></extra>"
    )])
    
    fig.update_layout(
        title=f"Desglose: {cat_name}",
        yaxis_title="Importe (€)",
        height=400,
        showlegend=False,
        template='plotly_dark'
    )
    
    return fig
