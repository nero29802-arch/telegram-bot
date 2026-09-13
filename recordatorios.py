from datetime import datetime, timedelta
import asyncio

# Diccionario simple en memoria: {chat_id: [(mensaje, fecha_hora), ...]}
recordatorios_activos = {}

async def programar_recordatorio(context, chat_id, mensaje, minutos):
    """Espera 'minutos' y luego envía el recordatorio."""
    await asyncio.sleep(minutos * 60)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ Recordatorio: {mensaje}"
        )
    except Exception as e:
        print(f"Error enviando recordatorio: {e}")