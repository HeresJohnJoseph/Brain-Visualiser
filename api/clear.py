"""Vercel serverless function: POST /api/clear — per-thought AI clearing."""
import json
import os
import re
import ssl
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

MODEL = os.environ.get("HEADROOM_MODEL", "claude-haiku-4-5-20251001")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

SYSTEM_PROMPT = """You are Headroom — a calm, sharp coach whose single job is to \
reduce the mental bandwidth a worry is taking up RIGHT NOW.

The user dumps one thing occupying their mind (a looming meeting, an awkward \
email, a decision, a nagging task). You give them just enough to set it down and \
get on with their day.

Voice: warm but unsentimental. Talk like a trusted, switched-on friend who happens \
to be brilliant at this — never clinical, never a listicle of self-help cliches, \
never patronising. Be specific to THEIR situation, not generic.

Return ONLY valid JSON (no prose, no code fences) matching exactly:
{
  "headline": "one short empathetic reframe that takes the charge out of it (max ~14 words)",
  "actions": [
    {"title": "imperative next move (max ~6 words)", "detail": "one concrete sentence on how/when"}
  ],
  "calm_note": "one short grounding line to settle the nerves (max ~16 words)"
}

Rules:
- 2 or 3 actions, no more. Each must genuinely OFFLOAD the worry (park it, prep it,
  shrink it, or hand it off) so it stops circling — not vague advice like "stay positive".
- If a time/event is mentioned, anchor an action to it (e.g. block 30 min tomorrow AM).
- No markdown, no emojis, no headers. JSON only."""


def _post_messages(system: str, user: str, max_tokens: int = 700) -> str:
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


def _shape(d: dict) -> dict:
    actions = []
    for a in (d.get("actions") or [])[:3]:
        if isinstance(a, dict):
            actions.append({"title": str(a.get("title", "")).strip(),
                            "detail": str(a.get("detail", "")).strip()})
        elif isinstance(a, str):
            actions.append({"title": a.strip(), "detail": ""})
    return {
        "headline": str(d.get("headline", "")).strip() or "Let's give this some headroom.",
        "actions": actions,
        "calm_note": str(d.get("calm_note", "")).strip(),
    }


def parse_model_json(text: str) -> dict:
    try:
        return _shape(json.loads(_clean(text)))
    except Exception:
        return _shape({"headline": "Here's a way to set this down.",
                       "actions": [], "calm_note": text.strip()[:200]})


def mock_response(thought: str, reason: str) -> dict:
    snippet = thought.strip().rstrip(".")
    if len(snippet) > 60:
        snippet = snippet[:57] + "…"
    return {
        "ok": True,
        "source": "mock",
        "reason": reason,
        "headline": "This is a known, finite thing — not a cloud over your whole day.",
        "actions": [
            {"title": "Park it on paper",
             "detail": f"Write the one outcome you want from \"{snippet}\" and close the tab in your head."},
            {"title": "Book the prep",
             "detail": "Block 30 focused minutes tomorrow morning so it has a home — and stop rehearsing it now."},
            {"title": "Name the worst case",
             "detail": "Say it out loud; it's almost always survivable, and that drains the dread."},
        ],
        "calm_note": "You've handled harder. Set it down — it'll be here when you choose to pick it up.",
    }


def call_claude(thought: str) -> dict:
    if not API_KEY:
        return mock_response(thought, reason="no_api_key")
    try:
        text = _post_messages(SYSTEM_PROMPT, thought)
        return {"ok": True, "source": MODEL, **parse_model_json(text)}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        print(f"[headroom] Anthropic HTTP {e.code}: {body[:300]}")
        return mock_response(thought, reason=f"api_error_{e.code}")
    except Exception as e:  # noqa: BLE001
        print(f"[headroom] Anthropic call failed: {e}")
        return mock_response(thought, reason="api_unreachable")


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
        thought = str(payload.get("thought", "")).strip()
        if not thought:
            return self._send(400, {"error": "empty thought"})
        return self._send(200, call_claude(thought))
