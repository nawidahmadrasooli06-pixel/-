import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, join_room, emit
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==========================================
# 1. SERVER & REAL-TIME WEBSOCKET (Flask & SocketIO)
# ==========================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'navid_game_final_secret_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ذخیره‌سازی دقیق اتاق‌های فعال
active_rooms = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>🎮 بازی استراتژیک قطار (سه‌رگک / نه‌رگک)</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body {
            background-color: #0b132b;
            color: #ffffff;
            font-family: system-ui, -apple-system, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 10px;
        }

        .screen { display: none; width: 100%; max-width: 360px; text-align: center; }
        .screen.active { display: flex; flex-direction: column; align-items: center; }

        .btn {
            width: 100%; padding: 13px; margin: 7px 0;
            background: linear-gradient(135deg, #1c2541, #3a506b);
            color: #4ea8de; border: 1.5px solid #4ea8de; border-radius: 12px;
            font-size: 15px; font-weight: bold; cursor: pointer;
            transition: all 0.2s ease;
        }
        .btn:active { transform: scale(0.97); background: #4ea8de; color: #0b132b; }

        .input-box {
            width: 100%; padding: 12px; margin: 8px 0;
            border-radius: 10px; border: 1px solid #4ea8de;
            background: #1c2541; color: #fff; text-align: center; font-size: 18px;
        }

        .code-display-box {
            background: #1c2541; border: 2px dashed #5bc0be; border-radius: 12px;
            padding: 15px; font-size: 28px; letter-spacing: 6px; color: #5bc0be;
            margin: 10px 0; cursor: pointer; position: relative;
        }
        .code-display-box:active { background: #223059; }

        .game-status {
            font-size: 13px; color: #5bc0be; background: #1c2541;
            padding: 6px 14px; border-radius: 20px; border: 1px solid #5bc0be;
            margin-bottom: 8px; width: 100%; text-align: center;
        }

        /* تخته بازی استاندارد و خلوت‌تر */
        .board-container {
            position: relative; width: 340px; height: 340px;
            background: #1c2541; border-radius: 16px; border: 2px solid #3a506b;
            box-shadow: 0 6px 20px rgba(0,0,0,0.6); margin-top: 4px;
        }
        .board-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
        .board-svg line, .board-svg rect { stroke: #5bc0be; stroke-width: 2; fill: none; }

        /* نقاط و مهره‌های کوچک‌تر و ظریف‌تر */
        .point {
            position: absolute; width: 18px; height: 18px; border-radius: 50%;
            background: rgba(91, 192, 190, 0.15); border: 1.2px solid #5bc0be;
            transform: translate(-50%, -50%); z-index: 2; cursor: pointer;
        }

        .board-piece {
            position: absolute; width: 15px; height: 15px; border-radius: 50%;
            transform: translate(-50%, -50%); z-index: 3;
            transition: left 0.4s cubic-bezier(0.25, 1, 0.5, 1), top 0.4s cubic-bezier(0.25, 1, 0.5, 1);
            pointer-events: none;
        }
        .board-piece.blue { background: #00b4d8; box-shadow: 0 0 6px #00b4d8; }
        .board-piece.red { background: #ff4d6d; box-shadow: 0 0 6px #ff4d6d; }

        .toast {
            position: fixed; bottom: 20px; background: #5bc0be; color: #0b132b;
            padding: 8px 16px; border-radius: 8px; font-weight: bold; font-size: 13px;
            display: none; z-index: 99; box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }
    </style>
</head>
<body>

    <div id="toast" class="toast">کد اتاق با موفقیت کپی شد!</div>

    <!-- صفحه ۱: منوی اصلی مینی‌اپ -->
    <div id="screen-main" class="screen active">
        <h2 style="margin-bottom: 18px; color: #4ea8de;">🎮 بازی قطار (سه‌رگک / نه‌رگک)</h2>
        <button class="btn" onclick="showScreen('screen-mode-select')">👥 بازی با دوستت (آنلاین)</button>
        <button class="btn" onclick="startAI()">🤖 بازی با کامپیوتر (آفلاین)</button>
    </div>

    <!-- صفحه ۲: انتخاب حالت بازی -->
    <div id="screen-mode-select" class="screen">
        <h3 style="margin-bottom: 14px;">انتخاب نوع سبک بازی:</h3>
        <button class="btn" onclick="selectGameType('sere')">⚔️ بازی سه‌رگک (سره‌شکن)</button>
        <button class="btn" onclick="selectGameType('nael')">👑 بازی نه‌رگک (نعل‌شکن)</button>
        <button class="btn" style="border-color:#ff4d6d; color:#ff4d6d;" onclick="showScreen('screen-main')">🔙 بازگشت</button>
    </div>

    <!-- صفحه ۳: ایجاد یا ورود با کد -->
    <div id="screen-room-action" class="screen">
        <h3 id="selected-type-title" style="margin-bottom: 12px; color:#5bc0be;"></h3>
        <button class="btn" onclick="createNewRoom()">➕ ساخت اتاق جدید</button>
        <div style="margin: 12px 0; width: 100%;">
            <input type="number" id="room-code-input" class="input-box" placeholder="کلید / کد اتاق دوستت را وارد کن">
            <button class="btn" onclick="joinExistingRoom()">🔑 ورود به اتاق با کد</button>
        </div>
        <button class="btn" style="border-color:#ff4d6d; color:#ff4d6d;" onclick="showScreen('screen-mode-select')">🔙 بازگشت</button>
    </div>

    <!-- صفحه ۴: نمایش کد اتاق با قابلیت کپی با یک لمس -->
    <div id="screen-room-created" class="screen">
        <h3 style="color: #5bc0be;">اتاق شما ساخته شد! 🎉</h3>
        <p style="margin: 8px 0; color: #aaa; font-size: 13px;">برای کپی کردن کد، روی آن لمس کنید:</p>
        <div id="created-code-display" class="code-display-box" onclick="copyRoomCode()">----</div>
        <p style="font-size: 12px; color: #e0a96d; margin: 10px 0;">کد را برای دوستت بفرست؛ به محض ورود او، مستقیم وارد تخته می‌شوید!</p>
        <button class="btn" style="border-color:#ff4d6d; color:#ff4d6d; margin-top: 15px;" onclick="showScreen('screen-room-action')">🔙 لغو و بازگشت</button>
    </div>

    <!-- صفحه ۵: تخته بازی آنلاین -->
    <div id="screen-board" class="screen">
        <div class="game-status" id="status-text">در حال برقراری ارتباط...</div>
        <div class="board-container" id="board">
            <svg class="board-svg" viewBox="0 0 340 340">
                <rect x="20" y="20" width="300" height="300" />
                <rect x="75" y="75" width="190" height="190" />
                <rect x="130" y="130" width="80" height="80" />
                <line x1="170" y1="20" x2="170" y2="130" />
                <line x1="170" y1="210" x2="170" y2="320" />
                <line x1="20" y1="170" x2="130" y2="170" />
                <line x1="210" y1="170" x2="320" y2="170" />
            </svg>
            <div id="pieces-layer"></div>
        </div>
    </div>

    <script>
        const socket = io();
        const tg = window.Telegram?.WebApp;
        if (tg) tg.expand();

        let currentRoom = null;
        let selectedGameMode = '';
        let myColor = null;
        let gameState = { board: Array(24).fill(null), turn: 'blue' };

        // مختصات ۲۴ نقطه استاندارد و خلوتر
        const POINTS = [
            {id: 0, x: 20, y: 20}, {id: 1, x: 170, y: 20}, {id: 2, x: 320, y: 20},
            {id: 3, x: 320, y: 170}, {id: 4, x: 320, y: 320}, {id: 5, x: 170, y: 320},
            {id: 6, x: 20, y: 320}, {id: 7, x: 20, y: 170},
            {id: 8, x: 75, y: 75}, {id: 9, x: 170, y: 75}, {id: 10, x: 265, y: 75},
            {id: 11, x: 265, y: 170}, {id: 12, x: 265, y: 265}, {id: 13, x: 170, y: 265},
            {id: 14, x: 75, y: 265}, {id: 15, x: 75, y: 170},
            {id: 16, x: 130, y: 130}, {id: 17, x: 170, y: 130}, {id: 18, x: 210, y: 130},
            {id: 19, x: 210, y: 170}, {id: 20, x: 210, y: 210}, {id: 21, x: 170, y: 210},
            {id: 22, x: 130, y: 210}, {id: 23, x: 130, y: 170}
        ];

        function showScreen(screenId) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById(screenId).classList.add('active');
        }

        function selectGameType(type) {
            selectedGameMode = type;
            document.getElementById('selected-type-title').innerText = type === 'sere' ? 'سبک: سه‌رگک (سره‌شکن)' : 'سبک: نه‌رگک (نعل‌شکن)';
            showScreen('screen-room-action');
        }

        function createNewRoom() {
            currentRoom = Math.floor(1000 + Math.random() * 9000).toString();
            document.getElementById('created-code-display').innerText = currentRoom;
            showScreen('screen-room-created');
            socket.emit('create_or_join', { room: currentRoom, mode: selectedGameMode });
        }

        function copyRoomCode() {
            const code = document.getElementById('created-code-display').innerText;
            navigator.clipboard.writeText(code).then(() => {
                const toast = document.getElementById('toast');
                toast.style.display = 'block';
                setTimeout(() => { toast.style.display = 'none'; }, 2000);
            });
        }

        function joinExistingRoom() {
            const code = document.getElementById('room-code-input').value.trim();
            if (code.length === 4) {
                currentRoom = code;
                socket.emit('create_or_join', { room: currentRoom });
            } else {
                alert("لطفاً کد ۴ رقمی معتبر وارد کنید!");
            }
        }

        function startAI() {
            alert("حالت بازی با کامپیوتر به‌زودی فعال می‌شود!");
        }

        const boardEl = document.getElementById('board');
        const piecesLayer = document.getElementById('pieces-layer');
        POINTS.forEach(pt => {
            const pDiv = document.createElement('div');
            pDiv.className = 'point';
            pDiv.style.left = `${pt.x}px`;
            pDiv.style.top = `${pt.y}px`;
            pDiv.onclick = () => handlePointClick(pt.id);
            boardEl.appendChild(pDiv);
        });

        socket.on('set_color', (data) => {
            myColor = data.color;
        });

        socket.on('start_game_board', (data) => {
            showScreen('screen-board');
            gameState = data;
            renderBoard();
            updateStatus();
        });

        socket.on('refresh_board', (data) => {
            gameState = data;
            renderBoard();
            updateStatus();
        });

        function updateStatus() {
            const statusEl = document.getElementById('status-text');
            if (gameState.turn === myColor) {
                statusEl.innerText = "🔴 نوبت شماست! (مهره را حرکت دهید)";
                statusEl.style.borderColor = "#00b4d8";
            } else {
                statusEl.innerText = "⏳ نوبت حریف است...";
                statusEl.style.borderColor = "#ff4d6d";
            }
        }

        function renderBoard() {
            piecesLayer.innerHTML = '';
            POINTS.forEach(pt => {
                const color = gameState.board[pt.id];
                if (color) {
                    const piece = document.createElement('div');
                    piece.className = `board-piece ${color}`;
                    piece.style.left = `${pt.x}px`;
                    piece.style.top = `${pt.y}px`;
                    piecesLayer.appendChild(piece);
                }
            });
        }

        function handlePointClick(id) {
            if (gameState.turn !== myColor) return;
            socket.emit('player_move', { room: currentRoom, point: id, color: myColor });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# مدیریت دقیق نشست‌های اتصال اتاق بدون معطلی حریف
@socketio.on('create_or_join')
def handle_create_or_join(data):
    room = data['room']
    join_room(room)

    if room not in active_rooms:
        active_rooms[room] = {
            'players': [],
            'board': [None] * 24,
            'turn': 'blue'
        }

    room_data = active_rooms[room]
    
    if request.sid not in room_data['players']:
        if len(room_data['players']) < 2:
            room_data['players'].append(request.sid)

    # تخصیص رنگ به بازیکنان
    if len(room_data['players']) == 1:
        emit('set_color', {'color': 'blue'})
    elif len(room_data['players']) == 2:
        emit('set_color', {'color': 'red'}, to=room_data['players'][1])
        # به محض تکمیل نفر دوم، هر دو نفر مستقیم وارد صفحه تخته بازی می‌شوند
        socketio.emit('start_game_board', room_data, room=room)

@socketio.on('player_move')
def handle_player_move(data):
    room = data['room']
    pt = data['point']
    color = data['color']

    room_data = active_rooms.get(room)
    if room_data and room_data['turn'] == color:
        room_data['board'][pt] = color
        room_data['turn'] = 'red' if color == 'blue' else 'blue'
        socketio.emit('refresh_board', room_data, room=room)

# ==========================================
# 2. TELEGRAM BOT (منوهای کامل و بدون ایراد)
# ==========================================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.onrender.com")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🎮 ورود به بازی قطار (سه‌رگک / نه‌رگک)", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📖 راهنمای بازی", callback_data="guide"), InlineKeyboardButton("ℹ️ درباره ربات", callback_data="about")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")]
    ]
    msg = "👑 **سلام! به مرکز بازی‌های استراتژیک (قطار) خوش آمدید.**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "guide":
        guide_text = (
            "📖 **راهنمای جامع بازی قطار (سه‌رگک / نه‌رگک):**\n\n"
            "⚔️ **سه‌رگک (سره‌شکن):** هدف ساخت ردیف‌های ۳ تایی از مهره‌ها برای حذف مهره‌های حریف است.\n\n"
            "👑 **نه‌رگک (نعل‌شکن):** نسخه پیشرفته‌تر با استراتژی‌های محاصره کامل مهره‌ها."
        )
        await query.message.reply_text(guide_text, parse_mode='Markdown')

    elif query.data == "about":
        about_text = (
            "ℹ️ **درباره ربات:**\n\n"
            "پلتفرم آنلاین اجرای بازی‌های فکری و استراتژیک قطار به‌صورت زنده در تلگرام.\n\n"
            "👤 **سازنده و توسعه‌دهنده:** نوید\n"
            "🆔 **آیدی ارتباطی:** @Navid_Admin"
        )
        await query.message.reply_text(about_text, parse_mode='Markdown')

    elif query.data == "settings":
        await query.message.reply_text("⚙️ **تنظیمات ربات:**\nگزینه‌های تنظیمات صدا و ظاهر بازی فعال است.")

if __name__ == '__main__':
    import threading
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.run_polling()
