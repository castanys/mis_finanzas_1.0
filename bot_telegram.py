"""
bot_telegram.py — Bot de Telegram para seguimiento financiero
Versión corregida para python-telegram-bot v22.x
Envía push diario (12:00) + mensual (día 1, 8:00) + anual (1 enero, 8:00) + responde consultas on-demand
Integración con advisor.py para análisis y LLM (Qwen/Claude)
Sistema 3-level de mensajes con ángulos aleatorios (BLOQUE 3)
"""

import os
import sys
import logging
from datetime import datetime, time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s — %(levelname)s — %(message)s'
)
logger = logging.getLogger(__name__)

# Importar telegram
try:
    from telegram import Update
    from telegram.ext import (
        Application, 
        CommandHandler, 
        MessageHandler, 
        filters,
        ContextTypes,
        ApplicationBuilder
    )
    from telegram.error import TelegramError
except ImportError:
    logger.error("❌ python-telegram-bot no instalado. Instala: pip install python-telegram-bot")
    sys.exit(1)

# Importar advisor
try:
    from advisor import (
        obtener_mensaje_para_bot,
        obtener_contexto_json,
        get_mes_nombre,
        analizar_presupuestos,
        generate_daily_message,
        generate_monthly_message,
        generate_annual_message
    )
except ImportError:
    logger.error("❌ advisor.py no encontrado en la ruta")
    sys.exit(1)

# ===== CONFIGURACIÓN =====

# Token del bot (obtener de @BotFather en Telegram)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", None)
if not TELEGRAM_TOKEN:
    logger.warning("⚠️ TELEGRAM_BOT_TOKEN no configurado")
    logger.info("   Configura: export TELEGRAM_BOT_TOKEN='tu_token_aqui'")
    logger.info("   O añade a .env: TELEGRAM_BOT_TOKEN=tu_token_aqui")
    sys.exit(1)

# ID del usuario (obtener del bot)
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID", None)
if not TELEGRAM_USER_ID:
    logger.warning("⚠️ TELEGRAM_USER_ID no configurado (se pedirá al usar /start)")

# Horas del push automático (BLOQUE 3: Sistema 3-level)
PUSH_HOUR_DIARIO = int(os.getenv("PUSH_HOUR_DIARIO", "12"))
PUSH_MINUTE_DIARIO = int(os.getenv("PUSH_MINUTE_DIARIO", "0"))
PUSH_HOUR_MENSUAL = int(os.getenv("PUSH_HOUR_MENSUAL", "8"))
PUSH_MINUTE_MENSUAL = int(os.getenv("PUSH_MINUTE_MENSUAL", "0"))

# ===== FUNCIONES DE LLM =====

def generar_mensaje_con_llm(prompt: str) -> str:
    """
    Llama al LLM (Qwen local o Claude API) para generar el mensaje
    
    Intenta en este orden:
    1. Qwen local (Ollama)
    2. Claude via API (fallback)
    3. Devuelve prompt crudo si ambos fallan
    """
    
    # Intentar Qwen local primero
    try:
        import requests
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2:1.5b-instruct",
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7
            },
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ Mensaje generado con Qwen")
            return result.get("response", prompt)
    except Exception as e:
        logger.warning(f"⚠️ Qwen no disponible: {e}")
    
    # Fallback: Claude API
    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            logger.info("✅ Mensaje generado con Claude")
            return message.content[0].text
    except Exception as e:
        logger.warning(f"⚠️ Claude no disponible: {e}")
    
    # Fallback: Devolver prompt crudo
    logger.warning("⚠️ Ningún LLM disponible. Devolviendo análisis crudo.")
    return f"**Análisis Financiero — {get_mes_nombre(datetime.now().month).capitalize()}**\n\n{prompt}"

# ===== HANDLERS DE COMANDOS =====

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja /start — registra el user_id"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Usuario"
    
    logger.info(f"👤 /start recibido de {user_name} (ID: {user_id})")
    
    message = f"""
Hola {user_name} 👋

Soy tu asesor financiero de Telegram. Puedo:
- 📅 Enviarte análisis cada día a las {PUSH_HOUR_DIARIO:02d}:{PUSH_MINUTE_DIARIO:02d} (contenido variado)
- 📊 Cierre mensual el día 1 a las {PUSH_HOUR_MENSUAL:02d}:{PUSH_MINUTE_MENSUAL:02d}
- 🎯 Revisión anual el 1 de enero
- 💬 Responder preguntas on-demand

**Comandos disponibles:**
/resumen — Análisis del mes actual
/presupuestos — Estado de presupuestos
/cargos — Cargos extraordinarios próximos
/ayuda — Ver esta ayuda

**Para configurar:**
- Guarda tu user_id: `{user_id}`
- Configura la variable: `export TELEGRAM_USER_ID={user_id}`

¡Empecemos! 🚀
"""
    
    await update.message.reply_text(message)

async def resumen_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja /resumen — envía análisis del mes actual (usa nuevo sistema)"""
    user_name = update.effective_user.first_name or "Usuario"
    logger.info(f"📊 /resumen solicitado por {user_name}")
    
    await update.message.reply_text("⏳ Analizando tu situación financiera...")
    
    try:
        # Generar prompt con sistema 3-level (elegir diario)
        prompt = generate_daily_message()
        
        # Llamar al LLM
        mensaje = generar_mensaje_con_llm(prompt)
        
        # Enviar respuesta
        await update.message.reply_text(mensaje)
        logger.info(f"✅ Resumen enviado a {user_name}")
    
    except Exception as e:
        logger.error(f"❌ Error en /resumen: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def presupuestos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja /presupuestos — estado de presupuestos"""
    user_name = update.effective_user.first_name or "Usuario"
    logger.info(f"💰 /presupuestos solicitado por {user_name}")
    
    try:
        stats = analizar_presupuestos()
        
        mensaje = f"""
**Presupuestos — {stats['mes_nombre'].capitalize()}**

📊 **Resumen General:**
• Presupuesto total: €{stats['total_presupuesto']:.2f}
• Gastos reales: €{stats['total_gasto']:.2f}
• Diferencia: €{stats['diferencia_total']:.2f}
• Progreso: {stats['pct_total']:.1f}%

✅ **Dentro del plan:**
"""
        
        if stats['categorias_dentro_plan']:
            for cat in stats['categorias_dentro_plan']:
                mensaje += f"\n• {cat['cat1']} → {cat['cat2']}: €{cat['gasto']:.2f} / €{cat['presupuesto']:.2f} ({cat['pct']:.0f}%)"
        else:
            mensaje += "\n*Todas las categorías tienen algún nivel de estrés*"
        
        if stats['categorias_en_naranja']:
            mensaje += "\n\n⚠️ **Naranja (80-100%):**"
            for cat in stats['categorias_en_naranja']:
                mensaje += f"\n• {cat['cat1']} → {cat['cat2']}: €{cat['gasto']:.2f} / €{cat['presupuesto']:.2f} ({cat['pct']:.0f}%)"
        
        if stats['categorias_en_rojo']:
            mensaje += "\n\n🔴 **Rojo (>100%):**"
            for cat in stats['categorias_en_rojo']:
                mensaje += f"\n• {cat['cat1']} → {cat['cat2']}: €{cat['gasto']:.2f} / €{cat['presupuesto']:.2f} ({cat['pct']:.0f}%)"
        
        await update.message.reply_text(mensaje)
        logger.info(f"✅ Presupuestos enviados a {user_name}")
    
    except Exception as e:
        logger.error(f"❌ Error en /presupuestos: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def cargos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja /cargos — cargos extraordinarios próximos"""
    user_name = update.effective_user.first_name or "Usuario"
    logger.info(f"📅 /cargos solicitado por {user_name}")
    
    try:
        from advisor import get_cargos_extraordinarios_proximos
        cargos = get_cargos_extraordinarios_proximos()
        
        if not cargos:
            mensaje = "✅ No hay cargos extraordinarios próximos. ¡Respira! 🎉"
        else:
            mensaje = "📅 **Cargos Extraordinarios Próximos**\n"
            for cargo in cargos:
                mensaje += f"\n💳 {cargo['descripcion']}\n"
                mensaje += f"   • Importe: €{cargo['importe']:.2f}\n"
                mensaje += f"   • Fecha: {cargo['fecha_cargo']}\n"
                mensaje += f"   • En: {cargo['dias_para_aviso']} días\n"
        
        await update.message.reply_text(mensaje)
        logger.info(f"✅ Cargos enviados a {user_name}")
    
    except Exception as e:
        logger.error(f"❌ Error en /cargos: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def ayuda_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja /ayuda"""
    mensaje = f"""
**Comandos Disponibles:**

/resumen — Análisis completo del mes con ángulo aleatorio
/presupuestos — Estado de presupuestos por categoría
/cargos — Cargos extraordinarios próximos
/ayuda — Ver este mensaje

**Sobre este bot:**
Soy tu asesor financiero. Te envío análisis en 3 cadencias:

📅 **Diario ({PUSH_HOUR_DIARIO:02d}:{PUSH_MINUTE_DIARIO:02d})**: Contenido variado (gastos, ritmo, merchant, etc.)
📊 **Mensual (día 1, {PUSH_HOUR_MENSUAL:02d}:{PUSH_MINUTE_MENSUAL:02d})**: Cierre del mes anterior
🎯 **Anual (1 enero)**: Revisión del año

Respondo en español, con tono cercano y sin jerga corporativa.

¿Preguntas? Contacta a Pablo.
"""
    await update.message.reply_text(mensaje)

# ===== PUSH AUTOMÁTICO (SISTEMA 3-LEVEL) =====

async def push_diario(context: ContextTypes.DEFAULT_TYPE):
    """
    Push diario (12:00) — Mensaje con ángulo aleatorio
    Se ejecuta automáticamente via job_queue de python-telegram-bot
    """
    if not TELEGRAM_USER_ID:
        logger.warning("⚠️ TELEGRAM_USER_ID no configurado. Saltando push diario.")
        return
    
    logger.info("📨 Enviando push diario...")
    
    try:
        # Generar prompt con ángulo aleatorio (BLOQUE 3)
        prompt = generate_daily_message()
        
        # Llamar al LLM
        mensaje = generar_mensaje_con_llm(prompt)
        
        # Enviar al usuario
        await context.bot.send_message(
            chat_id=int(TELEGRAM_USER_ID),
            text=mensaje,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Push diario enviado a {TELEGRAM_USER_ID}")
    
    except TelegramError as e:
        logger.error(f"❌ Error enviando push diario (Telegram): {e}")
    except Exception as e:
        logger.error(f"❌ Error enviando push diario: {e}")


async def push_mensual(context: ContextTypes.DEFAULT_TYPE):
    """
    Push mensual (día 1, 8:00) — Cierre del mes anterior
    Se ejecuta automáticamente via job_queue de python-telegram-bot
    """
    if not TELEGRAM_USER_ID:
        logger.warning("⚠️ TELEGRAM_USER_ID no configurado. Saltando push mensual.")
        return
    
    logger.info("📨 Enviando push mensual...")
    
    try:
        # Generar prompt mensual con ángulo rotativo (BLOQUE 3)
        prompt = generate_monthly_message()
        
        # Llamar al LLM
        mensaje = generar_mensaje_con_llm(prompt)
        
        # Enviar al usuario
        await context.bot.send_message(
            chat_id=int(TELEGRAM_USER_ID),
            text=mensaje,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Push mensual enviado a {TELEGRAM_USER_ID}")
    
    except TelegramError as e:
        logger.error(f"❌ Error enviando push mensual (Telegram): {e}")
    except Exception as e:
        logger.error(f"❌ Error enviando push mensual: {e}")


async def push_anual(context: ContextTypes.DEFAULT_TYPE):
    """
    Push anual (1 enero, 8:00) — Revisión del año anterior
    Se ejecuta automáticamente via job_queue de python-telegram-bot
    """
    if not TELEGRAM_USER_ID:
        logger.warning("⚠️ TELEGRAM_USER_ID no configurado. Saltando push anual.")
        return
    
    # Solo ejecutar si es 1 de enero
    hoy = datetime.now()
    if hoy.month != 1 or hoy.day != 1:
        return
    
    logger.info("📨 Enviando push anual...")
    
    try:
        # Generar prompt anual (BLOQUE 3)
        prompt = generate_annual_message()
        
        # Llamar al LLM
        mensaje = generar_mensaje_con_llm(prompt)
        
        # Enviar al usuario
        await context.bot.send_message(
            chat_id=int(TELEGRAM_USER_ID),
            text=mensaje,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Push anual enviado a {TELEGRAM_USER_ID}")
    
    except TelegramError as e:
        logger.error(f"❌ Error enviando push anual (Telegram): {e}")
    except Exception as e:
        logger.error(f"❌ Error enviando push anual: {e}")


async def mensaje_generico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes genéricos"""
    await update.message.reply_text(
        "👋 No entiendo ese comando. Usa /ayuda para ver opciones disponibles."
    )

# ===== INICIALIZACIÓN DEL BOT =====

def main():
    """Inicia el bot con handlers y scheduler — función síncrona"""
    
    logger.info("🚀 Iniciando bot de Telegram (BLOQUE 3: Sistema 3-level)...")
    
    # Crear aplicación
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Registrar handlers de comandos
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("resumen", resumen_handler))
    app.add_handler(CommandHandler("presupuestos", presupuestos_handler))
    app.add_handler(CommandHandler("cargos", cargos_handler))
    app.add_handler(CommandHandler("ayuda", ayuda_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_generico))
    
    # Configurar scheduler para push automático usando job_queue de python-telegram-bot
    if TELEGRAM_USER_ID:
        # Push diario a las 12:00
        hora_push_diario = time(hour=PUSH_HOUR_DIARIO, minute=PUSH_MINUTE_DIARIO)
        app.job_queue.run_daily(
            callback=push_diario,
            time=hora_push_diario,
            name="push_diario"
        )
        logger.info(f"📅 Push diario programado a las {PUSH_HOUR_DIARIO:02d}:{PUSH_MINUTE_DIARIO:02d}")
        
        # Push mensual el día 1 del mes a las 8:00
        hora_push_mensual = time(hour=PUSH_HOUR_MENSUAL, minute=PUSH_MINUTE_MENSUAL)
        app.job_queue.run_monthly(
            callback=push_mensual,
            when=hora_push_mensual,
            day=1,
            name="push_mensual"
        )
        logger.info(f"📅 Push mensual programado para el día 1 a las {PUSH_HOUR_MENSUAL:02d}:{PUSH_MINUTE_MENSUAL:02d}")
        
        # Push anual el 1 de enero (ejecutar diariamente pero solo actúa el 1 de enero)
        hora_push_anual = time(hour=PUSH_HOUR_MENSUAL, minute=PUSH_MINUTE_MENSUAL)
        app.job_queue.run_daily(
            callback=push_anual,
            time=hora_push_anual,
            name="push_anual"
        )
        logger.info(f"📅 Push anual programado para el 1 de enero a las {PUSH_HOUR_MENSUAL:02d}:{PUSH_MINUTE_MENSUAL:02d}")
    else:
        logger.warning("⚠️ No se configuraron pushes automáticos (falta TELEGRAM_USER_ID)")
    
    # Iniciar bot
    logger.info("✅ Bot iniciado. Escuchando actualizaciones...")
    
    # run_polling() es un método bloqueante síncrono
    # Crea y gestiona su propio event loop internamente
    # NO usar asyncio.run() — eso rompe el event loop
    app.run_polling()

# ===== ENTRY POINT =====

if __name__ == "__main__":
    try:
        # ✅ Llamada directa — NO usar asyncio.run()
        main()
    except KeyboardInterrupt:
        logger.info("\n⏹️ Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)
