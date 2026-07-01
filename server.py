#!/usr/bin/env python3
"""
HEADROOM — local server + Claude proxy
======================================
Serves the brain visualizer and proxies "clear my mind" requests to the
Anthropic API. Python standard library only — no pip install, no node.

Run:    python3 server.py
Then:   open http://localhost:4500

Env:
    ANTHROPIC_API_KEY   your key (sk-ant-...). If unset, the app still works
                        in MOCK mode with a sensible templated response.
    HEADROOM_MODEL      optional override (default: claude-haiku-4-5-20251001)
    PORT                optional (default: 4500)
"""

import json
import os
import re
import ssl
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "4500"))
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
    """Raw Anthropic Messages call. Returns concatenated text or raises."""
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


def call_claude(thought: str) -> dict:
    """Call Anthropic Messages API. Falls back to mock if no key or on error."""
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


def call_focus(items: list) -> dict:
    """Day-planning briefing over the user's open items."""
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


def _clean(text: str) -> str:
    """Strip code fences / surrounding prose down to the JSON object."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        json.loads(cleaned)
        return cleaned
    except Exception:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        return m.group(0) if m else cleaned


def parse_model_json(text: str) -> dict:
    """Be forgiving: strip code fences, grab the first {...} block."""
    try:
        return _shape(json.loads(_clean(text)))
    except Exception:
        # Last resort: treat the whole thing as a calm note.
        return _shape({"headline": "Here's a way to set this down.",
                       "actions": [], "calm_note": text.strip()[:200]})


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
    """Offline day-plan fallback built from the user's own list."""
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


def mock_response(thought: str, reason: str) -> dict:
    """Offline / no-key fallback so the app is always demoable."""
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


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter logs
        print("[headroom] " + (fmt % args))

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/" or path == "":
            path = "/index.html"
        if path == "/health":
            return self._send(200, json.dumps({"ok": True, "model": MODEL,
                                               "has_key": bool(API_KEY)}))
        target = (ROOT / path.lstrip("/")).resolve()
        if not str(target).startswith(str(ROOT)) or not target.is_file():
            return self._send(404, json.dumps({"error": "not found"}))
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css",
            ".js": "application/javascript",
            ".svg": "image/svg+xml",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
        }.get(target.suffix, "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)

    def do_POST(self):
        route = self.path.split("?", 1)[0]
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._send(400, json.dumps({"error": "bad request"}))

        if route == "/api/clear":
            thought = str(payload.get("thought", "")).strip()
            if not thought:
                return self._send(400, json.dumps({"error": "empty thought"}))
            return self._send(200, json.dumps(call_claude(thought)))

        if route == "/api/focus":
            items = payload.get("items") or []
            if not isinstance(items, list) or not items:
                return self._send(400, json.dumps({"error": "no items"}))
            return self._send(200, json.dumps(call_focus(items)))

        return self._send(404, json.dumps({"error": "not found"}))


def main():
    mode = f"LIVE (model: {MODEL})" if API_KEY else "MOCK (no ANTHROPIC_API_KEY set)"
    print("─" * 60)
    print("  HEADROOM is running")
    print(f"  → http://localhost:{PORT}")
    print(f"  AI mode: {mode}")
    print("  Ctrl+C to stop")
    print("─" * 60)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
