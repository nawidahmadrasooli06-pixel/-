import os
import random
import string
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is active!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# تعریف تمام ۱۶ قطار مجاز در بازی (طبق نقشه نوید)
MILLS = [
    # ۳ مربع (اضلاع)
    (0, 1, 2), (2, 3, 4), (4, 5, 6), (6, 7, 0),       # مربع بیرونی
    (8, 9, 10), (10, 11, 12), (12, 13, 14), (14, 15, 8), # مربع میانی
    (16, 17, 18), (18, 19, 20), (20, 21, 22), (22, 23, 16), # مربع کوچک
    
    # ۴ خط رابط وسط مربع‌ها
    (1, 9, 17),   # خط بالا
    (3, 11, 19),  # خط راست
    (5, 13, 21),  # خط پایین
    (7, 15, 23)   # خط چپ
]

# حافظه بازی نهره‌گک
games = {}

def create_board_markup(board, hand_p, hand_ai, burned_p, burned_ai):
    def symbol(i):
        if board[i] == "P": return "🔵"   # مهره شما (آبی)
        elif board[i] == "AI": return "🔴" # مهره حریف (قرمز)
        return "⚪"                       # نقطه خالی

    kb = [
        # مخزن مهره‌های دو طرف (قبل از چیدن)
        [InlineKeyboardButton(f"🎒 دست شما: {hand_p} مهره", callback_data="guide_hand"),
         InlineKeyboardButton(f"🎒 دست حریف: {hand_ai} مهره", callback_data="guide_hand")],
        
        # 🟢 مربع بیرونی (ضلع بالا)
        [InlineKeyboardButton(symbol(0), callback_data="pos_0"), InlineKeyboardButton("━━━", callback_data="none"),
         InlineKeyboardButton(symbol(1), callback_data="pos_1"), InlineKeyboardButton("━━━", callback_data="none"),
         InlineKeyboardButton(symbol(2), callback_data="pos_2")],
        
        # 🟡 مربع میانی (ضلع بالا)
        [InlineKeyboardButton("┃", callback_data="none"), InlineKeyboardButton(symbol(8), callback_data="pos_8"),
         InlineKeyboardButton(symbol(9), callback_data="pos_9"), InlineKeyboardButton(symbol(10), callback_data="pos_10"),
         InlineKeyboardButton("┃", callback_data="none")],

        # 🔴 مربع کوچک داخلی (ضلع بالا)
        [InlineKeyboardButton("┃ ┃", callback_data="none"), InlineKeyboardButton(symbol(16), callback_data="pos_16"),
         InlineKeyboardButton(symbol(17), callback_data="pos_17"), InlineKeyboardButton(symbol(18), callback_data="pos_18"),
         InlineKeyboardButton("┃ ┃", callback_data="none")],

        # 🎯 خط وسط + دایره مرکز (خانه سوخته‌ها)
        [InlineKeyboardButton(symbol(7), callback_data="pos_7"), InlineKeyboardButton(symbol(15), callback_data="pos_15"),
         InlineKeyboardButton(symbol(23), callback_data="pos_23"), 
         InlineKeyboardButton(f"🔥 سوخته: {burned_p + burned_ai}", callback_data="guide_burned"),
         InlineKeyboardButton(symbol(19), callback_data="pos_19"), InlineKeyboardButton(symbol(11), callback_data="pos_11"),
         InlineKeyboardButton(symbol(3), callback_data="pos_3")],

        # 🔴 مربع کوچک داخلی (ضلع پایین)
        [InlineKeyboardButton("┃ ┃", callback_data="none"), InlineKeyboardButton(symbol(22), callback_data="pos_22"),
         InlineKeyboardButton(symbol(21), callback_data="pos_21"), InlineKeyboardButton(symbol(20), callback_data="pos_20"),
         InlineKeyboardButton("┃ ┃", callback_data="none")],

        # 🟡 مربع میانی (ضلع پایین)
        [InlineKeyboardButton("┃", callback_data="none"), InlineKeyboardButton(symbol(14), callback_data="pos_14"),
         InlineKeyboardButton(symbol(13), callback_data="pos_13"), InlineKeyboardButton(symbol(12), callback_data="pos_12"),
         InlineKeyboardButton("┃", callback_data="none")],

        # 🟢 مربع بیرونی (ضلع پایین)
        [InlineKeyboardButton(symbol(6), callback_data="pos_6"), InlineKeyboardButton("━━━", callback_data="none"),
         InlineKeyboardButton(symbol(5), callback_data="pos_5"), InlineKeyboardButton("━━━", callback_data="none"),
         InlineKeyboardButton(symbol(4), callback_data="pos_4")],

        [InlineKeyboardButton("🔙 انصراف و بازگشت به منو", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 شروع بازی نهره‌گک (تخته سنتی)", callback_data="start_game")],
        [InlineKeyboardButton("درباره ربات ℹ️", callback_data="about")]
    ])
    await update.message.reply_text("سلام رفیق! به بازی جذاب نهره‌گک خوش اومدی. آماده‌ای؟ 👇", reply_markup=kb)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data == "guide_hand":
        await query.answer("رفیق! اول باید هر ۹ تا مهره‌تون رو یکی‌یکی وارد تخته کنین، بعدش جابه‌جایی شروع میشه! 😉", show_alert=True)
        return
    elif data == "guide_burned":
        await query.answer("اینجا دایره مرکزه! هر قطاری که ساخته بشه، مهره‌های سوخته حریف میان اینجا جا خوش می‌کنن! 🔥", show_alert=True)
        return

    if data == "start_game":
        games[user_id] = {
            "board": [" "] * 24,
            "hand_p": 9,
            "hand_ai": 9,
            "burned_p": 0,
            "burned_ai": 0,
            "mode": "place" # place (چیدن اول) / burn (سوزاندن)
        }
        await query.answer()
        await query.edit_message_text(
            "📜 **بازی نهره‌گک شروع شد!**\n\n"
            "۱. ابتدا مهره‌های آبی (🔵) خودت رو یکی‌یکی روی نقاط خالی بذار.\n"
            "۲. وقتی هر ۲ نفر ۹ مهره رو گذاشتید، نوبت حرکت دادن می‌رسه.\n"
            "۳. هر وقت قطار ۳‌تایی ساختی، می‌تونی یک مهره قرمز رو بسوزونی!",
            reply_markup=create_board_markup(games[user_id]["board"], 9, 9, 0, 0),
            parse_mode="Markdown"
        )
        return

    if data.startswith("pos_"):
        idx = int(data.split("_")[1])
        g = games.get(user_id)
        
        if not g:
            await query.answer("بازی تموم شده رفیق! از اول استارت بزن.", show_alert=True)
            return

        # اگر در حالت سوزاندن مهره حریف باشیم
        if g["mode"] == "burn":
            if g["board"][idx] == "AI":
                g["board"][idx] = " "
                g["burned_ai"] += 1
                g["mode"] = "place"
                await query.answer("ایول! مهره حریف سوخت و رفت توی دایره مرکز! 🔥", show_alert=True)
            else:
                await query.answer("دستت درد نکنه رفیق! ولی باید روی مهره قرمز حریف بزنی تا بسوزه! 😉", show_alert=True)
                return

        # حالت اول: چیدن اولیه ۹ مهره
        elif g["hand_p"] > 0:
            if g["board"][idx] != " ":
                await query.answer("اونجا که قبلاً مهره گذاشتی رفیق! یه نقطه خالی انتخاب کن 😄", show_alert=True)
                return
            
            # گذاشتن مهره کاربر
            g["board"][idx] = "P"
            g["hand_p"] -= 1

            # چک کردن قطار کاربر
            if check_mill(g["board"], idx, "P"):
                g["mode"] = "burn"
                await query.answer("ماشالله! قطار ساختی 🚂 حالا روی یکی از مهره‌های قرمز حریف بزن تا بسوزه!", show_alert=True)
            else:
                # حرکت هوش مصنوعی
                empty_spots = [i for i, val in enumerate(g["board"]) if val == " "]
                if g["hand_ai"] > 0 and empty_spots:
                    ai_move = random.choice(empty_spots)
                    g["board"][ai_move] = "AI"
                    g["hand_ai"] -= 1
                await query.answer()

        await query.edit_message_text(
            "🎮 **نوبت بازی:** مهره‌هات رو روی نقاط خالی چیدمان کن!",
            reply_markup=create_board_markup(g["board"], g["hand_p"], g["hand_ai"], g["burned_p"], g["burned_ai"])
        )

def check_mill(board, idx, player):
    for m in MILLS:
        if idx in m and board[m[0]] == board[m[1]] == board[m[2]] == player:
            return True
    return False

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    Thread(target=run_web).start()
    if TOKEN:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.run_polling()
