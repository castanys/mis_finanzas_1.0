#!/bin/bash

# Script para ejecutar el dashboard Streamlit

cd /home/pablo/apps/mis_finanzas_1.0

# Activar virtual environment
source venv/bin/activate

# Ejecutar Streamlit
streamlit run streamlit_app/app.py --logger.level=warning

# Desactivar venv al salir
deactivate
