# Finsense Analytics Dashboard

Dashboard web interactivo para análisis financiero personal con Streamlit.

## 🚀 Inicio Rápido

### Opción 1: Script de ejecución (recomendado)

```bash
cd /home/pablo/apps/mis_finanzas_1.0
./run_dashboard.sh
```

El dashboard se abrirá en `http://localhost:8501`

### Opción 2: Ejecutar manualmente

```bash
cd /home/pablo/apps/mis_finanzas_1.0
source venv/bin/activate
streamlit run streamlit_app/app.py
```

## 📊 Estructura

```
streamlit_app/
├── app.py                      # Página principal (home)
├── config.py                   # Configuración global
├── pages/
│   ├── 01_📊_Resumen.py       # ✅ IMPLEMENTADA - Vista general
│   ├── 02_📈_Evolución.py     # TODO
│   ├── 03_🔍_Categorías.py    # TODO
│   ├── 04_💰_FIRE.py          # TODO
│   ├── 05_💳_Recurrentes.py   # TODO
│   └── 06_🎯_Presupuestos.py  # TODO
└── components/
    ├── metrics.py             # ✅ Funciones de cálculo
    ├── charts.py              # ✅ Gráficos Plotly
    └── filters.py             # TODO
```

## ✅ Páginas Implementadas

### 01_📊_Resumen.py (MVP)

**Funcionalidades**:
- Selector de período (mes actual, mes específico, año completo)
- **4 KPIs principales**:
  - 📥 Ingresos totales
  - 📤 Gastos totales
  - 💾 Ahorro
  - 📅 Días restantes (si es mes actual)
- **Gráficos**:
  - Pie chart: Gastos por categoría
  - Bar chart: Top 10 gastos
- **Tabla**: Desglose por categoría
- **Información adicional**: Ratios, tasa de ahorro

**Datos**:
- Cargados desde finsense.db (SQLite)
- Cache de 1 hora para optimizar rendimiento
- Período seleccionable en sidebar

**Tecnología**:
- Streamlit para UI
- Plotly para gráficos interactivos
- SQLite3 para consultas

## 🔧 Configuración

Editar `streamlit_app/config.py`:

```python
DB_PATH = '../finsense.db'           # Ruta a la base de datos
DEFAULT_MONTHS_HISTORICO = 12        # Meses para análisis histórico
DEFAULT_FIRE_OBJETIVO = 400000.0     # Objetivo FIRE en €
DEFAULT_FIRE_RENTABILIDAD = 0.07     # Rentabilidad esperada
```

## 📈 Páginas Pendientes (Fase 2.2.2)

### 02_📈_Evolución.py
- Gráfico de línea: Evolución mensual (ingresos, gastos, ahorro)
- Estacionalidad: Comparar mismo mes años anteriores

### 03_🔍_Categorías.py
- Drill-down por categoría (Cat1)
- Tabla de transacciones individuales con filtros
- Comparativa temporal

### 04_💰_FIRE.py
- Configuración objetivo FIRE
- Proyección acumulada con interés compuesto
- Escenarios: pesimista/realista/optimista

### 05_💳_Recurrentes.py
- Lista de suscripciones y gastos recurrentes
- Próximos cargos estimados
- Total mensual y anual

### 06_🎯_Presupuestos.py
- Configuración de presupuestos por categoría
- Tracking vs real
- Alertas cuando se acerca al límite

## 💻 Tecnología

- **Framework**: Streamlit 1.54+
- **Gráficos**: Plotly 6.5+
- **BD**: SQLite3 (built-in)
- **Python**: 3.12+

## 🐛 Troubleshooting

### Port 8501 ya en uso

```bash
streamlit run streamlit_app/app.py --server.port 8502
```

### Cache de datos desactualizado

```bash
streamlit run streamlit_app/app.py --logger.level=debug
```

### Importar componentes no funciona

Asegúrate que el virtual environment está activado:

```bash
source venv/bin/activate
```

## 📝 Próximas Mejoras

- [ ] Exportar reportes a PDF
- [ ] Integración con API de análisis
- [ ] Alertas automáticas por email
- [ ] Sincronización con nuevos CSVs de bancos
- [ ] Modo oscuro/claro configurable

---

**Última actualización**: S19 (Fase 2.2 iniciada)
