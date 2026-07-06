# 04 — How It's Built (in plain English)

You don't need any of this to understand the product — but it's useful context if
someone asks "how does it work?" or "is my data safe?"

---

## It's a website, not an app to install

Headroom runs entirely in a web browser. There's nothing to download, no account
to create, no login. You visit the address and it's there. It works on a laptop
or a phone.

## Where it lives

- The site is hosted on a service called **Vercel**, which serves it to anyone who
  visits — quickly and for free at this scale.
- The code lives in a **GitHub repository** (an online folder of the project's
  files). Whenever the code is updated there, the live site updates itself
  automatically within a minute or two.
- **Live address:** https://brain-visualiser.vercel.app

## How it's put together (and why that's a strength)

The whole app is built with plain, standard web building blocks — no heavy
frameworks, no complicated build machinery. In practical terms this means:

- **It's cheap and reliable.** Fewer moving parts, almost nothing to break, nearly
  free to run.
- **It's easy to hand over.** Any competent web developer can pick it up and
  understand it. It isn't locked to any one specialist or vendor.
- **It loads fast** and works even on modest devices.

## Your data stays with you (privacy)

This is important and worth being clear on:

- Everything you type — your thoughts, worries, focus history — is saved **only in
  your own browser, on your own device.** It is *not* uploaded to a server, not
  stored in a database, not visible to anyone else.
- Because of this, your notes are private by design. The flip side: they live on
  the device you used, so they don't automatically appear on a different computer.
  (Making them sync across devices would be a future decision, and would change
  this privacy picture — see the roadmap.)

## About the "focus honesty" feature

The Focus screen can tell when you leave its browser tab, and for how long. It uses
this to give you an honest picture of your focus time. But it's worth stating
plainly what it **cannot** do:

- It cannot see which websites you visit, what apps you open, or anything on the
  rest of your screen. Web browsers deliberately wall websites off from each other
  for your safety.
- So instead of spying, Headroom simply *asks* you when you come back whether the
  detour was part of your task. It's an honesty tool built on trust, not
  surveillance. (A competitor called Rize does the deeper screen-watching version —
  but only because it's a program you install on your computer with special
  permissions, which many of its users find uncomfortable.)

## The AI, and its costs

- The optional AI helpers are powered by **Claude**, Anthropic's AI. Specifically a
  small, fast, inexpensive model.
- Turning it on requires a single secret key (an "API key") set once in the hosting
  settings. Usage costs are tiny — fractions of a cent per request.
- With the key switched off, the app falls back to sensible built-in responses, so
  it never appears broken. There is no scenario where a visitor sees an error
  because the AI is unavailable.
