import os
import json
import random
from flask import Flask, render_template_string, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==========================================
# 1. WEB SERVER & MINI APP FOR NEHREGAK
# ==========================================
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>بازی نره‌گک (نردبان)</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
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
            padding: 15px;
        }
        .header { text-align: center; margin-bottom: 10px; }
        .title { font-size: 20px; font-weight: bold; color: #38bdf8; margin-bottom: 5px; }
        .status { font-size: 14px; color: #94a3b8; background: #1e293b; padding: 8px 16px; border-radius: 20px; border: 1px solid #334155; }
        
        .hands {
            display: flex;
            justify-content: space-between;
            width: 100%;
            max-width: 360px;
            margin: 15px 0;
            background: #1e293b;
            padding: 10px 15px;
            border-radius: 12px;
        }
        .hand-box { text-align: center; }
        .hand-title { font-size: 12px; color: #94a3b8; margin-bottom: 5px; }
        .pieces-container { display: flex; gap: 4px; flex-wrap: wrap; max-width: 120px; }
        .piece-icon { width: 14px; height: 14px; border-radius: 50%; display: inline-block; }
        .piece-icon.blue { background: #00d2ff; box-shadow: 0 0 6px #00d2ff; }
        .piece-icon.red { background: #ff416c; box-shadow: 0 0 6px #ff416c; }

        .board-container {
            position: relative;
            width: 340px;
            height: 340px;
            background: #1e293b;
            border-radius: 16px;
            border: 2px solid #334155;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            margin-top: 10px;
        }
        
        /* Board Lines SVG */
        .board-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
        .board-svg line, .board-svg rect { stroke: #475569; stroke-width: 2; fill: none; }

        /* Intersecting Points */
        .point {
            position: absolute;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.15);
            border: 2px solid #38bdf8;
            transform: translate(-50%, -50%);
            z-index: 2;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .point:hover, .point:active {
            background: rgba(56, 189, 248, 0.4);
            scale: 1.2;
        }
        .point.selected {
            border-color: #facc15;
            box-shadow: 0 0 12px #facc15;
            background: rgba(250, 204, 21, 0.3);
        }

        /* Pieces on Board */
        .board-piece {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            pointer-events: none;
            transition: all 0.3s ease;
        }
        .board-piece.blue { background: radial-gradient(circle at 30% 30%, #80e5ff, #0088cc); box-shadow: 0 0 8px #00d2ff; }
        .board-piece.red { background: radial-gradient(circle at 30% 30%, #ff8099, #cc0033); box-shadow: 0 0 8px #ff416c; }

        .btn-reset {
            margin-top: 20px;
            padding: 10px 24px;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
        }
    </style>
</head>
<body>

    <div class="header">
        <div class="title">🎲 تخته سنتی (نره‌گک / نردبان)</div>
        <div class="status" id="status-text">نوبت شماست (آبی) - مهره بگذارید</div>
    </div>

    <div class="hands">
        <div class="hand-box">
            <div class="hand-title">دست شما (آبی): <span id="blue-count">9</span></div>
            <div class="pieces-container" id="blue-hand"></div>
        </div>
        <div class="hand-box">
            <div class="hand-title">دست حریف (قرمز): <span id="red-count">9</span></div>
            <div class="pieces-container" id="red-hand"></div>
        </div>
    </div>

    <div class="board-container" id="board">
        <svg class="board-svg" viewBox="0 0 340 340">
            <!-- Outer Square -->
            <rect x="20" y="20" width="300" height="300" />
            <!-- Middle Square -->
            <rect x="70" y="70" width="200" height="200" />
            <!-- Inner Square -->
            <rect x="120" y="120" width="100" height="100" />
            <!-- Cross Lines -->
            <line x1="170" y1="20" x2="170" y2="120" />
            <line x1="170" y1="220" x2="170" y2="320" />
            <line x1="20" y1="170" x2="120" y2="170" />
            <line x1="220" y1="170" x2="320" y2="170" />
        </svg>
    </div>

    <button class="btn-reset" onclick="resetGame()">شروع مجدد بازی</button>

    <script>
        const tg = window.Telegram?.WebApp;
        if (tg) tg.expand();

        // 24 Intersection Points positions in pixels (340x340 board)
        const POINTS = [
            // Outer
            {id: 0, x: 20, y: 20}, {id: 1, x: 170, y: 20}, {id: 2, x: 320, y: 20},
            {id: 3, x: 320, y: 170}, {id: 4, x: 320, y: 320}, {id: 5, x: 170, y: 320},
            {id: 6, x: 20, y: 320}, {id: 7, x: 20, y: 170},
            // Middle
            {id: 8, x: 70, y: 70}, {id: 9, x: 170, y: 70}, {id: 10, x: 270, y: 70},
            {id: 11, x: 270, y: 170}, {id: 12, x: 270, y: 270}, {id: 13, x: 170, y: 270},
            {id: 14, x: 70, y: 270}, {id: 15, x: 70, y: 170},
            // Inner
            {id: 16, x: 120, y: 120}, {id: 17, x: 170, y: 120}, {id: 18, x: 220, y: 120},
            {id: 19, x: 220, y: 170}, {id: 20, x: 220, y: 220}, {id: 21, x: 170, y: 220},
            {id: 22, x: 120, y: 220}, {id: 23, x: 120, y: 170}
        ];

        let state = {
            board: Array(24).fill(null), // null, 'blue', 'red'
            blueHand: 9,
            redHand: 9,
            turn: 'blue', // 'blue' (user), 'red' (AI)
            phase: 'place', // 'place', 'move'
            selectedPoint: null
        };

        const boardEl = document.getElementById('board');
        const statusText = document.getElementById('status-text');

        function initBoard() {
            // Render Points
            POINTS.forEach(pt => {
                const pDiv = document.createElement('div');
                pDiv.className = 'point';
                pDiv.style.left = `${pt.x}px`;
                pDiv.style.top = `${pt.y}px`;
                pDiv.id = `pt-${pt.id}`;
                pDiv.onclick = () => handlePointClick(pt.id);
                boardEl.appendChild(pDiv);
            });
            updateUI();
        }

        function updateUI() {
            // Render Hands
            const bHand = document.getElementById('blue-hand');
            const rHand = document.getElementById('red-hand');
            bHand.innerHTML = '';
            rHand.innerHTML = '';
            for(let i=0; i<state.blueHand; i++) bHand.appendChild(createPieceIcon('blue'));
            for(let i=0; i<state.redHand; i++) rHand.appendChild(createPieceIcon('red'));
            
            document.getElementById('blue-count').innerText = state.blueHand;
            document.getElementById('red-count').innerText = state.redHand;

            // Render Board Pieces
            POINTS.forEach(pt => {
                const ptEl = document.getElementById(`pt-${pt.id}`);
                ptEl.innerHTML = '';
                ptEl.classList.remove('selected');
                
                if (state.selectedPoint === pt.id) {
                    ptEl.classList.add('selected');
                }

                if (state.board[pt.id]) {
                    const piece = document.createElement('div');
                    piece.className = `board-piece ${state.board[pt.id]}`;
                    ptEl.appendChild(piece);
                }
            });

            if (state.turn === 'blue') {
                statusText.innerText = state.phase === 'place' ? "نوبت شماست: روی نقطه خالی کلیک کنید" : "نوبت شماست: مهره را جابه‌جا کنید";
            } else {
                statusText.innerText = "نوبت کامپیوتر است...";
            }
        }

        function createPieceIcon(color) {
            const d = document.createElement('div');
            d.className = `piece-icon ${color}`;
            return d;
        }

        function handlePointClick(id) {
            if (state.turn !== 'blue') return;

            if (state.phase === 'place') {
                if (state.board[id] === null && state.blueHand > 0) {
                    state.board[id] = 'blue';
                    state.blueHand--;
                    checkPhase();
                    switchTurn();
                }
            } else {
                // Move phase
                if (state.selectedPoint === null) {
                    if (state.board[id] === 'blue') {
                        state.selectedPoint = id;
                    }
                } else {
                    if (state.board[id] === null) {
                        state.board[id] = 'blue';
                        state.board[state.selectedPoint] = null;
                        state.selectedPoint = null;
                        switchTurn();
                    } else if (state.board[id] === 'blue') {
                        state.selectedPoint = id;
                    }
                }
            }
            updateUI();
        }

        function checkPhase() {
            if (state.blueHand === 0 && state.redHand === 0) {
                state.phase = 'move';
            }
        }

        function switchTurn() {
            state.turn = state.turn === 'blue' ? 'red' : 'blue';
            updateUI();
            if (state.turn === 'red') {
                setTimeout(aiMove, 800);
            }
        }

        function aiMove() {
            if (state.phase === 'place' && state.redHand > 0) {
                let emptyPoints = POINTS.map(p => p.id).filter(id => state.board[id] === null);
                if (emptyPoints.length > 0) {
                    let randomPt = emptyPoints[Math.floor(Math.random() * emptyPoints.length)];
                    state.board[randomPt] = 'red';
                    state.redHand--;
                }
            } else {
                let redPieces = POINTS.map(p => p.id).filter(id => state.board[id] === 'red');
                let emptyPoints = POINTS.map(p => p.id).filter(id => state.board[id] === null);
                if (redPieces.length > 0 && emptyPoints.length > 0) {
                    let from = redPieces[Math.floor(Math.random() * redPieces.length)];
                    let to = emptyPoints[Math.floor(Math.random() * emptyPoints.length)];
                    state.board[from] = null;
                    state.board[to] = 'red';
                }
            }
            checkPhase();
            state.turn = 'blue';
            updateUI();
        }

        function resetGame() {
            state = {
                board: Array(24).fill(null),
                blueHand: 9,
                redHand: 9,
                turn: 'blue',
                phase: 'place',
                selectedPoint: null
            };
            updateUI();
        }

        initBoard();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ==========================================
# 2. TELEGRAM BOT (SEREKAK & MENU)
# ==========================================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app-name.onrender.com")

# Serekak Game State Memory
serekak_games = {}

def get_serekak_keyboard(board):
    keyboard = []
    symbols = {'': '⬜', 'X': '❌', 'O': '⭕'}
    for r in range(3):
        row = []
        for c in range(3):
            idx = r * 3 + c
            val = board[idx]
            row.append(InlineKeyboardButton(symbols[val], callback_data=f"serekak_{idx}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ انصراف / خروج", callback_data="serekak_exit")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 بازی سه‌رکک (دوز تلگرامی)", callback_data="play_serekak")],
        [InlineKeyboardButton("🎲 بازی نره‌گک / نردبان (تخته)", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("ℹ️ درباره سازنده (نوید)", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "سلام رفیق! به منوی اصلی بازی‌ها خوش آمدی.👇\nلطفاً بازی مورد نظرت رو انتخاب کن:"
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "play_serekak":
        serekak_games[user_id] = {
            'board': [''] * 9,
            'turn': 'X' # User is X, AI is O
        }
        reply_markup = get_serekak_keyboard(serekak_games[user_id]['board'])
        await query.message.reply_text(
            "🎮 **نوبت شماست!** (مهره شما: ❌ / مهره هوش مصنوعی: ⭕)",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif data.startswith("serekak_"):
        if data == "serekak_exit":
            await query.edit_message_text("از بازی سه‌رکک خارج شدی. برای شروع مجدد /start را بزن.")
            return

        idx = int(data.split("_")[1])
        game = serekak_games.get(user_id)
        
        if not game or game['board'][idx] != '':
            return

        # User move
        game['board'][idx] = 'X'
        
        # Check Win
        if check_win(game['board'], 'X'):
            await query.edit_message_text("🎉 **تبریک! شما هوش مصنوعی را شکست دادید!** 🎉", reply_markup=get_serekak_keyboard(game['board']), parse_mode='Markdown')
            serekak_games.pop(user_id, None)
            return

        if '' not in game['board']:
            await query.edit_message_text("🤝 **بازی مساوی شد!**", reply_markup=get_serekak_keyboard(game['board']))
            serekak_games.pop(user_id, None)
            return

        # AI Move
        empty_indices = [i for i, v in enumerate(game['board']) if v == '']
        if empty_indices:
            ai_idx = random.choice(empty_indices)
            game['board'][ai_idx] = 'O'

        if check_win(game['board'], 'O'):
            await query.edit_message_text("🤖 **هوش مصنوعی برنده شد! دوباره تلاش کن.**", reply_markup=get_serekak_keyboard(game['board']), parse_mode='Markdown')
            serekak_games.pop(user_id, None)
            return

        await query.edit_message_text(
            "🎮 **نوبت شماست!** (مهره شما: ❌ / مهره هوش مصنوعی: ⭕)",
            reply_markup=get_serekak_keyboard(game['board']),
            parse_mode='Markdown'
        )

    elif data == "about":
        await query.message.reply_text("طراحی و توسعه توسط نوید عزیز ❤️")

def check_win(b, p):
    wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    return any(b[x] == b[y] == b[z] == p for x, y, z in wins)

# Run Flask & Telegram Bot
if __name__ == '__main__':
    import threading
    
    # Run Web Server
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False)).start()

    # Run Telegram Bot
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.run_polling()
