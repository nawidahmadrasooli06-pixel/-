import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, join_room, emit
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# 1. SERVER & REAL-TIME WEBSOCKET (Flask & SocketIO)
# ==========================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'navid_game_secret_key_2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# ذخیره‌سازی وضعیت اتاق‌های آنلاین
active_rooms = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>🎮 مرکز بازی استراتژیک</title>
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
            padding: 12px;
        }

        /* صفحات منوی مینی‌اپ */
        .screen { display: none; width: 100%; max-width: 360px; text-align: center; }
        .screen.active { display: flex; flex-direction: column; align-items: center; }

        .btn {
            width: 100%; padding: 14px; margin: 8px 0;
            background: linear-gradient(135deg, #1c2541, #3a506b);
            color: #4ea8de; border: 1.5px solid #4ea8de; border-radius: 12px;
            font-size: 15px; font-weight: bold; cursor: pointer;
            transition: all 0.2s ease;
        }
        .btn:active { transform: scale(0.97); background: #4ea8de; color: #0b132b; }

        .input-box {
            width: 100%; padding: 12px; margin: 10px 0;
            border-radius: 10px; border: 1px solid #4ea8de;
            background: #1c2541; color: #fff; text-align: center; font-size: 18px;
        }

        /* وضعیت و تخته بازی */
        .game-status {
            font-size: 13px; color: #5bc0be; background: #1c2541;
            padding: 6px 14px; border-radius: 20px; border: 1px solid #5bc0be;
            margin-bottom: 10px; width: 100%; text-align: center;
        }

        /* تخته بزرگ‌تر با حلقه‌های بازتر */
        .board-container {
            position: relative; width: 350px; height: 350px;
            background: #1c2541; border-radius: 18px; border: 2px solid #3a506b;
            box-shadow: 0 8px 24px rgba(0,0,0,0.6); margin-top: 5px;
        }
        .board-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
        .board-svg line, .board-svg rect { stroke: #5bc0be; stroke-width: 2.5; fill: none; }

        /* نقاط و مهره‌های ظریف‌تر (خوردتر) */
        .point {
            position: absolute; width: 22px; height: 22px; border-radius: 50%;
            background: rgba(91, 192, 190, 0.2); border: 1.5px solid #5bc0be;
            transform: translate(-50%, -50%); z-index: 2; cursor: pointer;
        }

        /* انیمیشن کشویی و روان حرکت مهره‌ها */
        .board-piece {
            position: absolute; width: 18px; height: 18px; border-radius: 50%;
            transform: translate(-50%, -50%); z-index: 3;
            transition: left 0.45s cubic-bezier(0.25, 1, 0.5, 1), top 0.45s cubic-bezier(0.25, 1, 0.5, 1);
            pointer-events: none;
        }
        .board-piece.blue { background: #00b4d8; box-shadow: 0 0 8px #00b4d8; }
        .board-piece.red { background: #ff4d6d; box-shadow: 0 0 8px #ff4d6d; }
    </style>
</head>
<body>

    <!-- صفحه ۱: انتخاب حالت اصلی -->
    <div id="screen-main" class="screen active">
        <h2 style="margin-bottom: 20px; color: #4ea8de;">🎮 انتخاب حالت بازی</h2>
        <button class="btn" onclick="showScreen('screen-mode-select')">👥 بازی با دوستت</button>
        <button class="btn" onclick="startAI()">🤖 بازی با کامپیوتر</button>
    </div>

    <!-- صفحه ۲: انتخاب نوع بازی -->
    <div id="screen-mode-select" class="screen">
        <h3 style="margin-bottom: 15px;">نوع بازی را انتخاب کنید:</h3>
        <button class="btn" onclick="selectGameType('sere')">⚔️ بازی سره‌شکن</button>
        <button class="btn" onclick="selectGameType('nael')">👑 بازی نعل‌شکن</button>
        <button class="btn" style="border-color:#ff4d6d; color:#ff4d6d;" onclick="showScreen('screen-main')">🔙 بازگشت</button>
    </div>

    <!-- صفحه ۳: ساخت یا ورود به اتاق -->
    <div id="screen-room-action" class="screen">
        <h3 id="selected-type-title" style="margin-bottom: 15px; color:#5bc0be;"></h3>
        <button class="btn" onclick="createNewRoom()">➕ ساخت اتاق جدید</button>
        <div style="margin: 15px 0; width: 100%;">
            <input type="number" id="room-code-input" class="input-box" placeholder="کد ۴ رقمی اتاق دوستت">
            <button class="btn" onclick="joinExistingRoom()">🔑 ورود به اتاق دوست</button>
        </div>
        <button class="btn" style="border-color:#ff4d6d; color:#ff4d6d;" onclick="showScreen('screen-mode-select')">🔙 بازگشت</button>
    </div>

    <!-- صفحه ۴: نمایش کد اتاق ساخت‌شده -->
    <div id="screen-room-created" class="screen">
        <h3>اتاق شما ساخته شد! 🎉</h3>
        <p style="margin: 10px 0; color: #aaa;">کد زیر را کپی کن و برای دوستت بفرست:</p>
        <div id="created-code-display" class="input-box" style="font-size: 26px; letter-spacing: 4px; color: #5bc0be;">----</div>
        <p style="font-size: 12px; color: #e0a96d; margin-bottom: 15px;">به محض اینکه دوستت کد را وارد کند، هر دو وارد تخته می‌شوید...</p>
    </div>

    <!-- صفحه ۵: تخته بازی آنلاین -->
    <div id="screen-board" class="screen">
        <div class="game-status" id="status-text">در حال اتصال...</div>
        <div class="board-container" id="board">
            <svg class="board-svg" viewBox="0 0 350 350">
                <rect x="20" y="20" width="310" height="310" />
                <rect x="75" y="75" width="200" height="200" />
                <rect x="130" y="130" width="90" height="90" />
                <line x1="175" y1="20" x2="175" y2="130" />
                <line x1="175" y1="220" x2="175" y2="330" />
                <line x1="20" y1="175" x2="130" y2="175" />
                <line x1="220" y1="175" x2="330" y2="175" />
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

        // مختصات ۲۴ نقطه تخته (با فضای بازتر)
        const POINTS = [
            {id: 0, x: 20, y: 20}, {id: 1, x: 175, y: 20}, {id: 2, x: 330, y: 20},
            {id: 3, x: 330, y: 175}, {id: 4, x: 330, y: 330}, {id: 5, x: 175, y: 330},
            {id: 6, x: 20, y: 330}, {id: 7, x: 20, y: 175},
            {id: 8, x: 75, y: 75}, {id: 9, x: 175, y: 75}, {id: 10, x: 275, y: 75},
            {id: 11, x: 275, y: 175}, {id: 12, x: 275, y: 275}, {id: 13, x: 175, y: 275},
            {id: 14, x: 75, y: 275}, {id: 15, x: 75, y: 175},
            {id: 16, x: 130, y: 130}, {id: 17, x: 175, y: 130}, {id: 18, x: 220, y: 130},
            {id: 19, x: 220, y: 175}, {id: 20, x: 220, y: 220}, {id: 21, x: 175, y: 220},
            {id: 22, x: 130, y: 220}, {id: 23, x: 130, y: 175}
        ];

        function showScreen(screenId) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById(screenId).classList.add('active');
        }

        function selectGameType(type) {
            selectedGameMode = type;
            document.getElementById('selected-type-title').innerText = type === 'sere' ? 'حالت: سره‌شکن' : 'حالت: نعل‌شکن';
            showScreen('screen-room-action');
        }

        function createNewRoom() {
            currentRoom = Math.floor(1000 + Math.random() * 9000).toString();
            document.getElementById('created-code-display').innerText = currentRoom;
            showScreen('screen-room-created');
            socket.emit('join_room_game', { room: currentRoom, mode: selectedGameMode });
        }

        function joinExistingRoom() {
            const code = document.getElementById('room-code-input').value.trim();
            if (code.length === 4) {
                currentRoom = code;
                socket.emit('join_room_game', { room: currentRoom });
            } else {
                alert("لطفاً یک کد ۴ رقمی معتبر وارد کنید!");
            }
        }

        function startAI() {
            alert("حالت بازی با کامپیوتر به‌زودی متصل می‌شود!");
        }

        // ساخت ساختار نقاط روی تخته
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

        // دریافت رویدادهای WebSocket
        socket.on('player_assigned', (data) => {
            myColor = data.color;
        });

        socket.on('game_start', (data) => {
            showScreen('screen-board');
            gameState = data;
            renderBoard();
            updateStatus();
        });

        socket.on('update_board', (data) => {
            gameState = data;
            renderBoard();
            updateStatus();
        });

        function updateStatus() {
            const statusEl = document.getElementById('status-text');
            if (gameState.turn === myColor) {
                statusEl.innerText = "🔴 نوبت شماست! (حرکت دهید)";
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
            socket.emit('make_move', { room: currentRoom, point: id, color: myColor });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# مدیریت اتاق‌های بازی آنلاین
@socketio.on('join_room_game')
def handle_join(data):
    room = data['room']
    join_room(room)

    if room not in active_rooms:
        active_rooms[room] = {
            'players': [],
            'board': [None] * 24,
            'turn': 'blue'
        }

    room_data = active_rooms[room]
    if len(room_data['players']) == 0:
        room_data['players'].append(request.sid)
        emit('player_assigned', {'color': 'blue'})
    elif len(room_data['players']) == 1:
        room_data['players'].append(request.sid)
        emit('player_assigned', {'color': 'red'})
        # با ورود بازیکن دوم، تخته اتوماتیک برای هر دو نفر باز می‌شود
        emit('game_start', room_data, to=room)

@socketio.on('make_move')
def handle_move(data):
    room = data['room']
    pt = data['point']
    color = data['color']

    room_data = active_rooms.get(room)
    if room_data and room_data['turn'] == color:
        room_data['board'][pt] = color
        room_data['turn'] = 'red' if color == 'blue' else 'blue'
        emit('update_board', room_data, to=room)

# ==========================================
# 2. TELEGRAM BOT (منوی کامل مطابق درخواست)
# ==========================================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.onrender.com")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🎮 ورود به بازی نعل‌شکن / سره‌شکن", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📖 راهنمای بازی", callback_data="guide"), InlineKeyboardButton("ℹ️ درباره ربات", callback_data="about")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")]
    ]
    msg = "👑 **سلام! به مرکز بازی‌های استراتژیک خوش آمدید.**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "guide":
        guide_text = (
            "📖 **راهنمای جامع بازی‌ها:**\n\n"
            "⚔️ **بازی سره‌شکن:** در این بازی باید مهره‌های خود را طوری بچینید که خطوط ۳ تایی بسازید و مهره‌های حریف را حذف کنید.\n\n"
            "👑 **بازی نعل‌شکن:** حالت پیشرفته‌تر استراتژیک که نیازمند محاصره کامل مهره‌های حریف و مسدود کردن راه‌های حرکت است."
        )
        await query.message.reply_text(guide_text, parse_mode='Markdown')

    elif query.data == "about":
        about_text = (
            "ℹ️ **درباره ربات:**\n\n"
            "این ربات یک پلتفرم آنلاین برای اجرای بازی‌های فکری و استراتژیک دو نفره (سره‌شکن و نعل‌شکن) به‌صورت زنده در تلگرام است.\n\n"
            "👤 **سازنده و توسعه‌دهنده:** نوید\n"
            "🆔 **آیدی ارتباطی:** @Navid_Admin"
        )
        await query.message.reply_text(about_text, parse_mode='Markdown')

    elif query.data == "settings":
        await query.message.reply_text("⚙️ **تنظیمات:**\nتنظیمات اعلان‌ها و ظاهر بازی فعال است.")

if __name__ == '__main__':
    import threading
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.run_polling()
