# Deploying to a VPS

Target: Ubuntu 22.04/24.04 VPS, **2 GB RAM** recommended (headless Chrome
uses ~0.5–1 GB per check; on 1 GB add swap). Any provider works —
DigitalOcean, Hetzner, Linode, Contabo, AWS Lightsail.

## Architecture on the server

```
internet ──> nginx :80/443 (basic auth) ──> gunicorn :5001 (webapp.py)
                                                 │
                                                 └─ spawns main.py (bot)
                                                        └─ headless Google Chrome
```

One systemd service (`olx-notifier`) runs gunicorn; with `BOT_AUTOSTART=true`
the web app launches the bot itself, so both survive reboots.

## Quick install

```bash
ssh root@<vps-ip>
git clone https://github.com/sahal-iocod/olx-kerala-cars.git /tmp/olx
sudo bash /tmp/olx/deploy/setup-vps.sh
```

Then finish:

```bash
sudo nano /opt/olx-notifier/.env                 # Telegram token + chat id
sudo htpasswd -c /etc/nginx/.htpasswd-olx admin  # web UI password
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl start olx-notifier
```

Open `http://<vps-ip>/`, log in, confirm the green "Bot is running" dot.

## Manual install (what the script does)

1. `apt install python3 python3-venv git nginx apache2-utils`
2. Install **Google Chrome** (`google-chrome-stable`). The scraper uses
   `channel="chrome"` because OLX blocks Playwright's bundled Chromium.
3. `useradd --system olx`, clone into `/opt/olx-notifier`, `chown -R olx`.
4. As `olx`: `python3 -m venv venv && venv/bin/pip install -r requirements.txt`
   then `venv/bin/playwright install chromium` (fallback browser) and as root
   `venv/bin/playwright install-deps chromium` (shared libs).
5. `cp .env.example .env`, fill in values, `chmod 600 .env`.
6. Copy `deploy/olx-notifier.service` → `/etc/systemd/system/`,
   `deploy/nginx-olx-notifier.conf` → `/etc/nginx/sites-available/` (+ symlink),
   `deploy/logrotate-olx-notifier` → `/etc/logrotate.d/`.
7. `systemctl daemon-reload && systemctl enable --now olx-notifier`.

## .env on the server

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
HEADLESS=true            # must stay true — no display on a VPS
CHECK_INTERVAL_MINUTES=5
WEBAPP_HOST=127.0.0.1    # nginx fronts it; never expose 5001 directly
WEBAPP_PORT=5001
BOT_AUTOSTART=true
FLASK_DEBUG=false
```

## Operating it

| Task | Command |
|---|---|
| Status | `systemctl status olx-notifier` |
| Web app logs | `journalctl -u olx-notifier -f` |
| Scraper logs | `tail -f /opt/olx-notifier/bot.log` |
| Restart everything | `sudo systemctl restart olx-notifier` |
| Update code | `cd /opt/olx-notifier && sudo -u olx git pull && sudo -u olx venv/bin/pip install -r requirements.txt && sudo systemctl restart olx-notifier` |
| Change filters | use the web UI (writes `filters.json`; bot picks it up next cycle) |

## HTTPS (optional, needs a domain)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d olx.yourdomain.com
```

## Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

Port 5001 is bound to localhost only and is not opened.

## Troubleshooting

- **`ERR_HTTP2_PROTOCOL_ERROR` / empty listings** — OLX's edge (Akamai)
  fingerprints the HTTP/2 connection and kills it with `INTERNAL_ERROR`,
  while the same request over HTTP/1.1 answers `200 OK`. The scraper now
  launches Chrome with `--disable-http2` to avoid this. Confirm from the VPS:

  ```bash
  curl -s -o /dev/null -w "%{http_code}\n" https://www.olx.in/            # 000 = h2 blocked
  curl -s --http1.1 -o /dev/null -w "%{http_code}\n" https://www.olx.in/  # 200 = IP is fine
  ```

  Also check Chrome is present — `google-chrome --version` must work for the
  `olx` user, or the bundled Chromium gets used instead.
- **Bot stopped after reboot** — check `BOT_AUTOSTART=true` in `.env`.
- **OOM / killed** — raise `MemoryMax` in the unit or add swap:
  `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`.
- **"Access Denied" in the log** — OLX served an edge block page. The bot now
  detects this, fails the check (so it backs off instead of reporting zero new
  cars) and clears `browser_state.json` so a block cookie isn't replayed.
  If it persists, increase `CHECK_INTERVAL_MINUTES` (10–15). `HEADLESS=false`
  is not an option on a VPS without Xvfb.
