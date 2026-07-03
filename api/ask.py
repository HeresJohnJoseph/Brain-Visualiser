"""Vercel serverless function: POST /api/ask — question answered over the thought list."""
import json
import os
import re
import ssl
import urllib.request
from http.server import BaseHTTPRequestHandler

MODEL = os.environ.get("HEADROOM_MODEL", "claude-haiku-4-5-20251001")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

ASK_SYSTEM = """You are Headroom — a calm, sharp companion who can see everything on \
the user's mind (their thought list is provided). Answer their question with that \
context. Brief, warm, concrete — a few sentences, or 2-3 tight moves if they ask what \
to do.

Return ONLY valid JSON (no prose, no code fences) matching exactly:
{"answer": "your reply, plain text, max ~90 words"}

Rules: ground every answer in their actual thoughts when relevant; never invent items; \
if their head is empty, say so kindly. No markdown, no emojis. JSON only."""


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


def _thoughts_context(thoughts: list) -> str:
    lines = []
    for t in thoughts[:40]:
        if not isinstance(t, dict):
            continue
        flag = " (done)" if t.get("done") else ""
        lines.append(f"- [{t.get('cat', '?')}/P{t.get('prio', 2)}] "
                     f"{str(t.get('text', '')).strip()[:120]}{flag}")
    return "\n".join(lines) or "(nothing — the list is empty)"


def mock_ask(question: str, thoughts: list, reason: str) -> dict:
    open_t = [t for t in thoughts if isinstance(t, dict) and not t.get("done")]
    if not open_t:
        ans = "Your head looks clear — nothing open right now. Enjoy the quiet."
    else:
        top = sorted(open_t, key=lambda t: -int(t.get("prio", 2) or 2))[:2]
        names = " and ".join('"' + str(t.get("text", ""))[:40] + '"' for t in top)
        ans = (f"You have {len(open_t)} open thoughts. The heaviest right now: {names}. "
               "Start with five minutes on the first one.")
    return {"ok": True, "source": "mock", "reason": reason, "answer": ans}


def call_ask(question: str, thoughts: list) -> dict:
    if not API_KEY:
        return mock_ask(question, thoughts, reason="no_api_key")
    user = ("My current thoughts:\n" + _thoughts_context(thoughts) +
            "\n\nMy question: " + question)
    try:
        out = _post_messages(ASK_SYSTEM, user)
        d = json.loads(_clean(out))
        ans = str(d.get("answer", "")).strip() or "I'm here — ask me again in a different way?"
        return {"ok": True, "source": MODEL, "answer": ans[:600]}
    except Exception as e:  # noqa: BLE001
        print(f"[headroom] ask call failed: {e}")
        return mock_ask(question, thoughts, reason="api_unreachable")


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
        question = str(payload.get("question", "")).strip()
        thoughts = payload.get("thoughts") or []
        if not question:
            return self._send(400, {"error": "empty question"})
        return self._send(200, call_ask(question, thoughts))
