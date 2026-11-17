import asyncio
import json
import logging
import secrets
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
        if user["id"] not in config.ADMIN_IDS:
            return fail("⛔ شما دسترسی مدیریت ندارید.", 403)
    return await handler(request)


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
    return _json(full_state(request.app["db"]))


async def api_add(request):
    db, backup = request.app["db"], request.app["backup"]
    body = await read_body(request)
    names = parse_names(str(body.get("text", "")))
    if not names:
        return fail("اسمی پیدا نشد.")
    added, skipped = db.add_names(names)
    backup.schedule()
    return _json(full_state(db, added=added, skipped=skipped))


async def api_remove(request):
    db, backup = request.app["db"], request.app["backup"]
    body = await read_body(request)
    name_id = _int(body.get("id"))
    if name_id is None or not db.remove_name(name_id):
        return fail("این اسم پیدا نشد.", 404)
    backup.schedule()
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
    return _json(full_state(db))


async def api_clear(request):
    db, backup = request.app["db"], request.app["backup"]
    db.clear_names()
    backup.schedule()
    return _json(full_state(db))


async def api_winners_clear(request):
    db, backup = request.app["db"], request.app["backup"]
    db.clear_winners()
    backup.schedule()
    return _json(full_state(db))


async def api_settings(request):
    db, backup = request.app["db"], request.app["backup"]
    body = await read_body(request)
    if "auto_remove" in body:
        db.set_auto_remove(bool(body["auto_remove"]))
        backup.schedule()
    return _json(full_state(db))


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
        backup.schedule()
        return _json(full_state(db, winner=winner, segments=names, removed=removed))


def create_web_app(db, backup) -> web.Application:
    app = web.Application(middlewares=[error_mw, auth_mw])
    app["db"] = db
    app["backup"] = backup
    app["spin_lock"] = asyncio.Lock()
    app.add_routes(
        [
            web.get("/", index),
            web.get("/style.css", style),
            web.get("/app.js", script),
            web.get("/health", health),
            web.post("/api/state", api_state),
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
