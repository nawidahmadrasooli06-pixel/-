import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, join_room, emit
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# 1. SERVER & REAL-TIME MULTIPLAYER (SocketIO)
# ==========================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_game_key_123'
socketio = SocketIO(app, cors_allowed_origins="*")

# ذخیره وضعیت اتاق‌های آنلاین
active_rooms = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>👑 نبرد آنلاین دو نفره</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body {
            background-color: #0f172a;
            color: #f8fafc;
            font-family: system-ui, -apple-system, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            min-height: 100vh;
            padding: 10px;
        }
        .header { text-align: center; margin-bottom: 8px; }
        .title { font-size: 18px; font-weight: bold; color: #38bdf8; margin-bottom: 4px; }
        .status { 
            font-size: 13px; color: #f1f5f9; background: #1e293b; 
            padding: 8px 16px; border-radius: 20px; border: 1px solid #38bdf8; 
            min-height: 40px; display: flex; align-items: center; justify-content: center;
        }
        .hands {
            display: flex; justify-content: space-between; width: 100%; max-width: 340px;
            margin: 8px 0; background: #1e293b; padding: 8px 12px; border-radius: 12px;
        }
        .hand-box { text-align: center; }
        .hand-title { font-size: 12px; font-weight: bold; color: #38bdf8; }
        .hand-title.red { color: #ef4444; }

        .board-container {
            position: relative; width: 340px; height: 340px;
            background: #1e293b; border-radius: 16px; border: 2px solid #334155;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }
        .board-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
        .board-svg line, .board-svg rect { stroke: #64748b; stroke-width: 2.5; fill: none; }

        .point {
            position: absolute; width: 28px; height: 28px; border-radius: 50%;
            background: rgba(255, 255, 255, 0.12); border: 2px solid #38bdf8;
            transform: translate(-50%, -50%); z-index: 2; cursor: pointer;
        }
        .point.selected { border-color: #facc15; box-shadow: 0 0 16px #facc15; }

        /* انیمیشن کشویی و نرم مهره‌ها */
        .board-piece {
            position: absolute; width: 22px; height: 22px; border-radius: 50%;
            transform: translate(-50%, -50%); z-index: 3;
            transition: left 0.5s cubic-bezier(0.25, 1, 0.5, 1), top 0.5s cubic-bezier(0.25, 1, 0.5, 1);
            pointer-events: none;
        }
        .board-piece.blue { background: #00d2ff; box-shadow: 0 0 10px #00d2ff; }
        .board-piece.red { background: #ff416c; box-shadow: 0 0 10px #ff416c; }
    </style>
</head>
<body>

    <div class="header">
        <div class="title" id="game-title">⚔️ تخته آنلاین دو نفره</div>
        <div class="status" id="status-text">در حال اتصال به سرور...</div>
    </div>

    <div class="hands">
        <div class="hand-box">
            <div class="hand-title" id="p1-display">بازیکن ۱ (آبی)</div>
        </div>
        <div class="hand-box">
            <div class="hand-title red" id="p2-display">بازیکن ۲ (قرمز)</div>
        </div>
    </div>

    <div class="board-container" id="board">
        <svg class="board-svg" viewBox="0 0 340 340">
            <rect x="20" y="20" width="300" height="300" />
            <rect x="70" y="70" width="200" height="200" />
            <rect x="120" y="120" width="100" height="100" />
            <line x1="170" y1="20" x2="170" y2="120" />
            <line x1="170" y1="220" x2="170" y2="320" />
            <line x1="20" y1="170" x2="120" y2="170" />
            <line x1="220" y1="170" x2="320" y2="170" />
        </svg>
        <div id="pieces-layer"></div>
    </div>

    <script>
        const socket = io();
        const tg = window.Telegram?.WebApp;
        if (tg) tg.expand();

        const urlParams = new URLSearchParams(window.location.search);
        const roomCode = urlParams.get('room');
        let myName = prompt("نام خود را وارد کنید:", "بازیکن") || "بازیکن";

        const POINTS = [
            {id: 0, x: 20, y: 20}, {id: 1, x: 170, y: 20}, {id: 2, x: 320, y: 20},
            {id: 3, x: 320, y: 170}, {id: 4, x: 320, y: 320}, {id: 5, x: 170, y: 320},
            {id: 6, x: 20, y: 320}, {id: 7, x: 20, y: 170},
            {id: 8, x: 70, y: 70}, {id: 9, x: 170, y: 70}, {id: 10, x: 270, y: 70},
            {id: 11, x: 270, y: 170}, {id: 12, x: 270, y: 270}, {id: 13, x: 170, y: 270},
            {id: 14, x: 70, y: 270}, {id: 15, x: 70, y: 170},
            {id: 16, x: 120, y: 120}, {id: 17, x: 170, y: 120}, {id: 18, x: 220, y: 120},
            {id: 19, x: 220, y: 170}, {id: 20, x: 220, y: 220}, {id: 21, x: 170, y: 220},
            {id: 22, x: 120, y: 220}, {id: 23, x: 120, y: 170}
        ];

        let gameState = { board: Array(24).fill(null), turn: 'blue' };
        let myColor = null;

        const boardEl = document.getElementById('board');
        const piecesLayer = document.getElementById('pieces-layer');
        const statusText = document.getElementById('status-text');

        POINTS.forEach(pt => {
            const pDiv = document.createElement('div');
            pDiv.className = 'point';
            pDiv.style.left = `${pt.x}px`;
            pDiv.style.top = `${pt.y}px`;
            pDiv.onclick = () => handlePointClick(pt.id);
            boardEl.appendChild(pDiv);
        });

        socket.emit('join_game', { room: roomCode, name: myName });

        socket.on('player_assigned', (data) => {
            myColor = data.color;
            statusText.innerText = `شما با رنگ ${myColor === 'blue' ? 'آبی' : 'قرمز'} وارد شدید. منتظر حریف...`;
        });

        socket.on('update_board', (data) => {
            gameState = data;
            renderBoard();
            statusText.innerText = gameState.turn === myColor ? "🔴 نوبت شماست!" : "⏳ نوبت حریف است...";
        });

        function renderBoard() {
            piecesLayer.innerHTML = '';
            POINTS.forEach(pt => {
                const color = gameState.board[pt.id];
                if (color) {
                    const piece = document.createElement('div');
                    piece.className = `board-piece ${color}`;
                    // انیمیشن کشویی روان با تغییر Positional CSS
                    piece.style.left = `${pt.x}px`;
                    piece.style.top = `${pt.y}px`;
                    piecesLayer.appendChild(piece);
                }
            });
        }

        function handlePointClick(id) {
            if (gameState.turn !== myColor) return;
            socket.emit('make_move', { room: roomCode, point: id, color: myColor });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# مدیریت WebSocket برای هم‌گام‌سازی دو بازیکن آنلاین
@socketio.on('join_game')
def handle_join(data):
    room = data['room']
    name = data['name']
    join_room(room)

    if room not in active_rooms:
        active_rooms[room] = {
            'players': {},
            'board': [None] * 24,
            'turn': 'blue'
        }

    room_data = active_rooms[room]
    if len(room_data['players']) == 0:
        room_data['players'][request.sid] = {'color': 'blue', 'name': name}
        emit('player_assigned', {'color': 'blue'})
    elif len(room_data['players']) == 1:
        room_data['players'][request.sid] = {'color': 'red', 'name': name}
        emit('player_assigned', {'color': 'red'})
        emit('update_board', room_data, to=room)

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
# 2. TELEGRAM BOT HANDLER
# ==========================================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.onrender.com")

user_states = {}
user_rooms = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("⚔️ بازی با کامپیوتر (آفلاین)", callback_data="ai_menu")],
        [InlineKeyboardButton("👥 ساخت / ورود به اتاق دو نفره (آنلاین)", callback_data="friend_room_menu")]
    ]
    msg = "👑 **به ربات تخته استراتژیک خوش آمدید!**\nلطفاً حالت بازی را انتخاب کنید:"
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "friend_room_menu":
        kb = [
            [InlineKeyboardButton("➕ ساخت اتاق جدید", callback_data="select_game_type")],
            [InlineKeyboardButton("🔑 ورود با کد اتاق", callback_data="join_room")]
        ]
        await query.message.reply_text("👥 **بخش بازی با دوستان (آنلاین زنده):**", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "select_game_type":
        kb = [
            [InlineKeyboardButton("👑 بازی نه‌رگک آنلاین", callback_data="create_9regak")],
            [InlineKeyboardButton("⚔️ بازی سه‌رگک آنلاین", callback_data="create_3regak")]
        ]
        await query.message.reply_text("🎮 نوع بازی را برای ساخت اتاق انتخاب کنید:", reply_markup=InlineKeyboardMarkup(kb))

    elif data in ["create_9regak", "create_3regak"]:
        room_code = str(random.randint(1000, 9999))
        user_rooms[room_code] = {'host': user_id, 'type': data}
        
        url = f"{WEBAPP_URL}?room={room_code}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 ورود به تخته شما (میزبان)", web_app=WebAppInfo(url=url))]])
        
        await query.message.reply_text(
            f"🔑 **اتاق با موفقیت ساخته شد!**\nکد اتاق: `{room_code}`\n\nاین کد را به دوستتان بدهید تا وارد کند.",
            reply_markup=kb,
            parse_mode='Markdown'
        )

    elif data == "join_room":
        user_states[user_id] = 'awaiting_room_code'
        await query.message.reply_text("لطفاً کد ۴ رقمی اتاق دوستتان را ارسال کنید:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_states.get(user_id) == 'awaiting_room_code':
        if text in user_rooms:
            user_states.pop(user_id, None)
            url = f"{WEBAPP_URL}?room={text}"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 ورود به تخته دو نفره آنلاین", web_app=WebAppInfo(url=url))]])
            
            # پیام هم برای دوست و هم راهنمایی شروع بازی
            await update.message.reply_text(
                f"✅ **با موفقیت وارد اتاق {text} شدید!**\nروی دکمه زیر کلیک کنید تا وارد بازی زنده با دوست خود شوید:",
                reply_markup=kb,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ کد اتاق یافت نشد یا منقضی شده است. دوباره کد را بفرستید:")

if __name__ == '__main__':
    import threading
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.run_polling()
