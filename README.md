# BDayRadar

BDayRadar is a local FastAPI website that signs in to the user's own Telegram account through Telegram's official user API and displays birthdays that are visible in that account's contacts.

## Requirements

You need Python 3.10 or newer and a Telegram `api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org). The app is intended to run on `127.0.0.1`, not as a public service.

## Setup

Create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Copy the environment template and fill in your own Telegram credentials:

```bash
cp .env.example .env
```

Start the website:

```bash
python3 app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Enter your phone number, the login code Telegram provides, and your 2FA password if Telegram requests it.

## Privacy and security

The app only requests contacts belonging to the authenticated Telegram account and reads birthday fields that Telegram returns for those contacts. It does not search arbitrary users, bypass privacy settings, or scrape Telegram Web. OTPs and 2FA passwords are sent to Telegram through the local process and are not written to disk by this app. Telethon creates a local session file after successful authentication; `.gitignore` prevents that file and `.env` from being committed.

Do not expose this development server to the public internet. Do not share the generated `telegram_session.session` file, your `.env` file, your OTP, or your 2FA password. To invalidate the session, use the app's **Log out** button or revoke the session in Telegram's **Settings → Devices**.

## Data limitations

Telegram only exposes birthdays according to each contact's configured privacy settings. A contact may omit a birthday, omit the year, or hide it from you. The app therefore cannot and should not reveal birthdays that Telegram does not return.
