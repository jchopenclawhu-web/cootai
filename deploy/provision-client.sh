#!/usr/bin/env bash
# provision-client.sh — set up ONE CooTai client agent on a fresh Ubuntu VPS.
#
# Run as root on the new host:
#   ./provision-client.sh <client-slug> <line-channel-token> <line-channel-secret>
#
# Result: systemd service cootai-agent@<slug>, listening on an auto-assigned port,
#         ready for a Cloudflare tunnel hostname <slug>.cootai.tw
set -euo pipefail

SLUG="${1:?usage: provision-client.sh <slug> <channel-access-token> <channel-secret>}"
CA_TOKEN="${2:?missing channel access token}"
CA_SECRET="${3:?missing channel secret}"

[[ "$SLUG" =~ ^[a-z0-9][a-z0-9-]{1,30}$ ]] || { echo "slug must be lowercase a-z0-9-"; exit 1; }

BASE=/srv/cootai/clients/$SLUG
REPO_URL="${COOTAI_REPO_URL:-https://github.com/jchopenclawhu-web/cootai.git}"

echo "==> Provisioning client: $SLUG at $BASE"

# ---------- 1. system packages ----------
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
  python3 python3-venv python3-pip ffmpeg curl ca-certificates git

# ---------- 2. cloudflared ----------
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "==> Installing cloudflared"
  curl -fsSL -o /tmp/cloudflared.deb \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  dpkg -i /tmp/cloudflared.deb >/dev/null
  rm -f /tmp/cloudflared.deb
fi

# ---------- 2b. swap file (KVM 1/2 boxes are RAM-tight during Whisper load) ----------
if ! swapon --show | grep -q .; then
  echo "==> Adding 2G swap"
  fallocate -l 2G /swapfile && chmod 600 /swapfile
  mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# ---------- 3. code + venv ----------
mkdir -p "$BASE"
if [ -d "$BASE/agent/.git" ]; then
  git -C "$BASE/agent" fetch --depth 1 origin main
  git -C "$BASE/agent" reset --hard origin/main
else
  echo "==> Cloning repo"
  git clone --depth 1 "$REPO_URL" "$BASE/agent"
fi

python3 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install --quiet --upgrade pip
"$BASE/venv/bin/pip" install --quiet numpy faster-whisper

# ---------- 4. per-client config ----------
cat > "$BASE/agent/credentials.json" <<JSON
{"channel_access_token": "$CA_TOKEN", "channel_secret": "$CA_SECRET"}
JSON
chmod 600 "$BASE/agent/credentials.json"
chown -R root:root "$BASE"

# ---------- 5. port allocation (one port per client on this host) ----------
PORTFILE=/srv/cootai/ports
touch "$PORTFILE"
if grep -q "^$SLUG:" "$PORTFILE"; then
  PORT=$(grep "^$SLUG:" "$PORTFILE" | cut -d: -f2)
else
  PORT=$(( 8080 + $(wc -l < "$PORTFILE") ))
  echo "$SLUG:$PORT" >> "$PORTFILE"
fi
echo "==> Assigned port $PORT"

# ---------- 6. LLM key (per-host, shared secret file) ----------
ENVFILE=/etc/cootai/llm.env
mkdir -p /etc/cootai
if [ ! -f "$ENVFILE" ]; then
  echo "OPENROUTER_API_KEY=" > "$ENVFILE"
  chmod 600 "$ENVFILE"
  echo "!! Edit $ENVFILE and add OPENROUTER_API_KEY before starting."
fi

# ---------- 7. systemd template unit ----------
cat > /etc/systemd/system/cootai-agent@.service <<'UNIT'
[Unit]
Description=CooTai LINE agent (%i)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/cootai/llm.env
Environment=PYTHONUNBUFFERED=1
Environment=RETENTION_DAYS=90
WorkingDirectory=/srv/cootai/clients/%i/agent
ExecStart=/bin/bash -c 'PORT=$(grep "^%i:" /srv/cootai/ports | cut -d: -f2); \
  exec /srv/cootai/clients/%i/venv/bin/python /srv/cootai/clients/%i/agent/webhook.py'
Restart=always
RestartSec=5
# hardening — keep in sync with docs/技術特性說明書.md §6
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true
ReadWritePaths=/srv/cootai/clients/%i/agent

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now "cootai-agent@$SLUG"

sleep 8
if systemctl is-active --quiet "cootai-agent@$SLUG"; then
  echo "==> Agent active on port $PORT"
else
  echo "!! Agent failed. Check: journalctl -u cootai-agent@$SLUG -n 50"
  exit 1
fi

# ---------- 8. next steps ----------
cat <<EOF

============================================================
Client '$SLUG' provisioned.

  Local check : curl -H 'User-Agent: Mozilla/5.0' http://127.0.0.1:$PORT/   (expect 405)

NEXT — Cloudflare tunnel (run on THIS host):
  1. cloudflared tunnel create $SLUG
  2. Write ~/.cloudflared/config.yml:
       tunnel: <tunnel-id>
       credentials-file: /root/.cloudflared/<tunnel-id>.json
       ingress:
         - hostname: $SLUG.cootai.tw
           service: http://localhost:$PORT
         - service: http_status:404
  3. cloudflared tunnel route dns $SLUG $SLUG.cootai.tw
  4. systemd unit for cloudflared, then:
  5. LINE console -> Messaging API -> Webhook URL: https://$SLUG.cootai.tw
  6. LINE console -> response settings: Chat ON / Webhooks ON / Auto-reply OFF / Greeting OFF

Whisper model (~464MB) downloads on first voice message, or pre-warm:
  systemctl restart cootai-agent@$SLUG   # warmup thread fetches it
============================================================
EOF
