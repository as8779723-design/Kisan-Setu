import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import string
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY", "").strip()
ASI_ONE_BASE_URL = "https://api.asi1.ai/v1"

app = FastAPI(title="Kisan Setu API", version="0.1.0")


class VoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: str = Field(default="hi", max_length=10)
    farmer: dict[str, Any] = Field(default_factory=dict)


def get_weather(city: str) -> dict[str, Any]:
    """Get a real 3-day forecast from Open-Meteo; no API key is required."""
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        geo.raise_for_status()
        places = geo.json().get("results", [])
        if not places:
            return {"ok": False, "error": f"Location not found: {city}", "source": "Open-Meteo"}

        place = places[0]
        forecast = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
                "timezone": "auto",
                "forecast_days": 3,
            },
            timeout=10,
        )
        forecast.raise_for_status()
        data = forecast.json()
        return {
            "ok": True,
            "location": place.get("name", city),
            "region": place.get("admin1", ""),
            "country": place.get("country", ""),
            "daily_forecast": data.get("daily", {}),
            "source": "Open-Meteo",
            "note": "Forecast is informational; local field conditions may differ.",
        }
    except requests.RequestException:
        return {"ok": False, "error": "Weather service is temporarily unavailable.", "source": "Open-Meteo"}


def is_weather_question(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in ("weather", "forecast", "मौसम", "बारिश", "वर्षा", "rain"))


def requested_city(text: str, farmer: dict[str, Any]) -> str:
    # Handle simple English requests such as "weather in Meerut".
    match = re.search(r"\b(?:weather|forecast|rain)\s+(?:in|for|at)\s+([A-Za-z][A-Za-z .'-]{1,60})", text, re.I)
    if match:
        city = re.split(r"\b(?:today|tomorrow|please|this week)\b|[?!,.;]", match.group(1), flags=re.I)[0].strip()
        if city:
            return city
    # Use the farmer's saved district when the user asks in Hindi or doesn't specify a place.
    return str(farmer.get("district") or farmer.get("city") or "Meerut").strip()[:80]


def ask_asi_one(user_text: str, language: str, farmer: dict[str, Any], weather_data: dict[str, Any] | None) -> str:
    if not ASI_ONE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="ASI_ONE_API_KEY is missing. Add your key to the .env file and restart the server.",
        )

    language_name = {"hi": "Hindi", "en": "English", "mr": "Marathi", "ta": "Tamil"}.get(language, "Hindi")
    honorific = {"hi": "सर", "en": "sir", "mr": "साहेब", "ta": "ஐயா"}.get(language, "सर")
    system_prompt = (
        "You are Kisan Setu, a careful farming-information assistant for Indian farmers. "
        f"Speak in the style of Jarvis: a calm, loyal, quietly witty AI butler. Address the farmer as '{honorific}'. "
        "Start with a brief acknowledgement such as 'Certainly, sir.' (in the reply language), then give the answer as a crisp status report "
        "in 2 to 4 short sentences, and end with one useful next step or offer, for example 'Shall I check the forecast for you?'. "
        "Keep any humour dry and rare, and never joke about crop loss, money, health or weather damage. "
        "Replies are read aloud, so use plain sentences only: no lists, markdown, emojis or long strings of numbers. "
        f"Reply in {language_name}. Use short, simple, practical language. "
        "Distinguish verified tool data from general guidance. Never invent live weather, mandi prices, "
        "government-scheme eligibility, or crop diagnoses. If information is missing, say so and ask a brief follow-up. "
        "Do not prescribe pesticides or exact chemical doses. For serious crop problems, advise checking with a local agriculture officer. "
        "Weather data alone is not enough to make an irrigation decision; encourage checking field moisture and crop stage."
    )
    context = {
        "farmer_profile": {
            "district": farmer.get("district", ""),
            "state": farmer.get("state", ""),
            "crops": farmer.get("crops", ""),
            "language": farmer.get("language", language_name),
        },
        "weather_tool_result": weather_data,
    }
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Farmer's question: {user_text}\n\n"
                f"Available context and tool result (JSON): {json.dumps(context, ensure_ascii=False)}\n\n"
                "Answer the question. If a tool failed, be transparent and do not guess its result."
            ),
        },
    ]
    try:
        response = requests.post(
            f"{ASI_ONE_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {ASI_ONE_API_KEY}", "Content-Type": "application/json"},
            json={"model": os.getenv("ASI_ONE_MODEL", "asi1-mini"), "messages": messages, "temperature": 0.4, "max_tokens": 500},
            timeout=45,
        )
        if response.status_code in (401, 403):
            raise HTTPException(status_code=502, detail="ASI:One rejected the API key. Check your key in .env.")
        response.raise_for_status()
        payload = response.json()
        answer = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not isinstance(answer, str) or not answer.strip():
            raise HTTPException(status_code=502, detail="ASI:One returned an empty answer. Please try again.")
        return answer.strip()
    except HTTPException:
        raise
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Could not reach ASI:One. Check your internet connection and try again.")
    except (ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="The AI service returned an unexpected response.")


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "asi_one_configured": bool(ASI_ONE_API_KEY)}


@app.post("/api/voice")
def voice_assistant(request: VoiceRequest):
    question = request.text.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Please ask a farming question.")

    weather_data = None
    if is_weather_question(question):
        city = requested_city(question, request.farmer)
        weather_data = get_weather(city)

    answer = ask_asi_one(question, request.language, request.farmer, weather_data)
    return {"response": answer, "tool_used": "open-meteo" if weather_data is not None else None, "weather": weather_data}
