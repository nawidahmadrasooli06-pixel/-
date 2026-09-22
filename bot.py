import os
import logging
from threading import Thread
from flask import Flask, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app_web = Flask(__name__)

# رابط گرافیکی پیشرفته، مینیمال و انیمیشنی (Mini App)
HTML_GAME = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>بازی نهره‌گک</title>
    <style>
        * { box-sizing: border-box; user-select: none; }
        body {
            background: linear-gradient(135deg, #0f172a, #1e293b);
            color: #f8fafc;
            font-family: 'Segoe UI', Tahoma, sans-serif;
            text-align: center;
            margin: 0;
            padding: 12px;
            overflow: hidden;
        }
        .header-title {
            font-size: 18px;
            font-weight: bold;
            color: #38bdf8;
            margin-bottom: 8px;
        }
        #status-bar {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid #334155;
            padding: 8px 12px;
            border-radius: 10px;
            font-size: 13px;
            color: #e2e8f0;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        /* مخزن مهره‌ها */
        .pouches-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 360px;
            margin: 0 auto 10px auto;
            background: rgba(15, 23, 42, 0.6);
            padding: 8px 12px;
            border-radius: 12px;
            border: 1px solid #1e293b;
        }
        .pouch-box {
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
            max-width: 140px;
        }
        
        /* مهره‌های ریزتر و شیک */
        .piece {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
            transition: all 0.5s cubic-bezier(0.25, 1, 0.5, 1);
        }
        .piece.blue { background: radial-gradient(circle at 5px 5px, #38bdf8, #0284c7); }
        .piece.red { background: radial-gradient(circle at 5px 5px, #f43f5e, #be123c); }

        /* تخته بزرگ و مینیمال */
        #board-wrapper {
            position: relative;
            width: 350px;
            height: 350px;
            margin: 0 auto;
            background: #090d16;
            border-radius: 20px;
            border: 2px solid #334155;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            padding: 10px;
        }
        svg { width: 100%; height: 100%; }
        line, rect { stroke: #64748b; stroke-width: 2; fill: none; }
        
        /* نقطه‌های ریز دکمه‌ای */
        circle.spot {
            fill: #38bdf8;
            r: 6;
            cursor: pointer;
            transition: transform 0.2s, fill 0.2s;
        }
        circle.spot:hover {
            fill: #facc15;
            r: 8;
        }
        
        /* دایره مرکز سوخته‌ها */
        circle.center-burn-ring {
            fill: rgba(244, 63, 94, 0.08);
            stroke: #f43f5e;
            stroke-dasharray: 4;
            stroke-width: 1.5;
        }
    </style>
</head>
<body>

    <div class="header-title">🎲 تخته سنتی نهره‌گک (۲ نفره)</div>
    <div id="status-bar">💡 رفیق! روی هر نقطه‌ای که می‌خوای مهره‌ت بذاری کلیک کن.</div>

    <!-- مخزن مهره‌های آبی (شما) و قرمز (حریف) -->
    <div class="pouches-container">
        <div>
            <div style="font-size: 11px; margin-bottom:3px; color:#38bdf8;">دست شما (آبی):</div>
            <div class="pouch-box" id="pouch-blue"></div>
        </div>
        <div>
            <div style="font-size: 11px; margin-bottom:3px; color:#f43f5e;">دست حریف (قرمز):</div>
            <div class="pouch-box" id="pouch-red"></div>
        </div>
    </div>

    <!-- تخته اصلی با انیمیشن کشویی -->
    <div id="board-wrapper">
        <svg viewBox="0 0 300 300" id="svg-board">
            <!-- ۳ مربع اصلی -->
            <rect x="20" y="20" width="260" height="260" rx="6" />
            <rect x="60" y="60" width="180" height="180" rx="4" />
            <rect x="100" y="100" width="100" height="100" rx="2" />

            <!-- خطوط رابط وسط -->
            <line x1="150" y1="20" x2="150" y2="100" />
            <line x1="150" y1="200" x2="150" y2="280" />
            <line x1="20" y1="150" x2="100" y2="150" />
            <line x1="200" y1="150" x2="280" y2="150" />

            <!-- خانه مرکز (مهره‌های سوخته) -->
            <circle cx="150" cy="150" r="28" class="center-burn-ring" />

            <!-- ۲۴ نقطه ریز اصلی روی تخته -->
            <!-- مربع بیرونی -->
            <circle cx="20" cy="20" class="spot" data-id="0" />
            <circle cx="150" cy="20" class="spot" data-id="1" />
            <circle cx="280" cy="20" class="spot" data-id="2" />
            <circle cx="280" cy="150" class="spot" data-id="3" />
            <circle cx="280" cy="280" class="spot" data-id="4" />
            <circle cx="150" cy="280" class="spot" data-id="5" />
            <circle cx="20" cy="280" class="spot" data-id="6" />
            <circle cx="20" cy="150" class="spot" data-id="7" />

            <!-- مربع میانی -->
            <circle cx="60" cy="60" class="spot" data-id="8" />
            <circle cx="150" cy="60" class="spot" data-id="9" />
            <circle cx="240" cy="60" class="spot" data-id="10" />
            <circle cx="240" cy="150" class="spot" data-id="11" />
            <circle cx="240" cy="240" class="spot" data-id="12" />
            <circle cx="150" cy="240" class="spot" data-id="13" />
            <circle cx="60" cy="240" class="spot" data-id="14" />
            <circle cx="60" cy="150" class="spot" data-id="15" />

            <!-- مربع کوچک -->
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
        // ساخت ۹ مهره برای هر دو طرف در مخزن
        const pBlue = document.getElementById('pouch-blue');
        const pRed = document.getElementById('pouch-red');

        for(let i=0; i<9; i++){
            let b = document.createElement('div');
            b.className = 'piece blue';
            b.id = 'blue-' + i;
            pBlue.appendChild(b);

            let r = document.createElement('div');
            r.className = 'piece red';
            r.id = 'red-' + i;
            pRed.appendChild(r);
        }

        let blueCount = 0;

        // کلیک روی نقطه‌ها برای سریدن آروم مهره
        document.querySelectorAll('.spot').forEach(spot => {
            spot.addEventListener('click', function() {
                if(blueCount < 9 && this.getAttribute('data-filled') !== 'true') {
                    let piece = document.getElementById('blue-' + blueCount);
                    if(piece) {
                        this.setAttribute('data-filled', 'true');
                        this.style.fill = "#38bdf8";
                        this.style.r = "8";
                        piece.style.opacity = "0.3";
                        blueCount++;
                        document.getElementById('status-bar').innerText = "حرکت عالی بود! نوبت مهره بعدیه.";
                    }
                }
            });
        });
    </script>
</body>
</html>
"""

@app_web.route('/')
def home():
    return "Bot Server Active!"

@app_web.route('/game')
def game():
    return render_template_string(HTML_GAME)

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host='0.0.0.0', port=port)

# متن بخش درباره سازنده
ABOUT_TEXT = (
    "🎮 **ربات بازی هیجان‌انگیز نهره‌گک**\n\n"
    "👨‍💻 **طراحی و توسعه‌یافته توسط:** 〘Cactuc = نــوید\n"
    "🆔 @cactuc580\n\n"
    "💡 *اگر نظر، پیشنهاد یا ایده‌ای برای بهتر شدن بازی داشتید، می‌توانید با من در میان بگذارید.*\n\n"
    "📌 *این ربات گیمینگ صرفاً برای سرگرمی و خوش‌گذشتن شما عزیزان ساخته شده است. امیدوارم نهایت لذت را ببرید! ❤️*"
)

# منوی کامل و چندگزینه‌ای اصیل تلگرام
def get_full_main_menu():
    web_app_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'game-nawid.onrender.com')}/game"
    
    kb = [
        [InlineKeyboardButton("🤖 بازی با ربات (تک‌نفره)", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton("🌐 بازی آنلاین کشوری", callback_data="online_play"), InlineKeyboardButton("🔗 بازی با دوستان (کد / لینک)", callback_data="friend_play")],
        [InlineKeyboardButton("🏆 جدول برترین‌ها", callback_data="leaderboard"), InlineKeyboardButton("⚙️ تنظیمات / Settings", callback_data="settings")],
        [InlineKeyboardButton("ℹ️ درباره سازنده (نوید)", callback_data="about")]
    ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام رفیق! به منوی اصلی ربات بازی خوش اومدی. گزینه مورد نظرت رو انتخاب کن: 👇",
        reply_markup=get_full_main_menu()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "about":
        await query.answer()
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="main_menu")]])
        await query.edit_message_text(ABOUT_TEXT, reply_markup=back_btn, parse_mode="Markdown")

    elif data == "main_menu":
        await query.answer()
        await query.edit_message_text("منوی اصلی بازی:", reply_markup=get_full_main_menu())

    elif data in ["online_play", "friend_play", "leaderboard", "settings"]:
        await query.answer("این بخش به‌زودی در آپدیت بعدی فعال میشه رفیق! 😉", show_alert=True)

# ثبت دستور /start در کیبورد تلگرام
async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "شروع مجدد و باز کردن منوی اصلی 🎮")
    ])

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    Thread(target=run_web).start()
    if TOKEN:
        app = Application.builder().token(TOKEN).post_init(post_init).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.run_polling()
