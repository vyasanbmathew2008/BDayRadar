import calendar
import os
from contextlib import asynccontextmanager
from datetime import date
from html import escape

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from telethon import TelegramClient, functions
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

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


def selected_year(request: Request) -> int:
    current_year = date.today().year
    raw_year = request.query_params.get("year", str(current_year))
    try:
        year = int(raw_year)
    except ValueError:
        return current_year
    return year if 1900 <= year <= 2100 else current_year


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
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f4f7fb; color: #152238; }}
    main {{ max-width: 1420px; margin: 30px auto; padding: 0 20px; }}
    .card {{ background: white; border: 1px solid #dce5f0; border-radius: 18px; padding: 28px; box-shadow: 0 10px 30px #17335c12; }}
    h1 {{ margin: 0; letter-spacing: -0.03em; }}
    h2 {{ margin: 0; }}
    p, label {{ color: #51627a; line-height: 1.55; }}
    form {{ display: grid; gap: 12px; margin-top: 18px; }}
    input {{ box-sizing: border-box; width: 100%; border: 1px solid #c9d5e5; border-radius: 10px; padding: 12px 13px; font: inherit; }}
    button, .button {{ border: 0; border-radius: 10px; padding: 10px 14px; background: #2864d7; color: white; font: inherit; cursor: pointer; text-decoration: none; display: inline-block; }}
    button.secondary, .button.secondary {{ background: #e8eef8; color: #1d3b6c; }}
    .notice {{ border-radius: 10px; padding: 12px 14px; margin: 18px 0; }}
    .error {{ background: #fff0f0; color: #9c2e2e; }}
    .success {{ background: #edfbf3; color: #1e7045; }}
    .info {{ background: #edf4ff; color: #2a548f; }}
    .muted {{ color: #728198; font-size: .92rem; }}
    .calendar-header {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; margin: 22px 0 26px; flex-wrap: wrap; }}
    .year-nav {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
    .year-nav .year {{ font-size: 1.25rem; font-weight: 750; min-width: 88px; text-align: center; }}
    .logout-form {{ margin: 0; display: block; }}
    .months {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }}
    .month {{ border: 1px solid #dce5f0; border-radius: 14px; overflow: hidden; background: #fbfdff; }}
    .month-title {{ margin: 0; padding: 14px 15px 10px; font-size: 1.05rem; }}
    .weekdays, .days {{ display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); }}
    .weekday {{ padding: 7px 4px; color: #7b8ba1; font-size: .72rem; font-weight: 700; text-align: center; text-transform: uppercase; }}
    .day {{ min-height: 74px; padding: 7px; border-top: 1px solid #edf1f6; border-right: 1px solid #edf1f6; background: white; }}
    .day:nth-child(7n) {{ border-right: 0; }}
    .day-number {{ display: block; color: #65768d; font-size: .78rem; font-weight: 700; margin-bottom: 5px; }}
    .day.today {{ background: #eef5ff; box-shadow: inset 0 3px 0 #2864d7; }}
    .day.today .day-number {{ color: #2864d7; }}
    .birthday-chip {{ display: block; border-radius: 6px; background: #e7f7ef; color: #176a43; font-size: .73rem; font-weight: 650; line-height: 1.2; margin-top: 4px; padding: 4px 5px; overflow-wrap: anywhere; }}
    .birthday-chip small {{ display: block; color: #4a8067; font-size: .64rem; font-weight: 500; margin-top: 2px; }}
    .empty {{ color: #a7b3c2; }}
    .legend {{ display: flex; gap: 16px; align-items: center; margin-top: 20px; flex-wrap: wrap; }}
    .legend-item {{ display: inline-flex; align-items: center; gap: 7px; color: #66778f; font-size: .9rem; }}
    .legend-swatch {{ width: 12px; height: 12px; border-radius: 3px; background: #e7f7ef; border: 1px solid #c7ead7; }}
    .legend-today {{ width: 12px; height: 12px; border-radius: 3px; background: #eef5ff; border-top: 3px solid #2864d7; }}
    @media (max-width: 1050px) {{ .months {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 680px) {{ main {{ margin: 14px auto; padding: 0 10px; }} .card {{ padding: 18px 12px; }} .months {{ grid-template-columns: 1fr; }} .day {{ min-height: 68px; padding: 6px 4px; }} .birthday-chip {{ font-size: .68rem; }} }}
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
    """Load birthdays visible to this account from Telegram contact profiles.

    The ordinary contacts.getContacts response does not reliably include the
    birthday field. Telegram's full-user response does, when the birthday is
    visible to the authenticated account. contacts.getBirthdays is also merged
    as the official near-date refresh path.
    """
    contacts_result = await client(functions.contacts.GetContactsRequest(hash=0))
    contacts = list(getattr(contacts_result, "users", []))
    birthdays_by_id: dict[int, object] = {}

    # This official method refreshes birthdays that fall within +/- one day.
    # Its response includes a contact_id -> birthday mapping.
    try:
        near_birthdays = await client(functions.contacts.GetBirthdaysRequest())
        birthdays_by_id.update({
            item.contact_id: item.birthday
            for item in getattr(near_birthdays, "contacts", [])
            if getattr(item, "contact_id", None) and getattr(item, "birthday", None)
        })
        for user in getattr(near_birthdays, "users", []):
            if getattr(user, "birthday", None):
                birthdays_by_id[user.id] = user.birthday
    except Exception:
        # Full profiles below remain the primary path for the annual calendar.
        pass

    visible = []
    for user in contacts:
        birthday = birthdays_by_id.get(getattr(user, "id", None))
        try:
            full = await client(functions.users.GetFullUserRequest(id=user))
            birthday = getattr(getattr(full, "full_user", None), "birthday", None) or birthday
        except Exception:
            # A single unavailable profile should not prevent other contacts
            # from appearing in the calendar.
            pass
        if not birthday or not getattr(birthday, "day", None) or not getattr(birthday, "month", None):
            continue
        name = " ".join(
            part for part in [getattr(user, "first_name", None), getattr(user, "last_name", None)] if part
        )
        if not name:
            name = getattr(user, "username", None) or str(getattr(user, "id", "Telegram contact"))
        visible.append({
            "name": name,
            "day": birthday.day,
            "month": birthday.month,
            "year": getattr(birthday, "year", None),
        })
    return visible


def birthdays_for_calendar(birthdays: list[dict], year: int) -> dict[tuple[int, int], list[dict]]:
    by_date: dict[tuple[int, int], list[dict]] = {}
    leap_year = calendar.isleap(year)
    for item in birthdays:
        month = item["month"]
        day = item["day"]
        # Keep February 29 birthdays visible in every annual view. In non-leap
        # years they appear on February 28 with a clear label.
        display_month, display_day = month, day
        february_29 = month == 2 and day == 29
        if february_29 and not leap_year:
            display_day = 28
        by_date.setdefault((display_month, display_day), []).append({**item, "february_29": february_29})
    for people in by_date.values():
        people.sort(key=lambda person: person["name"].lower())
    return by_date


def render_month(year: int, month: int, by_date: dict[tuple[int, int], list[dict]]) -> str:
    month_days = calendar.monthrange(year, month)[1]
    first_weekday = calendar.monthrange(year, month)[0]
    cells = []
    today = date.today()
    for _ in range(first_weekday):
        cells.append('<div class="day empty" aria-hidden="true"></div>')
    for day in range(1, month_days + 1):
        is_today = year == today.year and month == today.month and day == today.day
        today_class = " today" if is_today else ""
        chips = []
        for person in by_date.get((month, day), []):
            label = escape(person["name"])
            suffix = "<small>February 29 birthday</small>" if person["february_29"] and not calendar.isleap(year) else ""
            chips.append(f'<span class="birthday-chip" title="{label}">{label}{suffix}</span>')
        cells.append(
            f'<div class="day{today_class}"><span class="day-number">{day}</span>{"".join(chips)}</div>'
        )
    while len(cells) % 7:
        cells.append('<div class="day empty" aria-hidden="true"></div>')
    weekdays = "".join(f'<span class="weekday">{name}</span>' for name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    return f"""<section class="month" aria-label="{calendar.month_name[month]} {year}">
  <h3 class="month-title">{calendar.month_name[month]}</h3>
  <div class="weekdays">{weekdays}</div>
  <div class="days">{"".join(cells)}</div>
</section>"""


def render_calendar(year: int, birthdays: list[dict]) -> str:
    by_date = birthdays_for_calendar(birthdays, year)
    months = "".join(render_month(year, month, by_date) for month in range(1, 13))
    current_year = date.today().year
    previous_year = year - 1
    next_year = year + 1
    total_days = 366 if calendar.isleap(year) else 365
    birthday_count = len(birthdays)
    return f"""<div class="calendar-header">
  <div><h2>Birthday calendar</h2><p class="muted">{total_days} days in {year}; {birthday_count} visible contact birthday{'s' if birthday_count != 1 else ''}.</p></div>
  <div class="year-nav">
    <a class="button secondary" href="/?year={previous_year}">Previous</a>
    <span class="year">{year}</span>
    <a class="button secondary" href="/?year={next_year}">Next</a>
    <a class="button secondary" href="/?year={current_year}">Today</a>
  </div>
  <form class="logout-form" method="post" action="/logout"><button class="secondary" type="submit">Log out</button></form>
</div>
<div class="months">{months}</div>
<div class="legend"><span class="legend-item"><span class="legend-swatch"></span>Visible birthday</span><span class="legend-item"><span class="legend-today"></span>Today</span></div>
<p class="muted">Birthdays are shown only when Telegram returns them for this account. February 29 birthdays appear on February 28 in non-leap years.</p>"""


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not await client.is_user_authorized():
        return HTMLResponse(render_page(login_form()))
    year = selected_year(request)
    try:
        birthdays = await get_visible_birthdays()
    except Exception as exc:
        error = f'<h2>Could not load birthdays</h2><div class="notice error">{escape(str(exc))}</div><a href="/">Try again</a>'
        return HTMLResponse(render_page(error), status_code=502)
    return HTMLResponse(render_page(render_calendar(year, birthdays)))


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
