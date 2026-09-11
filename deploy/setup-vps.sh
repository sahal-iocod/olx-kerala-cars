#!/usr/bin/env bash
# One-shot setup for a fresh Ubuntu 22.04 / 24.04 VPS.
# Run as root:  sudo bash deploy/setup-vps.sh
#
# What it does:
#   1. Installs Python, Google Chrome (real Chrome — OLX blocks the
#      bundled Playwright Chromium), nginx and Playwright's OS deps
#   2. Creates a dedicated "olx" user and /opt/olx-notifier
#   3. Clones/updates the repo, builds the venv, installs requirements
#   4. Installs the systemd unit, nginx site and logrotate config
#
# After it finishes: edit /opt/olx-notifier/.env, create the nginx
# password, then `systemctl start olx-notifier`.

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/sahal-iocod/olx-kerala-cars.git}"
APP_DIR=/opt/olx-notifier
APP_USER=olx

if [[ $EUID -ne 0 ]]; then
    echo "Run as root: sudo bash $0" >&2
    exit 1
fi

echo "==> 1/6 System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip git curl gnupg ca-certificates \
    nginx apache2-utils fonts-liberation xvfb

echo "==> 2/6 Google Chrome (stable)"
if ! command -v google-chrome >/dev/null 2>&1; then
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
        | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list
    apt-get update
    apt-get install -y google-chrome-stable
fi
google-chrome --version

echo "==> 3/6 App user and directory"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR"

if [[ -d "$APP_DIR/.git" ]]; then
    echo "    repo exists — pulling latest"
    sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only || true
else
    if [[ -f "$(dirname "$0")/../webapp.py" ]]; then
        echo "    copying local checkout"
        cp -r "$(cd "$(dirname "$0")/.." && pwd)/." "$APP_DIR/"
        rm -rf "$APP_DIR/venv"
    else
        git clone "$REPO_URL" "$APP_DIR"
    fi
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> 4/6 Python venv + dependencies"
sudo -u "$APP_USER" bash -c "
    cd '$APP_DIR' &&
    python3 -m venv venv &&
    venv/bin/pip install --upgrade pip &&
    venv/bin/pip install -r requirements.txt &&
    PLAYWRIGHT_BROWSERS_PATH='$APP_DIR/.pw-browsers' venv/bin/playwright install chromium
"
# OS libraries Chrome/Chromium need (root-only step)
"$APP_DIR/venv/bin/playwright" install-deps chromium

echo "==> 5/6 .env"
if [[ ! -f "$APP_DIR/.env" ]]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo "    created $APP_DIR/.env — EDIT IT with your Telegram token/chat id"
fi

echo "==> 6/6 systemd, nginx, logrotate"
cp "$APP_DIR/deploy/olx-notifier.service" /etc/systemd/system/olx-notifier.service
cp "$APP_DIR/deploy/logrotate-olx-notifier" /etc/logrotate.d/olx-notifier
cp "$APP_DIR/deploy/nginx-olx-notifier.conf" /etc/nginx/sites-available/olx-notifier
ln -sf /etc/nginx/sites-available/olx-notifier /etc/nginx/sites-enabled/olx-notifier
rm -f /etc/nginx/sites-enabled/default
systemctl daemon-reload
systemctl enable olx-notifier

if [[ ! -f /etc/nginx/.htpasswd-olx ]]; then
    echo
    echo "    No nginx password yet. Create one now:"
    echo "      sudo htpasswd -c /etc/nginx/.htpasswd-olx admin"
fi

cat <<MSG

Setup complete. Remaining steps:

  1. sudo nano $APP_DIR/.env          # TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  2. sudo htpasswd -c /etc/nginx/.htpasswd-olx admin
  3. sudo nginx -t && sudo systemctl reload nginx
  4. sudo systemctl start olx-notifier
  5. Open http://<your-vps-ip>/  (log in with the htpasswd user)

Check on it:
  systemctl status olx-notifier
  journalctl -u olx-notifier -f
  tail -f $APP_DIR/bot.log
MSG
