import os
import random
import string
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ساخت وب‌سرور برای آنلاین ماندن در Render
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is alive and running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# حافظه بازی‌ها
rooms = {}
ai_games = {}

ABOUT_TEXT_FA = (
    "🎮 **ربات بازی هیجان‌انگیز**\n\n"
    "👨‍💻 **طراحی و توسعه‌یافته توسط:** 〘Cactuc = نــوید\n"
    "🆔 @cactuc580\n\n"
    "💡 *اگر نظر، پیشنهاد یا ایده‌ای برای بهتر شدن بازی داشتید، می‌توانید با من در میان بگذارید.*\n\n"
    "📌 *این ربات گیمینگ صرفاً برای سرگرمی و خوش‌گذشتن شما عزیزان ساخته شده است. امیدوارم نهایت لذت را ببرید! ❤️*"
)

RULES_NAHREGAK = (
    "📜 **راهنمای بازی نهره‌گک (دوز ۹ تایی سنتی):**\n\n"
    "۱. هر بازیکن با ۹ مهره بازی را شروع می‌کند.\n"
    "۲. هدف این است که با چیدن ۳ مهره در یک خط، یک **قطار** بسازید.\n"
    "۳. با هر بار ساخت قطار، می‌توانید یکی از مهره‌های حریف را بسوزانید!\n"
    "۴. بازیکن زمانی می‌بازد که تعداد مهره‌هایش به کمتر از ۳ برسد."
)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🎮 بازی دوز سریع (۳x۳)", callback_data="play_ai_3")],
        [InlineKeyboardButton("🏆 بازی نهره‌گک (۹ مهره‌ای سنتی)", callback_data="play_nahregak")],
        [InlineKeyboardButton("🔗 بازی با دوستان (کد اتاق)", callback_data="play_friends_menu")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"), InlineKeyboardButton("🏆 جدول برترین‌ها", callback_data="leaderboard")],
        [InlineKeyboardButton("درباره ربات ℹ️", callback_data="about")]
    ]
    return InlineKeyboardMarkup(keyboard)

def render_board_3x3(board, prefix="cell"):
    keyboard = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            idx = i + j
            val = board[idx] if board[idx] != " " else "▫️"
            row.append(InlineKeyboardButton(val, callback_data=f"{prefix}_{idx}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ انصراف / خروج", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_msg = f"سلام {user.first_name} عزیز! 👋\nبه ربات گیمینگ نوید خوش آمدی. یک حالت بازی را انتخاب کن:"
    await update.message.reply_text(welcome_msg, reply_markup=get_main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "about":
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]])
        await query.edit_message_text(ABOUT_TEXT_FA, reply_markup=back_btn, parse_mode="Markdown")

    elif data == "main_menu":
        context.user_data["awaiting_code"] = False
        await query.edit_message_text("منوی اصلی بازی:", reply_markup=get_main_menu())

    elif data == "play_nahregak":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 شروع بازی ۹ مهره‌ای با ربات", callback_data="play_ai_9")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ])
        await query.edit_message_text(RULES_NAHREGAK, reply_markup=kb, parse_mode="Markdown")

    elif data == "play_friends_menu":
        kb = [
            [InlineKeyboardButton("➕ ساخت اتاق جدید", callback_data="create_room")],
            [InlineKeyboardButton("🔑 ورود با کد اتاق", callback_data="join_room_prompt")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text("🎮 **بخش بازی با دوستان**\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "create_room":
        room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        rooms[room_code] = {"host": user_id, "guest": None, "board": [" "] * 9}
        
        msg = (
            f"🏰 **اتاق بازی شما ساخته شد!**\n\n"
            f"🔑 کد اتاق: `{room_code}`\n\n"
            f"این کد ۴ رقمی را برای دوستت بفرست تا وارد اتاق شود!"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="play_friends_menu")]])
        await query.edit_message_text(msg, reply_markup=kb, parse_mode="Markdown")

    elif data == "join_room_prompt":
        context.user_data["awaiting_code"] = True
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="play_friends_menu")]])
        await query.edit_message_text("🔑 **لطفاً کد ۴ رقمی اتاق را بفرستید:**", reply_markup=kb, parse_mode="Markdown")

    # بازی ۳x۳
    elif data in ["play_ai_3", "play_ai_9"]:
        ai_games[user_id] = {"board": [" "] * 9, "turn": "user"}
        msg_text = "🎮 **نوبت شماست!** (مهره شما: 🟦 / مهره هوش مصنوعی: 🟥)"
        await query.edit_message_text(msg_text, reply_markup=render_board_3x3(ai_games[user_id]["board"], "ai_cell"))

    elif data.startswith("ai_cell_"):
        idx = int(data.split("_")[2])
        game = ai_games.get(user_id)
        if not game or game["board"][idx] != " ":
            return

        # حرکت کاربر (مهره آبی)
        game["board"][idx] = "🟦"
        
        if check_winner(game["board"]) == "🟦":
            end_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 شروع مجدد بازی (/start)", callback_data="main_menu")]
            ])
            await query.edit_message_text(
                "🎉🔥 **پیروزی عالی! شما برنده این نبرد شدید!** 🔥🎉\n\n"
                "دمت گرم! هوش مصنوعی را با یک قطار فوق‌العاده شکست دادی. 💪\n"
                "برای بازی دوباره، دکمه زیر را لمس کنید:",
                reply_markup=end_kb,
                parse_mode="Markdown"
            )
            return

        # حرکت هوش مصنوعی (مهره قرمز)
        empty_cells = [i for i, val in enumerate(game["board"]) if val == " "]
        if empty_cells:
            ai_move = random.choice(empty_cells)
            game["board"][ai_move] = "🟥"
            
            if check_winner(game["board"]) == "🟥":
                end_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 شروع مجدد بازی (/start)", callback_data="main_menu")]
                ])
                await query.edit_message_text(
                    "🤖 **هوش مصنوعی این بار برنده شد!**\n\n"
                    "اشکالی نداره، دوباره شانس خودت رو امتحان کن. 😉\n"
                    "برای شروع مجدد روی دکمه زیر بزن:",
                    reply_markup=end_kb,
                    parse_mode="Markdown"
                )
                return
        else:
            end_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 شروع مجدد بازی (/start)", callback_data="main_menu")]
            ])
            await query.edit_message_text(
                "🤝 **یک نبرد برابر! بازی مساوی شد.**\n\nبرای بازی دوباره روی دکمه زیر کلیک کنید:",
                reply_markup=end_kb,
                parse_mode="Markdown"
            )
            return

        await query.edit_message_text(
            "🎮 **نوبت شماست!** (مهره شما: 🟦 / مهره هوش مصنوعی: 🟥)",
            reply_markup=render_board_3x3(game["board"], "ai_cell")
        )

# دریافت کد ۴ رقمی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_code"):
        code = update.message.text.strip().upper()
        if code in rooms:
            context.user_data["awaiting_code"] = False
            await update.message.reply_text(f"✅ با موفقیت وارد اتاق `{code}` شدید! منتظر شروع...", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ کد وارد شده معتبر نیست! دوباره تلاش کنید.")

def check_winner(b):
    lines = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for a, bb, c in lines:
        if b[a] == b[bb] == b[c] and b[a] != " ":
            return b[a]
    return None

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    Thread(target=run_web).start()
    
    if TOKEN:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.run_polling()
