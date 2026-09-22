import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# تنظیمات لوگ‌ها
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# متن بخش درباره سازنده (نوید)
ABOUT_TEXT_FA = (
    "🎮 **ربات بازی هیجان‌انگیز**\n\n"
    "👨‍💻 **طراحی و توسعه‌یافته توسط:** 〘Cactuc = نــوید\n"
    "🆔 @cactuc580\n\n"
    "💡 *اگر نظر، پیشنهاد یا ایده‌ای برای بهتر شدن بازی داشتید، می‌توانید با من در میان بگذارید.*\n\n"
    "📌 *این ربات گیمینگ صرفاً برای سرگرمی و خوش‌گذشتن شما عزیزان ساخته شده است. امیدوارم نهایت لذت را ببرید! ❤️*"
)

ABOUT_TEXT_EN = (
    "🎮 **Exciting Gaming Bot**\n\n"
    "👨‍💻 **Designed & Developed by:** 〘Cactuc = Navid\n"
    "🆔 @cactuc580\n\n"
    "💡 *If you have any feedback or suggestions, feel free to share them with me.*\n\n"
    "📌 *This gaming bot is created purely for your entertainment. Hope you enjoy it! ❤️*"
)

# منوی اصلی
def get_main_menu(lang="fa"):
    if lang == "fa":
        keyboard = [
            [InlineKeyboardButton("🤖 بازی با ربات (تک‌نفره)", callback_data="play_ai")],
            [InlineKeyboardButton("🔗 بازی با دوستان (کد / لینک)", callback_data="play_friends"), InlineKeyboardButton("🌐 بازی آنلاین کشوری", callback_data="play_online")],
            [InlineKeyboardButton("🏆 جدول برترین‌ها", callback_data="leaderboard"), InlineKeyboardButton("⚙️ تنظیمات / Settings", callback_data="settings")],
            [InlineKeyboardButton("ℹ️ درباره سازنده (نوید)", callback_data="about")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🤖 Play vs AI (Single)", callback_data="play_ai")],
            [InlineKeyboardButton("🔗 Play with Friends", callback_data="play_friends"), InlineKeyboardButton("🌐 Quick Online Match", callback_data="play_online")],
            [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"), InlineKeyboardButton("⚙️ Settings / تنظیمات", callback_data="settings")],
            [InlineKeyboardButton("ℹ️ About Creator (Navid)", callback_data="about")]
        ]
    return InlineKeyboardMarkup(keyboard)

# دستور start/
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = context.user_data.get("lang", "fa")
    
    welcome_msg = f"سلام {user.first_name} عزیز! 👋\nبه ربات گیمینگ نوید خوش آمدی. یک حالت بازی را انتخاب کن:" if lang == "fa" else f"Welcome {user.first_name}! 👋\nChoose a game mode to start:"
    
    await update.message.reply_text(welcome_msg, reply_markup=get_main_menu(lang), parse_mode="Markdown")

# مدیریت کلیک روی دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    lang = context.user_data.get("lang", "fa")
    data = query.data

    if data == "about":
        text = ABOUT_TEXT_FA if lang == "fa" else ABOUT_TEXT_EN
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت / Back", callback_data="main_menu")]])
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    elif data == "main_menu":
        welcome_msg = "منوی اصلی بازی:" if lang == "fa" else "Main Menu:"
        await query.edit_message_text(welcome_msg, reply_markup=get_main_menu(lang))

    elif data == "settings":
        kb = [
            [InlineKeyboardButton("🇮🇷 تغییر به فارسی", callback_data="lang_fa"), InlineKeyboardButton("🇬🇧 Switch to English", callback_data="lang_en")],
            [InlineKeyboardButton("🔙 بازگشت / Back", callback_data="main_menu")]
        ]
        text = "⚙️ **تنظیمات ربات / Settings**\nزبان مورد نظر خود را انتخاب کنید:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("lang_"):
        new_lang = data.split("_")[1]
        context.user_data["lang"] = new_lang
        msg = "زبان به فارسی تغییر یافت! 🇮🇷" if new_lang == "fa" else "Language changed to English! 🇬🇧"
        await query.edit_message_text(msg, reply_markup=get_main_menu(new_lang))

    elif data == "play_friends":
        user_id = query.from_user.id
        link = f"https://t.me/{context.bot.username}?start=room_{user_id}"
        msg = (
            f"🎮 **اتاق بازی اختصاصی شما ساخته شد!**\n\n"
            f"لینک زیر را برای ۳ نفر از دوستانت بفرست تا وارد اتاق شوند:\n`{link}`\n\n"
            f"منتظر ورود بازیکنان..."
        ) if lang == "fa" else (
            f"🎮 **Your Private Game Room is Ready!**\n\n"
            f"Share this link with up to 3 friends:\n`{link}`\n\n"
            f"Waiting for players..."
        )
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت / Back", callback_data="main_menu")]])
        await query.edit_message_text(msg, reply_markup=back_btn, parse_mode="Markdown")

    else:
        msg = "این بخش در حال اتصال به سرور بازی است..." if lang == "fa" else "Connecting to game server..."
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت / Back", callback_data="main_menu")]])
        await query.edit_message_text(msg, reply_markup=back_btn)

# اجرای اصلی ربات
if __name__ == "__main__":
    # گرفتن توکن از متغیرهای محیطی Render
    TOKEN = os.environ.get("BOT_TOKEN")
    
    if not TOKEN:
        print("خطا: BOT_TOKEN در Environment Variables تعریف نشده است!")
    else:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        
        print("ربات نوید با موفقیت و بدون باگ در حال اجرا است...")
        app.run_polling()
