"""Vercel serverless function: POST /api/breakdown — task -> ordered checklist."""
import json
import os
import re
import ssl
import urllib.request
from http.server import BaseHTTPRequestHandler

MODEL = os.environ.get("HEADROOM_MODEL", "claude-haiku-4-5-20251001")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

BREAKDOWN_SYSTEM = """You are Headroom — a calm, sharp chief-of-staff. The user has \
one task on their mind and needs it turned into a concrete, ordered plan so they know \
exactly what to do next, without having to hold the whole thing in their head.

Voice: plain, specific, doable. Each step should be something they could start in the \
next few minutes — not a restatement of the task, an actual next physical action.

Return ONLY valid JSON (no prose, no code fences) matching exactly:
{
  "steps": ["first concrete step", "second concrete step", "..."]
}

Rules:
- 3 to 6 steps, ordered start to finish.
- Each step is a short imperative phrase (max ~10 words) — an action, not a goal.
- Break big/vague tasks into smaller ones; don't pad a small task with filler steps.
- No markdown, no emojis, no headers, no numbering in the text itself. JSON only."""


def _post_messages(system: str, user: str, max_tokens: int = 400) -> str:
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


def shape_breakdown(d: dict) -> dict:
    steps = []
    for s in (d.get("steps") or [])[:6]:
        s = str(s).strip()
        if s:
            steps.append(s)
    return {"steps": steps[:6] or ["Open it and reread what's actually being asked.",
                                   "Write down the one outcome that would count as done.",
                                   "Do the smallest first step, right now."]}


def mock_breakdown(thought: str, reason: str) -> dict:
    snippet = thought.strip().rstrip(".")
    if len(snippet) > 50:
        snippet = snippet[:47] + "…"
    return {
        "ok": True, "source": "mock", "reason": reason,
        "steps": [
            f"Reread \"{snippet}\" and write the one outcome that counts as done.",
            "Break it into the 2-3 pieces it's actually made of.",
            "Do the smallest piece first — five minutes, no more.",
            "Block time for the rest, then step away.",
        ],
    }


def call_breakdown(thought: str) -> dict:
    if not API_KEY:
        return mock_breakdown(thought, reason="no_api_key")
    try:
        text = _post_messages(BREAKDOWN_SYSTEM, thought)
        return {"ok": True, "source": MODEL, **shape_breakdown(json.loads(_clean(text)))}
    except Exception as e:  # noqa: BLE001
        print(f"[headroom] breakdown call failed: {e}")
        return mock_breakdown(thought, reason="api_unreachable")


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
        return self._send(200, call_breakdown(thought))
