# BDayRadar

BDayRadar is a local FastAPI website that signs in to the user's own Telegram account through Telegram's official user API and displays birthdays that are visible in that account's contacts.

## Requirements

You need Python 3.10 or newer and a Telegram `api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org). The app is intended to run on `127.0.0.1`, not as a public service.

## Setup

The easiest option is to download and run the launcher. It automatically clones or fast-forwards the repository, creates the virtual environment, installs dependencies, creates `.env` on first run, and starts the website:

```bash
curl -fsSL https://raw.githubusercontent.com/vyasanbmathew2008/BDayRadar/main/run.sh -o run-bdayradar.sh
chmod +x run-bdayradar.sh
./run-bdayradar.sh
```

On the first run, the launcher prompts for your Telegram `api_id` and `api_hash`. It saves them in a local `.env` file with restrictive permissions and does not overwrite an existing valid `.env`. You can run the same command again later to fetch GitHub updates and restart the app.

If you prefer manual setup, create and activate a virtual environment, install dependencies, copy `.env.example` to `.env`, add your Telegram credentials, and run `python3 app.py`.

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Enter your phone number, the login code Telegram provides, and your 2FA password if Telegram requests it.

## Privacy and security

The app only requests contacts belonging to the authenticated Telegram account and reads birthday fields that Telegram returns for those contacts. It does not search arbitrary users, bypass privacy settings, or scrape Telegram Web. OTPs and 2FA passwords are sent to Telegram through the local process and are not written to disk by this app. Telethon creates a local session file after successful authentication; `.gitignore` prevents that file and `.env` from being committed.

Do not expose this development server to the public internet. Do not share the generated `telegram_session.session` file, your `.env` file, your OTP, or your 2FA password. To invalidate the session, use the app's **Log out** button or revoke the session in Telegram's **Settings → Devices**.

## Data limitations

Telegram only exposes birthdays according to each contact's configured privacy settings. A contact may omit a birthday, omit the year, or hide it from you. The app therefore cannot and should not reveal birthdays that Telegram does not return.
