import html
import logging
from functools import wraps

from telegram import (
    BotCommand,
    InlineKeyboardButton as Btn,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Update,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from utils import clean_name, fa, format_time, parse_names

log = logging.getLogger("bot")
HTML = ParseMode.HTML
PAGE = 8


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def db_of(ctx):
    return ctx.application.bot_data["db"]


def backup_of(ctx):
    return ctx.application.bot_data["backup"]


# ---------------- access control ----------------
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id not in config.ADMIN_IDS:
            chat = update.effective_chat
            if chat and chat.type != "private":
                return  # stay silent in groups
            if update.callback_query:
                await update.callback_query.answer("⛔ دسترسی ندارید", show_alert=True)
            elif update.effective_message:
                await update.effective_message.reply_text(
                    "⛔ این ربات اختصاصی است و فقط ادمین می‌تواند از آن استفاده کند.\n"
                    f"شناسه عددی شما: <code>{user.id if user else '?'}</code>",
                    parse_mode=HTML,
                )
            return
        return await func(update, ctx)

    return wrapper


async def show(update: Update, text: str, markup=None):
    q = update.callback_query
    if q:
        try:
            await q.edit_message_text(text, parse_mode=HTML, reply_markup=markup)
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                raise
    else:
        await update.effective_message.reply_text(text, parse_mode=HTML, reply_markup=markup)


# ---------------- keyboards ----------------
def webapp_button():
    label = "🎡 باز کردن گردونه"
    if config.WEBAPP_URL.startswith("https://"):
        return Btn(label, web_app=WebAppInfo(url=config.WEBAPP_URL))
    return Btn(label, callback_data="m:nourl")


def main_menu():
    return InlineKeyboardMarkup(
        [
            [webapp_button()],
            [Btn("➕ افزودن اسم", callback_data="m:add"), Btn("➖ حذف اسم", callback_data="m:del:0")],
            [Btn("📋 لیست شرکت‌کنندگان", callback_data="m:list")],
            [Btn("🏆 برندگان قبلی", callback_data="m:winners")],
            [Btn("🔄 پاک کردن لیست", callback_data="m:clear"), Btn("⚙️ تنظیمات", callback_data="m:settings")],
        ]
    )


def back_row():
    return [Btn("↩️ منوی اصلی", callback_data="m:main")]


def pick_keyboard(names, action: str, page: int):
    pages = max(1, (len(names) + PAGE - 1) // PAGE)
    page = min(max(page, 0), pages - 1)
    icon = "❌" if action == "del" else "✏️"
    rows = [
        [Btn(f"{icon} {n['name']}", callback_data=f"x:{action}:{n['id']}")]
        for n in names[page * PAGE : (page + 1) * PAGE]
    ]
    nav = []
    if page > 0:
        nav.append(Btn("◀️ قبلی", callback_data=f"m:{action}:{page - 1}"))
    if page < pages - 1:
        nav.append(Btn("بعدی ▶️", callback_data=f"m:{action}:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append(back_row())
    return InlineKeyboardMarkup(rows), page, pages


# ---------------- screens ----------------
def home_text(db) -> str:
    n = db.count_names()
    auto = "روشن ✅" if db.auto_remove() else "خاموش ⛔️"
    return (
        "🎡 <b>CACTUC SPINNER</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"👥 تعداد شرکت‌کنندگان: <b>{fa(n)}</b>\n"
        f"🗑 حذف خودکار برنده: <b>{auto}</b>\n\n"
        "یکی از گزینه‌ها را انتخاب کن 👇"
    )


async def show_home(update, ctx, prefix: str = ""):
    ctx.user_data.pop("mode", None)
    await show(update, prefix + home_text(db_of(ctx)), main_menu())


async def show_pick(update, ctx, action: str, page: int, prefix: str = ""):
    names = db_of(ctx).list_names()
    if not names:
        await show(update, prefix + "📭 لیست خالی است.", InlineKeyboardMarkup([back_row()]))
        return
    markup, page, pages = pick_keyboard(names, action, page)
    title = "➖ کدام اسم حذف شود؟" if action == "del" else "✏️ کدام اسم ویرایش شود؟"
    await show(update, f"{prefix}{title}\n(صفحه {fa(page + 1)} از {fa(pages)})", markup)


async def show_list(update, ctx):
    names = db_of(ctx).list_names()
    if not names:
        await show(
            update,
            "📭 لیست خالی است.\nبا «➕ افزودن اسم» شروع کن.",
            InlineKeyboardMarkup([[Btn("➕ افزودن اسم", callback_data="m:add")], back_row()]),
        )
        return
    lines, size = [], 0
    for i, n in enumerate(names, 1):
        line = f"{fa(i)}. {esc(n['name'])}"
        if size + len(line) > 3600:
            lines.append(f"… و {fa(len(names) - i + 1)} اسم دیگر")
            break
        lines.append(line)
        size += len(line) + 1
    text = f"📋 <b>لیست شرکت‌کنندگان</b> ({fa(len(names))} نفر)\n━━━━━━━━━━━━━━\n" + "\n".join(lines)
    markup = InlineKeyboardMarkup(
        [
            [Btn("✏️ ویرایش اسم", callback_data="m:edit:0"), Btn("➖ حذف اسم", callback_data="m:del:0")],
            [Btn("➕ افزودن اسم", callback_data="m:add")],
            back_row(),
        ]
    )
    await show(update, text, markup)


async def show_winners(update, ctx):
    winners = db_of(ctx).list_winners(20)
    if not winners:
        await show(update, "🏆 هنوز برنده‌ای ثبت نشده است.", InlineKeyboardMarkup([back_row()]))
        return
    lines = [f"{fa(i)}. 🏆 <b>{esc(w['name'])}</b> — {format_time(w['won_at'])}" for i, w in enumerate(winners, 1)]
    text = "🏆 <b>برندگان قبلی</b> (۲۰ مورد آخر)\n━━━━━━━━━━━━━━\n" + "\n".join(lines)
    markup = InlineKeyboardMarkup([[Btn("🗑 پاک کردن تاریخچه", callback_data="m:winclear")], back_row()])
    await show(update, text, markup)


async def show_settings(update, ctx):
    on = db_of(ctx).auto_remove()
    text = (
        "⚙️ <b>تنظیمات</b>\n━━━━━━━━━━━━━━\n"
        f"🗑 حذف خودکار برنده از لیست: <b>{'روشن ✅' if on else 'خاموش ⛔️'}</b>\n\n"
        "اگر روشن باشد، بعد از هر چرخش اسم برنده از لیست حذف می‌شود."
    )
    label = "⛔️ خاموش کردن حذف خودکار" if on else "✅ روشن کردن حذف خودکار"
    await show(update, text, InlineKeyboardMarkup([[Btn(label, callback_data="x:toggle")], back_row()]))


async def confirm(update, text: str, yes_data: str):
    await show(
        update,
        text,
        InlineKeyboardMarkup([[Btn("✅ بله، مطمئنم", callback_data=yes_data), Btn("❌ انصراف", callback_data="m:main")]]),
    )


# ---------------- handlers ----------------
@admin_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await show_home(update, ctx)


async def cmd_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.effective_message.reply_text(f"شناسه عددی شما: <code>{user.id}</code>", parse_mode=HTML)


async def send_group_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    short = config.APP_SHORT_NAME
    if not short:
        await update.effective_message.reply_text("⚠️ APP_SHORT_NAME در Render تنظیم نشده است.")
        return
    url = f"https://t.me/{ctx.bot.username}/{short}?startapp=group"
    await update.effective_message.reply_text(
        "🎡 گردونه آماده است. فقط ادمین می‌تواند بچرخاند؛ نتیجه اینجا اعلام می‌شود.",
        reply_markup=InlineKeyboardMarkup([[Btn("🎡 باز کردن گردونه", url=url)]]),
    )


@admin_only
async def cmd_setgroup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db_of(ctx).set_setting("group_chat_id", str(update.effective_chat.id))
    backup_of(ctx).schedule()
    await update.effective_message.reply_text("✅ این گروه ثبت شد؛ از این به بعد برنده‌ها اینجا اعلام می‌شوند.")
    await send_group_button(update, ctx)


@admin_only
async def cmd_wheel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await send_group_button(update, ctx)


@admin_only
async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await show_home(update, ctx, "❎ لغو شد.\n\n")


@admin_only
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = (q.data or "").split(":")
    kind, action = parts[0], parts[1] if len(parts) > 1 else ""
    arg = parts[2] if len(parts) > 2 else ""
    db = db_of(ctx)
    await q.answer()

    if kind == "m":
        if action == "main":
            await show_home(update, ctx)
        elif action == "nourl":
            await q.answer("آدرس WEBAPP_URL تنظیم نشده یا https نیست.", show_alert=True)
        elif action == "add":
            ctx.user_data["mode"] = {"type": "add"}
            await show(
                update,
                "✍️ اسم‌ها را بفرست.\n\n"
                "• برای یک اسم: فقط همان اسم\n"
                "• برای چند اسم: هر اسم در یک خط، یا با ویرگول جدا کن\n\n"
                f"(حداکثر {fa(config.MAX_NAMES)} اسم، هر اسم تا {fa(config.MAX_NAME_LEN)} حرف)",
                InlineKeyboardMarkup([[Btn("❌ انصراف", callback_data="m:main")]]),
            )
        elif action in ("del", "edit"):
            await show_pick(update, ctx, action, int(arg or 0))
        elif action == "list":
            await show_list(update, ctx)
        elif action == "winners":
            await show_winners(update, ctx)
        elif action == "clear":
            n = db.count_names()
            if n == 0:
                await show(update, "📭 لیست از قبل خالی است.", InlineKeyboardMarkup([back_row()]))
            else:
                await confirm(update, f"⚠️ همه {fa(n)} اسم پاک شود؟", "x:clear")
        elif action == "winclear":
            await confirm(update, "⚠️ تاریخچه برندگان کامل پاک شود؟", "x:winclear")
        elif action == "settings":
            await show_settings(update, ctx)
    elif kind == "x":
        backup = backup_of(ctx)
        if action == "del":
            ok = db.remove_name(int(arg))
            backup.schedule()
            await show_pick(update, ctx, "del", 0, "✅ حذف شد.\n\n" if ok else "⚠️ این اسم پیدا نشد.\n\n")
        elif action == "edit":
            item = db.get_name(int(arg))
            if not item:
                await show_pick(update, ctx, "edit", 0, "⚠️ این اسم پیدا نشد.\n\n")
                return
            ctx.user_data["mode"] = {"type": "edit", "id": item["id"]}
            await show(
                update,
                f"✏️ اسم فعلی: <b>{esc(item['name'])}</b>\n\nاسم جدید را بفرست:",
                InlineKeyboardMarkup([[Btn("❌ انصراف", callback_data="m:main")]]),
            )
        elif action == "clear":
            db.clear_names()
            backup.schedule()
            await show_home(update, ctx, "🔄 لیست پاک شد.\n\n")
        elif action == "winclear":
            db.clear_winners()
            backup.schedule()
            await show_home(update, ctx, "🗑 تاریخچه برندگان پاک شد.\n\n")
        elif action == "toggle":
            db.set_auto_remove(not db.auto_remove())
            backup.schedule()
            await show_settings(update, ctx)


@admin_only
async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = ctx.user_data.get("mode")
    text = update.effective_message.text or ""
    db = db_of(ctx)
    after = InlineKeyboardMarkup(
        [[webapp_button()], [Btn("➕ افزودن بیشتر", callback_data="m:add")], back_row()]
    )
    if not mode:
        await update.effective_message.reply_text("از منوی زیر استفاده کن 👇", reply_markup=main_menu())
        return
    if mode["type"] == "add":
        names = parse_names(text)
        if not names:
            await update.effective_message.reply_text("⚠️ اسمی پیدا نشد. دوباره بفرست یا /cancel بزن.")
            return
        added, skipped = db.add_names(names)
        backup_of(ctx).schedule()
        ctx.user_data.pop("mode", None)
        msg = f"✅ {fa(added)} اسم اضافه شد."
        if skipped:
            msg += f"\n⚠️ {fa(skipped)} اسم اضافه نشد چون ظرفیت ({fa(config.MAX_NAMES)} نفر) پر شد."
        msg += f"\n👥 مجموع: {fa(db.count_names())} نفر"
        await update.effective_message.reply_text(msg, reply_markup=after)
    elif mode["type"] == "edit":
        new_name = clean_name(text)
        if not new_name:
            await update.effective_message.reply_text("⚠️ اسم معتبر نیست. دوباره بفرست یا /cancel بزن.")
            return
        ok = db.rename(mode["id"], new_name)
        backup_of(ctx).schedule()
        ctx.user_data.pop("mode", None)
        await update.effective_message.reply_text(
            f"✅ اسم به <b>{esc(new_name)}</b> تغییر کرد." if ok else "⚠️ این اسم پیدا نشد.",
            parse_mode=HTML,
            reply_markup=after,
        )


async def on_error(update, ctx: ContextTypes.DEFAULT_TYPE):
    log.error("Update caused error", exc_info=ctx.error)


def build_application() -> Application:
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler(["start", "menu"], cmd_start, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("setgroup", cmd_setgroup, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("wheel", cmd_wheel, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, on_text))
    app.add_error_handler(on_error)
    return app


async def setup_bot(app: Application) -> None:
    try:
        await app.bot.set_my_commands(
            [
                BotCommand("start", "منوی اصلی"),
                BotCommand("cancel", "لغو عملیات"),
                BotCommand("id", "نمایش شناسه عددی من"),
            ]
        )
        if config.WEBAPP_URL.startswith("https://"):
            await app.bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="🎡 گردونه", web_app=WebAppInfo(url=config.WEBAPP_URL))
            )
    except Exception as e:  # noqa: BLE001
        log.warning("setup_bot failed: %s", e)
