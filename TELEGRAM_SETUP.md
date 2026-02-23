# 🤖 Setup Bot Telegram — mis_finanzas_castanys_bot

## Estado Actual ✅

- **Token**: Configurado y validado ✓ (conecta a Telegram API correctamente)
- **Bot Name**: `@mis_finanzas_castanys_bot` ✓
- **Dependencias**: Instaladas ✓ (python-telegram-bot 22.6, apscheduler)
- **Startup Script**: Arreglado ✓ (S33: carga correcta de `.env`)
- **User ID**: ⏳ PENDIENTE (usuario debe enviar `/start` al bot)

## ⏳ Estado: Completado al 95% — Falta Obtener User ID

El bot está **100% listo técnicamente**. Solo falta que obtengamos tu `user_id` de Telegram enviando `/start` al bot. Esto toma **< 5 minutos**.

## Próximos Pasos — 5 minutos

### 1. Iniciar el bot (en terminal)

```bash
cd /home/pablo/apps/mis_finanzas_1.0
./start_bot.sh
```

Verás logs indicando que el bot está escuchando (línea: `✅ Bot iniciado. Escuchando actualizaciones...`). **Mantén esta terminal abierta.**

### 2. Abrir Telegram y buscar el bot

1. Abre **Telegram** en otro dispositivo/ventana
2. Busca: **`@mis_finanzas_castanys_bot`**
3. Dale click en "Start" o envía `/start`

### 3. Obtener tu User ID

El bot responderá con un mensaje tipo:

```
Hola Pablo 👋

Soy tu asesor financiero de Telegram. Puedo:
- 📅 Enviarte un análisis diario a las 08:00 AM
- 📊 Responder preguntas sobre tu situación financiera
- 💰 Recordarte cargos extraordinarios próximos

**Comandos disponibles:**
/resumen — Análisis del mes actual
/presupuestos — Estado de presupuestos
/cargos — Cargos extraordinarios próximos
/ayuda — Ver esta ayuda

**Para configurar:**
- Guarda tu user_id: `123456789`
- Configura la variable: `export TELEGRAM_USER_ID=123456789`

¡Empecemos! 🚀
```

**Copia ese número de user_id** (ej: `123456789`) de la sección "Para configurar"

### 4. Configurar .env

Edita `.env` y reemplaza la línea:

```
TELEGRAM_USER_ID=
```

Por (reemplaza `123456789` por tu user_id real):

```
TELEGRAM_USER_ID=123456789
```

**Método 1: Editar manualmente**
```bash
nano /home/pablo/apps/mis_finanzas_1.0/.env
# Busca TELEGRAM_USER_ID= y reemplaza con tu número
# Ctrl+O para guardar, Ctrl+X para salir
```

**Método 2: Con sed (una línea)**
```bash
sed -i 's/^TELEGRAM_USER_ID=$/TELEGRAM_USER_ID=123456789/' /home/pablo/apps/mis_finanzas_1.0/.env
```

### 5. Reiniciar el bot

Presiona `Ctrl+C` en la terminal del bot para detenerlo, y vuélvelo a iniciar:

```bash
./start_bot.sh
```

Verás el log: `⏰ Push automático configurado para las 08:00 AM`

### 6. Verificar que funciona

En Telegram, envía estos comandos al bot:

- `/resumen` — Ver análisis del mes actual
- `/presupuestos` — Estado de presupuestos
- `/cargos` — Cargos extraordinarios próximos
- `/ayuda` — Ver todos los comandos

El bot debe responder con análisis financiero dentro de 5-10 segundos.

**Si todo funciona**: ¡El bot está listo para enviar notificaciones diarias a las 8:00 AM! 🎉

## Iniciar el Bot (Background)

### Opción A: Terminal en primer plano

```bash
cd /home/pablo/apps/mis_finanzas_1.0
./start_bot.sh
```

Verás logs en la terminal. Presiona `Ctrl+C` para detener.

### Opción B: Background con systemd (recomendado)

```bash
# Crear servicio systemd
sudo tee /etc/systemd/system/mis-finanzas-bot.service > /dev/null << 'EOF'
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
EOF

# Activar servicio
sudo systemctl daemon-reload
sudo systemctl enable mis-finanzas-bot
sudo systemctl start mis-finanzas-bot

# Ver estado
sudo systemctl status mis-finanzas-bot

# Ver logs
sudo journalctl -u mis-finanzas-bot -f
```

### Opción C: Background con nohup

```bash
cd /home/pablo/apps/mis_finanzas_1.0
nohup ./start_bot.sh > logs/bot.log 2>&1 &
echo $! > logs/bot.pid

# Ver logs en tiempo real
tail -f logs/bot.log

# Detener bot
kill $(cat logs/bot.pid)
```

## Push Automático Diario

Una vez configurado `TELEGRAM_USER_ID`, recibirás un mensaje automático cada día a las **8:00 AM** con:

- 📊 Estado de presupuestos (categorías en plan/naranja/rojo)
- 📅 Cargos extraordinarios próximos
- 💡 Recomendaciones personalizadas (generadas por IA)

### Cambiar hora del push

Edita `.env`:

```
PUSH_HOUR=8    # Hora (0-23)
PUSH_MINUTE=0  # Minutos (0-59)
```

Ejemplos:
- `PUSH_HOUR=7 PUSH_MINUTE=30` → 7:30 AM
- `PUSH_HOUR=20 PUSH_MINUTE=0` → 8:00 PM

## Configuración Opcional — LLM (IA)

El bot genera mensajes personalizados con IA. Por defecto intenta:

1. **Qwen local** (rápido, sin costo) ← Recomendado
2. **Claude API** (fallback)
3. **Prompt crudo** (si ambos fallan)

### Activar Qwen local (Ollama)

```bash
# Instalar Ollama: https://ollama.ai
# Luego descargar modelo:
ollama pull qwen2:1.5b-instruct

# En otra terminal, iniciar Ollama:
ollama serve

# El bot automáticamente usará Qwen (sin config adicional)
```

### Activar Claude (fallback)

1. Obtén API key en https://console.anthropic.com/
2. Edita `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Comandos del Bot

| Comando | Descripción |
|---------|-------------|
| `/start` | Bienvenida e info de setup |
| `/resumen` | Análisis completo del mes |
| `/presupuestos` | Estado de presupuestos |
| `/cargos` | Cargos extraordinarios próximos |
| `/ayuda` | Ver todos los comandos |

## Solución de Problemas

### ❌ Bot no responde

1. Verifica que está corriendo:
   ```bash
   ps aux | grep bot_telegram.py
   ```

2. Verifica logs:
   ```bash
   tail -f logs/bot.log
   ```

3. Verifica token en `.env`:
   ```bash
   cat .env | grep TELEGRAM_BOT_TOKEN
   ```

### ❌ No recibo push a las 8:00 AM

1. Verifica `TELEGRAM_USER_ID` en `.env`:
   ```bash
   cat .env | grep TELEGRAM_USER_ID
   ```

2. Verifica hora del sistema:
   ```bash
   date
   ```

3. Revisa logs (busca "Push"):
   ```bash
   grep "Push" logs/bot.log
   ```

### ❌ "ConnectionError" o "Failed to connect"

El bot necesita internet. Verifica:

```bash
ping 8.8.8.8
```

### ❌ "Qwen not available"

Instala Ollama y descarga el modelo:

```bash
ollama pull qwen2:1.5b-instruct
ollama serve  # En otra terminal
```

## Archivos Importantes

```
mis_finanzas_1.0/
├── .env                      ← Tu configuración (NO commitar)
├── bot_telegram.py           ← Bot principal
├── advisor.py                ← Análisis financiero
├── start_bot.sh              ← Script para iniciar
├── finsense.db               ← BD (presupuestos + cargos)
├── logs/
│   └── bot.log               ← Logs del bot
└── README_BOT.md             ← Guía detallada
```

## Próximos Pasos

1. ✅ Token configurado
2. ⏳ **Buscar bot en Telegram y enviar /start**
3. ⏳ Copiar user_id a `.env`
4. ⏳ Iniciar bot: `./start_bot.sh`
5. ⏳ Probar comandos
6. ⏳ Configurar systemd para ejecución en background

---

**¿Preguntas?** Ver `README_BOT.md` para guía completa.

**Última actualización**: 2026-02-22
