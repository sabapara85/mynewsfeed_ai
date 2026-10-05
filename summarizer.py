"""DeepSeek-powered briefing generation — split by report type."""
import json
import os
import re

from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    timeout=90.0,
)

MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")


GENERAL_SYSTEM = (
    "You are a high-IQ geopolitical and domestic affairs analyst writing a private "
    "daily briefing. You are precise, dense, and never waste words. You never add "
    "disclaimers or meta commentary."
)

ECONOMIC_SYSTEM = (
    "You are a high-IQ financial analyst and market strategist writing a private "
    "daily briefing. You are precise, dense, and specific about assets, indices and "
    "macro drivers. You never add disclaimers or meta commentary."
)


GENERAL_USER = """INPUT — GENERAL NEWS HEADLINES:
{headlines}

TASK
Return ONLY a valid JSON object with exactly one key:

"summary": an array of exactly 10 strings. The top India + World news a
well-informed citizen must know. Factual, dense, specific. No fluff.

RULES
- No opinions, no hedging, no "as an AI", no disclaimers.
- Be specific: name countries, people, numbers.
- Output pure JSON only. No markdown fences. No text before or after.
"""


ECONOMIC_USER = """INPUT — ECONOMIC / MARKET NEWS HEADLINES:
{headlines}

TASK
Return ONLY a valid JSON object with exactly these three keys:

1. "summary": array of exactly 10 strings. News that can move markets:
   commodities (crude, gold, metals), equities, sectors, central banks,
   geopolitics, macro data. Each line must name the asset, sector or
   index affected.

2. "india_market_outlook": a single paragraph of 3-4 sentences. Based ONLY
   on the news above, what to expect for Nifty / Sensex, key sectors,
   the rupee and FII flows today.

3. "usa_market_outlook": a single paragraph of 3-4 sentences. Based ONLY
   on the news above, what to expect for S&P 500 / Nasdaq, the dollar,
   Fed expectations and bonds.

RULES
- No opinions, no hedging, no "as an AI", no disclaimers.
- Be specific: name companies, indices, commodities, numbers.
- If the news does not support a conclusion, say "unclear" instead of guessing.
- Output pure JSON only. No markdown fences. No text before or after.
"""


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def _fix_lines(value, count=10):
    if isinstance(value, str):
        value = [v.strip(" -•\t") for v in value.split("\n") if v.strip()]
    if not isinstance(value, list):
        value = []
    value = [str(v).strip() for v in value if str(v).strip()]
    if len(value) > count:
        value = value[:count]
    while len(value) < count:
        value.append("—")
    return value


def build_general_briefing(headlines):
    prompt = GENERAL_USER.format(
        headlines="\n".join(f"- {h}" for h in headlines) or "- (no headlines)"
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": GENERAL_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=900,
    )
    data = _extract_json(response.choices[0].message.content)
    return {"general_summary": _fix_lines(data.get("summary"))}


def build_economic_briefing(headlines):
    prompt = ECONOMIC_USER.format(
        headlines="\n".join(f"- {h}" for h in headlines) or "- (no headlines)"
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": ECONOMIC_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=1400,
    )
    data = _extract_json(response.choices[0].message.content)
    return {
        "investment_summary": _fix_lines(data.get("summary")),
        "india_market_outlook": str(data.get("india_market_outlook", "unclear")).strip(),
        "usa_market_outlook": str(data.get("usa_market_outlook", "unclear")).strip(),
    }