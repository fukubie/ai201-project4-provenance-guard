import json
import re
import statistics
import uuid
import datetime

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from groq import Groq

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

audit_log: dict = {}

_GROQ_SYSTEM_PROMPT = """You are an AI-detection classifier. Analyze the user-provided text for patterns \
characteristic of AI-generated writing: uniform sentence length, generic transitional phrases \
("Furthermore,", "It is important to note that", "In conclusion,"), low semantic surprise, \
and predictable structural flow.

Return ONLY a JSON object in this exact format with no other text:
{"score": <float between 0.0 and 1.0>}

Where 0.0 means the text is almost certainly human-written and 1.0 means the text is almost certainly AI-generated."""


def score_text_groq(text: str) -> float:
    try:
        client = Groq()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _GROQ_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=32,
        )
        raw = response.choices[0].message.content
        score = json.loads(raw)["score"]
        return max(0.0, min(1.0, float(score)))
    except Exception:
        return 0.0


_STDEV_NORMALIZATION = 15.0


def score_text_stylometric(text: str) -> float:
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if len(sentences) < 2:
        return 0.5  # insufficient data per planning.md blind-spot note
    lengths = [len(s.split()) for s in sentences]
    std_dev = statistics.stdev(lengths)
    # High std_dev = variable (human-like) → low score; low std_dev = uniform (AI-like) → high score
    return max(0.0, min(1.0, 1.0 - (std_dev / _STDEV_NORMALIZATION)))


def get_transparency_label(score: float) -> str:
    if score < 0.40:
        return "Verified Original: Our system recognizes this text as original, human-crafted creative work."
    elif score <= 0.75:
        return "Attribution Unclear: This text contains a blend of structural patterns. We are unable to confidently verify its origin."
    else:
        return "Generated Content: Our system has detected a high probability of automated or AI-assisted writing patterns within this text."


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute")
def submit():
    body = request.get_json(silent=True)
    if not body or not body.get("text", "").strip():
        return jsonify({"error": "Request body must be JSON with a non-empty 'text' field."}), 400

    text = body["text"]
    content_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    groq_score = score_text_groq(text)
    stylometric_score = score_text_stylometric(text)
    confidence = round((0.65 * groq_score) + (0.35 * stylometric_score), 4)
    label = get_transparency_label(confidence)

    audit_log[content_id] = {
        "content_id": content_id,
        "text": text,
        "groq_score": groq_score,
        "stylometric_score": stylometric_score,
        "confidence": confidence,
        "label": label,
        "timestamp": timestamp,
        "status": "classified",
    }

    return jsonify({
        "content_id": content_id,
        "confidence": confidence,
        "label": label,
        "timestamp": timestamp,
    })


@app.route("/appeal", methods=["POST"])
def appeal():
    body = request.get_json(silent=True)
    if not body or not body.get("content_id", "").strip() or not body.get("creator_reasoning", "").strip():
        return jsonify({"error": "Request body must be JSON with non-empty 'content_id' and 'creator_reasoning' fields."}), 400

    content_id = body["content_id"]
    if content_id not in audit_log:
        return jsonify({"error": f"No entry found for content_id '{content_id}'."}), 404

    entry = audit_log[content_id]
    if entry["status"] != "classified":
        return jsonify({"error": f"Entry is already '{entry['status']}' and cannot be re-appealed."}), 409

    entry["status"] = "under_review"
    entry["creator_reasoning"] = body["creator_reasoning"]
    entry["appeal_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": "Your appeal has been received. This entry is now marked for human review.",
    })


@app.route("/log", methods=["GET"])
def get_log():
    return jsonify({
        "entries": list(audit_log.values()),
        "count": len(audit_log),
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
