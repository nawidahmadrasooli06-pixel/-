import asyncio
import html
import json
import logging
import math
import secrets
import time
from pathlib import Path

from aiohttp import web

import config
from auth import validate_init_data
from utils import clean_name, parse_names

log = logging.getLogger("api")
BASE = Path(__file__).parent
NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}


def _json(data, status=200):
    return web.json_response(data, status=status, dumps=lambda o: json.dumps(o, ensure_ascii=False))


def fail(msg: str, status: int = 400):
    return _json({"ok": False, "error": msg}, status)


def full_state(db, **extra):
    return {
        "ok": True,
        "names": db.list_names(),
        "winners": db.list_winners(),
        "settings": {"auto_remove": db.auto_remove()},
        "limits": {"max_names": config.MAX_NAMES, "max_len": config.MAX_NAME_LEN},
        **extra,
    }


async def read_body(request) -> dict:
    try:
        data = await request.json()
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@web.middleware
async def error_mw(request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception:  # noqa: BLE001
        log.exception("Unhandled error")
        return fail("خطای داخلی سرور", 500)


@web.middleware
async def auth_mw(request, handler):
    if request.path.startswith("/api/"):
        user = validate_init_data(request.headers.get("X-Init-Data", ""), config.BOT_TOKEN)
        if not user:
            return fail("نشست نامعتبر است. اپ را از داخل تلگرام باز کنید.", 401)
        owner = user["id"] in config.ADMIN_IDS
        request["owner"] = owner
        if not owner:
            if request.path not in READ_PATHS:
                return fail("⛔ فقط ادمین اصلی می‌تواند این کار را انجام دهد.", 403)
            if not await is_member(request.app, user["id"]):
                return fail("⛔ فقط اعضای گروه می‌توانند گردونه را ببینند.", 403)
    return await handler(request)


READ_PATHS = {"/api/state", "/api/live"}  # what group members (viewers) may call
TAU = 2 * math.pi


def bump(app) -> None:
    app["version"] += 1


async def is_member(app, user_id: int) -> bool:
    group, bot = app["db"].get_setting("group_chat_id"), app["bot"]
    if not group or not bot:
        return False
    now = time.time()
    hit = app["member_cache"].get(user_id)
    if hit and now - hit[0] < 120:
        return hit[1]
    try:
        m = await bot.get_chat_member(int(group), user_id)
        ok = m.status in ("creator", "administrator", "member") or (
            m.status == "restricted" and getattr(m, "is_member", False)
        )
    except Exception:  # noqa: BLE001
        ok = False
    app["member_cache"][user_id] = (now, ok)
    return ok


# ---------- pages ----------
async def index(request):
    return web.FileResponse(BASE / "index.html", headers=NO_CACHE)


async def style(request):
    return web.FileResponse(BASE / "style.css", headers=NO_CACHE)


async def script(request):
    return web.FileResponse(BASE / "app.js", headers=NO_CACHE)


async def health(request):
    return web.Response(text="ok")


# ---------- API ----------
async def api_state(request):
    app = request.app
    return _json(
        full_state(
            app["db"],
            rotation=app["rotation"],
            version=app["version"],
            spin_seq=app["spin_seq"],
            role="owner" if request.get("owner") else "viewer",
        )
    )


async def api_live(request):
    app = request.app
    return _json(
        {
            "ok": True,
            "version": app["version"],
            "spin_seq": app["spin_seq"],
            "event": app["live_event"],
            "server_time": int(time.time() * 1000),
        }
    )


async def api_add(request):
    db, backup = request.app["db"], request.app["backup"]
    body = await read_body(request)
    names = parse_names(str(body.get("text", "")))
    if not names:
        return fail("اسمی پیدا نشد.")
    added, skipped = db.add_names(names)
    backup.schedule()
    bump(request.app)
    return _json(full_state(db, added=added, skipped=skipped))


async def api_remove(request):
    db, backup = request.app["db"], request.app["backup"]
    body = await read_body(request)
    name_id = _int(body.get("id"))
    if name_id is None or not db.remove_name(name_id):
        return fail("این اسم پیدا نشد.", 404)
    backup.schedule()
    bump(request.app)
    return _json(full_state(db))


async def api_edit(request):
    db, backup = request.app["db"], request.app["backup"]
    body = await read_body(request)
    name_id = _int(body.get("id"))
    new_name = clean_name(str(body.get("name", "")))
    if name_id is None or not new_name:
        return fail("اسم معتبر نیست.")
    if not db.rename(name_id, new_name):
        return fail("این اسم پیدا نشد.", 404)
    backup.schedule()
    bump(request.app)
    return _json(full_state(db))


async def api_clear(request):
    db, backup = request.app["db"], request.app["backup"]
    db.clear_names()
    backup.schedule()
    bump(request.app)
    return _json(full_state(db))


async def api_winners_clear(request):
    db, backup = request.app["db"], request.app["backup"]
    db.clear_winners()
    backup.schedule()
    bump(request.app)
    return _json(full_state(db))


async def api_settings(request):
    db, backup = request.app["db"], request.app["backup"]
    body = await read_body(request)
    if "auto_remove" in body:
        db.set_auto_remove(bool(body["auto_remove"]))
        backup.schedule()
        bump(request.app)
    return _json(full_state(db))


async def _announce(bot, chat_id: int, name: str):
    await asyncio.sleep(7.5)  # wait until the wheel animation ends on the admin's phone
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🎡 <b>CACTUC SPINNER</b>\n━━━━━━━━━━━━━━\n🏆 برنده: <b>{html.escape(name, quote=False)}</b> 🎉",
            parse_mode="HTML",
        )
    except Exception:  # noqa: BLE001
        log.exception("Could not announce winner in group")


async def api_spin(request):
    db, backup = request.app["db"], request.app["backup"]
    async with request.app["spin_lock"]:
        names = db.list_names()
        if len(names) < 2:
            return fail("برای چرخاندن حداقل دو اسم لازم است.")
        winner = secrets.choice(names)  # server-side cryptographically secure choice
        db.add_winner(winner["name"])
        removed = False
        if db.auto_remove():
            removed = db.remove_name(winner["id"])
        app = request.app
        idx = next(i for i, x in enumerate(names) if x["id"] == winner["id"])
        seg = TAU / len(names)
        jitter = (secrets.randbelow(1000) / 1000 - 0.5) * seg * 0.6  # visual only, stays inside the slice
        r0 = app["rotation"]
        target = (-(idx + 0.5) * seg + jitter) % TAU
        delta = ((target - (r0 % TAU)) % TAU) + TAU * (6 + secrets.randbelow(3))
        app["rotation"] = (r0 + delta) % TAU
        app["spin_seq"] += 1
        event = {
            "seq": app["spin_seq"], "winner": winner, "segments": names, "removed": removed,
            "r0": r0, "delta": delta, "duration": 6500, "started_at": int(time.time() * 1000),
        }
        app["live_event"] = event
        backup.schedule()
        bump(request.app)
        group = db.get_setting("group_chat_id")
        bot = request.app["bot"]
        if group and bot:
            task = asyncio.create_task(_announce(bot, int(group), winner["name"]))
            request.app["tasks"].add(task)
            task.add_done_callback(request.app["tasks"].discard)
        return _json(full_state(db, winner=winner, segments=names, removed=removed, event=event,
                                server_time=event["started_at"]))


def create_web_app(db, backup, bot=None) -> web.Application:
    app = web.Application(middlewares=[error_mw, auth_mw])
    app["db"] = db
    app["backup"] = backup
    app["bot"] = bot
    app["tasks"] = set()
    app["version"] = 0
    app["spin_seq"] = 0
    app["live_event"] = None
    app["rotation"] = 0.0
    app["member_cache"] = {}
    app["spin_lock"] = asyncio.Lock()
    app.add_routes(
        [
            web.get("/", index),
            web.get("/style.css", style),
            web.get("/app.js", script),
            web.get("/health", health),
            web.post("/api/state", api_state),
            web.post("/api/live", api_live),
            web.post("/api/add", api_add),
            web.post("/api/remove", api_remove),
            web.post("/api/edit", api_edit),
            web.post("/api/clear", api_clear),
            web.post("/api/winners_clear", api_winners_clear),
            web.post("/api/settings", api_settings),
            web.post("/api/spin", api_spin),
        ]
    )
    return app
