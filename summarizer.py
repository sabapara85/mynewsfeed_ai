"""DeepSeek briefing — 25 lines per category with source URLs."""
import json
import os
import re
import traceback

from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    timeout=90.0,
)

MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
print(f"[summarizer] Using model: {MODEL}", flush=True)


GENERAL_SYSTEM = (
    "You are a high-IQ geopolitical and domestic affairs analyst writing a private "
    "daily briefing. You are precise, dense, and never waste words."
)

ECONOMIC_SYSTEM = (
    "You are a high-IQ financial analyst and market strategist writing a private "
    "daily briefing. You are precise, dense, and specific about assets, indices and "
    "macro drivers."
)


GENERAL_USER = """INPUT — GENERAL NEWS HEADLINES (numbered):
{headlines}

TASK
Return ONLY a valid JSON object with exactly one key:

"summary": an array of exactly 25 objects. Each object must have:
  - "text": a single-sentence summary of an important story.
  - "ref": the number of the source headline it is based on (integer).

Pick the 25 most important stories from the input. Each "ref" must match a
headline number shown above. Keep each "text" to one tight sentence.

RULES
- Output pure JSON only. No markdown fences. No text before or after.
"""


ECONOMIC_USER = """INPUT — ECONOMIC / MARKET NEWS HEADLINES (numbered):
{headlines}

TASK
Return ONLY a valid JSON object with exactly these keys:

1. "summary": an array of exactly 25 objects. Each object has:
   - "text": a single-sentence market-moving summary.
   - "ref": the number of the source headline it is based on (integer).

2. "india_market_outlook": one paragraph, 3-4 sentences, on Nifty/Sensex,
   sectors, rupee, FII flows.

3. "usa_market_outlook": one paragraph, 3-4 sentences, on S&P 500/Nasdaq,
   dollar, Fed, bonds.

RULES
- Each "ref" must match a headline number shown above.
- Keep each "text" to one tight sentence.
- Output pure JSON only. No markdown fences.
"""


def _extract_json(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("DeepSeek returned an empty response")
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def _normalize_items(value, sources, count=25):
    """Turn AI output into [{'text', 'url'}, ...] with URL resolved from 'ref'."""
    if not isinstance(value, list):
        value = []

    out = []
    for entry in value[:count]:
        text = ""
        ref = None
        if isinstance(entry, dict):
            text = str(entry.get("text", "")).strip()
            ref = entry.get("ref")
        elif isinstance(entry, str):
            text = entry.strip()

        url = ""
        try:
            idx = int(ref) - 1
            if 0 <= idx < len(sources):
                url = sources[idx]["url"]
        except (TypeError, ValueError):
            pass

        if text:
            out.append({"text": text, "url": url})

    while len(out) < count:
        out.append({"text": "—", "url": ""})

    return out


def _call_model(system, user):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=4500,
        )
    except Exception:
        print("[summarizer] DeepSeek call failed:", flush=True)
        traceback.print_exc()
        raise

    content = response.choices[0].message.content
    print(f"[summarizer] finish_reason: {response.choices[0].finish_reason}", flush=True)
    return content


def _format_headlines(sources):
    return "\n".join(f"{i+1}. {h['title']}" for i, h in enumerate(sources))


def build_general_briefing(sources):
    prompt = GENERAL_USER.format(headlines=_format_headlines(sources))
    content = _call_model(GENERAL_SYSTEM, prompt)
    data = _extract_json(content)
    return {"general_summary": _normalize_items(data.get("summary"), sources)}


def build_economic_briefing(sources):
    prompt = ECONOMIC_USER.format(headlines=_format_headlines(sources))
    content = _call_model(ECONOMIC_SYSTEM, prompt)
    data = _extract_json(content)
    return {
        "investment_summary": _normalize_items(data.get("summary"), sources),
        "india_market_outlook": str(data.get("india_market_outlook", "unclear")).strip(),
        "usa_market_outlook": str(data.get("usa_market_outlook", "unclear")).strip(),
    }
