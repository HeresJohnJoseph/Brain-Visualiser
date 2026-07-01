# Headroom

A brain visualizer for clearing mental bandwidth. Dump what's circling in your
head — each worry becomes a glowing thought clustered on a real anatomical
brain image, sized by urgency and pulsing red-hot if it's a worry. Tap one and
an AI coach (Claude) gives you a short reframe, 2–3 concrete moves to offload
it, and a grounding note. Rate how it makes you feel (joy / stress /
excitement), plan your whole day in one tap, and see how it all connects on a
force-directed graph.

Three pages, one shared store (`localStorage`):

- **`index.html`** — Brain dump: the visualizer + capture + AI clearing.
- **`dashboard.html`** — Overview: load-reactive hero, to-dos, habit tracker,
  what needs attention.
- **`connections.html`** — Connections: an Obsidian-graph-style view of every
  thought, filterable by category, with "compounding stress" links between
  thoughts you've both rated highly stressful.

## Run it locally

```bash
python3 server.py          # then open http://localhost:4500
```

Or double-click **`Start Headroom.command`**. No `npm install`, no build step
— Python standard library only.

## Live AI vs demo mode

- **Demo mode** (default): works offline with a sensible templated response.
- **Live mode**: set your Anthropic key and the coach uses **Claude Haiku 4.5**:

  ```bash
  export ANTHROPIC_API_KEY="sk-ant-..."
  python3 server.py
  ```

  Override the model with `HEADROOM_MODEL` if you want Sonnet for richer
  responses. The key stays server-side — never exposed in the browser.

## Deploying to Vercel

The app is split so it deploys as-is with zero config:

- `index.html`, `dashboard.html`, `connections.html`, `brain.png` — served as
  static files.
- `api/clear.py`, `api/focus.py` — Vercel Python serverless functions (Vercel
  auto-detects any `.py` file under `/api`), replacing `server.py`'s proxy
  role in production. `server.py` itself is only used for local dev and is
  ignored by Vercel (it's not inside `/api`).

Steps:

1. Push this repo to GitHub.
2. On [vercel.com/new](https://vercel.com/new), import the repo — no build
   command or output directory needed, leave defaults.
3. In the project's **Settings → Environment Variables**, add:
   - `ANTHROPIC_API_KEY` = your key (omit this to run live in demo/mock mode)
   - `HEADROOM_MODEL` (optional, defaults to `claude-haiku-4-5-20251001`)
4. Deploy. `/api/clear` and `/api/focus` work identically to local dev.

## Files

| File | What it is |
|------|------------|
| `index.html` | Brain dump — canvas physics + capture + AI clearing |
| `dashboard.html` | Overview — command-center dashboard |
| `connections.html` | Connections — force-directed graph view |
| `brain.png` | The anatomical brain hero image, shared by all pages |
| `server.py` | Local dev only: static server + Claude proxy |
| `api/clear.py`, `api/focus.py` | Production: Vercel serverless equivalents |
| `Start Headroom.command` | Double-click local launcher |

## How it works

- Thoughts live in `localStorage['brainviz.thoughts.v1']`, habits in
  `localStorage['headroom_habits_v1']` — shared across all three pages, with
  a `storage` event listener keeping tabs in sync.
- `POST /api/clear {thought}` → Claude returns strict JSON
  (`headline`, `actions[]`, `calm_note`), rendered in the thought's card.
- `POST /api/focus {items}` → Claude returns a day brief (`brief`, `focus[]`,
  `park`) covering the 2–3 things that actually matter.
- Cleared thoughts and mood ratings (`joy`/`stress`/`excitement`, 0–5) cache
  on the thought object — instant on revisit, no re-calling the API.
