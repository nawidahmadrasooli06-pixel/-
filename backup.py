"""Free persistence trick for hosts with an ephemeral disk (Render free plan).

After changes, the SQLite file is sent to the admin's private chat with the bot and
pinned. On startup, if the database file is missing, it is restored from that pinned file.
"""
import asyncio
import logging
import os
import sqlite3
import tempfile

log = logging.getLogger("backup")
BACKUP_FILENAME = "cactuc_spinner_backup.db"


async def restore_if_missing(bot, db_path: str, admin_ids: list[int]):
    """Returns (admin_id, message_id) of the restored backup message, or None."""
    if os.path.exists(db_path):
        return None
    for admin in admin_ids:
        try:
            chat = await bot.get_chat(admin)
            pm = chat.pinned_message
            if not (pm and pm.document and pm.document.file_name == BACKUP_FILENAME):
                continue
            tg_file = await bot.get_file(pm.document.file_id)
            await tg_file.download_to_drive(db_path)
            con = sqlite3.connect(db_path)
            ok = con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            con.close()
            if not ok:
                os.remove(db_path)
                continue
            log.info("Database restored from Telegram backup.")
            return admin, pm.message_id
        except Exception as e:  # noqa: BLE001
            log.warning("Restore attempt failed for %s: %s", admin, e)
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except OSError:
                    pass
    return None


class Backup:
    def __init__(self, bot, db, chat_id: int, enabled: bool, last_message_id=None):
        self.bot = bot
        self.db = db
        self.chat_id = chat_id
        self.enabled = enabled
        self.last_message_id = last_message_id
        self._dirty = False
        self._task = None
        self._lock = asyncio.Lock()

    def schedule(self) -> None:
        if not self.enabled:
            return
        self._dirty = True
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        while self._dirty:
            await asyncio.sleep(15)
            self._dirty = False
            try:
                await self.run_now()
            except Exception as e:  # noqa: BLE001
                log.warning("Backup failed: %s", e)

    async def flush(self) -> None:
        if self.enabled and self._dirty:
            self._dirty = False
            try:
                await self.run_now()
            except Exception as e:  # noqa: BLE001
                log.warning("Final backup failed: %s", e)

    async def run_now(self) -> None:
        async with self._lock:
            fd, tmp = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            try:
                self.db.snapshot_to(tmp)
                with open(tmp, "rb") as fh:
                    msg = await self.bot.send_document(
                        chat_id=self.chat_id,
                        document=fh,
                        filename=BACKUP_FILENAME,
                        caption="💾 پشتیبان خودکار CACTUC SPINNER (حذفش نکن)",
                        disable_notification=True,
                    )
                await self.bot.pin_chat_message(
                    chat_id=self.chat_id, message_id=msg.message_id, disable_notification=True
                )
                old = self.last_message_id
                self.last_message_id = msg.message_id
                if old and old != msg.message_id:
                    try:
                        await self.bot.delete_message(chat_id=self.chat_id, message_id=old)
                    except Exception:  # noqa: BLE001
                        pass
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
