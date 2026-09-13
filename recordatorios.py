import sqlite3
import asyncio
from datetime import datetime, timedelta

DB_PATH = "recordatorios.db"



def inicializar_db():
    """Crea la tabla de recordatorios si no existe"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recordatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            mensaje TEXT NOT NULL,
            fecha_disparo INTEGER NOT NULL,
            enviado INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def guardar_recordatorio(chat_id: int, mensaje: str, fecha_disparo: datetime) -> int:
    """Guarda un recordatorio nuevo y devuelve su id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO recordatorios (chat_id, mensaje, fecha_disparo) VALUES (?, ?, ?)",
        (chat_id, mensaje, fecha_disparo.isoformat())
    )
    conn.commit()
    id_recordatorio = cursor.lastrowid
    conn.close()
    return id_recordatorio


def marcar_como_enviado(id_recordatorio: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE recordatorios SET enviado = 1 WHERE id = ?",
        (id_recordatorio,)
    )
    conn.commit()
    conn.close()

def obtener_pendientes():
    """Devuelve todos los recordatorios que aun no se enviaron"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, chat_id, mensaje, fecha_disparo FROM recordatorios WHERE enviado = 0"
    )
    filas = cursor.fetchall()
    conn.close()
    return filas


async def programar_recordatorio(contex, chat_id, mensaje, minutos):
    """Guarda el recordatorio en la DB y espera para enviarlo."""
    fecha_disparo = datetime.now() + timedelta(minutes=minutos)
    id_recordatorio = guardar_recordatorio(chat_id, mensaje, fecha_disparo)

    await asyncio.sleep(minutos * 60)

    try:
        await contex.bot.send_mesage(
            chat_id=chat_id,
            text=f" Recordatorio: {mensaje}"
        )
        marcar_como_enviado(id_recordatorio)
    except Exception as e:
        print(f"Error enviado recordatorio: {e}")


async def restaurar_recordatorios_pendientes(app):
    """Al iniciar el bot, reprograma los recordatorios que quedaron pendientes."""
    pendientes = obtener_pendientes()
    ahora = datetime.now()

    for id_rec, chat_id, mensaje, fecha_str in pendientes:
        fecha_disparo = datetime.fromisoformat(fecha_str)
        segundos_restantes = (fecha_disparo - ahora).total_seconds()

        if segundos_restantes <= 0:
            # Ya pasó la hora mientras el bot estaba apagado: avisar ahora mismo
           try:
               await app.bot.send_message(
                   chat_id=chat_id,
                   text=f" Recordatorio (atrasado): {mensaje}"
               )
               marcar_como_enviado(id_rec)
           except Exception as e:
               print(f"Error enviando recordatorio: {e}")
        else:
            asyncio.create_task(
                _reprogramar(app, id_rec, chat_id, mensaje, segundos_restantes)
            )

async def _reprogramar(app, id_recordatorio, chat_id, mensaje, segundos):
    await asyncio.sleep(segundos)
    try:
        await app.bot.send_message(
            chat_id=chat_id,
            text=f" Recordatorio: {mensaje}"
        )
        marcar_como_enviado(id_recordatorio)
    except Exception as e:
        print(f"Error enviando recordatorio: {e}")