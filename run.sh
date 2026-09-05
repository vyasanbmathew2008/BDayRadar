#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${BDAYRADAR_REPO_URL:-https://github.com/vyasanbmathew2008/BDayRadar.git}"
APP_DIR="${BDAYRADAR_DIR:-$HOME/BDayRadar}"
BRANCH="${BDAYRADAR_BRANCH:-main}"

log() { printf '\n[BDayRadar] %s\n' "$*"; }
fail() { printf '\n[BDayRadar] ERROR: %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || fail "git is required."
command -v python3 >/dev/null 2>&1 || fail "python3 is required."

if [[ -d "$APP_DIR/.git" ]]; then
  log "Updating $APP_DIR from GitHub..."
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
else
  if [[ -e "$APP_DIR" ]]; then
    fail "$APP_DIR exists but is not a Git repository. Set BDAYRADAR_DIR to another directory or remove it."
  fi
  log "Cloning BDayRadar from GitHub..."
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

if [[ ! -d .venv ]]; then
  log "Creating Python virtual environment..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

if [[ ! -f .env || "$(grep -E '^TELEGRAM_API_(ID|HASH)=' .env 2>/dev/null || true)" == *"replace_with_your_api_hash"* ]]; then
  if [[ -f .env ]]; then
    log "Existing .env contains placeholder credentials; keeping a backup at .env.backup."
    cp .env ".env.backup.$(date +%Y%m%d%H%M%S)"
  fi
  umask 077
  printf '\nTelegram credentials are required. They are saved only in %s/.env.\n' "$APP_DIR"
  read -r -p 'Telegram API ID: ' api_id
  read -r -s -p 'Telegram API hash: ' api_hash
  printf '\n'
  [[ -n "$api_id" && -n "$api_hash" ]] || fail "Both Telegram API ID and API hash are required."
  cat > .env <<EOF
TELEGRAM_API_ID=$api_id
TELEGRAM_API_HASH=$api_hash
TELEGRAM_SESSION=telegram_session
PORT=8000
EOF
  chmod 600 .env
fi

log "Starting BDayRadar at http://127.0.0.1:8000"
exec python app.py
