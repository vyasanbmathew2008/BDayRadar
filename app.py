import asyncio
import calendar
import os
from contextlib import asynccontextmanager
from datetime import date
from html import escape
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from telethon import TelegramClient, functions
from telethon.errors import SessionPasswordNeededError, PhoneCodeExpiredError, PhoneCodeInvalidError

load_dotenv()

API_ID = int(os.environ.get("TELEGRAM_API_ID", "0"))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
SESSION_FILE = os.environ.get("TELEGRAM_SESSION", "telegram_session")

if not API_ID or not API_HASH:
    raise RuntimeError("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env before starting the app.")

client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
state = {
    "phone": None,
    "phone_code_hash": None,
    "needs_2fa": False,
    "message": None,
    "message_kind": "info",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    await client.connect()
    yield
    await client.disconnect()


app = FastAPI(title="BDayRadar", lifespan=lifespan)


def set_message(text: str, kind: str = "info") -> None:
    state["message"] = text
    state["message_kind"] = kind


def birthday_sort_key(item: dict) -> tuple[int, int, str]:
    today = date.today()
    year = today.year
    try:
        candidate = date(year, item["month"], item["day"])
    except ValueError:
        candidate = date(year, 2, 28)
    if candidate < today:
        year += 1
    return (year, item["month"], item["day"])


def render_page(content: str = "") -> str:
    message = ""
    if state["message"]:
        message = f'<div class="notice {escape(state["message_kind"])}">{escape(state["message"])}</div>'
        state["message"] = None

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>BDayRadar</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0; background: #f4f7fb; color: #152238; }}
    main {{ max-width: 760px; margin: 48px auto; padding: 0 20px; }}
    .card {{ background: white; border: 1px solid #dce5f0; border-radius: 18px; padding: 28px; box-shadow: 0 10px 30px #17335c12; }}
    h1 {{ margin-top: 0; letter-spacing: -0.03em; }}
    h2 {{ margin-bottom: 8px; }}
    p, label {{ color: #51627a; line-height: 1.55; }}
    form {{ display: grid; gap: 12px; margin-top: 18px; }}
    input {{ box-sizing: border-box; width: 100%; border: 1px solid #c9d5e5; border-radius: 10px; padding: 12px 13px; font: inherit; }}
    button {{ border: 0; border-radius: 10px; padding: 12px 16px; background: #2864d7; color: white; font: inherit; cursor: pointer; }}
    button.secondary {{ background: #e8eef8; color: #1d3b6c; }}
    .notice {{ border-radius: 10px; padding: 12px 14px; margin: 18px 0; }}
    .error {{ background: #fff0f0; color: #9c2e2e; }}
    .success {{ background: #edfbf3; color: #1e7045; }}
    .info {{ background: #edf4ff; color: #2a548f; }}
    .birthday {{ display: flex; justify-content: space-between; gap: 16px; padding: 15px 0; border-bottom: 1px solid #e7edf5; }}
    .birthday:last-child {{ border-bottom: 0; }}
    .name {{ font-weight: 700; }}
    .date {{ color: #2864d7; font-weight: 650; white-space: nowrap; }}
    .muted {{ color: #728198; font-size: .92rem; }}
    .toolbar {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; }}
    .toolbar form {{ margin: 0; }}
    code {{ background: #eef2f8; padding: 2px 5px; border-radius: 5px; }}
  </style>
</head>
<body><main><div class="card">
  <h1>BDayRadar</h1>
  {message}
  {content}
</div></main></body></html>"""


def login_form() -> str:
    return """<h2>Connect your Telegram account</h2>
<p>This local app uses Telegram's official user authorization flow. Your OTP and optional 2FA password are submitted directly to Telegram through the local process and are not saved by this app.</p>
<form method="post" action="/auth/request-code">
  <label for="phone">Phone number in international format</label>
  <input id="phone" name="phone" placeholder="+1234567890" autocomplete="tel" required>
  <button type="submit">Send Telegram code</button>
</form>
<p class="muted">Only birthdays that Telegram makes visible to your logged-in account can be shown.</p>"""


async def get_visible_birthdays() -> list[dict]:
    contacts = await client(functions.contacts.GetContactsRequest(hash=0))
    results = []
    for user in getattr(contacts, "users", []):
        birthday = getattr(user, "birthday", None)
        if not birthday or not getattr(birthday, "day", None) or not getattr(birthday, "month", None):
            continue
        name = " ".join(part for part in [getattr(user, "first_name", None), getattr(user, "last_name", None)] if part)
        if not name:
            name = getattr(user, "username", None) or str(getattr(user, "id", "Telegram contact"))
        results.append({
            "name": name,
            "day": birthday.day,
            "month": birthday.month,
            "year": getattr(birthday, "year", None),
        })
    results.sort(key=birthday_sort_key)
    return results


@app.get("/", response_class=HTMLResponse)
async def home():
    if not await client.is_user_authorized():
        return HTMLResponse(render_page(login_form()))
    try:
        birthdays = await get_visible_birthdays()
    except Exception as exc:
        return HTMLResponse(render_page(f"<h2>Could not load birthdays</h2><div class=\"notice error\">{escape(str(exc))}</div><a href=\"/\">Try again</a>"), status_code=502)

    rows = "".join(
        f'<div class="birthday"><span><span class="name">{escape(item["name"])}</span>'
        f'<br><span class="muted">Visible birthday in your Telegram contacts</span></span>'
        f'<span class="date">{calendar.month_name[item["month"]]} {item["day"]}</span></div>'
        for item in birthdays
    )
    body = f"""<div class="toolbar"><div><h2>Upcoming birthdays</h2><p class="muted">Showing birthdays available to this Telegram account.</p></div>
<form method="post" action="/logout"><button class="secondary" type="submit">Log out</button></form></div>
{rows or '<p>No visible birthdays were returned for your contacts.</p>'}
<p class="muted">Telegram’s birthday API may return only information permitted by each contact’s privacy settings.</p>"""
    return HTMLResponse(render_page(body))


@app.post("/auth/request-code", response_class=HTMLResponse)
async def request_code(phone: str = Form(...)):
    phone = phone.strip()
    try:
        sent = await client.send_code_request(phone)
        state.update({"phone": phone, "phone_code_hash": sent.phone_code_hash, "needs_2fa": False})
        set_message("Telegram sent a login code. Enter it below.", "success")
        body = """<h2>Enter Telegram code</h2><p>Check your Telegram app or the delivery method Telegram selected for this login.</p>
<form method="post" action="/auth/verify"><label for="code">Login code</label><input id="code" name="code" inputmode="numeric" autocomplete="one-time-code" required><label for="password">2FA password (only if requested)</label><input id="password" name="password" type="password" autocomplete="current-password"><button type="submit">Verify and continue</button></form>"""
        return HTMLResponse(render_page(body))
    except Exception as exc:
        set_message(f"Could not request a Telegram code: {exc}", "error")
        return RedirectResponse("/", status_code=303)


@app.post("/auth/verify", response_class=HTMLResponse)
async def verify(code: str = Form(...), password: str = Form("")):
    if not state["phone"] or not state["phone_code_hash"]:
        set_message("Your login attempt expired. Start again.", "error")
        return RedirectResponse("/", status_code=303)
    try:
        if state["needs_2fa"]:
            if not password:
                raise ValueError("Telegram requires your 2FA password.")
            await client.check_password(password)
        else:
            try:
                await client.sign_in(state["phone"], code.strip(), phone_code_hash=state["phone_code_hash"])
            except SessionPasswordNeededError:
                state["needs_2fa"] = True
                if not password:
                    set_message("Telegram requires your 2FA password. Enter it and submit again.", "info")
                    body = """<h2>Telegram 2FA required</h2><form method="post" action="/auth/verify"><input type="hidden" name="code" value=""><label for="password">2FA password</label><input id="password" name="password" type="password" autocomplete="current-password" required><button type="submit">Finish sign-in</button></form>"""
                    return HTMLResponse(render_page(body))
                await client.check_password(password)
        state.update({"phone": None, "phone_code_hash": None, "needs_2fa": False})
        set_message("Signed in successfully.", "success")
        return RedirectResponse("/", status_code=303)
    except (PhoneCodeExpiredError, PhoneCodeInvalidError) as exc:
        set_message(f"Telegram rejected the code: {exc}", "error")
        return RedirectResponse("/", status_code=303)
    except Exception as exc:
        set_message(f"Sign-in failed: {exc}", "error")
        return RedirectResponse("/", status_code=303)


@app.post("/logout")
async def logout():
    await client.log_out()
    state.update({"phone": None, "phone_code_hash": None, "needs_2fa": False})
    set_message("You have been logged out. The local session file was invalidated by Telegram.", "success")
    return RedirectResponse("/", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")), reload=False)
