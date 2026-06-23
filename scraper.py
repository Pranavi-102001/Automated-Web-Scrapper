"""
scraper.py
──────────
Fetches raw HTML from a URL.

Strategy:
  1. Try a lightweight requests + BeautifulSoup fetch first (fast, no browser).
  2. If the page appears to be JavaScript-rendered (thin text content), fall back
     to Playwright (headless Chromium) to obtain the fully-rendered DOM.
"""

import os
import re
import time
import logging
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 50000))

# Heuristic: if visible text is shorter than this after a static fetch,
# we assume the page relies on JS and switch to Playwright.
JS_THRESHOLD_CHARS = 500

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ── URL Validation ────────────────────────────────────────────────────────────

def validate_url(url: str) -> tuple[bool, str]:
    """
    Validates whether *url* is a well-formed HTTP/HTTPS URL.

    Returns
    -------
    (is_valid: bool, message: str)
    """
    url = url.strip()
    if not url:
        return False, "URL cannot be empty."

    # Prepend scheme if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"Unsupported scheme '{parsed.scheme}'. Use http or https."
        if not parsed.netloc:
            return False, "URL is missing a valid domain."
        # Basic domain sanity check
        if not re.match(r"^[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}$", parsed.netloc.split(":")[0]):
            return False, f"Domain '{parsed.netloc}' does not look valid."
        return True, url  # return normalised URL as message
    except Exception as exc:
        return False, f"URL parsing error: {exc}"


# ── Static Scraping (requests + BeautifulSoup) ────────────────────────────────

def _static_fetch(url: str, timeout: int) -> str:
    """
    Fetches *url* with requests and returns visible text extracted by
    BeautifulSoup.  Raises on HTTP / connection errors.
    """
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script / style noise
    for tag in soup(["script", "style", "noscript", "meta", "head"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return text


# ── Dynamic Scraping (Playwright) ─────────────────────────────────────────────

def _playwright_fetch(url: str, timeout: int) -> str:
    """
    Uses a headless Chromium browser via Playwright to render the page and
    return its visible text content.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed or browsers are not set up. "
            "Run: pip install playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            locale="en-US",
        )
        page = context.new_page()

        try:
            page.goto(url, timeout=timeout * 1_000, wait_until="networkidle")
            # Wait a little more for lazy-loaded content
            time.sleep(2)
        except PWTimeout:
            logger.warning("Playwright page load timed out; using whatever rendered so far.")

        # Extract visible text via JS
        text = page.evaluate(
            """() => {
                const scripts = document.querySelectorAll('script, style, noscript');
                scripts.forEach(el => el.remove());
                return document.body.innerText;
            }"""
        )
        browser.close()

    return text or ""


# ── Public API ────────────────────────────────────────────────────────────────

def scrape(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Main entry-point.  Scrapes *url* and returns a result dict:

    {
        "success":  bool,
        "url":      str,
        "method":   "static" | "playwright",
        "content":  str,   # truncated visible text
        "error":    str,   # only present on failure
    }
    """
    result: dict = {"success": False, "url": url, "method": None, "content": ""}

    # ── 1. Validate ──────────────────────────────────────────────────────────
    valid, msg = validate_url(url)
    if not valid:
        result["error"] = msg
        return result

    url = msg  # normalised URL

    # ── 2. Static fetch ──────────────────────────────────────────────────────
    try:
        logger.info("Attempting static fetch: %s", url)
        text = _static_fetch(url, timeout)
        method = "static"
    except requests.exceptions.Timeout:
        result["error"] = f"Request timed out after {timeout} seconds."
        return result
    except requests.exceptions.ConnectionError as exc:
        result["error"] = f"Connection error: {exc}"
        return result
    except requests.exceptions.HTTPError as exc:
        result["error"] = f"HTTP error {exc.response.status_code}: {exc}"
        return result
    except Exception as exc:
        result["error"] = f"Unexpected error during static fetch: {exc}"
        return result

    # ── 3. JS-render fallback ────────────────────────────────────────────────
    if len(text.strip()) < JS_THRESHOLD_CHARS:
        logger.info("Static content too thin (%d chars). Switching to Playwright.", len(text))
        try:
            text = _playwright_fetch(url, timeout)
            method = "playwright"
        except Exception as exc:
            # If Playwright also fails, surface the error
            result["error"] = f"Playwright rendering failed: {exc}"
            return result

    # ── 4. Truncate & return ─────────────────────────────────────────────────
    content = text[:MAX_CONTENT_LENGTH]
    result.update({"success": True, "url": url, "method": method, "content": content})
    logger.info("Scraped %d chars via %s from %s", len(content), method, url)
    return result
