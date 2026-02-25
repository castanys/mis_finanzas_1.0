# 🚀 EMPIEZA AQUÍ — mis_finanzas_1.0

## ¿Qué se completó en esta sesión?

Hemos construido un **sistema completo de seguimiento financiero** con:

1. **Dashboard Streamlit** — Ve tus presupuestos vs gastos en tiempo real
2. **Bot Telegram** — Recibe análisis diario a las 8:00 AM + consulta on-demand
3. **Análisis con IA** — Recomendaciones personalizadas (Qwen local o Claude)

## 🎯 Próximos Pasos (5 minutos)

### Paso 1: Abre Telegram

Busca el bot: **`@mis_finanzas_castanys_bot`**

### Paso 2: Envía `/start`

El bot responderá con:
```
Hola Pablo 👋

Soy tu asesor financiero. Puedo:
- 📅 Enviarte un análisis diario a las 08:00 AM
- 📊 Responder preguntas sobre tu situación
- 💰 Recordarte cargos próximos

Para configurar:
- Guarda tu user_id: 123456789
```

### Paso 3: Copia tu User ID

El número que ves (ej: `123456789`) es tu **user_id**.

### Paso 4: Edita `.env`

```bash
nano /home/pablo/apps/mis_finanzas_1.0/.env
```

Busca la línea:
```
TELEGRAM_USER_ID=
```

Y reemplázala por:
```
TELEGRAM_USER_ID=123456789
```

(usa el número que copiaste en paso 3)

### Paso 5: Inicia el bot

```bash
cd /home/pablo/apps/mis_finanzas_1.0
./start_bot.sh
```

Verás:
```
🚀 Iniciando bot: mis_finanzas_castanys_bot
📱 Busca @mis_finanzas_castanys_bot en Telegram
💬 Envía /start para obtener tu user_id

⏹️  Presiona Ctrl+C para detener
```

### Paso 6: Prueba los comandos en Telegram

Envía estos comandos al bot:

- `/resumen` — Análisis completo del mes actual
- `/presupuestos` — Estado de presupuestos por categoría
- `/cargos` — Cargos extraordinarios próximos
- `/ayuda` — Ver todos los comandos

---

## 📚 Documentación

- **TELEGRAM_SETUP.md** — Guía rápida
- **README_BOT.md** — Guía completa con troubleshooting
- **SESSION_25_SUMMARY.txt** — Resumen técnico
- **.env.example** — Variables de configuración

---

## 📊 Qué hay en el bot

### Análisis Automático (Diario a las 8:00 AM)

El bot te envía:
- Estado de presupuestos (categorías en plan, naranja, rojo)
- Cargos extraordinarios próximos
- Recomendaciones personalizadas (IA)
- Ocasional humor (~1 chiste/semana)

### Consultas On-Demand

- `/resumen` — Análisis completo mes actual
- `/presupuestos` — Desglose por categoría
- `/cargos` — Alertas de cargos próximos
- `/ayuda` — Ver comandos

### Dashboard Streamlit

Accede a `streamlit_app/pages/06_🎯_Presupuestos.py` para:
- Ver barras de progreso de presupuestos
- Editar presupuestos desde la UI
- Ver calendario de cargos extraordinarios

---

## 💡 Ejemplo

**Febrero 2026** (mes actual):

```
Presupuesto variables: €660
Gasto real:           €924 (140%)
```

**Bot te dirá:**

> "Pablo, febrero va complicado — estamos 40% por encima del presupuesto. 
> Probablemente por la transferencia a Yolanda (Cuenta Común, €400).
> 
> Categorías en plan: ✅
> Cargos próximos: Línea Directa en 6 días (€341).
> 
> Sugerencia: Revisa si hay gastos discrecionales que reducir antes de fin de mes."

---

## 🔧 Configuración Avanzada (Opcional)

### Cambiar hora del push automático

Edita `.env`:
```
PUSH_HOUR=8    # Hora (0-23)
PUSH_MINUTE=0  # Minutos (0-59)
```

### Activar Qwen local (IA más rápida)

```bash
# Instala Ollama: https://ollama.ai
ollama pull qwen2:1.5b-instruct
ollama serve  # En otra terminal
```

### Activar Claude API (fallback)

```bash
# Obtén API key: https://console.anthropic.com/
# Edita .env:
ANTHROPIC_API_KEY=sk-ant-...
```

### Ejecutar bot en background (systemd)

Ver `README_BOT.md` para instrucciones completas.

---

## ✅ Verificación

¿Todo configurado? Verifica:

```bash
# 1. Token válido
cat .env | grep TELEGRAM_BOT_TOKEN

# 2. User ID configurado
cat .env | grep TELEGRAM_USER_ID

# 3. Dependencias instaladas
source venv/bin/activate
python3 -c "import telegram, apscheduler; print('✅ OK')"

# 4. BD con presupuestos
sqlite3 finsense.db "SELECT COUNT(*) FROM presupuestos;"
```

---

## 🆘 Problemas?

- **Bot no responde**: Ver `README_BOT.md` sección "Solución de problemas"
- **Error de token**: Verifica `.env` y el token de @BotFather
- **No recibo push**: Verifica que `TELEGRAM_USER_ID` está configurado y el bot está corriendo

---

## 📊 Estado Actual (Febrero 2026)

| Concepto | Valor |
|----------|-------|
| Presupuesto variables | €660 |
| Gasto real | €924 |
| % Utilizado | 140% |
| Próximo cargo | Línea Directa €341 (28 feb) |
| Días restantes mes | 6 |

---

## 🎉 ¡Listo!

Todo está preparado. Solo necesitas:

1. Buscar el bot en Telegram
2. Enviar `/start`
3. Copiar tu user_id
4. Guardar en `.env`
5. Ejecutar `./start_bot.sh`

**¡Que disfrutes tu asesor financiero! 🤖**

---

Última actualización: 2026-02-22
