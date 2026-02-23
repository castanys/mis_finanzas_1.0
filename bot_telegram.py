"""
bot_telegram.py — Bot de Telegram para seguimiento financiero
Envía push diario a las 8:00 AM + responde consultas on-demand
Integración con advisor.py para análisis y LLM (Qwen/Claude)
"""

import os
import sys
import logging
from datetime import datetime, time
import asyncio
import json

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

# Importar APScheduler para scheduling
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    logger.error("❌ apscheduler no instalado. Instala: pip install apscheduler")
    sys.exit(1)

# Importar advisor
try:
    from advisor import (
        obtener_mensaje_para_bot,
        obtener_contexto_json,
        get_mes_nombre,
        analizar_presupuestos
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

# Hora del push automático (defecto: 8:00 AM)
PUSH_HOUR = int(os.getenv("PUSH_HOUR", "8"))
PUSH_MINUTE = int(os.getenv("PUSH_MINUTE", "0"))

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
- 📅 Enviarte un análisis diario a las {PUSH_HOUR:02d}:{PUSH_MINUTE:02d} AM
- 📊 Responder preguntas sobre tu situación financiera
- 💰 Recordarte cargos extraordinarios próximos

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
    """Maneja /resumen — envía análisis del mes actual"""
    user_name = update.effective_user.first_name or "Usuario"
    logger.info(f"📊 /resumen solicitado por {user_name}")
    
    await update.message.reply_text("⏳ Analizando tu situación financiera...")
    
    try:
        # Generar prompt
        prompt = obtener_mensaje_para_bot()
        
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
    mensaje = """
**Comandos Disponibles:**

/resumen — Análisis completo del mes actual con recomendaciones
/presupuestos — Estado de presupuestos por categoría
/cargos — Cargos extraordinarios próximos
/ayuda — Ver este mensaje

**Sobre este bot:**
Soy tu asesor financiero. Cada día a las 08:00 AM te envío un análisis personalizado de tu situación.

Respondo en español, con tono cercano y sin jerga corporativa.

¿Preguntas? Contacta a Pablo.
"""
    await update.message.reply_text(mensaje)

# ===== PUSH AUTOMÁTICO DIARIO =====

async def push_diario(context: ContextTypes.DEFAULT_TYPE):
    """
    Tarea programada: envía push a las 8:00 AM
    Se ejecuta automáticamente via APScheduler
    """
    if not TELEGRAM_USER_ID:
        logger.warning("⚠️ TELEGRAM_USER_ID no configurado. Saltando push.")
        return
    
    logger.info("📨 Enviando push diario...")
    
    try:
        # Generar prompt
        prompt = obtener_mensaje_para_bot()
        
        # Llamar al LLM
        mensaje = generar_mensaje_con_llm(prompt)
        
        # Enviar al usuario
        await context.bot.send_message(
            chat_id=int(TELEGRAM_USER_ID),
            text=mensaje,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Push enviado a {TELEGRAM_USER_ID}")
    
    except TelegramError as e:
        logger.error(f"❌ Error enviando push (Telegram): {e}")
    except Exception as e:
        logger.error(f"❌ Error enviando push: {e}")

async def mensaje_generico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes genéricos"""
    await update.message.reply_text(
        "👋 No entiendo ese comando. Usa /ayuda para ver opciones disponibles."
    )

# ===== INICIALIZACIÓN DEL BOT =====

async def main():
    """Inicia el bot con handlers y scheduler"""
    
    logger.info("🚀 Iniciando bot de Telegram...")
    
    # Crear aplicación
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Registrar handlers de comandos
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("resumen", resumen_handler))
    app.add_handler(CommandHandler("presupuestos", presupuestos_handler))
    app.add_handler(CommandHandler("cargos", cargos_handler))
    app.add_handler(CommandHandler("ayuda", ayuda_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_generico))
    
    # Configurar scheduler para push diario usando job_queue de python-telegram-bot
    if TELEGRAM_USER_ID:
        # Usar el job_queue integrado de la aplicación
        job_queue = app.job_queue
        job_queue.scheduler.add_job(
            push_diario,
            CronTrigger(hour=PUSH_HOUR, minute=PUSH_MINUTE),
            args=(app.context_types.context,),
            id="push_diario",
            name="Push financiero diario",
            replace_existing=True
        )
        
        logger.info(f"📅 Scheduler configurado: Push diario a {PUSH_HOUR:02d}:{PUSH_MINUTE:02d}")
    else:
        logger.warning("⚠️ No se configuró push automático (falta TELEGRAM_USER_ID)")
    
    # Iniciar bot
    async with app:
        logger.info("✅ Bot iniciado. Escuchando actualizaciones...")
        await app.run_polling()

# ===== ENTRY POINT =====

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️ Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)
