#!/bin/bash
# Ensure influence dash + permanent tunnel are up. Prints URLs + status.
# Token is read from dash/.token (0600) for URL construction on local stdout only.
set -e
cd "$(dirname "$0")/.."
DASH_DIR="$PWD/dash"
# Public dash = tunnel-only. No app token on every visit (DASH_TOKEN empty).
# If you later want an extra gate: export DASH_TOKEN before starting, then
# open once with ?token=… — browser gets an HttpOnly cookie and you're done.
TOKEN="${DASH_TOKEN:-}"
CFG="$HOME/.cloudflared/influence-dash.yml"
HOST="agentcom.org"
PHONE_HOST="phone.agentcom.org"

# ensure phone edge + tunnel
if ! curl -s -m 3 http://127.0.0.1:8794/api/health >/dev/null 2>&1 && ! curl -s -m 3 http://127.0.0.1:8794/v1/health >/dev/null 2>&1; then
  if [ ! -f "$DASH_DIR/phone_proxy.pid" ] || ! kill -0 "$(cat "$DASH_DIR/phone_proxy.pid")" 2>/dev/null; then
    echo "starting phone proxy :8794..."
    nohup python3 "$DASH_DIR/phone_proxy.py" > "$DASH_DIR/phone_proxy.log" 2>&1 &
    echo $! > "$DASH_DIR/phone_proxy.pid"
  fi
fi
if [ -f "$DASH_DIR/phone_tunnel_token" ]; then
  # single runner only: check for a live cloudflared holding this tunnel token
  if ! pgrep -af 'cloudflared.*run' | grep -q 'phone'; then
    echo "starting phone tunnel..."
    nohup cloudflared tunnel --no-autoupdate run --token "$(cat "$DASH_DIR/phone_tunnel_token")" \
      > "$DASH_DIR/phone_tunnel.log" 2>&1 &
    echo $! > "$DASH_DIR/phone_tunnel.pid"
  fi
fi

dash_up=0
if curl -s -m 5 http://127.0.0.1:8793/api/health | grep -q '"ok": true'; then
  dash_up=1
else
  echo "starting dash on :8793 (LIVE=1)..."
  DASH_TOKEN="$TOKEN" DASH_PORT=8793 LIVE=1 DASH_DB="$DASH_DIR/influence.db" \
    DASH_JOURNAL="$DASH_DIR/decisions.db" PATH="$PWD/.venv/bin:$PATH" \
    nohup python3 "$DASH_DIR/server.py" > "$DASH_DIR/dash.log" 2>&1 &
  echo "$!" > "$DASH_DIR/.dash.pid"
  sleep 4
  curl -s -m 8 http://127.0.0.1:8793/api/health | grep -q '"ok": true' \
    && dash_up=1 || dash_up=0
fi

tun_up=0
if pgrep -f "cloudflared.*influence-dash" > /dev/null 2>&1; then
  tun_up=1
else
  echo "starting permanent tunnel..."
  nohup cloudflared tunnel --config "$CFG" run influence-dash \
    > "$DASH_DIR/tunnel-perm.log" 2>&1 &
  echo "$!" > "$DASH_DIR/.tunnel-perm.pid"
  sleep 8
  pgrep -f "cloudflared.*influence-dash" > /dev/null 2>&1 && tun_up=1 || tun_up=0
fi

echo "dash: $([ "$dash_up" = 1 ] && echo UP || echo DOWN) (loopback :8793)"
echo "tunnel: $([ "$tun_up" = 1 ] && echo UP || echo DOWN) (influence-dash)"
echo -n "phone edge: "; curl -s -m 5 "https://$PHONE_HOST/v1/status" || echo FAIL
if [ "${1:-}" = "status" ]; then
  echo -n "local health: "; curl -s -m 8 http://127.0.0.1:8793/api/health || echo FAIL
  echo -n "public health: "; curl -s -m 10 "https://$HOST/api/health" || echo FAIL
  echo -n "public state w/o token: "; curl -s -m 10 -o /dev/null -w "%{http_code}\n" "https://$HOST/api/state"
  echo -n "phone status: "; curl -s -m 10 "https://$PHONE_HOST/v1/status" || echo FAIL
  exit 0
fi
if [ -n "$TOKEN" ]; then
  echo "open: http://127.0.0.1:8793/?token=$TOKEN"
  echo "public: https://$HOST/?token=$TOKEN"
else
  echo "open: http://127.0.0.1:8793/"
  echo "public: https://$HOST/"
fi
echo "phone: https://$PHONE_HOST/v1/status"
