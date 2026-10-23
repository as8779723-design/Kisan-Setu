# 🌱 Kisan Setu — AI Farming Assistant

Kisan Setu is a farmer-focused web application concept designed to make useful agricultural information easier to access. It brings farming assistance, weather information, and learning resources together in one place, with a voice-friendly interface.

> **Project status:** Prototype / work in progress. Features that depend on external APIs must be tested with valid configuration and an internet connection. Agentverse and Agent Chat Protocol (ACP) integration are not included in this prototype unless added separately.

## ✨ Planned and prototype features

- **AI Farmer Assistant** — ask farming questions through the assistant interface.
- **Voice assistant** — use browser speech recognition where supported; the frontend sends recognized text to the backend.
- **Weather information** — retrieve current conditions and forecast data through Open-Meteo.
- **Market prices** — planned area for mandi/market-price information; verify the source and freshness before relying on values.
- **Crop disease help** — general guidance; this prototype is not a substitute for a qualified agricultural expert.
- **Kisan Shiksha** — agricultural learning resources.
- **Government schemes** — a place to discover scheme information; eligibility should always be confirmed through official sources.
- **Nearby agricultural resources** — intended to help users locate useful agricultural services.

Feature availability depends on the current code, configuration, and connected services.

## 🧰 Technology

- HTML, CSS, and JavaScript
- Python with FastAPI
- ASI:One API for AI responses (requires an API key)
- Open-Meteo for weather data
- Browser Web Speech API for voice input where supported

## 📁 Project structure

```text
Kisan-Setu/
├── index.html          # Frontend
├── app.py              # FastAPI backend
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment configuration
├── .gitignore          # Files that should not be committed
└── README.md
```

## 🚀 Run locally

### 1. Requirements

- Python 3.10 or newer recommended
- Internet connection
- An ASI:One API key for AI responses

### 2. Open the project folder

Open the project folder in VS Code or a terminal.

### 3. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Copy `.env.example` to `.env` and add your own API key:

```env
ASI_ONE_API_KEY=put_your_key_here
ASI_ONE_MODEL=asi1-mini
```

Do not commit `.env` or publish your API key. Keep `.env` in `.gitignore`.

### 6. Start the server

```bash
uvicorn app:app --reload
```

Then open this address in your browser:

```text
http://127.0.0.1:8000
```

If the project uses a different entry point or port in your local version, follow the matching configuration in `app.py`.

## 🌦️ Weather and time accuracy

- Weather results require an internet connection and a successful response from Open-Meteo.
- Weather data represents the provider's available observations/forecast and may not be identical to a nearby field's conditions.
- Time should be displayed using India Standard Time (IST) where configured.
- If data is missing or the service fails, the app should indicate that it is unavailable rather than inventing a value.
- Check weather and market data before making farming decisions.

## 🔐 Security

- Never upload `.env`, API keys, passwords, or private credentials to GitHub.
- Use `.env.example` only for placeholder values.
- If an API key is accidentally published, revoke it and create a replacement.
- Do not put secret API keys in frontend JavaScript.

## 🧪 Current limitations

- This is a prototype and has not been independently verified for production use.
- AI responses depend on the configured API key and service availability.
- Voice features depend on browser/device support and microphone permission.
- Market prices, scheme details, crop diagnosis, and nearby-resource listings should be connected to reliable sources and tested before being described as live features.
- **Fetch.ai / Agentverse / ACP:** a dedicated Agentverse agent and ACP workflow must be implemented and tested separately before claiming hackathon compliance.

## 🛣️ Future improvements

- Complete and test Agentverse registration and ACP integration.
- Add verified mandi price sources and timestamps.
- Improve language support and accessibility for farmers.
- Connect crop-health guidance to validated agricultural sources.
- Add tests, error handling, and deployment documentation.

## 🤝 Contributing

Contributions and suggestions are welcome. For changes, create a branch, make a focused update, and submit a pull request.

## ⚠️ Disclaimer

Kisan Setu is an informational prototype. It does not replace advice from agricultural extension officers, agronomists, or official government sources. Confirm important crop, weather, market, and scheme information before acting on it.

## 📄 License

No license has been selected yet. Add a license file before allowing others to reuse or redistribute this project.
