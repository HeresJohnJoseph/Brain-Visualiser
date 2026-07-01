#!/bin/bash
# Double-click to start Headroom. Leave this window open while you use it.
cd "$(dirname "$0")"

# Optional: paste your key here to get live Claude coaching (otherwise runs in demo mode)
# export ANTHROPIC_API_KEY="sk-ant-..."

( sleep 1; open "http://localhost:4500" ) &

echo "──────────────────────────────────────────────"
echo "  HEADROOM is starting…"
echo "  Your browser will open at http://localhost:4500"
echo "  Close this window (or Ctrl+C) when you're done."
echo "──────────────────────────────────────────────"

lsof -ti:4500 | xargs kill -9 2>/dev/null
python3 server.py
