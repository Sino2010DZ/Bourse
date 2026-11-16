"""Météo de Genève via Open-Meteo (service public gratuit, sans clé)."""

from __future__ import annotations

import asyncio
from typing import Callable

from outils.web_public import lire_json

GENEVE = (46.2044, 6.1432)
URL = (
    "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation"
    "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"
    "&timezone=Europe%2FZurich&forecast_days=4"
)

# Codes météo de l'OMM -> (texte, icône)
CODES = {
    0: ("Ciel dégagé", "☀️"), 1: ("Plutôt dégagé", "🌤️"), 2: ("Partiellement nuageux", "⛅"), 3: ("Couvert", "☁️"),
    45: ("Brouillard", "🌫️"), 48: ("Brouillard givrant", "🌫️"),
    51: ("Bruine légère", "🌦️"), 53: ("Bruine", "🌦️"), 55: ("Bruine forte", "🌧️"),
    56: ("Bruine verglaçante", "🌧️"), 57: ("Bruine verglaçante", "🌧️"),
    61: ("Pluie faible", "🌦️"), 63: ("Pluie", "🌧️"), 65: ("Forte pluie", "🌧️"),
    66: ("Pluie verglaçante", "🌧️"), 67: ("Pluie verglaçante", "🌧️"),
    71: ("Neige faible", "🌨️"), 73: ("Neige", "🌨️"), 75: ("Forte neige", "❄️"), 77: ("Grains de neige", "🌨️"),
    80: ("Averses", "🌦️"), 81: ("Averses", "🌧️"), 82: ("Fortes averses", "⛈️"),
    85: ("Averses de neige", "🌨️"), 86: ("Fortes averses de neige", "❄️"),
    95: ("Orage", "⛈️"), 96: ("Orage avec grêle", "⛈️"), 99: ("Orage avec grêle", "⛈️"),
}


def decrire(code) -> tuple[str, str]:
    return CODES.get(int(code) if code is not None else -1, ("Inconnu", "🌡️"))


def mettre_en_forme(brut: dict) -> dict:
    c = brut["current"]
    d = brut["daily"]
    texte, icone = decrire(c.get("weather_code"))
    jours = []
    for i, date in enumerate(d["time"]):
        t, ic = decrire(d["weather_code"][i])
        jours.append({
            "date": date, "temps": t, "icone": ic,
            "min": d["temperature_2m_min"][i], "max": d["temperature_2m_max"][i],
            "pluie_pct": d["precipitation_probability_max"][i],
            "lever": d.get("sunrise", [None] * len(d["time"]))[i], "coucher": d.get("sunset", [None] * len(d["time"]))[i],
        })
    return {
        "lieu": "Genève",
        "heure": c.get("time"),
        "temperature": c.get("temperature_2m"),
        "ressenti": c.get("apparent_temperature"),
        "vent_kmh": c.get("wind_speed_10m"),
        "precipitation_mm": c.get("precipitation"),
        "temps": texte,
        "icone": icone,
        "jours": jours,
        "source": "Open-Meteo",
    }


class ServiceMeteo:
    def __init__(self, lecteur: Callable[[str], dict] | None = None) -> None:
        self.lecteur = lecteur or (lambda url: lire_json(url, duree_cache=15 * 60))

    async def geneve(self) -> dict:
        brut = await asyncio.to_thread(self.lecteur, URL.format(lat=GENEVE[0], lon=GENEVE[1]))
        return mettre_en_forme(brut)
