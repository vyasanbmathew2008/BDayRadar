# BDayRadar

BDayRadar is a local FastAPI website that signs in to the user's own Telegram account through Telegram's official user API and displays birthdays that are visible in that account's contacts.

## Requirements

You need Python 3.10 or newer and a Telegram `api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org). The app is intended to run on `127.0.0.1`, not as a public service.

## Setup

The local launcher is intentionally not stored in GitHub. Keep `run.sh` inside your local `bdayradar` directory next to your existing `.env`, then run:

```bash
cd /path/to/bdayradar
chmod +x ./run.sh
./run.sh
```

The launcher pulls the latest repository update, prepares the virtual environment, installs dependencies, and starts the website. It requires `.env` to already exist and **never creates, overwrites, backs up, or edits it**. Your Telegram credentials therefore remain in your local directory only. You can run the same command again later to update the code and restart the app.

If you prefer manual setup, create and activate a virtual environment, install dependencies, copy `.env.example` to `.env`, add your Telegram credentials, and run `python3 app.py`.

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Enter your phone number, the login code Telegram provides, and your 2FA password if Telegram requests it.

## Privacy and security

The app only requests contacts belonging to the authenticated Telegram account and reads birthday fields that Telegram returns for those contacts. It does not search arbitrary users, bypass privacy settings, or scrape Telegram Web. OTPs and 2FA passwords are sent to Telegram through the local process and are not written to disk by this app. Telethon creates a local session file after successful authentication; `.gitignore` prevents that file and `.env` from being committed.

Do not expose this development server to the public internet. Do not share the generated `telegram_session.session` file, your `.env` file, your OTP, or your 2FA password. To invalidate the session, use the app's **Log out** button or revoke the session in Telegram's **Settings → Devices**.

## Data limitations

Telegram only exposes birthdays according to each contact's configured privacy settings. A contact may omit a birthday, omit the year, or hide it from you. The app therefore cannot and should not reveal birthdays that Telegram does not return.
