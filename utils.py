import re
from datetime import datetime

import config

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_SPLIT = re.compile(r"[\n\r,،;؛]+")


def fa(value) -> str:
    """Convert digits to Persian digits."""
    return str(value).translate(_FA)


def clean_name(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[: config.MAX_NAME_LEN].strip()


def parse_names(text: str) -> list[str]:
    names = []
    for part in _SPLIT.split(text or ""):
        name = clean_name(part)
        if name:
            names.append(name)
    return names


def format_time(iso: str) -> str:
    try:
        from zoneinfo import ZoneInfo

        dt = datetime.fromisoformat(iso).astimezone(ZoneInfo(config.TIMEZONE))
        return fa(dt.strftime("%Y/%m/%d  %H:%M"))
    except Exception:
        return iso
