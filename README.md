# 🕷️ AI Web Scraper

An AI-powered web scraping tool built with **Streamlit**, **BeautifulSoup**, **Playwright**, **Pandas**, and **Google Gemini**.

Enter any URL, describe what data you want in plain English, and get a clean, downloadable table in seconds.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Smart Scraping** | BeautifulSoup for static pages; auto-falls back to Playwright for JS-rendered pages |
| **Natural Language Queries** | Tell Gemini what you need — no CSS selectors or XPaths required |
| **Structured Output** | Gemini returns JSON → converted to a Pandas DataFrame |
| **URL Validation** | Catches malformed URLs before any network call |
| **Error Handling** | Graceful messages for timeouts, HTTP errors, JS-render failures, and bad API keys |
| **CSV Download** | One-click export |
| **Excel Download** | One-click `.xlsx` export via openpyxl |

---

## 📁 Project Structure

```
AI_Web_Scraper/
│
├── app.py            ← Streamlit UI
├── scraper.py        ← Static + dynamic scraping logic
├── ai_extractor.py   ← Gemini API integration & JSON → DataFrame
├── requirements.txt  ← Python dependencies
├── .env.example      ← Environment variable template
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone / create the project folder

```bash
mkdir AI_Web_Scraper && cd AI_Web_Scraper
# copy all files into this directory
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers

```bash
playwright install chromium
```

This installs a headless Chromium binary (~170 MB) used for JavaScript-rendered pages.

### 5. Configure your API key

```bash
cp .env.example .env
# Open .env and replace 'your_gemini_api_key_here' with your real key
```

Get a free Gemini API key at → https://aistudio.google.com/app/apikey

### 6. Run the app

```bash
streamlit run app.py
```

The app opens at **http://localhost:8501** by default.

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | — | Your Google Gemini API key |
| `REQUEST_TIMEOUT` | No | `30` | Seconds before scraping times out |
| `MAX_CONTENT_LENGTH` | No | `50000` | Max chars of page text sent to Gemini |

---

## 💡 Example Queries

| URL | Query |
|---|---|
| `https://books.toscrape.com` | Extract book title and price |
| `https://quotes.toscrape.com` | Extract quote text and author name |
| `https://news.ycombinator.com` | Extract story title and number of points |
| `https://webscraper.io/test-sites/e-commerce/allinone` | Extract product name, price, and rating |

---

## ⚙️ How It Works

```
User Input (URL + Query)
        │
        ▼
   URL Validation
        │
        ▼
 requests + BeautifulSoup  ──── thin content? ────►  Playwright (headless Chromium)
        │                                                      │
        └──────────────────────┬────────────────────────────┘
                               ▼
                     Visible page text
                               │
                               ▼
              Gemini 1.5 Flash  ←  User query + page text
                               │
                               ▼
                      JSON array of records
                               │
                               ▼
                       Pandas DataFrame
                               │
                   ┌───────────┴────────────┐
                   ▼                        ▼
            Display table           CSV / Excel download
```

---

## 🐛 Troubleshooting

| Symptom | Fix |
|---|---|
| `GEMINI_API_KEY is not set` | Add your key to `.env` and restart the app |
| `playwright install` not found | Run `pip install playwright` first, then `playwright install chromium` |
| Empty extraction results | The page may block bots; try a different URL or rephrase your query |
| Timeout errors | Increase `REQUEST_TIMEOUT` in `.env` or check your network connection |
| `ModuleNotFoundError` | Make sure you activated your virtual environment before running pip install |

---

## 📦 Dependencies

```
streamlit          — UI framework
beautifulsoup4     — HTML parsing (static pages)
playwright         — Browser automation (JS-rendered pages)
google-generativeai — Gemini API client
pandas             — DataFrame + CSV/Excel export
python-dotenv      — .env file loading
requests           — HTTP client
lxml               — Fast HTML parser backend
openpyxl           — Excel export
httpx              — HTTP transport layer
```

---

## ⚠️ Ethical Usage

- Respect each website's `robots.txt` and Terms of Service.
- Do not scrape at high frequency or store personal data without consent.
- This tool is intended for **research and personal productivity** only.
