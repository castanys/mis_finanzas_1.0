#!/bin/bash
# Script para iniciar el bot de Telegram

cd /home/pablo/apps/mis_finanzas_1.0

# Cargar variables de entorno
set -a
source .env
set +a

# Verificar que el token está configurado
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN no configurado en .env"
    exit 1
fi

# Verificar venv
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Error: venv no encontrado"
    exit 1
fi

# Activar venv
source venv/bin/activate

# Iniciar bot
echo "🚀 Iniciando bot: mis_finanzas_castanys_bot"
echo "📱 Busca @mis_finanzas_castanys_bot en Telegram"
echo "💬 Envía /start para obtener tu user_id"
echo ""
echo "⏹️  Presiona Ctrl+C para detener"
echo ""

python3 bot_telegram.py
