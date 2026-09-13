import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

def obtener_clima(ciudad: str) -> str:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": ciudad,
        "appid": API_KEY,
        "units": "metric",
        "lang": "es"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if response.status_code != 200:
            return f"No pude encontrar el clima de '{ciudad}'. Verificá el nombre."

        temp = data["main"]["temp"]
        sensacion = data["main"]["feels_like"]
        descripcion = data["weather"][0]["description"]

        return (
            f"🌤️ Clima en {ciudad.title()}:\n"
            f"Temperatura: {temp}°C\n"
            f"Sensación térmica: {sensacion}°C\n"
            f"Condición: {descripcion}"
        )
    except Exception as e:
        return f"Ocurrió un error al consultar el clima: {e}"