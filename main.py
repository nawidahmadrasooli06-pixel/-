import asyncio
import logging
import signal

import aiohttp
from aiohttp import web
from telegram import Update

import config
from api import create_web_app
from backup import Backup, restore_if_missing
from bot import build_application, setup_bot
from database import Database

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("main")


async def keep_alive() -> None:
    """Ping our own public URL so Render's free plan does not put the service to sleep."""
    url = config.WEBAPP_URL + "/health"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        while True:
            await asyncio.sleep(600)
            try:
                async with session.get(url) as resp:
                    await resp.read()
            except Exception as e:  # noqa: BLE001
                log.warning("keep-alive ping failed: %s", e)


async def main() -> None:
    config.validate()
    application = build_application()
    await application.initialize()

    primary_admin = config.ADMIN_IDS_LIST[0]
    restored = await restore_if_missing(application.bot, config.DB_PATH, config.ADMIN_IDS_LIST)
    db = Database(config.DB_PATH)
    last_msg = restored[1] if restored and restored[0] == primary_admin else None
    backup = Backup(application.bot, db, primary_admin, config.BACKUP_ENABLED, last_msg)
    application.bot_data["db"] = db
    application.bot_data["backup"] = backup
    await setup_bot(application)

    runner = web.AppRunner(create_web_app(db, backup, application.bot))
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", config.PORT).start()
    log.info("Web server listening on port %s", config.PORT)

    await application.start()
    await application.updater.start_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    log.info("CACTUC SPINNER is running.")

    ping_task = None
    if config.KEEP_ALIVE and config.WEBAPP_URL.startswith("https://"):
        ping_task = asyncio.create_task(keep_alive())

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    await stop.wait()

    log.info("Shutting down...")
    if ping_task:
        ping_task.cancel()
    await application.updater.stop()
    await application.stop()
    await backup.flush()
    await application.shutdown()
    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
