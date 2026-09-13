import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from clima import obtener_clima
from recordatorios import (
    programar_recordatorio,
    inicializar_db,
    restaurar_recordatorios_pendientes
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")


# --- Comandos ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy tu bot Zeuscito 🤖\n\n"
        "Comandos disponibles:\n"
        "/clima <ciudad> - Consulta el clima\n"
        "/recordar <minutos> <mensaje> - Te aviso en X minutos"
    )


async def clima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /clima <ciudad>\nEj: /clima San José")
        return

    ciudad = " ".join(context.args)
    await update.message.reply_text("Consultando... 🔎")
    resultado = obtener_clima(ciudad)
    await update.message.reply_text(resultado)


async def recordar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso: /recordar <minutos> <mensaje>\nEj: /recordar 10 Sacar la comida del horno"
        )
        return

    try:
        minutos = int(context.args[0])
    except ValueError:
        await update.message.reply_text("El primer valor debe ser un número de minutos.")
        return

    mensaje = " ".join(context.args[1:])
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        f" Listo, te recuerdo en {minutos} minuto(s): \"{mensaje}\""
    )

    # Se programa en segundo plano, sin bloquear el bot
    asyncio.create_task(
        programar_recordatorio(context, chat_id, mensaje, minutos)
    )


# --- Main ---

def main():
    inicializar_db()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clima", clima))
    app.add_handler(CommandHandler("recordar", recordar))


    app.job_queue.run_once(
        lambda ctx:asyncio.create_task(restaurar_recordatorios_pendientes(app)),
        when=1
    )

    print("Bot corriendo... presioná Ctrl+C para detener.")
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()