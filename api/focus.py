"""Vercel serverless function: POST /api/focus — day-planning briefing."""
import json
import os
import re
import ssl
import urllib.request
from http.server import BaseHTTPRequestHandler

MODEL = os.environ.get("HEADROOM_MODEL", "claude-haiku-4-5-20251001")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

FOCUS_SYSTEM = """You are Headroom — a calm chief-of-staff for someone's day. You \
are handed their open to-dos and what's pressing. Your job: cut the overwhelm and \
tell them what actually matters, in a way that lowers their shoulders.

Voice: warm, decisive, human. Like a brilliant friend who's seen their list and \
says "okay, breathe — here's what we're actually doing." Never a generic productivity \
lecture. Be concrete to THEIR list.

Return ONLY valid JSON (no prose, no code fences) matching exactly:
{
  "brief": "one warm, grounding sentence about today (max ~18 words)",
  "focus": [
    {"title": "the task, echoed in a few words", "note": "why it's first / the smallest way to start"}
  ],
  "park": "one sentence naming what they can consciously NOT worry about today (max ~18 words)"
}

Rules:
- Pick the 2-3 things that genuinely matter most (urgent + high-leverage). No more.
- Each note must reduce friction: name the first 5-minute move, not the whole task.
- 'park' should give explicit permission to drop or defer something.
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


def shape_focus(d: dict) -> dict:
    focus = []
    for f in (d.get("focus") or [])[:3]:
        if isinstance(f, dict):
            focus.append({"title": str(f.get("title", "")).strip(),
                          "note": str(f.get("note", "")).strip()})
        elif isinstance(f, str):
            focus.append({"title": f.strip(), "note": ""})
    return {
        "brief": str(d.get("brief", "")).strip() or "Here's where to point your energy today.",
        "focus": focus,
        "park": str(d.get("park", "")).strip(),
    }


def mock_focus(items: list, reason: str) -> dict:
    openish = [i for i in items if not i.get("done")]
    ordered = sorted(openish, key=lambda i: (not i.get("urgent"),
                                             0 if "over" in str(i.get("due", "")).lower() else 1))
    seen, top = set(), []
    for it in ordered:
        t = str(it.get("title", "")).strip()
        if t and t not in seen:
            seen.add(t); top.append(it)
        if len(top) == 3:
            break
    focus = []
    for i, it in enumerate(top):
        note = ("Start with the first 5 minutes — open it, don't finish it."
                if i == 0 else "Next, while you've got momentum.")
        focus.append({"title": str(it.get("title", "")).strip(), "note": note})
    leftover = openish[3:]
    park = ("Everything else can wait until tomorrow — it's parked, not forgotten."
            if leftover else "Nothing else is on fire. Protect your focus and breathe.")
    return {"ok": True, "source": "mock", "reason": reason,
            "brief": "Two or three things matter today. The rest is noise — let it be quiet.",
            "focus": focus, "park": park}


def call_focus(items: list) -> dict:
    lines = []
    for it in items[:20]:
        tag = []
        if it.get("urgent"):
            tag.append("URGENT")
        if it.get("due"):
            tag.append("due " + str(it["due"]))
        suffix = (" [" + ", ".join(tag) + "]") if tag else ""
        lines.append("- " + str(it.get("title", "")).strip() + suffix)
    user = "Here is everything on my plate today:\n" + "\n".join(lines) + \
           "\n\nTell me what to focus on and what to let go."
    if not API_KEY:
        return mock_focus(items, reason="no_api_key")
    try:
        text = _post_messages(FOCUS_SYSTEM, user)
        return {"ok": True, "source": MODEL, **shape_focus(json.loads(_clean(text)))}
    except Exception as e:  # noqa: BLE001
        print(f"[headroom] focus call failed: {e}")
        return mock_focus(items, reason="api_unreachable")


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
        items = payload.get("items") or []
        if not isinstance(items, list) or not items:
            return self._send(400, {"error": "no items"})
        return self._send(200, call_focus(items))
