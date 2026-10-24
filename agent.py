
import os
import re
import requests
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI
from uagents import Agent, Context, Protocol

from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    StartSessionContent,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = (
    os.getenv("ASI_ONE_API_KEY")
    or os.getenv("ASI1_API_KEY")
    or ""
).strip()

BASE_URL = os.getenv(
    "ASI_ONE_BASE_URL",
    "https://api.asi1.ai/v1"
).rstrip("/")

MODEL = os.getenv("ASI_ONE_MODEL", "asi1")

if not API_KEY:
    raise RuntimeError(
        "API key missing. Add ASI_ONE_API_KEY to agent/.env"
    )

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

agent = Agent(
    name="Kisan-Setu",
    seed=os.getenv("AGENT_SEED"),
    mailbox=True,
    publish_agent_details=True,
)

# Standard Agent Chat Protocol
chat_proto = Protocol(spec=chat_protocol_spec)


# --------------------------------------------------
# 2. CHAT MESSAGE HELPER
# --------------------------------------------------

def create_text_chat(
    text: str,
    end_session: bool = False
) -> ChatMessage:

    content = [
        TextContent(type="text", text=text)
    ]

    if end_session:
        content.append(
            EndSessionContent(type="end-session")
        )

    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=content,
    )


# --------------------------------------------------
# 3. WEATHER TOOL
# --------------------------------------------------

def get_weather(city: str) -> dict:
    """Fetch current weather and a three-day forecast."""

    try:
        geo_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1,
                "language": "en",
            },
            timeout=15,
        )
        geo_response.raise_for_status()

        places = geo_response.json().get("results", [])

        if not places:
            return {"error": f"City not found: {city}"}

        place = places[0]

        weather_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "precipitation,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "daily": (
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "forecast_days": 3,
                "timezone": "auto",
            },
            timeout=15,
        )
        weather_response.raise_for_status()

        data = weather_response.json()

        return {
            "city": place.get("name", city),
            "country": place.get("country", ""),
            "current": data.get("current", {}),
            "forecast": data.get("daily", {}),
            "timezone": data.get("timezone", ""),
        }

    except requests.RequestException:
        return {
            "error": "Weather service is temporarily unavailable."
        }


def is_weather_question(text: str) -> bool:
    keywords = (
        "weather",
        "temperature",
        "rain",
        "rainfall",
        "forecast",
        "humidity",
        "wind",
    )

    text = text.lower()
    return any(word in text for word in keywords)


def find_city(text: str) -> str:
    """Extract a city from common weather questions."""

    patterns = [
        r"\bweather\s+(?:in|at|for)\s+([A-Za-z][A-Za-z .'-]{1,50})",
        r"\b(?:temperature|rain|rainfall)\s+(?:in|at|for)\s+([A-Za-z][A-Za-z .'-]{1,50})",
        r"\b(?:in|at)\s+([A-Za-z][A-Za-z .'-]{1,50})\s+(?:weather|today)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern, text, re.IGNORECASE
        )

        if match:
            city = match.group(1).strip(" .?!,")

            city = re.split(
                r"\b(today|tomorrow|now|currently|please)\b",
                city,
                flags=re.IGNORECASE,
            )[0].strip(" .?!,")

            if city:
                return city

    return ""


# --------------------------------------------------
# 4. ASI:ONE AI
# --------------------------------------------------

def ask_asi_one(
    question: str,
    weather: dict | None = None
) -> str:

    system_prompt = """
You are Kisan Setu, a helpful Indian farming assistant.

Your purpose is to help farmers with:
- Crop care and farming practices
- Weather information and planning
- Irrigation and soil management
- General agricultural questions

Instructions:
- Greet users politely when appropriate.
- Use simple, clear language.
- Reply in the language used by the farmer where possible.
- Give practical, concise advice.
- Use supplied weather data when available.
- Never invent current weather or claim a tool succeeded
  when it returned an error.
- Do not make unsupported pesticide or fertilizer dosage claims.
- For serious crop problems, suggest contacting a local
  agricultural expert.
"""

    user_message = question

    if weather is not None:
        user_message += (
            "\n\nWeather tool result (JSON): "
            + str(weather)
        )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.4,
        )

        answer = response.choices[0].message.content

        return answer or (
            "Sorry, I couldn't prepare an answer. Please try again."
        )

    except Exception:
        return (
            "Namaste! I'm having trouble connecting to my AI "
            "service right now. Please try again shortly."
        )


# --------------------------------------------------
# 5. STANDARD CHAT PROTOCOL HANDLER
# --------------------------------------------------

@chat_proto.on_message(ChatMessage)
async def handle_message(
    ctx: Context,
    sender: str,
    msg: ChatMessage
):
    ctx.logger.info(f"Received chat message from {sender}")

    # Always acknowledge incoming messages.
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=msg.msg_id,
        ),
    )

    # Extract text and process session markers.
    text_parts = []

    for item in msg.content:
        if isinstance(item, StartSessionContent):
            ctx.logger.info(
                f"Chat session started with {sender}"
            )

        elif isinstance(item, TextContent):
            text_parts.append(item.text)

        elif isinstance(item, EndSessionContent):
            ctx.logger.info(
                f"Chat session ended by {sender}"
            )

    question = " ".join(text_parts).strip()

    if not question:
        reply = (
            "Namaste! Welcome to Kisan Setu. "
            "Ask me about farming, crops, or weather."
        )

    else:
        weather_data = None

        if is_weather_question(question):
            city = (
                find_city(question)
                or os.getenv("DEFAULT_CITY", "Meerut")
            )

            ctx.logger.info(
                f"Calling weather tool for {city}"
            )

            weather_data = get_weather(city)

        ctx.logger.info("Generating AI response")

        reply = ask_asi_one(
            question,
            weather_data,
        )

    # Send the AI response back to the farmer.
    await ctx.send(
        sender,
        create_text_chat(reply, end_session=True),
    )

    ctx.logger.info("Kisan Setu response sent")


# --------------------------------------------------
# 6. HANDLE ACKNOWLEDGEMENTS
# --------------------------------------------------

@chat_proto.on_message(ChatAcknowledgement)
async def handle_acknowledgement(
    ctx: Context,
    sender: str,
    msg: ChatAcknowledgement
):
    ctx.logger.info(
        f"Received acknowledgement from {sender} "
        f"for message {msg.acknowledged_msg_id}"
    )


# --------------------------------------------------
# 7. REGISTER CHAT PROTOCOL
# --------------------------------------------------

agent.include(
    chat_proto,
    publish_manifest=True,
)


# --------------------------------------------------
# 8. START AGENT
# --------------------------------------------------

if __name__ == "__main__":
    agent.run()
