"""Vercel serverless function: POST /api/sweep — freeform brain dump -> sorted thoughts."""
import json
import os
import re
import ssl
import urllib.request
from http.server import BaseHTTPRequestHandler

MODEL = os.environ.get("HEADROOM_MODEL", "claude-haiku-4-5-20251001")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

SWEEP_SYSTEM = """You are Headroom — a calm assistant that tidies a messy brain dump. \
The user typed everything on their mind in one unsorted stream. Split it into \
individual, self-contained thoughts.

Return ONLY valid JSON (no prose, no code fences) matching exactly:
{
  "items": [
    {"text": "the thought, lightly cleaned up", "cat": "task|todo|worry|idea|goal", "size": "s|m|l"}
  ]
}

Rules:
- Preserve the user's own words as much as possible; fix only obvious typos, drop filler.
- One item per distinct thought; never merge two concerns into one item. Max 12 items.
- cat: task = work needing focused effort; todo = errand or small life admin; worry = a
  fear or anxiety that loops ("keeping me up"); idea = something to explore or create;
  goal = longer-term aspiration.
- size: s = minutes, m = an hour or two, l = big or multi-day.
- No markdown, no emojis. JSON only."""


def _post_messages(system: str, user: str, max_tokens: int = 900) -> str:
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=40, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(
        b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
    )


def _clean(text: str) -> str:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        json.loads(cleaned)
        return cleaned
    except Exception:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        return m.group(0) if m else cleaned


def shape_sweep(d: dict) -> dict:
    cats = {"task", "todo", "worry", "idea", "goal"}
    sizes = {"s", "m", "l"}
    items = []
    for it in (d.get("items") or [])[:12]:
        if not isinstance(it, dict):
            continue
        text = str(it.get("text", "")).strip()
        if not text:
            continue
        items.append({"text": text[:200],
                      "cat": it.get("cat") if it.get("cat") in cats else "todo",
                      "size": it.get("size") if it.get("size") in sizes else "m"})
    return {"items": items}


WORRY_HINTS = ("worried", "worry", "afraid", "scared", "anxious", "what if",
               "will we", "can't stop", "keeping me up")
TODO_HINTS = ("buy ", "book ", "call ", "email ", "renew ", "pay ", "pick up",
              "schedule ", "cancel ")
IDEA_HINTS = ("idea", "maybe ", "what about", "could try", "should try", "imagine")


def mock_sweep(text: str, reason: str) -> dict:
    parts = []
    for line in re.split(r"[\n;]+|(?<=[.!?])\s+", text):
        line = line.strip(" -•\t")
        if len(line) > 2:
            parts.append(line[:200])
        if len(parts) == 12:
            break
    items = []
    for p in parts:
        low = p.lower()
        if "?" in p or any(h in low for h in WORRY_HINTS):
            cat = "worry"
        elif any(low.startswith(h) or (" " + h) in low for h in TODO_HINTS):
            cat = "todo"
        elif any(h in low for h in IDEA_HINTS):
            cat = "idea"
        else:
            cat = "task"
        items.append({"text": p, "cat": cat,
                      "size": "l" if len(p) > 90 else ("m" if len(p) > 40 else "s")})
    return {"ok": True, "source": "mock", "reason": reason, "items": items}


def call_sweep(text: str) -> dict:
    if not API_KEY:
        return mock_sweep(text, reason="no_api_key")
    try:
        out = _post_messages(SWEEP_SYSTEM, text)
        return {"ok": True, "source": MODEL, **shape_sweep(json.loads(_clean(out)))}
    except Exception as e:  # noqa: BLE001
        print(f"[headroom] sweep call failed: {e}")
        return mock_sweep(text, reason="api_unreachable")


class handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._send(400, {"error": "bad request"})
        text = str(payload.get("text", "")).strip()
        if not text:
            return self._send(400, {"error": "empty text"})
        return self._send(200, call_sweep(text))
