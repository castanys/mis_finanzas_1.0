# 🚀 INICIAR BOT — INSTRUCCIONES SIMPLES

## El Bot NO Responde — Solución

El problema es que **necesitas mantener el bot corriendo en una terminal separada** (sin cerrarla).

---

## PASO 1: Abre Una Terminal Nueva

```bash
cd /home/pablo/apps/mis_finanzas_1.0
./run_bot_debug.sh
```

**IMPORTANTE**: Mantén esta terminal abierta. No presiones Ctrl+C (todavía).

Deberías ver:

```
✅ Bot iniciado. Escuchando actualizaciones...
```

---

## PASO 2: En Telegram (Otra Ventana)

1. **Abre Telegram**
2. **Busca**: `@mis_finanzas_castanys_bot`
3. **Presiona**: Click en el botón "Start" o escribe `/start`
4. **Espera 2-3 segundos**

---

## PASO 3: Verifica la Terminal (Paso 1)

Deberías ver un log como:

```
👤 /start recibido de Pablo (ID: 123456789)
```

Y en Telegram recibirás un mensaje con tu `user_id`.

**Copia ese número** (ej: `123456789`).

---

## PASO 4: Actualiza .env

Abre **otra terminal** (no la del bot):

```bash
# Reemplaza 123456789 con el user_id que recibiste
cd /home/pablo/apps/mis_finanzas_1.0
sed -i 's/^TELEGRAM_USER_ID=$/TELEGRAM_USER_ID=123456789/' .env

# Verifica que se guardó
grep TELEGRAM_USER_ID .env
```

---

## PASO 5: Reinicia el Bot

En la **primera terminal** (donde corre el bot):

1. **Presiona**: `Ctrl+C` (una sola vez)
2. **Ejecuta**: `./run_bot_debug.sh`

Deberías ver:

```
📅 Scheduler configurado: Push diario a 08:00
```

---

## PASO 6: Prueba en Telegram

En Telegram, envía:

```
/resumen
```

**El bot debe responder en 5-10 segundos** con tu análisis financiero.

---

## ✅ Si ves que el bot responde a `/resumen`

¡TODO FUNCIONA! 🎉

Ahora el bot te enviará automáticamente un análisis a las **08:00 AM** cada día.

---

## ❌ Si el bot NO responde

1. **Verifica que la terminal sigue corriendo** (debe decir `Escuchando actualizaciones...`)
2. **Espera 5 segundos** (a veces tarda un poco)
3. **Intenta de nuevo** con `/resumen`

Si sigue sin funcionar:
- Ver `TEST_BOT.md` para debugging más detallado
- Ver `TELEGRAM_SETUP.md` para instalación completa

---

## 📝 RESUMEN EN 3 LÍNEAS

1. Terminal #1: `./run_bot_debug.sh` (MANTÉN ABIERTA)
2. Telegram: `/start` al bot @mis_finanzas_castanys_bot
3. Copia user_id → Terminal #2: `sed -i 's/^TELEGRAM_USER_ID=$/TELEGRAM_USER_ID=<id>/' .env` → Reinicia bot

**¡LISTO!** 🚀
