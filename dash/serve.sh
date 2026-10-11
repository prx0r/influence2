#!/bin/bash
# Serve influence dash on loopback. Optional token: DASH_TOKEN or dash/.token.
# Default (no token) = open — correct when access is only via the CF tunnel.
set -e
cd "$(dirname "$0")"
TOKFILE=.token
if [ -n "${DASH_TOKEN:-}" ]; then
  :
elif [ -f "$TOKFILE" ] && [ "${DASH_REQUIRE_TOKEN:-0}" = "1" ]; then
  export DASH_TOKEN="$(cat "$TOKFILE")"
else
  export DASH_TOKEN=""
fi
export DASH_PORT="${DASH_PORT:-8793}"
export LIVE="${LIVE:-0}"
export DASH_DB="${DASH_DB:-$PWD/influence.db}"
export DASH_JOURNAL="${DASH_JOURNAL:-$PWD/decisions.db}"
export PATH="/home/ubuntu/influence/.venv/bin:$PATH"
if [ -n "$DASH_TOKEN" ]; then
  echo "dash token gate ON"
  echo "open: http://127.0.0.1:$DASH_PORT/?token=$DASH_TOKEN"
else
  echo "dash open (tunnel is the perimeter)"
  echo "open: http://127.0.0.1:$DASH_PORT/"
fi
if [ "$1" == "--tunnel" ]; then
  nohup python3 server.py > dash.log 2>&1 &
  echo $! > .dash.pid
  nohup cloudflared tunnel --url "http://127.0.0.1:$DASH_PORT" --no-autoupdate > tunnel.log 2>&1 &
  echo $! > .tunnel.pid
  sleep 6
  grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" tunnel.log | head -n 1 || tail -n 5 tunnel.log
else
  exec python3 server.py
fi
