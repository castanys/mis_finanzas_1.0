# 🧪 Test Bot Telegram — Guía paso a paso

## Problema Actual

El bot se inicia correctamente (`✅ Bot iniciado. Escuchando actualizaciones...`) pero:
- No responde a `/start` cuando lo envías
- Puede ser porque el bot se está ejecutando en una terminal que cierra inmediatamente

## Solución: Ejecutar en Terminal Separada (SIN TIMEOUT)

### Paso 1: Terminal #1 — Iniciar el bot

Abre **una nueva terminal** y ejecuta:

```bash
cd /home/pablo/apps/mis_finanzas_1.0
./start_bot.sh
```

Deberías ver:

```
2026-02-23 19:36:08,004 — WARNING — ⚠️ TELEGRAM_USER_ID no configurado...
2026-02-23 19:36:08,004 — INFO — 🚀 Iniciando bot de Telegram...
2026-02-23 19:36:08,236 — INFO — HTTP Request: POST https://api.telegram.org/...
2026-02-23 19:36:08,237 — INFO — ✅ Bot iniciado. Escuchando actualizaciones...
```

**IMPORTANTE**: Mantén esta terminal abierta. No presiones Ctrl+C. El bot necesita estar corriendo continuamente.

### Paso 2: Telegram — Enviar /start

En **otra ventana/dispositivo** con Telegram:

1. Busca: `@mis_finanzas_castanys_bot`
2. Presiona "Start" o envía: `/start`
3. **Espera 2-3 segundos**

### Paso 3: Verifica la Terminal #1

En la terminal donde corre el bot, deberías ver logs como:

```
2026-02-23 19:36:20,123 — INFO — 👤 /start recibido de Pablo (ID: 123456789)
```

### Paso 4: Telegram recibirá respuesta

El bot responderá en Telegram con:

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

### Paso 5: Copiar user_id y actualizar .env

Una vez recibas el mensaje, **copia el número** de user_id (ej: `123456789`).

En **otra terminal** (Terminal #2), ejecuta:

```bash
# Reemplaza 123456789 con tu user_id real
sed -i 's/^TELEGRAM_USER_ID=$/TELEGRAM_USER_ID=123456789/' /home/pablo/apps/mis_finanzas_1.0/.env

# Verifica que se actualizó
grep TELEGRAM_USER_ID /home/pablo/apps/mis_finanzas_1.0/.env
```

### Paso 6: Reiniciar el bot

En la Terminal #1:
1. Presiona `Ctrl+C` para detener el bot
2. Ejecuta de nuevo: `./start_bot.sh`

Deberías ver un nuevo log:

```
2026-02-23 19:36:30,123 — INFO — 📅 Scheduler configurado: Push diario a 08:00
```

### Paso 7: Verificar que funciona

En Telegram, envía:

```
/resumen
```

El bot debe responder en **5-10 segundos** con análisis de tu presupuesto.

---

## 🚨 Troubleshooting

### El bot no responde a comandos

- ✅ Verifica que `./start_bot.sh` está corriendo (mira Terminal #1)
- ✅ Espera 5 segundos después de enviar comando
- ✅ Verifica que el user_id está correcto: `grep TELEGRAM_USER_ID .env`

### El bot dice "Error: Cannot close a running event loop"

- ✅ **IGNORAR este error** — es una advertencia de Python al interrumpir el event loop
- ✅ Presiona `Ctrl+C` una sola vez y espera 3 segundos antes de volver a iniciar

### El bot no inicia en absoluto

- ✅ Verifica que `.env` existe: `cat /home/pablo/apps/mis_finanzas_1.0/.env`
- ✅ Verifica que `TELEGRAM_BOT_TOKEN` está correcto
- ✅ Verifica que `venv` existe: `ls /home/pablo/apps/mis_finanzas_1.0/venv/bin/python3`

---

## 📝 Resumen de Lo Que Debe Pasar

```
Terminal #1 (Bot corriendo):
./start_bot.sh
→ ✅ Bot iniciado. Escuchando actualizaciones...

Telegram:
/start
→ 👤 /start recibido de Pablo (ID: 123456789)
→ Mensaje de bienvenida con user_id

Terminal #2:
sed -i 's/^TELEGRAM_USER_ID=$/TELEGRAM_USER_ID=123456789/' .env

Terminal #1:
Ctrl+C (detener)
./start_bot.sh (reiniciar)
→ 📅 Scheduler configurado: Push diario a 08:00

Telegram:
/resumen
→ Análisis financiero en 5-10 segundos
```

**¿Ves que el bot responde a `/resumen`? → ¡TODO FUNCIONA!** 🎉
