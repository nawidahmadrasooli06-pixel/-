import os
import re

from dotenv import load_dotenv

load_dotenv()


def _ids(value: str) -> list[int]:
    out = []
    for part in re.split(r"[,\s]+", value or ""):
        if part.strip().lstrip("-").isdigit():
            out.append(int(part))
    return out


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS_LIST = _ids(os.getenv("ADMIN_IDS", ""))
ADMIN_IDS = set(ADMIN_IDS_LIST)
WEBAPP_URL = (os.getenv("WEBAPP_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
PORT = int(os.getenv("PORT", "8080"))
DB_PATH = os.getenv("DB_PATH", "spinner.db")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Berlin")
KEEP_ALIVE = os.getenv("KEEP_ALIVE", "1") == "1"
BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "1") == "1"

APP_SHORT_NAME = os.getenv("APP_SHORT_NAME", "").strip()

MAX_NAMES = 100
MAX_NAME_LEN = 30


def validate() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN تنظیم نشده است (فایل .env یا Environment در Render).")
    if not ADMIN_IDS_LIST:
        raise SystemExit("ADMIN_IDS تنظیم نشده است. شناسه عددی تلگرام خودت را وارد کن.")
