import sqlite3
import asyncio
from datetime import datetime, timedelta
from os.path import curdir

DB_PATH = "recordatorios.db"

# Guarda las tareas asyncio activas para poder cancelarlas: {id_recordatorio: Task}
tareas_activas = {}


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

def eliminar_recordatorio(id_recordtorio: int, chat_id: int) -> bool:

    """Elimina un recordatorio pendiente y devuelve True(verdadero) si existía y se borro"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM recordatorios WHERE id = ? AND chat_id = ? AND enviado = 0",
        (id_recordtorio, chat_id)
    )
    filas_afectadas = cursor.rowcount
    conn.commit()
    conn.close()
    return filas_afectadas > 0


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


def obtener_pendientes_por_chat(chat_id: int):

    """Recordatorios pendientes de un chat en especifico usado por /misrecordatorios."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, mensaje, fecha_disparo FROM recordatorios WHERE enviado = 0 AND chat_id = ? ORDER BY fecha_disparo",
        (chat_id,)

    )
    filas = cursor.fetchall()
    conn.close()
    return filas


async def _ejecutar_recordatorio(bot, id_recordatorio, chat_id, mensaje, segundos):

    """Espera y envía el recordatorio y se puede cancelar mientas se espera."""

    try:
        await asyncio.sleep(segundos)
        await bot.send_message(chat_id=chat_id, text=f"Recordatorio: {mensaje}")
        marcar_como_enviado(id_recordatorio)
    except asyncio.CancelledError:
        pass  # El usuario lo cancela on /cancelar
    except Exception as e:
        print(f"Error enviando recordatorio: {e}")
    finally:
        tareas_activas.pop(id_recordatorio, None)


async def programar_recordatorio(contex, chat_id, mensaje, minutos):

    """Guarda el recordatorio en la DB y espera para enviarlo."""

    fecha_disparo = datetime.now() + timedelta(minutes=minutos)
    id_recordatorio = guardar_recordatorio(chat_id, mensaje, fecha_disparo)

    task = asyncio.create_task(
        _ejecutar_recordatorio(contex.bot, id_recordatorio, chat_id, mensaje, minutos * 60)

    )
    tareas_activas[id_recordatorio] = task
    return id_recordatorio



def cancelar_recordatorio(id_recordatorio: int, chat_id: int) -> bool:

    """Borra el recordatorio de la DB y cancela su taras si esta activa"""

    if not eliminar_recordatorio(id_recordatorio, chat_id):
        return False

    task = tareas_activas.get(id_recordatorio)
    if task:
        task.cancel()

    return True

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
               print(f"Error enviando recordatorio atrasados: {e}")
        else:
            task = asyncio.create_task(
                _ejecutar_recordatorio(app.bot,id_rec, chat_id, mensaje, segundos_restantes)

            )
            tareas_activas[id_rec] = task