#!/usr/bin/env sh
# PRAHARI-SIM demo launcher for macOS and Linux (Phase 10). Serves the static dashboard (dashboard/dist) on
# http://localhost:8765 and opens it in presenter mode: no engine, no internet. Builds the dashboard first when
# dist/ is missing or when called with --build (that step needs Node.js and `npm install` done once).
#   scripts/demo.sh            # serve and open
#   scripts/demo.sh --build    # rebuild (copies recordings/ and results/ in), then serve
#   PORT=9000 scripts/demo.sh  # another port
set -e
cd "$(dirname "$0")/.."
PORT="${PORT:-8765}"
URL="http://localhost:$PORT/?presenter=1"

if [ "$1" = "--build" ] || [ ! -f dashboard/dist/index.html ]; then
  echo "building the dashboard…"
  (cd dashboard && npm run build)
fi

# Open the browser once the server is up (keys: 1–9 steps, Space play, S/R switches, F full screen).
( sleep 1
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1
  else echo "open $URL in a browser"; fi ) &

echo "serving dashboard/dist on $URL — press Ctrl-C to stop"
if command -v python3 >/dev/null 2>&1; then
  exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory dashboard/dist
fi
cd dashboard && exec npx vite preview --port "$PORT" --strictPort
