# Bot de Telegram — Asesor Financiero 🤖

Sistema automático de seguimiento financiero con push diario a las 8:00 AM.

## ¿Qué hace?

- **Push diario (8:00 AM)**: Análisis de tu situación financiera con recomendaciones personalizadas
- **Comandos on-demand**:
  - `/resumen` — Análisis completo del mes actual
  - `/presupuestos` — Estado de presupuestos por categoría
  - `/cargos` — Cargos extraordinarios próximos
  - `/ayuda` — Ver todos los comandos

## Instalación

### 1. Crear el bot en Telegram

1. Abre Telegram, busca **@BotFather**
2. Envía `/start`
3. Envía `/newbot`
4. Elige un nombre (ej: "Mi Asesor Financiero")
5. Elige un username (ej: `mis_finanzas_bot`)
6. **BotFather te dará un token** — cópialo

### 2. Configurar variables de entorno

Copia `.env.example` a `.env`:

```bash
cp .env.example .env
```

Edita `.env` y añade tu token:

```
TELEGRAM_BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh
```

### 3. Instalar dependencias

```bash
pip install python-telegram-bot apscheduler anthropic requests
```

### 4. Obtener tu User ID

En una terminal:

```bash
export TELEGRAM_BOT_TOKEN='tu_token_aqui'
python3 bot_telegram.py
```

El bot se iniciará. En Telegram, busca tu bot por username (ej: `@mis_finanzas_bot`) y envía `/start`.

El bot te mostrará tu **user_id** (ej: `123456789`).

Cópialo en `.env`:

```
TELEGRAM_USER_ID=123456789
```

### 5. Iniciar el bot

```bash
# Cargar variables de entorno
source venv/bin/activate
export $(cat .env | xargs)

# Ejecutar bot
python3 bot_telegram.py
```

El bot estará escuchando. Prueba `/resumen` en Telegram.

## Configuración Avanzada

### LLM — Generación de mensajes

El bot intenta usar un LLM en este orden:

#### Opción 1: Qwen local (Ollama) — Recomendado 🟢

Más rápido, sin costo, privacidad.

**Setup:**

1. Instala Ollama: https://ollama.ai
2. Descarga modelo Qwen:

```bash
ollama pull qwen2:1.5b-instruct
```

3. En otra terminal, inicia Ollama:

```bash
ollama serve
```

4. El bot automáticamente usará Qwen (sin config adicional)

#### Opción 2: Claude API — Fallback

Si Qwen no está disponible, usa Claude (requiere API key).

**Setup:**

1. Obtén tu API key en https://console.anthropic.com/
2. Añade a `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

#### Opción 3: Prompt crudo

Si ambos fallan, el bot envía el análisis sin procesar por LLM.

### Hora del push diario

Por defecto: 8:00 AM. Cambiar en `.env`:

```
PUSH_HOUR=8
PUSH_MINUTE=0
```

Ejemplos:
- `PUSH_HOUR=7 PUSH_MINUTE=30` → 7:30 AM
- `PUSH_HOUR=20 PUSH_MINUTE=0` → 8:00 PM (20:00)

### Ejecutar el bot en background (Linux/Mac)

```bash
# Crear script
cat > run_bot.sh << 'EOF'
#!/bin/bash
cd /home/pablo/apps/mis_finanzas_1.0
source venv/bin/activate
export $(cat .env | xargs)
python3 bot_telegram.py >> logs/bot.log 2>&1
EOF

chmod +x run_bot.sh

# Ejecutar en background
nohup ./run_bot.sh &

# Ver logs
tail -f logs/bot.log
```

### Ejecutar el bot con systemd (Linux)

Crear `/etc/systemd/system/mis-finanzas-bot.service`:

```ini
[Unit]
Description=Bot Telegram - Asesor Financiero
After=network.target

[Service]
Type=simple
User=pablo
WorkingDirectory=/home/pablo/apps/mis_finanzas_1.0
Environment="PATH=/home/pablo/apps/mis_finanzas_1.0/venv/bin"
EnvironmentFile=/home/pablo/apps/mis_finanzas_1.0/.env
ExecStart=/home/pablo/apps/mis_finanzas_1.0/venv/bin/python3 bot_telegram.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mis-finanzas-bot
sudo systemctl start mis-finanzas-bot

# Ver estado
sudo systemctl status mis-finanzas-bot

# Ver logs
sudo journalctl -u mis-finanzas-bot -f
```

## Estructura de archivos

```
mis_finanzas_1.0/
├── bot_telegram.py          ← Bot principal
├── advisor.py               ← Análisis financiero + prompts
├── .env                     ← Configuración (no commitar)
├── .env.example             ← Template de configuración
├── README_BOT.md            ← Este archivo
├── finsense.db              ← BD (presupuestos + cargos_extraordinarios)
├── streamlit_app/
│   └── pages/
│       └── 06_🎯_Presupuestos.py  ← Página Streamlit
└── logs/
    └── bot.log              ← Logs del bot
```

## Solución de problemas

### ❌ `ModuleNotFoundError: No module named 'telegram'`

```bash
pip install python-telegram-bot apscheduler
```

### ❌ Bot no recibe push a las 8:00

1. Verifica que `TELEGRAM_USER_ID` está configurado:

```bash
echo $TELEGRAM_USER_ID
```

2. Verifica logs:

```bash
tail -f logs/bot.log | grep "Push"
```

3. La zona horaria puede ser diferente. Verifica:

```bash
python3 -c "from datetime import datetime; print(datetime.now())"
```

### ❌ `ConnectionError` al llamar a Qwen

Ollama no está corriendo:

```bash
ollama serve
```

O está en otra dirección — edita `bot_telegram.py`:

```python
response = requests.post(
    "http://mi-servidor:11434/api/generate",  # Cambiar aquí
    ...
)
```

### ❌ Claude API no funciona

- Verifica API key: `echo $ANTHROPIC_API_KEY`
- Verifica saldo: https://console.anthropic.com/account/billing

## Comandos del bot

### `/start`
Bienvenida e información de configuración.

### `/resumen`
Análisis completo:
- Estado de presupuestos
- Categorías en plan/naranja/rojo
- Cargos extraordinarios próximos
- Recomendaciones del LLM

### `/presupuestos`
Desglose de presupuestos vs gastos actuales:
- Presupuesto total y gasto total
- Cada categoría con estado (verde/naranja/rojo)

### `/cargos`
Lista de cargos extraordinarios próximos con:
- Descripción
- Importe
- Fecha estimada
- Días hasta el aviso

### `/ayuda`
Ver todos los comandos.

## Arquitectura

```
Bot Telegram
    ↓
advisor.py (análisis financiero)
    ↓
finsense.db (presupuestos + cargos_extraordinarios + transacciones)
    ↓
LLM (Qwen/Claude)
    ↓
Mensaje personalizado
    ↓
Telegram API
    ↓
Usuario 📱
```

## Notas

- El bot usa **Async/Await** para manejo de múltiples usuarios
- Push automático usa **APScheduler** con trigger CRON
- Análisis financiero se cachea cada 1 hora (performance)
- Todos los logs van a `logs/bot.log` (crear si no existe)

## Próximos pasos

- [ ] Dashboard web en Streamlit (ya existe: `06_🎯_Presupuestos.py`)
- [ ] Notificaciones por email (similar a Telegram)
- [ ] Exportación de reportes mensuales
- [ ] Análisis predictivo de ahorro

---

**Última actualización**: 2026-02-22
