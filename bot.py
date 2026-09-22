import os
import json
import random
from flask import Flask, render_template_string, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

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
    <title>👑 نبرد حماسی نه‌رگک</title>
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
        .title { font-size: 22px; font-weight: bold; color: #38bdf8; margin-bottom: 5px; }
        .status { font-size: 13px; color: #f1f5f9; background: #1e293b; padding: 8px 16px; border-radius: 20px; border: 1px solid #38bdf8; }
        
        .hands {
            display: flex;
            justify-content: space-between;
            width: 100%;
            max-width: 340px;
            margin: 12px 0;
            background: #1e293b;
            padding: 10px 15px;
            border-radius: 12px;
        }
        .hand-box { text-align: center; }
        .hand-title { font-size: 12px; color: #94a3b8; margin-bottom: 5px; }
        .pieces-container { display: flex; gap: 4px; flex-wrap: wrap; max-width: 110px; }
        .piece-icon { width: 14px; height: 14px; border-radius: 50%; display: inline-block; }
        .piece-icon.blue { background: #00d2ff; box-shadow: 0 0 6px #00d2ff; }
        .piece-icon.red { background: #ff416c; box-shadow: 0 0 6px #ff416c; }

        .board-container {
            position: relative;
            width: 320px;
            height: 320px;
            background: #1e293b;
            border-radius: 16px;
            border: 2px solid #334155;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }
        
        .board-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
        .board-svg line, .board-svg rect { stroke: #64748b; stroke-width: 2.5; fill: none; }

        .point {
            position: absolute;
            width: 26px;
            height: 26px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid #38bdf8;
            transform: translate(-50%, -50%);
            z-index: 2;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .point.selected {
            border-color: #facc15;
            box-shadow: 0 0 14px #facc15;
            background: rgba(250, 204, 21, 0.4);
        }

        .board-piece {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            pointer-events: none;
        }
        .board-piece.blue { background: #00d2ff; box-shadow: 0 0 8px #00d2ff; }
        .board-piece.red { background: #ff416c; box-shadow: 0 0 8px #ff416c; }

        .btn-reset {
            margin-top: 15px;
            padding: 10px 20px;
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
        <div class="title">👑 نبرد حماسی نه‌رگک</div>
        <div class="status" id="status-text">نوبت شماست (آبی) - مهره بگذارید</div>
    </div>

    <div class="hands">
        <div class="hand-box">
            <div class="hand-title">دست شما (آبی): <span id="blue-count">9</span></div>
            <div class="pieces-container" id="blue-hand"></div>
        </div>
        <div class="hand-box">
            <div class="hand-title">کامپیوتر (قرمز): <span id="red-count">9</span></div>
            <div class="pieces-container" id="red-hand"></div>
        </div>
    </div>

    <div class="board-container" id="board">
        <svg class="board-svg" viewBox="0 0 320 320">
            <rect x="20" y="20" width="280" height="280" />
            <rect x="70" y="70" width="180" height="180" />
            <rect x="120" y="120" width="80" height="80" />
            <line x1="160" y1="20" x2="160" y2="120" />
            <line x1="160" y1="200" x2="160" y2="300" />
            <line x1="20" y1="160" x2="120" y2="160" />
            <line x1="200" y1="160" x2="300" y2="160" />
        </svg>
    </div>

    <button class="btn-reset" onclick="resetGame()">شروع مجدد بازی</button>

    <script>
        const tg = window.Telegram?.WebApp;
        if (tg) tg.expand();

        const POINTS = [
            {id: 0, x: 20, y: 20}, {id: 1, x: 160, y: 20}, {id: 2, x: 300, y: 20},
            {id: 3, x: 300, y: 160}, {id: 4, x: 300, y: 300}, {id: 5, x: 160, y: 300},
            {id: 6, x: 20, y: 300}, {id: 7, x: 20, y: 160},
            {id: 8, x: 70, y: 70}, {id: 9, x: 160, y: 70}, {id: 10, x: 250, y: 70},
            {id: 11, x: 250, y: 160}, {id: 12, x: 250, y: 250}, {id: 13, x: 160, y: 250},
            {id: 14, x: 70, y: 250}, {id: 15, x: 70, y: 160},
            {id: 16, x: 120, y: 120}, {id: 17, x: 160, y: 120}, {id: 18, x: 200, y: 120},
            {id: 19, x: 200, y: 160}, {id: 20, x: 200, y: 200}, {id: 21, x: 160, y: 200},
            {id: 22, x: 120, y: 200}, {id: 23, x: 120, y: 160}
        ];

        let state = {
            board: Array(24).fill(null),
            blueHand: 9,
            redHand: 9,
            turn: 'blue',
            phase: 'place',
            selectedPoint: null
        };

        const boardEl = document.getElementById('board');
        const statusText = document.getElementById('status-text');

        function initBoard() {
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
            const bHand = document.getElementById('blue-hand');
            const rHand = document.getElementById('red-hand');
            bHand.innerHTML = '';
            rHand.innerHTML = '';
            for(let i=0; i<state.blueHand; i++) bHand.appendChild(createPieceIcon('blue'));
            for(let i=0; i<state.redHand; i++) rHand.appendChild(createPieceIcon('red'));
            
            document.getElementById('blue-count').innerText = state.blueHand;
            document.getElementById('red-count').innerText = state.redHand;

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
                statusText.innerText = state.phase === 'place' ? "نوبت شماست: لمس نقطه‌های خالی برای قرار دادن مهره" : "نوبت شماست: مهره را انتخاب و جابه‌جا کنید";
            } else {
                statusText.innerText = "تفکر هوش مصنوعی...";
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
                setTimeout(aiMove, 600);
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
# 2. TELEGRAM BOT
# ==========================================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://game-nawid.onrender.com")

serekak_games = {}
rooms = {}
user_states = {}

WIN_COMBOS = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]

def get_serekak_keyboard(board, selected=None):
    keyboard = []
    symbols = {'': '⬜', 'X': '❌', 'O': '⭕'}
    for r in range(3):
        row = []
        for c in range(3):
            idx = r * 3 + c
            text = symbols[board[idx]]
            if selected == idx:
                text = "🟡"
            row.append(InlineKeyboardButton(text, callback_data=f"serekak_{idx}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ انصراف و خروج", callback_data="serekak_exit")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Direct Render HTTPS URL
    app_url = WEBAPP_URL.rstrip('/')
    
    keyboard = [
        [InlineKeyboardButton("⚔️ نبرد هیجان‌انگیز سه‌رگک (با کامپیوتر)", callback_data="play_serekak_ai")],
        [InlineKeyboardButton("👑 نبرد حماسی نه‌رگک (تخته آنلاین)", web_app=WebAppInfo(url=app_url))],
        [InlineKeyboardButton("👥 ساخت / ورود به اتاق بازی با دوستان", callback_data="friend_room_menu")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"), InlineKeyboardButton("📖 راهنمای بازی", callback_data="guide")],
        [InlineKeyboardButton("ℹ️ درباره ربات", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "سلام رفیق! 👑 به مرکز بازی‌های استراتژیک خوش آمدی.\nلطفاً یکی از گزینه‌های زیر را انتخاب کن:"
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "play_serekak_ai":
        serekak_games[user_id] = {
            'board': [''] * 9,
            'x_count': 0,
            'o_count': 0,
            'phase': 'place',
            'selected': None
        }
        await query.message.reply_text(
            "⚔️ **بازی سه‌رگک برابر هوش مصنوعی قدرتمند!**\n\n🔹 **مرحله ۱:** مهره‌های خود (❌) را در خانه‌های خالی بنشانید.",
            reply_markup=get_serekak_keyboard(serekak_games[user_id]['board']),
            parse_mode='Markdown'
        )

    elif data.startswith("serekak_"):
        if data == "serekak_exit":
            serekak_games.pop(user_id, None)
            await query.edit_message_text("از بازی خارج شدی. /start را بزن.")
            return

        idx = int(data.split("_")[1])
        game = serekak_games.get(user_id)
        if not game:
            return

        board = game['board']

        # --- PHASE 1: PLACING PIECES ---
        if game['phase'] == 'place':
            if board[idx] == '':
                board[idx] = 'X'
                game['x_count'] += 1

                if check_win(board, 'X'):
                    await query.edit_message_text("🎉 **تبریک! شما هوش مصنوعی قدرتمند را شکست دادید!**", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')
                    serekak_games.pop(user_id, None)
                    return

                # AI Turn
                if game['o_count'] < 3:
                    ai_idx = get_smart_ai_move(board)
                    if ai_idx is not None:
                        board[ai_idx] = 'O'
                        game['o_count'] += 1

                if check_win(board, 'O'):
                    await query.edit_message_text("🤖 **هوش مصنوعی برنده شد! دوباره شانس خودت رو امتحان کن.**", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')
                    serekak_games.pop(user_id, None)
                    return

                if game['x_count'] == 3 and game['o_count'] == 3:
                    game['phase'] = 'move'
                    await query.edit_message_text(
                        "🔄 **تمام مهره‌ها کاشته شدند!**\nحالا وارد **فاز جابه‌جایی و ساخت قطار** شدید. مهره خود (❌) را انتخاب کرده و به خانه خالی منتقل کنید.",
                        reply_markup=get_serekak_keyboard(board),
                        parse_mode='Markdown'
                    )
                    return

                await query.edit_message_text("🎮 **نوبت شماست!** خانه خالی را انتخاب کنید.", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')

        # --- PHASE 2: MOVING PIECES (TRAIN PHASE) ---
        elif game['phase'] == 'move':
            if game['selected'] is None:
                if board[idx] == 'X':
                    game['selected'] = idx
                    await query.edit_message_text("🟡 **مهره انتخاب شد!** حالا خانه خالی مقصد را انتخاب کن:", reply_markup=get_serekak_keyboard(board, selected=idx), parse_mode='Markdown')
            else:
                if board[idx] == '':
                    board[idx] = 'X'
                    board[game['selected']] = ''
                    game['selected'] = None

                    if check_win(board, 'X'):
                        await query.edit_message_text("🚂🎉 **قطار کامل شد! شما برنده شدید!**", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')
                        serekak_games.pop(user_id, None)
                        return

                    # Smart AI Movement
                    ai_from, ai_to = get_smart_ai_shift(board)
                    if ai_from is not None and ai_to is not None:
                        board[ai_from] = ''
                        board[ai_to] = 'O'

                    if check_win(board, 'O'):
                        await query.edit_message_text("🤖🚂 **هوش مصنوعی قطار ساخت و برنده شد!**", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')
                        serekak_games.pop(user_id, None)
                        return

                    await query.edit_message_text("🎮 **نوبت شماست!** مهره را جابه‌جا کنید تا قطار بسازید.", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')
                elif board[idx] == 'X':
                    game['selected'] = idx
                    await query.edit_message_text("🟡 **مهره جدید انتخاب شد!** خانه مقصد را بزنید:", reply_markup=get_serekak_keyboard(board, selected=idx), parse_mode='Markdown')

    elif data == "friend_room_menu":
        kb = [
            [InlineKeyboardButton("➕ ساخت اتاق جدید", callback_data="create_room")],
            [InlineKeyboardButton("🔑 ورود با کد اتاق", callback_data="join_room")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")]
        ]
        await query.message.reply_text("👥 **بخش بازی با دوستان (دو نفره):**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data == "create_room":
        room_code = str(random.randint(1000, 9999))
        rooms[room_code] = {'host': user_id, 'guest': None}
        await query.message.reply_text(f"🔑 **اتاق ساخته شد!**\nکد اتاق شما: `{room_code}`\nاین کد را برای دوستتان بفرستید تا وارد بازی شود.", parse_mode='Markdown')

    elif data == "join_room":
        user_states[user_id] = 'awaiting_room_code'
        await query.message.reply_text("لطفاً کد ۴ رقمی اتاق دوستت رو بفرست:")

    elif data == "guide":
        guide_text = (
            "📖 **راهنمای جامع بازی‌ها:**\n\n"
            "⚔️ **بازی سه‌رگک (دوز):**\n"
            "۱. ابتدا هر بازیکن ۳ مهره روی صفحه قرار می‌دهد.\n"
            "۲. پس از اتمام مهره‌ها، فاز جابه‌جایی شروع می‌شود و باید مهره‌ها را در خانه‌های خالی جابه‌جا کنید تا قطار (۳ مهره هم‌ردیف) بسازید.\n\n"
            "👑 **بازی نه‌رگک (تخته سنتی):**\n"
            "روی نقاط درخشان تقاطع‌ها کلیک کنید تا مهره قرار داده و حریف را محاصره کنید!"
        )
        await query.message.reply_text(guide_text, parse_mode='Markdown')

    elif data == "settings":
        await query.message.reply_text("⚙️ **تنظیمات:**\nسطح هوش مصنوعی روی حالت **پیشرفته/قوی** فعال است.")

    elif data == "about":
        await query.message.reply_text("🤖 **درباره ربات:**\nاین ربات هوشمند جهت اجرای بازی‌های استراتژیک سنتی (سه‌رگک و نه‌رگک) به‌صورت آنلاین و هوش مصنوعی طراحی و اجرا شده است.\n\nطراح و توسعه‌دهنده: نوید ❤️")

    elif data == "back_main":
        await start(update, context)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_states.get(user_id) == 'awaiting_room_code':
        if text in rooms:
            rooms[text]['guest'] = user_id
            user_states.pop(user_id, None)
            await update.message.reply_text(f"✅ با موفقیت وارد اتاق `{text}` شدید! بازی به‌زودی شروع می‌شود.", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ کد اتاق اشتباه است. دوباره وارد کنید:")

def check_win(b, p):
    return any(b[x] == b[y] == b[z] == p for x, y, z in WIN_COMBOS)

def get_smart_ai_move(board):
    for i in range(9):
        if board[i] == '':
            board[i] = 'O'
            if check_win(board, 'O'):
                return i
            board[i] = ''

    for i in range(9):
        if board[i] == '':
            board[i] = 'X'
            if check_win(board, 'X'):
                board[i] = ''
                return i
            board[i] = ''

    if board[4] == '':
        return 4

    empty = [i for i, v in enumerate(board) if v == '']
    return random.choice(empty) if empty else None

def get_smart_ai_shift(board):
    o_indices = [i for i, v in enumerate(board) if v == 'O']
    empty_indices = [i for i, v in enumerate(board) if v == '']

    for f in o_indices:
        for t in empty_indices:
            board[f] = ''
            board[t] = 'O'
            if check_win(board, 'O'):
                return f, t
            board[f] = 'O'
            board[t] = ''

    if o_indices and empty_indices:
        return random.choice(o_indices), random.choice(empty_indices)
    return None, None

if __name__ == '__main__':
    import threading
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False)).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.run_polling()
