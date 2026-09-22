import os
import random
import string
import logging
from threading import Thread
from flask import Flask, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app_web = Flask(__name__)

HTML_GAME = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>بازی سنتی</title>
    <style>
        * { box-sizing: border-box; user-select: none; margin: 0; padding: 0; }
        body {
            background: linear-gradient(135deg, #0f172a, #1e293b);
            color: #f8fafc;
            font-family: 'Segoe UI', Tahoma, sans-serif;
            text-align: center;
            padding: 12px;
            overflow: hidden;
        }
        .header-title { font-size: 17px; font-weight: bold; color: #38bdf8; margin-bottom: 8px; }
        #status-bar {
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid #334155;
            padding: 8px 12px;
            border-radius: 10px;
            font-size: 13px;
            color: #e2e8f0;
            margin-bottom: 12px;
        }
        .pouches {
            display: flex; justify-content: space-between; align-items: center;
            max-width: 340px; margin: 0 auto 10px auto;
            background: rgba(15, 23, 42, 0.6); padding: 8px 12px; border-radius: 12px;
        }
        .pouch-box { display: flex; gap: 4px; flex-wrap: wrap; max-width: 140px; }
        .piece {
            width: 16px; height: 16px; border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
            transition: all 0.3s;
        }
        .piece.blue { background: radial-gradient(circle at 4px 4px, #38bdf8, #0284c7); }
        .piece.red { background: radial-gradient(circle at 4px 4px, #f43f5e, #be123c); }
        #board-wrapper {
            position: relative; width: 330px; height: 330px; margin: 0 auto;
            background: #090d16; border-radius: 20px; border: 2px solid #334155;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5); padding: 10px;
        }
        svg { width: 100%; height: 100%; }
        line, rect { stroke: #64748b; stroke-width: 2.5; fill: none; }
        circle.spot {
            fill: #facc15; stroke: #090d16; stroke-width: 2; r: 9;
            cursor: pointer; transition: all 0.2s;
        }
        circle.spot:hover { fill: #38bdf8; r: 11; }
        circle.center-burn { fill: rgba(244, 63, 94, 0.1); stroke: #f43f5e; stroke-dasharray: 4; stroke-width: 1.5; }
    </style>
</head>
<body>
    <div class="header-title" id="game-title">🎲 تخته سنتی (۲ نفره)</div>
    <div id="status-bar">💡 روی هر نقطه‌ای که می‌خوای مهره‌ت بذاری کلیک کن.</div>

    <div class="pouches">
        <div>
            <div style="font-size: 11px; margin-bottom:3px; color:#38bdf8;">دست شما (آبی):</div>
            <div class="pouch-box" id="pouch-blue"></div>
        </div>
        <div>
            <div style="font-size: 11px; margin-bottom:3px; color:#f43f5e;">دست حریف (قرمز):</div>
            <div class="pouch-box" id="pouch-red"></div>
        </div>
    </div>

    <div id="board-wrapper">
        <svg viewBox="0 0 300 300" id="svg-board">
            <rect x="20" y="20" width="260" height="260" rx="6" />
            <rect x="60" y="60" width="180" height="180" rx="4" />
            <rect x="100" y="100" width="100" height="100" rx="2" />
            <line x1="150" y1="20" x2="150" y2="100" />
            <line x1="150" y1="200" x2="150" y2="280" />
            <line x1="20" y1="150" x2="100" y2="150" />
            <line x1="200" y1="150" x2="280" y2="150" />
            <circle cx="150" cy="150" r="28" class="center-burn" />

            <circle cx="20" cy="20" class="spot" data-id="0" />
            <circle cx="150" cy="20" class="spot" data-id="1" />
            <circle cx="280" cy="20" class="spot" data-id="2" />
            <circle cx="280" cy="150" class="spot" data-id="3" />
            <circle cx="280" cy="280" class="spot" data-id="4" />
            <circle cx="150" cy="280" class="spot" data-id="5" />
            <circle cx="20" cy="280" class="spot" data-id="6" />
            <circle cx="20" cy="150" class="spot" data-id="7" />
            <circle cx="60" cy="60" class="spot" data-id="8" />
            <circle cx="150" cy="60" class="spot" data-id="9" />
            <circle cx="240" cy="60" class="spot" data-id="10" />
            <circle cx="240" cy="150" class="spot" data-id="11" />
            <circle cx="240" cy="240" class="spot" data-id="12" />
            <circle cx="150" cy="240" class="spot" data-id="13" />
            <circle cx="60" cy="240" class="spot" data-id="14" />
            <circle cx="60" cy="150" class="spot" data-id="15" />
            <circle cx="100" cy="100" class="spot" data-id="16" />
            <circle cx="150" cy="100" class="spot" data-id="17" />
            <circle cx="200" cy="100" class="spot" data-id="18" />
            <circle cx="200" cy="150" class="spot" data-id="19" />
            <circle cx="200" cy="200" class="spot" data-id="20" />
            <circle cx="150" cy="200" class="spot" data-id="21" />
            <circle cx="100" cy="200" class="spot" data-id="22" />
            <circle cx="100" cy="150" class="spot" data-id="23" />
        </svg>
    </div>

    <script>
        const pBlue = document.getElementById('pouch-blue');
        const pRed = document.getElementById('pouch-red');
        for(let i=0; i<9; i++){
            let b = document.createElement('div'); b.className = 'piece blue'; b.id = 'blue-' + i; pBlue.appendChild(b);
            let r = document.createElement('div'); r.className = 'piece red'; r.id = 'red-' + i; pRed.appendChild(r);
        }
        let blueCount = 0;
        document.querySelectorAll('.spot').forEach(spot => {
            spot.addEventListener('click', function() {
                if(blueCount < 9 && this.getAttribute('data-filled') !== 'true') {
                    let piece = document.getElementById('blue-' + blueCount);
                    if(piece) {
                        this.setAttribute('data-filled', 'true');
                        this.style.fill = "#38bdf8";
                        piece.style.opacity = "0.2";
                        blueCount++;
                        document.getElementById('status-bar').innerText = "حرکت عالی بود! نوبت مهره بعدی.";
                    }
                }
            });
        });
    </script>
</body>
</html>
"""

@app_web.route('/')
def home(): return "Bot Server Active!"

@app_web.route('/game')
def game(): return render_template_string(HTML_GAME)

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host='0.0.0.0', port=port)

ABOUT_TEXT = (
    "🎮 **ربات جامع بازی‌های سنتی**\n\n"
    "این ربات شامل بازی‌های اصیل و خاطره‌انگیز نهره‌گک (۹‌ریگک) و سه‌ریگک به صورت ۲‌نفره گرافیکی است.\n\n"
    "💡 *امیدواریم از بازی لذت ببرید!*"
)

def get_main_menu():
    host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'game-nawid.onrender.com')
    web_app_url = f"https://{host}/game"
    
    kb = [
        [InlineKeyboardButton("🤖 بازی با کامپیوتر (نهره‌گک)", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton("❌ بازی سه‌ریگک (۳‌ریگک)", web_app=WebAppInfo(url=web_app_url)), InlineKeyboardButton("👥 بازی با دوستان (کد)", callback_data="friend_menu")],
        [InlineKeyboardButton("📖 راهنمای بازی", callback_data="help"), InlineKeyboardButton("⚙️ تنظیمات / Settings", callback_data="settings")],
        [InlineKeyboardButton("ℹ️ درباره ربات", callback_data="about")]
    ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام رفیق! به منوی اصلی بازی خوش آمدی. لطفاً گزینه مورد نظرت را انتخاب کن: 👇", reply_markup=get_main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "about":
        await query.answer()
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="main_menu")]])
        await query.edit_message_text(ABOUT_TEXT, reply_markup=back_btn, parse_mode="Markdown")

    elif data == "main_menu":
        await query.answer()
        await query.edit_message_text("منوی اصلی بازی:", reply_markup=get_main_menu())

    elif data == "friend_menu":
        await query.answer()
        kb = [
            [InlineKeyboardButton("➕ ساخت کد اتاق جدید", callback_data="create_room")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
        await query.edit_message_text("👥 **بخش بازی دو نفره با دوستان:**\n\nکد اتاق بسازید و برای دوستتان ارسال کنید!", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "create_room":
        await query.answer()
        room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'game-nawid.onrender.com')
        web_app_url = f"https://{host}/game?room={room_code}"
        kb = [[InlineKeyboardButton("🎮 ورود به اتاق ۲ نفره", web_app=WebAppInfo(url=web_app_url))]]
        await query.edit_message_text(f"🔑 **کد اتاق:** `{room_code}`\n\nروی دکمه زیر بزنید و وارد شوید!", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data in ["help", "settings"]:
        await query.answer("این بخش فعال است!", show_alert=True)

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    Thread(target=run_web).start()
    if TOKEN:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.run_polling()
