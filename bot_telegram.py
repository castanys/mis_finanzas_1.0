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
        generate_annual_message,
        get_bloque_seguimiento_mes,
        get_bloque_fondo_mensual
    )
except ImportError:
    logger.error("❌ advisor.py no encontrado en la ruta")
    sys.exit(1)

# Importar sync_trade_republic (BLOQUE 2)
try:
    from sync_trade_republic import sync_trade_republic
except ImportError:
    logger.warning("⚠️ sync_trade_republic.py no encontrado. El sync de TR estará deshabilitado.")
    sync_trade_republic = None

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
                model="claude-haiku-4-5",
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

        # Añadir bloque de seguimiento (datos reales, fuera del LLM)
        bloque = get_bloque_seguimiento_mes()
        if bloque:
            mensaje = mensaje + bloque

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

async def sin_clasificar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja /sin_clasificar — lista transacciones sin clasificar"""
    user_name = update.effective_user.first_name or "Usuario"
    logger.info(f"🔍 /sin_clasificar solicitado por {user_name}")
    
    try:
        import sqlite3
        db_path = "/home/pablo/apps/mis_finanzas_1.0/finsense.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Contar total sin clasificar
        cursor.execute(
            "SELECT COUNT(*) FROM transacciones "
            "WHERE cat1='SIN_CLASIFICAR' OR cat1 IS NULL OR cat1=''"
        )
        total_sin_clasificar = cursor.fetchone()[0]
        
        if total_sin_clasificar == 0:
            mensaje = "✅ ¡Todas las transacciones están clasificadas! 🎉"
        else:
            # Obtener últimas 20 sin clasificar (ordenadas por fecha descendente)
            cursor.execute(
                "SELECT fecha, importe, descripcion, banco FROM transacciones "
                "WHERE cat1='SIN_CLASIFICAR' OR cat1 IS NULL OR cat1='' "
                "ORDER BY fecha DESC LIMIT 20"
            )
            txs = cursor.fetchall()
            
            mensaje = f"📊 **Transacciones Sin Clasificar** ({total_sin_clasificar} total)\n\n"
            mensaje += "**Últimas 20:**\n\n"
            
            for idx, (fecha, importe, descripcion, banco) in enumerate(txs, 1):
                # Truncar descripción si es muy larga
                desc_corta = descripcion[:50] + ("..." if len(descripcion) > 50 else "")
                mensaje += f"{idx}. {fecha} | €{importe:>7.2f} | {banco}\n"
                mensaje += f"   _{desc_corta}_\n\n"
        
        conn.close()
        await update.message.reply_text(mensaje, parse_mode="Markdown")
        logger.info(f"✅ Sin clasificar enviado a {user_name}")
    
    except Exception as e:
        logger.error(f"❌ Error en /sin_clasificar: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def ayuda_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja /ayuda"""
    mensaje = f"""
**Comandos Disponibles:**

/resumen — Análisis completo del mes con ángulo aleatorio
/presupuestos — Estado de presupuestos por categoría
/cargos — Cargos extraordinarios próximos
/sin_clasificar — Transacciones sin clasificar
/ayuda — Ver este mensaje

**Importar documentos:**
📁 Adjunta un PDF o CSV al chat
Soportados: .pdf, .csv, .xls, .xlsx
• Trade Republic (extractos de cuenta)
• Mediolanum (movimientos)
• Otros bancos

El bot procesará automáticamente y te dará el resumen.

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
    Push diario (12:00) — Mensaje con ángulo aleatorio (SOLO si hay nuevas transacciones)
    Se ejecuta automáticamente via job_queue de python-telegram-bot
    
    Flujo:
    1. Detecta cambios: compara MAX(rowid) actual vs. último rowid enviado
    2. Si NO hay cambios → omite push (log informativo)
    3. Si HAY cambios → genera mensaje, envía, y actualiza rowid guardado
    
    Nota: Sync de Trade Republic desactivado (CSV descartado, solo PDFs vía Telegram)
    """
    if not TELEGRAM_USER_ID:
        logger.warning("⚠️ TELEGRAM_USER_ID no configurado. Saltando push diario.")
        return
    
    logger.info("📨 Iniciando push diario...")
    
    try:
        # ===== DETECCIÓN DE CAMBIOS: Comparar rowid de transacciones =====
        import sqlite3
        from pathlib import Path
        
        # Ruta de la BD
        db_path = Path(__file__).parent / "finsense.db"
        conn = sqlite3.connect(str(db_path))
        
        # Obtener MAX(rowid) actual
        max_rowid_actual = conn.execute("SELECT MAX(rowid) FROM transacciones").fetchone()[0] or 0
        
        # Crear tabla de estado si no existe
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_estado (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)
        
        # Leer último rowid enviado
        row = conn.execute("SELECT valor FROM bot_estado WHERE clave='ultimo_rowid_push_diario'").fetchone()
        ultimo_rowid = int(row[0]) if row else -1
        
        # Si no hay nuevas transacciones → omitir push
        if max_rowid_actual == ultimo_rowid:
            logger.info(f"⏭️ Push diario omitido: no hay nuevas transacciones desde el último envío (rowid: {ultimo_rowid})")
            conn.close()
            return
        
        logger.info(f"✅ Nuevas transacciones detectadas (rowid: {ultimo_rowid} → {max_rowid_actual})")
        
        # ===== BLOQUE 3: Generar y enviar mensaje diario =====
        # Generar prompt con ángulo aleatorio (BLOQUE 3)
        prompt = generate_daily_message()

        # Llamar al LLM
        mensaje = generar_mensaje_con_llm(prompt)

        # Añadir bloque de seguimiento (datos reales, fuera del LLM)
        bloque = get_bloque_seguimiento_mes()
        if bloque:
            mensaje = mensaje + bloque

        # Enviar al usuario
        await context.bot.send_message(
            chat_id=int(TELEGRAM_USER_ID),
            text=mensaje,
            parse_mode="Markdown"
        )
        
        # Actualizar último rowid enviado
        conn.execute("INSERT OR REPLACE INTO bot_estado VALUES ('ultimo_rowid_push_diario', ?)", (str(max_rowid_actual),))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Push diario enviado a {TELEGRAM_USER_ID}. Rowid guardado: {max_rowid_actual}")
    
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

        # Añadir bloque de fondo de caprichos del mes cerrado
        hoy = datetime.now()
        mes_cerrado = hoy.month - 1 if hoy.month > 1 else 12
        anio_cerrado = hoy.year if hoy.month > 1 else hoy.year - 1
        bloque_fondo = get_bloque_fondo_mensual(anio_cerrado, mes_cerrado)
        if bloque_fondo:
            mensaje = mensaje + "\n\n" + bloque_fondo

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


async def documento_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja documentos (PDF/CSV) — descarga y procesa transacciones
    
    Flujo:
    1. Verifica que el remitente es el usuario autorizado (TELEGRAM_USER_ID)
    2. Descarga el archivo a input/
    3. Ejecuta process_transactions.py --file en background
    4. Notifica al usuario con el resultado
    5. Archiva el archivo en input/procesados/
    """
    import subprocess
    import shutil
    from pathlib import Path
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Usuario"
    
    # Seguridad: solo el usuario autorizado puede enviar documentos
    if TELEGRAM_USER_ID and str(user_id) != str(TELEGRAM_USER_ID):
        logger.warning(f"⚠️ Intento no autorizado de importar documento de {user_name} (ID: {user_id})")
        await update.message.reply_text("❌ No autorizado para enviar documentos.")
        return
    
    # Obtener información del documento
    document = update.message.document
    file_name = document.file_name
    file_size_mb = document.file_size / (1024 * 1024)
    
    # Validar extensión
    allowed_extensions = ['.pdf', '.csv', '.xls', '.xlsx']
    file_ext = Path(file_name).suffix.lower()
    if file_ext not in allowed_extensions:
        logger.warning(f"⚠️ Extensión no permitida: {file_ext}")
        await update.message.reply_text(
            f"❌ Formato no soportado: {file_ext}\n"
            f"Soportados: {', '.join(allowed_extensions)}"
        )
        return
    
    logger.info(f"📥 Documento recibido: {file_name} ({file_size_mb:.2f} MB)")
    
    # Confirmar recepción
    await update.message.reply_text(f"⏳ Recibido: {file_name}\nProcesando...")
    
    try:
        # Descargar el archivo
        file = await context.bot.get_file(document.file_id)
        input_dir = Path("/home/pablo/apps/mis_finanzas_1.0/input")
        file_path = input_dir / file_name
        
        await file.download_to_drive(str(file_path))
        logger.info(f"✅ Archivo descargado a {file_path}")
        
        # Guardar MAX(rowid) antes del procesamiento para detectar txs sin clasificar nuevas
        import sqlite3
        db_path = "/home/pablo/apps/mis_finanzas_1.0/finsense.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(rowid) FROM transacciones")
        rowid_antes = cursor.fetchone()[0] or 0
        conn.close()
        
        # Ejecutar process_transactions.py en background
        logger.info(f"🔄 Procesando {file_name}...")
        result = subprocess.run(
            [
                "/home/pablo/apps/mis_finanzas_1.0/venv/bin/python3",
                "/home/pablo/apps/mis_finanzas_1.0/process_transactions.py",
                "--file", str(file_path),
                "--no-stats"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parsear resultado
        output = result.stdout + result.stderr
        logger.info(f"📋 Output: {output[:500]}")
        
        # Contar nuevas transacciones en el output
        nuevas_txs = 0
        if "nuevas transacciones" in output.lower():
            try:
                # Buscar patrón "X nuevas transacciones"
                import re
                match = re.search(r'(\d+)\s+nuevas?\s+transacciones?', output, re.IGNORECASE)
                if match:
                    nuevas_txs = int(match.group(1))
            except:
                pass
        
        # Contar txs sin clasificar nuevas (entre rowid_antes y MAX(rowid) actual)
        sin_clasificar_nuevas = 0
        sin_clasificar_list = []
        if nuevas_txs > 0:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT rowid, descripcion, importe FROM transacciones "
                    "WHERE rowid > ? AND (cat1='SIN_CLASIFICAR' OR cat1 IS NULL OR cat1='') "
                    "ORDER BY rowid DESC LIMIT 50",
                    (rowid_antes,)
                )
                sin_clasificar_nuevas = len(cursor.fetchall())
                conn.close()
            except Exception as e:
                logger.warning(f"⚠️ Error contando sin_clasificar: {e}")
        
        # Preparar respuesta
        if result.returncode == 0:
            # Éxito
            if nuevas_txs > 0:
                status = f"✅ Procesado: {nuevas_txs} nuevas transacciones importadas"
            else:
                status = "ℹ️ Procesado: 0 nuevas transacciones (ya estaban en la BD)"
            
            # Escapar nombre de archivo para Markdown (reemplazar caracteres especiales)
            file_name_safe = file_name.replace("_", "\\_").replace("-", "\\-").replace("[", "\\[").replace("]", "\\]")
            
            response = (
                f"**{status}**\n"
                f"📄 Archivo: `{file_name_safe}`\n"
                f"📊 Tamaño: {file_size_mb:.2f} MB\n"
                f"📁 Archivado en: input/procesados/\n"
            )
            
            # Añadir alerta si hay txs sin clasificar
            if sin_clasificar_nuevas > 0:
                response += f"⚠️ {sin_clasificar_nuevas} transacciones sin clasificar — usa /sin_clasificar para ver el detalle\n"
        else:
            # Error
            error_msg = result.stderr or "Error desconocido"
            # Escapar error_msg para evitar problemas de Markdown
            error_msg_safe = error_msg[:200].replace("[", "\\[").replace("]", "\\]")
            response = (
                f"❌ Error procesando el archivo:\n"
                f"`{error_msg_safe}`"
            )
            logger.error(f"❌ Error: {error_msg}")
        
        # Enviar respuesta
        try:
            await update.message.reply_text(response, parse_mode="Markdown")
        except Exception as markdown_err:
            # Si falla por Markdown, enviar sin format
            logger.warning(f"⚠️ Error Markdown, enviando sin formato: {markdown_err}")
            await update.message.reply_text(response)
        
        # ===== BLOQUE NUEVO: Enviar análisis del día siempre (si el proceso fue exitoso) =====
        if result.returncode == 0:
            try:
                logger.info("📊 Generando análisis del día tras importación...")
                await update.message.reply_text("📊 Generando estado financiero del día...")
                
                # Generar prompt con ángulo aleatorio (igual que push diario)
                prompt = generate_daily_message()

                # Llamar al LLM
                mensaje_diario = generar_mensaje_con_llm(prompt)

                # Añadir bloque de seguimiento (datos reales, fuera del LLM)
                bloque = get_bloque_seguimiento_mes()
                if bloque:
                    mensaje_diario = mensaje_diario + bloque

                # Enviar análisis
                await update.message.reply_text(mensaje_diario, parse_mode="Markdown")
                logger.info("✅ Análisis del día enviado tras importación")
            
            except Exception as e:
                logger.warning(f"⚠️ Error generando análisis del día: {e}")
                # No detener el flujo si falla el análisis — el PDF ya se procesó correctamente
        
        # Mover archivo a procesados/ si todo fue bien
        if result.returncode == 0:
            processed_dir = input_dir / "procesados"
            processed_dir.mkdir(parents=True, exist_ok=True)
            new_path = processed_dir / file_name
            if file_path.exists():
                shutil.move(str(file_path), str(new_path))
                logger.info(f"✅ Archivo archivado en {new_path}")
            else:
                logger.info(f"ℹ️ Archivo ya movido por el pipeline: {file_name}")
        
        logger.info(f"✅ Importación completada: {file_name}")
    
    except subprocess.TimeoutExpired:
        logger.error("⏱️ El procesamiento tardó demasiado (>60s)")
        await update.message.reply_text("❌ El procesamiento tardó demasiado. Intenta con un archivo más pequeño.")
    
    except Exception as e:
        logger.error(f"❌ Error importando documento: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

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
    app.add_handler(CommandHandler("sin_clasificar", sin_clasificar_handler))
    app.add_handler(CommandHandler("ayuda", ayuda_handler))
    
    # Handler para documentos (PDF/CSV) — procesar transacciones
    app.add_handler(MessageHandler(filters.Document.ALL, documento_handler))
    
    # Handler para mensajes genéricos (debe ir al final)
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
