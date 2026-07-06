# 02 — Feature Guide

Everything the app does, page by page. Nothing here needs technical knowledge.

---

## The arrival

When the site opens, a short **loading moment** plays — a dark screen with a
counter rolling up to 100 and calming words fading through ("Breathe… Arrive…
Set it down"). This isn't just decoration: it gives the brain animation a moment
to load so the first thing you see is perfect. Then the screen gently assembles
itself, piece by piece.

---

## Screen 1 — Brain dump (the home)

A large, slowly rotating **image of a brain** fills the screen, glowing against a
starfield. This is the heart of the product.

**Emptying your head**
- A single input at the bottom reads *"What's on your mind?"* You type a thought,
  press Enter, and it becomes a **neuron** — a point of light on the brain.
- Before adding, you pick what *kind* of thought it is with a coloured dot:
  - **Task** (blue) — work that needs focused effort
  - **To-do** (teal) — an errand or bit of life admin
  - **Keeping me up** (red) — a worry that loops
  - **Idea** (purple) — something to explore or make
  - **Goal** (amber) — a longer-term aspiration, with a target date
- Each category clusters on its own region of the brain, so your mind literally
  sorts itself into place.

**The neurons themselves**
- Worries pulse red-hot. More urgent thoughts glow brighter. Bigger thoughts are
  bigger points of light. It's an at-a-glance emotional map of your head.

**Opening a thought** (click any neuron)
A card appears with everything for that one thought:
- Edit the text; set its **size** (small / medium / large) and mood ratings
  (joy / stress / excitement).
- **Help me set this down** — the AI coach gives a short reframe, two or three
  concrete ways to offload it, and a grounding note. (For worries it reads
  *"Help me set this down"*; for tasks, *"Break it down"* into a step checklist.)
- **Quiet session** — start a focused timer on just this thought (see Screen 2).
- Mark it done (it settles into a "Set down" list) or delete it.

**The mental-load bar**
Along the top of the side panel, a bar shows how full your head is — *Clear,
Light, Busy, Heavy* — and which category is **"running hot"** right now, with a
one-tap offer to take a two-minute reset.

**The Coach**
If your load is high and you haven't emptied your head in a while, a gentle prompt
appears offering a **two-minute breathing reset** — a calming ring that breathes
in and out with a countdown. Afterwards it asks how your head feels (1–10) and
points you at the single heaviest thing to pick back up. It never nags; you can
always say "not now."

**Sweep my head**
When you're too overloaded to sort anything, one button opens a blank page. You
pour *everything* out in one stream, and the AI splits it into individual, tidy,
categorised thoughts for you to approve with a tap — then drops them all onto the
brain at once.

**Plan my day**
One tap and the AI reads your open list and tells you the two or three things that
actually matter today, and what you can consciously *not* worry about.

**The morning briefing**
A "sun" button opens a welcome panel: a greeting, your key numbers (how much
headroom you have, thoughts open, worries), and a box to ask the app anything.

**The pop-out pill**
A small always-on-top mini-window (in Chrome/Edge) that floats over your other
work, showing your headroom and a quick box to capture a thought the moment it
strikes — without switching back to the site.

**Your full list**
A side drawer (the "Your mind" button) holds every thought, grouped by category
with counts, done items tucked into a "Set down" section at the bottom.

---

## Screen 2 — Focus

A timer for doing one thing properly. Modelled on the Pomodoro method (focused
rounds separated by short breaks).

- A large **ring timer** sits centre-screen. Inside it, you pick a thought to
  focus on (or "just focus"), choose a length (15 / 25 / 45 minutes), and start.
- The ring fills as you work. When a round ends, it offers **"Take 5?"** — a
  proper five-minute break with its own green ring ("Stand up. Look far away").
  Then it's back for the next round. Little dots track how many rounds you've done.

**The honesty feature (the standout)**
Headroom quietly notices when you *leave the Focus tab* mid-round.
- If you're gone more than a few minutes, it sends a notification: *"Still on
  task? — is this part of it?"*
- When you come back, it asks: *"You were away 6 minutes. Was that part of the
  task?"* — you answer **Part of the task** or **I drifted**.
- The final recap then tells you the truth: your true focus time versus time
  adrift ("28m true focus · −17m adrift"), with a log of each time you stepped
  away, labelled by *your own* answers.

Important: this only notices you leaving the browser tab — it **cannot see which
websites you visit or what's on your screen**. (See [04 — How It's Built](04-how-its-built.md)
for why that matters.)

**The recap**
When you finish, a breakdown shows exactly what happened: true focus minutes,
rounds completed, task steps ticked off, thoughts you jotted down mid-session, and
a "how does your head feel?" rating. You can mark the task done right there.

**Today's sessions**
A side rail shows a timeline of every focus session you've done today.

---

## Screen 3 — Overview

Your day and your mental state, at a glance. Opens with a warm greeting and the
date.

- **Three glance cards** — how much headroom you have right now, what you cleared
  yesterday, and how long since you last emptied your head.
- **Ask Headroom** — a chat box that can see your whole list. Ask "what should I
  set down first?" or "what can wait until next week?" and get a grounded answer.
- **State of mind** — a load-reactive brain that reflects how busy your head is.
- **Headroom over time** — a 14-day trend line of how clear your head has been,
  with dots showing how it *actually felt* after your resets. (Computed calm vs.
  felt calm, side by side — the most honest chart in the app.)
- **Needs your attention** — your worries and most urgent items, first.
- **Today's to-dos** and a **habit tracker** with streaks.
- **Quiet sessions** — a timeline of your focus sessions with an honest per-session
  breakdown (including any time that drifted).
- **On track today** — a simple progress meter.

---

## The AI helpers, summarised

| Helper | What it does |
|--------|--------------|
| Help me set this down | Reframes a worry + 2–3 ways to offload it + a calm note |
| Break it down | Turns a big task into a short, tickable checklist |
| Sweep my head | Sorts a freeform brain-dump into tidy, categorised thoughts |
| Plan my day | Names the few things that matter today and what to park |
| Ask Headroom | Answers questions about your own list |

All of these degrade gracefully: with the AI switched off they still return
sensible, pre-written responses, so the app is never broken.
