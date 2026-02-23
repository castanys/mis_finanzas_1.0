#!/bin/bash

# Script para iniciar el bot con logging completo
# USO: ./run_bot_debug.sh

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║           🤖 BOT TELEGRAM — INICIANDO CON DEBUG                               ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""

cd /home/pablo/apps/mis_finanzas_1.0

# Verificar .env
if [ ! -f .env ]; then
    echo "❌ ERROR: .env no encontrado"
    exit 1
fi

# Cargar variables
set -a
source .env
set +a

# Verificar token
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ ERROR: TELEGRAM_BOT_TOKEN no configurado en .env"
    exit 1
fi

echo "✓ Token: ${TELEGRAM_BOT_TOKEN:0:20}..."
echo "✓ User ID: ${TELEGRAM_USER_ID:-'(VACÍO — se obtiene con /start)'}"
echo ""

# Activar venv
source venv/bin/activate

echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║  INSTRUCCIONES:                                                                ║"
echo "║                                                                                ║"
echo "║  1. El bot está corriendo (verás 'Bot iniciado' abajo)                        ║"
echo "║  2. Abre Telegram en otra ventana/dispositivo                                 ║"
echo "║  3. Busca: @mis_finanzas_castanys_bot                                        ║"
echo "║  4. Envía: /start                                                            ║"
echo "║  5. Espera 2-3 segundos a que responda                                       ║"
echo "║  6. Verás los logs aquí cuando el bot reciba tu mensaje                      ║"
echo "║  7. El bot te dará tu user_id                                                ║"
echo "║  8. Presiona Ctrl+C para detener este script                                 ║"
echo "║                                                                                ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "⏳ Iniciando bot..."
echo ""

# Ejecutar bot
python3 -u bot_telegram.py
