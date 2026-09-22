import os
import random
import string
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ساخت وب‌سرور برای زنده ماندن در Render
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# حافظه بازی‌ها و اتاق‌ها
rooms = {}  # room_code: {"players": [], "board": [...], "turn": user_id}
ai_games = {} # user_id: {"board": [...], "turn": "user"}

ABOUT_TEXT_FA = (
    "🎮 **ربات بازی هیجان‌انگیز**\n\n"
    "👨‍💻 **طراحی و توسعه‌یافته توسط:** 〘Cactuc = نــوید\n"
    "🆔 @cactuc580\n\n"
    "💡 *اگر نظر، پیشنهاد یا ایده‌ای برای بهتر شدن بازی داشتید، می‌توانید با من در میان بگذارید.*\n\n"
    "📌 *این ربات گیمینگ صرفاً برای سرگرمی و خوش‌گذشتن شما عزیزان ساخته شده است. امیدوارم نهایت لذت را ببرید! ❤️*"
)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🤖 بازی با ربات (تک‌نفره)", callback_data="play_ai")],
        [InlineKeyboardButton("🔗 بازی با دوستان (کد اتاق)", callback_data="play_friends_menu")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"), InlineKeyboardButton("🏆 جدول برترین‌ها", callback_data="leaderboard")],
        [InlineKeyboardButton("درباره ربات ℹ️", callback_data="about")]
    ]
    return InlineKeyboardMarkup(keyboard)

def render_board(board, prefix="cell"):
    # ساخت صفحه بازی دوز (۳x۳)
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
    welcome_msg = f"سلام {user.first_name} عزیز! 👋\nبه ربات گیمینگ خوش آمدی. یک حالت بازی را انتخاب کن:"
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

    elif data == "play_friends_menu":
        kb = [
            [InlineKeyboardButton("➕ ساخت اتاق جدید", callback_data="create_room")],
            [InlineKeyboardButton("🔑 ورود با کد اتاق", callback_data="join_room_prompt")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text("🎮 **بخش بازی با دوستان**\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "create_room":
        # ساخت کد ۴ رقمی شیک
        room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        rooms[room_code] = {"host": user_id, "guest": None, "board": [" "] * 9}
        
        msg = (
            f"🏰 **اتاق بازی شما ساخته شد!**\n\n"
            f"🔑 کد اتاق: `{room_code}`\n\n"
            f"این کد ۴ رقمی را برای دوستت بفرست.\n"
            f"دوستت باید در بخش «ورود با کد اتاق» این کد را وارد کند تا بازی شروع شود!"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="play_friends_menu")]])
        await query.edit_message_text(msg, reply_markup=kb, parse_mode="Markdown")

    elif data == "join_room_prompt":
        context.user_data["awaiting_code"] = True
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="play_friends_menu")]])
        await query.edit_message_text("🔑 **لطفاً کد ۴ رقمی اتاق را بفرستید:**\n(فرقی نمی‌کند حروف بزرگ باشد یا کوچک)", reply_markup=kb, parse_mode="Markdown")

    # شروع بازی با هوش مصنوعی (تک‌نفره)
    elif data == "play_ai":
        ai_games[user_id] = {"board": [" "] * 9, "turn": "user"}
        await query.edit_message_text("🎮 **بازی دوز با هوش مصنوعی**\nنوبت شماست (❌):", reply_markup=render_board(ai_games[user_id]["board"], "ai_cell"))

    elif data.startswith("ai_cell_"):
        idx = int(data.split("_")[2])
        game = ai_games.get(user_id)
        if not game or game["board"][idx] != " ":
            return

        # حرکت کاربر
        game["board"][idx] = "❌"
        
        # بررسی برد کاربر
        if check_winner(game["board"]) == "❌":
            await query.edit_message_text("🎉 **تبریک! شما هوش مصنوعی را شکست دادید!** 🏆", reply_markup=render_board(game["board"], "done"))
            return

        # حرکت هوش مصنوعی
        empty_cells = [i for i, val in enumerate(game["board"]) if val == " "]
        if empty_cells:
            ai_move = random.choice(empty_cells)
            game["board"][ai_move] = "⭕"
            
            if check_winner(game["board"]) == "⭕":
                await query.edit_message_text("🤖 **هوش مصنوعی برنده شد! دوباره تلاش کن.**", reply_markup=render_board(game["board"], "done"))
                return
        else:
            await query.edit_message_text("🤝 **بازی مساوی شد!**", reply_markup=render_board(game["board"], "done"))
            return

        await query.edit_message_text("🎮 **بازی دوز با هوش مصنوعی**\nنوبت شماست (❌):", reply_markup=render_board(game["board"], "ai_cell"))

    else:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]])
        await query.edit_message_text("این بخش به زودی فعال می‌شود!", reply_markup=kb)

# دریافت متن (کد ۴ رقمی) از کاربر
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_code"):
        code = update.message.text.strip().upper()
        if code in rooms:
            context.user_data["awaiting_code"] = False
            await update.message.reply_text(f"✅ با موفقیت وارد اتاق `{code}` شدید! منتظر شروع...", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ کد وارد شده معتبر نیست! دوباره تلاش کنید یا انصراف دهید.")

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
