import os
import logging
from threading import Thread
from flask import Flask, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app_web = Flask(__name__)

# کد صفحه گرافیکی بازی (HTML/CSS/JS)
HTML_GAME = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>بازی نهره‌گک</title>
    <style>
        body {
            background-color: #1e1e2e;
            color: #ffffff;
            font-family: Tahoma, sans-serif;
            text-align: center;
            margin: 0;
            padding: 10px;
            touch-action: none;
        }
        h3 { margin: 5px 0; color: #89b4fa; }
        #status-bar {
            background: #313244;
            padding: 8px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 14px;
        }
        #pouch {
            display: flex;
            justify-content: center;
            gap: 8px;
            min-height: 45px;
            background: #45475a;
            padding: 5px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .piece {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: inline-block;
            cursor: grab;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .piece.blue { background: radial-gradient(circle at 10px 10px, #89dceb, #1e66f5); }
        .piece.red { background: radial-gradient(circle at 10px 10px, #f38ba8, #d20f39); }
        
        #board-container {
            position: relative;
            width: 320px;
            height: 320px;
            margin: 0 auto;
            background: #181825;
            border-radius: 12px;
            border: 2px solid #585b70;
        }
        svg { width: 100%; height: 100%; }
        line, rect { stroke: #cdd6f4; stroke-width: 2; fill: none; }
        circle.spot {
            fill: #a6adc8;
            r: 5;
            cursor: pointer;
            transition: 0.2s;
        }
        circle.spot:hover { fill: #f9e2af; r: 8; }
        circle.center-burn {
            fill: #f38ba8;
            opacity: 0.2;
            stroke: #f38ba8;
            stroke-dasharray: 4;
        }
    </style>
</head>
<body>

    <h3>🎯 بازی نهره‌گک (تخته سنتی)</h3>
    <div id="status-bar">نوبت شماست! مهره آبی را بکشید و روی نقطه بگذارید.</div>

    <!-- مخزن مهره‌های قابل کشیدن -->
    <div id="pouch">
        <div class="piece blue" draggable="true" id="p1"></div>
        <div class="piece blue" draggable="true" id="p2"></div>
        <div class="piece blue" draggable="true" id="p3"></div>
        <div class="piece blue" draggable="true" id="p4"></div>
        <div class="piece blue" draggable="true" id="p5"></div>
        <div class="piece blue" draggable="true" id="p6"></div>
        <div class="piece blue" draggable="true" id="p7"></div>
        <div class="piece blue" draggable="true" id="p8"></div>
        <div class="piece blue" draggable="true" id="p9"></div>
    </div>

    <!-- تخته بازی با خطوط واقعی و نقطه‌های ریز -->
    <div id="board-container">
        <svg viewBox="0 0 300 300">
            <!-- ۳ مربع اصلی -->
            <rect x="20" y="20" width="260" height="260" />
            <rect x="60" y="60" width="180" height="180" />
            <rect x="100" y="100" width="100" height="100" />

            <!-- خطوط رابط وسط -->
            <line x1="150" y1="20" x2="150" y2="100" />
            <line x1="150" y1="200" x2="150" y2="280" />
            <line x1="20" y1="150" x2="100" y2="150" />
            <line x1="200" y1="150" x2="280" y2="150" />

            <!-- دایره مرکز (خانه سوخته‌ها) -->
            <circle cx="150" cy="150" r="25" class="center-burn" />

            <!-- ۲۴ نقطه ریز بازی -->
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
        // قابلیت Drag & Drop ساده
        let draggedPiece = null;
        document.querySelectorAll('.piece').forEach(p => {
            p.addEventListener('dragstart', (e) => {
                draggedPiece = e.target;
            });
        });

        document.querySelectorAll('.spot').forEach(spot => {
            spot.addEventListener('dragover', (e) => e.preventDefault());
            spot.addEventListener('drop', (e) => {
                e.preventDefault();
                if(draggedPiece) {
                    spot.style.fill = "#1e66f5";
                    spot.style.r = "10";
                    draggedPiece.remove();
                    draggedPiece = null;
                    document.getElementById('status-bar').innerText = "آفرین! حرکت بعد رو بزن.";
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # آدرس وب‌اپ بر روی سرور Render
    web_app_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'game-nawid.onrender.com')}/game"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 باز کردن تخته بازی (گرافیکی و کشویی)", web_app=WebAppInfo(url=web_app_url))]
    ])
    await update.message.reply_text("سلام نوید عزیز! برای بازی روی تخته واقعی و گرافیکی، روی دکمه زیر بزن 👇", reply_markup=kb)

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    Thread(target=run_web).start()
    if TOKEN:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.run_polling()
