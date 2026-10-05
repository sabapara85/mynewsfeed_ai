"""Daily Briefing — Flask backend with two report types."""
import io
import os
import threading
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, abort, jsonify, render_template, request, send_file

from news import get_general_headlines, get_investment_headlines
from pdf_maker import build_pdf
from summarizer import build_economic_briefing, build_general_briefing

app = Flask(__name__)

IST = ZoneInfo("Asia/Kolkata")
CACHE_TTL = 600          # 10 minutes per type
MAX_REPORTS = 20

_lock = threading.Lock()
_cache = {"general": {"ts": 0.0, "id": None},
          "economic": {"ts": 0.0, "id": None}}
_reports = {}


# ---------- Global error handler (returns JSON, not HTML) ----------
@app.errorhandler(Exception)
def handle_error(e):
    import traceback
    traceback.print_exc()
    return jsonify(error=f"{type(e).__name__}: {e}"), 500


def _now_ist():
    return datetime.now(IST)


def _session_label(dt):
    h = dt.hour
    if h < 11:
        return "Morning"
    if h < 17:
        return "Noon"
    return "Night"


def _generate(report_type: str, force: bool = True) -> dict:
    if report_type not in ("general", "economic"):
        raise ValueError("Invalid report type")

    with _lock:
        cached = _cache[report_type]
        if (not force and cached["id"]
                and time.time() - cached["ts"] < CACHE_TTL
                and cached["id"] in _reports):
            return _reports[cached["id"]]

    now = _now_ist()

    if report_type == "general":
        headlines = get_general_headlines()
        briefing = build_general_briefing(headlines)
        label = "General Awareness"
    else:
        headlines = get_investment_headlines()
        briefing = build_economic_briefing(headlines)
        label = "Economic & Investment Impact"

    payload = {
        "id": uuid.uuid4().hex[:12],
        "type": report_type,
        "report_label": label,
        "session": _session_label(now),
        "date": now.strftime("%d %b %Y"),
        "generated_at": now.strftime("%H:%M"),
        "headline_count": len(headlines),
        **briefing,
    }
    payload["pdf"] = build_pdf(payload).getvalue()

    with _lock:
        _reports[payload["id"]] = payload
        _cache[report_type] = {"id": payload["id"], "ts": time.time()}
        if len(_reports) > MAX_REPORTS:
            for key in list(_reports.keys())[:-MAX_REPORTS]:
                _reports.pop(key, None)

    return payload


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify(status="ok")


@app.route("/api/generate", methods=["POST"])
def api_generate():
    req = request.get_json(silent=True) or {}
    report_type = req.get("type", "general")

    if report_type not in ("general", "economic"):
        return jsonify(error="Invalid report type"), 400

    try:
        data = _generate(report_type, force=True)
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        return jsonify(error=f"Generation failed: {type(exc).__name__}: {exc}"), 500

    return jsonify({
        "id": data["id"],
        "type": data["type"],
        "report_label": data["report_label"],
        "session": data["session"],
        "date": data["date"],
        "generated_at": data["generated_at"],
        "headline_count": data["headline_count"],
        "general_summary": data.get("general_summary"),
        "investment_summary": data.get("investment_summary"),
        "india_market_outlook": data.get("india_market_outlook"),
        "usa_market_outlook": data.get("usa_market_outlook"),
    })


@app.route("/download/<report_id>")
def download(report_id):
    with _lock:
        report = _reports.get(report_id)
    if not report:
        abort(404)

    safe_label = report["report_label"].replace(" ", "").replace("&", "")
    filename = f"{safe_label}_{report['session']}_{report['date'].replace(' ', '-')}.pdf"
    return send_file(
        io.BytesIO(report["pdf"]),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
