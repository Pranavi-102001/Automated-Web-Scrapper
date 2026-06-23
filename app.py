"""
app.py
──────
Streamlit application — AI-Powered Web Scraper.

Run with:
    streamlit run app.py
"""

import io
import logging
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load .env variables before any module that reads them
load_dotenv()

from scraper import scrape, validate_url
from ai_extractor import extract

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Web Scraper",
    page_icon="🕷️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

    /* ── Root palette ── */
    :root {
        --bg:        #0d0f14;
        --surface:   #161a23;
        --border:    #252b38;
        --accent:    #00e5a0;
        --accent2:   #0070f3;
        --text:      #e8eaf0;
        --muted:     #8891a4;
        --danger:    #ff4f6a;
        --warn:      #f5a623;
    }

    /* ── Global ── */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'DM Sans', sans-serif;
    }

    [data-testid="stHeader"] { background: transparent !important; }

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

    /* ── Main content area ── */
    .main .block-container {
        max-width: 860px;
        padding: 2.5rem 2rem 4rem;
        margin: 0 auto;
    }

    /* ── Hero banner ── */
    .hero {
        text-align: center;
        padding: 3rem 0 2rem;
        border-bottom: 1px solid var(--border);
        margin-bottom: 2.5rem;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(0,229,160,0.12);
        border: 1px solid rgba(0,229,160,0.35);
        color: var(--accent);
        font-family: 'Space Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        padding: 4px 14px;
        border-radius: 100px;
        margin-bottom: 1.2rem;
    }
    .hero-title {
        font-family: 'Space Mono', monospace;
        font-size: 2.6rem;
        font-weight: 700;
        line-height: 1.15;
        color: var(--text);
        margin: 0 0 0.75rem;
    }
    .hero-title span { color: var(--accent); }
    .hero-sub {
        color: var(--muted);
        font-size: 1rem;
        font-weight: 300;
        max-width: 520px;
        margin: 0 auto;
        line-height: 1.6;
    }

    /* ── Card ── */
    .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.8rem 2rem;
        margin-bottom: 1.5rem;
    }
    .card-label {
        font-family: 'Space Mono', monospace;
        font-size: 0.68rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.5rem;
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #1e2330 !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.95rem !important;
        padding: 0.6rem 0.9rem !important;
        transition: border-color 0.2s;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(0,229,160,0.15) !important;
    }

    /* ── Primary button ── */
    .stButton > button {
        width: 100%;
        background: var(--accent) !important;
        color: #0d0f14 !important;
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.06em !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        cursor: pointer !important;
        transition: opacity 0.2s, transform 0.15s !important;
    }
    .stButton > button:hover {
        opacity: 0.88 !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }

    /* ── Download buttons ── */
    .stDownloadButton > button {
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.85rem !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.1rem !important;
        transition: border-color 0.2s, color 0.2s !important;
    }
    .stDownloadButton > button:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
    }

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        overflow: hidden;
    }

    /* ── Alerts ── */
    .stAlert { border-radius: 10px !important; }

    /* ── Status pills ── */
    .pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-family: 'Space Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        padding: 3px 10px;
        border-radius: 100px;
    }
    .pill-green { background: rgba(0,229,160,0.12); color: var(--accent); border: 1px solid rgba(0,229,160,0.3); }
    .pill-blue  { background: rgba(0,112,243,0.12); color: #4da6ff;       border: 1px solid rgba(0,112,243,0.3); }
    .pill-red   { background: rgba(255,79,106,0.12); color: var(--danger); border: 1px solid rgba(255,79,106,0.3); }

    /* ── Metrics row ── */
    .metrics-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.2rem;
        flex-wrap: wrap;
    }
    .metric-box {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.9rem 1.3rem;
        min-width: 140px;
        flex: 1;
    }
    .metric-label {
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--accent);
    }
    .metric-sub {
        font-size: 0.78rem;
        color: var(--muted);
        margin-top: 2px;
    }

    /* ── Divider ── */
    hr { border-color: var(--border) !important; }

    /* ── Spinner ── */
    [data-testid="stSpinner"] { color: var(--accent) !important; }

    /* ── Select / Expander ── */
    .streamlit-expanderHeader {
        background: var(--surface) !important;
        border-color: var(--border) !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 0.8rem !important;
        color: var(--muted) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
        <div class="hero-badge">⚡ Gemini-Powered</div>
        <div class="hero-title">AI <span>Web</span> Scraper</div>
        <div class="hero-sub">
            Describe the data you need in plain English.
            We scrape, extract, and hand you a clean table — ready to download.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Input Card ────────────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)

st.markdown('<div class="card-label">🌐 Target URL</div>', unsafe_allow_html=True)
url_input = st.text_input(
    label="url",
    label_visibility="collapsed",
    placeholder="https://books.toscrape.com",
    key="url_field",
)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="card-label">💬 What do you want to extract?</div>', unsafe_allow_html=True)
query_input = st.text_area(
    label="query",
    label_visibility="collapsed",
    placeholder=(
        "e.g. Extract book title and price\n"
        "e.g. Extract job title, company name, and location\n"
        "e.g. Extract product name, price, and rating"
    ),
    height=110,
    key="query_field",
)

st.markdown("<br>", unsafe_allow_html=True)
run_btn = st.button("🕷️  Extract Data", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Examples ──────────────────────────────────────────────────────────────────
with st.expander("📖  Example URLs & Queries", expanded=False):
    st.markdown(
        """
| URL | Sample Query |
|-----|-------------|
| `https://books.toscrape.com` | Extract book title and price |
| `https://quotes.toscrape.com` | Extract quote text and author |
| `https://news.ycombinator.com` | Extract story title and points |
| `https://webscraper.io/test-sites/e-commerce/allinone` | Extract product name, price, and rating |
        """
    )

# ── Main logic ────────────────────────────────────────────────────────────────
if run_btn:
    # ── Validation ────────────────────────────────────────────────────────────
    errors = []
    if not url_input.strip():
        errors.append("Please enter a URL.")
    if not query_input.strip():
        errors.append("Please describe what you want to extract.")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    # Validate URL format before spending time scraping
    valid, msg = validate_url(url_input.strip())
    if not valid:
        st.error(f"❌ Invalid URL — {msg}")
        st.stop()

    normalised_url = msg

    # ── Scraping ──────────────────────────────────────────────────────────────
    st.markdown("---")
    with st.spinner("🔍 Fetching page content…"):
        scrape_result = scrape(normalised_url)

    if not scrape_result["success"]:
        st.error(f"❌ Scraping failed — {scrape_result['error']}")
        st.stop()

    method_label = (
        "Playwright (JS-rendered)" if scrape_result["method"] == "playwright"
        else "BeautifulSoup (static)"
    )
    pill_cls = "pill-blue" if scrape_result["method"] == "playwright" else "pill-green"

    st.markdown(
        f'<span class="pill {pill_cls}">✓ Scraped via {method_label}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI Extraction ─────────────────────────────────────────────────────────
    with st.spinner("🤖 Asking Gemini to extract your data…"):
        extract_result = extract(query_input.strip(), scrape_result["content"])

    if not extract_result["success"]:
        st.error(f"❌ Extraction failed — {extract_result['error']}")

        # Helpful hint when the API key is missing
        if "GEMINI_API_KEY" in extract_result.get("error", ""):
            st.info(
                "💡 Add your Gemini API key to a `.env` file in the project root:\n"
                "```\nGEMINI_API_KEY=your_key_here\n```\n"
                "Get a free key at https://aistudio.google.com/app/apikey"
            )
        st.stop()

    df: pd.DataFrame = extract_result["dataframe"]
    row_count = extract_result["row_count"]
    col_count = len(df.columns)

    # ── Metrics ───────────────────────────────────────────────────────────────
    col_names = ", ".join(df.columns.tolist())
    st.markdown(
        f"""
        <div class="metrics-row">
            <div class="metric-box">
                <div class="metric-label">Rows extracted</div>
                <div class="metric-value">{row_count}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Columns</div>
                <div class="metric-value">{col_count}</div>
                <div class="metric-sub">{col_names}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Source</div>
                <div class="metric-value" style="font-size:0.85rem; padding-top:6px; word-break:break-all;">{normalised_url[:40]}{"…" if len(normalised_url)>40 else ""}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Data Table ────────────────────────────────────────────────────────────
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    dl_col1, dl_col2, _ = st.columns([1, 1, 2])

    # CSV
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    dl_col1.download_button(
        label="⬇ Download CSV",
        data=csv_bytes,
        file_name="scraped_data.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Excel
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Scraped Data")
    excel_bytes = excel_buffer.getvalue()

    dl_col2.download_button(
        label="⬇ Download Excel",
        data=excel_bytes,
        file_name="scraped_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <br><hr>
    <div style="text-align:center; color: #4a5568; font-family: 'Space Mono', monospace;
                font-size: 0.68rem; letter-spacing: 0.12em; padding: 1rem 0;">
        AI WEB SCRAPER &nbsp;·&nbsp; GEMINI + BEAUTIFULSOUP + PLAYWRIGHT
    </div>
    """,
    unsafe_allow_html=True,
)
