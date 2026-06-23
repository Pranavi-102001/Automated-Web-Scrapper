"""
ai_extractor.py
───────────────
Sends scraped text + user query to Google Gemini and parses the
structured JSON response into a Pandas DataFrame.
"""

import json
import logging
import os
import re

import pandas as pd

logger = logging.getLogger(__name__)

# ── Gemini client setup ───────────────────────────────────────────────────────

def _get_gemini_model():
    """
    Initialises and returns a Gemini GenerativeModel instance.
    Reads GEMINI_API_KEY from the environment (loaded by app.py via dotenv).
    """
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai is not installed. Run: pip install google-generativeai"
        ) from exc

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file or set it as an environment variable."
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    return model


# ── Prompt builder ────────────────────────────────────────────────────────────
def _build_prompt(user_query: str, page_text: str) -> str:
    """
    Constructs the instruction prompt sent to Gemini.

    The prompt asks Gemini to return ONLY a JSON array so that we can
    deterministically parse it into a DataFrame without extra text processing.
    """

    return f"""
You are an expert web data extraction agent.

YOUR ROLE
---------
Analyze webpage content and extract structured data that matches the user's request.

USER REQUEST
------------
{user_query}

EXTRACTION RULES
----------------
1. Return ONLY valid JSON.
2. Return ONLY a JSON array.
3. Do NOT use markdown.
4. Do NOT use code fences.
5. Do NOT write explanations.
6. Do NOT write notes.
7. Do NOT write any text before or after the JSON array.
8. Extract ALL matching records found on the page.
9. Each record must be returned as a separate JSON object.
10. Use null for missing values.
11. Never invent data.
12. Use exactly the values found on the page.
13. Normalize whitespace.
14. If multiple products, books, jobs, listings, articles, or records exist, return ALL of them.
15. Never return only a summary.
16. Prefer structured extraction over summarization.
17. If no matching records exist, return:
[]

FIELD DETECTION
---------------
Infer the field names from the user's request.

EXAMPLES
--------

User Request:
Extract book title, price and availability

Output:
[
  {{
    "title": "A Light in the Attic",
    "price": "£51.77",
    "availability": "In stock"
  }},
  {{
    "title": "Tipping the Velvet",
    "price": "£53.74",
    "availability": "In stock"
  }}
]

User Request:
Extract product name, price and rating

Output:
[
  {{
    "product_name": "Phone X",
    "price": "$999",
    "rating": "4.8"
  }}
]

User Request:
Extract job title, company and location

Output:
[
  {{
    "job_title": "Data Scientist",
    "company": "ABC Corp",
    "location": "London"
  }}
]

WEBPAGE CONTENT
---------------
{page_text}

FINAL INSTRUCTION
-----------------
Return ONLY a valid JSON array.

JSON:
"""


# ── JSON parser ───────────────────────────────────────────────────────────────

def _parse_json_response(raw: str) -> list[dict]:
    """
    Attempts to parse a JSON array from *raw*.

    Handles the common case where the model accidentally wraps the array in
    markdown code fences (```json … ```) despite instructions.
    """
    # Strip any leading/trailing whitespace
    raw = raw.strip()

    # Remove markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    # Try direct parse
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Sometimes the model wraps in {"data": [...]}
            for v in data.values():
                if isinstance(v, list):
                    return v
        return [data]
    except json.JSONDecodeError:
        pass

    # Last resort: find the first [...] block in the response
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Gemini did not return valid JSON. "
        "Try rephrasing your query or check if the page has the requested data.\n\n"
        f"Raw response (first 500 chars):\n{raw[:500]}"
    )


# ── Public API ────────────────────────────────────────────────────────────────

def extract(user_query: str, page_text: str) -> dict:
    """
    Main entry-point.

    Parameters
    ----------
    user_query : str
        Natural-language description of what to extract.
    page_text : str
        Visible text scraped from the target web page.

    Returns
    -------
    dict with keys:
        success   : bool
        dataframe : pd.DataFrame  (empty on failure)
        row_count : int
        error     : str           (only present on failure)
    """
    result: dict = {"success": False, "dataframe": pd.DataFrame(), "row_count": 0}

    if not user_query.strip():
        result["error"] = "Query cannot be empty."
        return result

    if not page_text.strip():
        result["error"] = "No page content to analyse."
        return result

    # ── Call Gemini ──────────────────────────────────────────────────────────
    try:
        model = _get_gemini_model()
    except (RuntimeError, ValueError) as exc:
        result["error"] = str(exc)
        return result

    prompt = _build_prompt(user_query, page_text)

    try:
        logger.info("Sending %d-char prompt to Gemini…", len(prompt))
        response = model.generate_content(prompt)
        raw_text = response.text
        logger.info("Gemini response received (%d chars).", len(raw_text))
    except Exception as exc:
        result["error"] = f"Gemini API error: {exc}"
        return result

    # ── Parse response ───────────────────────────────────────────────────────
    try:
        records = _parse_json_response(raw_text)
    except ValueError as exc:
        result["error"] = str(exc)
        return result

    if not records:
        result["error"] = (
            "Gemini found no data matching your query on this page. "
            "Try a different query or a different URL."
        )
        return result

    # ── Build DataFrame ──────────────────────────────────────────────────────
    try:
        df = pd.DataFrame(records)
        # Drop fully-null columns
        df.dropna(axis=1, how="all", inplace=True)
        # Replace None with empty string for display
        df.fillna("", inplace=True)
    except Exception as exc:
        result["error"] = f"Failed to build DataFrame: {exc}"
        return result

    result.update({"success": True, "dataframe": df, "row_count": len(df)})
    logger.info("Extracted %d rows, %d columns.", len(df), len(df.columns))
    return result
