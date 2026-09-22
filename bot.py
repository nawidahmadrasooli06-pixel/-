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
        .title { font-size: 20px; font-weight: bold; color: #38bdf8; margin-bottom: 4px; }
        .status { 
            font-size: 12px; 
            color: #f1f5f9; 
            background: #1e293b; 
            padding: 6px 14px; 
            border-radius: 20px; 
            border: 1px solid #38bdf8; 
            min-height: 36px; 
            display: flex; 
            align-items: center; 
            justify-content: center;
            text-align: center;
        }
        
        .hands {
            display: flex;
            justify-content: space-between;
            width: 100%;
            max-width: 350px;
            margin: 8px 0;
            background: #1e293b;
            padding: 8px 12px;
            border-radius: 12px;
        }
        .hand-box { text-align: center; }
        .hand-title { font-size: 12px; font-weight: bold; color: #38bdf8; margin-bottom: 4px; }
        .hand-title.red { color: #ef4444; }
        .pieces-container { display: flex; gap: 3px; flex-wrap: wrap; max-width: 110px; }
        .piece-icon { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
        .piece-icon.blue { background: #00d2ff; box-shadow: 0 0 5px #00d2ff; }
        .piece-icon.red { background: #ff416c; box-shadow: 0 0 5px #ff416c; }

        .board-container {
            position: relative;
            width: 340px;
            height: 340px;
            background: #1e293b;
            border-radius: 16px;
            border: 2px solid #334155;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            margin-top: 5px;
        }
        
        .board-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
        .board-svg line, .board-svg rect { stroke: #64748b; stroke-width: 2.5; fill: none; }

        .point {
            position: absolute;
            width: 26px;
            height: 26px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.15);
            border: 2px solid #38bdf8;
            transform: translate(-50%, -50%);
            z-index: 2;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: border-color 0.3s, background 0.3s;
        }
        .point.selected {
            border-color: #facc15;
            box-shadow: 0 0 14px #facc15;
            background: rgba(250, 204, 21, 0.4);
        }
        .point.killable {
            border-color: #ef4444;
            box-shadow: 0 0 14px #ef4444;
            animation: pulse 1s infinite;
        }
        .point.mill-highlight {
            border-color: #facc15;
            box-shadow: 0 0 18px #facc15;
            animation: millPulse 0.8s infinite alternate;
        }

        @keyframes pulse {
            0% { transform: translate(-50%, -50%) scale(1); }
            50% { transform: translate(-50%, -50%) scale(1.15); }
            100% { transform: translate(-50%, -50%) scale(1); }
        }
        @keyframes millPulse {
            0% { transform: translate(-50%, -50%) scale(1); box-shadow: 0 0 8px #facc15; }
            100% { transform: translate(-50%, -50%) scale(1.25); box-shadow: 0 0 20px #facc15; }
        }

        .board-piece {
            position: absolute;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            z-index: 3;
            transition: left 0.4s ease-in-out, top 0.4s ease-in-out;
            pointer-events: none;
        }
        .board-piece.blue { background: #00d2ff; box-shadow: 0 0 8px #00d2ff; }
        .board-piece.red { background: #ff416c; box-shadow: 0 0 8px #ff416c; }

        .graveyard {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border: 1.5px dashed #64748b;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: center;
            gap: 2px;
            padding: 4px;
            z-index: 1;
        }
        .graveyard-piece { width: 10px; height: 10px; border-radius: 50%; }
        .graveyard-piece.blue { background: #00d2ff; }
        .graveyard-piece.red { background: #ff416c; }

        .btn-reset {
            margin-top: 12px;
            padding: 10px 24px;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        }

        /* WINNER MODAL */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(15, 23, 42, 0.85);
            z-index: 100;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            text-align: center;
        }
        .modal-content {
            background: #1e293b;
            border: 2px solid #facc15;
            border-radius: 16px;
            padding: 24px;
            max-width: 320px;
            box-shadow: 0 0 25px rgba(250, 204, 21, 0.4);
            animation: popIn 0.4s ease-out;
        }
        @keyframes popIn {
            0% { transform: scale(0.5); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }
        .winner-title { font-size: 22px; font-weight: bold; color: #facc15; margin-bottom: 12px; }
        .winner-msg { font-size: 14px; color: #f8fafc; line-height: 1.6; margin-bottom: 18px; }
    </style>
</head>
<body>

    <div class="header">
        <div class="title">👑 نبرد حماسی نه‌رگک</div>
        <div class="status" id="status-text">شروع بازی...</div>
    </div>

    <div class="hands">
        <div class="hand-box">
            <div class="hand-title" id="player-name-display">آبی: 9</div>
            <div class="pieces-container" id="blue-hand"></div>
        </div>
        <div class="hand-box">
            <div class="hand-title red">کامپیوتر: 9</div>
            <div class="pieces-container" id="red-hand"></div>
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

        <div class="graveyard" id="graveyard"></div>
        <div id="pieces-layer"></div>
    </div>

    <button class="btn-reset" onclick="resetGame()">شروع مجدد بازی</button>

    <!-- WINNER MODAL -->
    <div class="modal" id="winner-modal">
        <div class="modal-content">
            <div class="winner-title">🎉 پایان بازی 🎉</div>
            <div class="winner-msg" id="winner-text"></div>
            <button class="btn-reset" onclick="closeModalAndReset()">شروع مجدد بازی</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram?.WebApp;
        if (tg) tg.expand();

        let playerName = prompt("لطفاً نام خود را برای بازی وارد کنید:", "احمد") || "احمد";

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

        const MILLS = [
            [0,1,2], [2,3,4], [4,5,6], [6,7,0],
            [8,9,10], [10,11,12], [12,13,14], [14,15,8],
            [16,17,18], [18,19,20], [20,21,22], [22,23,16],
            [1,9,17], [3,11,19], [5,13,21], [7,15,23]
        ];

        let state = {
            board: Array(24).fill(null),
            blueHand: 9,
            redHand: 9,
            turn: 'blue',
            phase: 'place',
            selectedPoint: null,
            isRemoving: false,
            killedBlue: 0,
            killedRed: 0,
            formedMillsBlue: [],
            formedMillsRed: [],
            lastBrokenMillBlue: null,
            highlightedMill: [],
            gameOver: false
        };

        const boardEl = document.getElementById('board');
        const piecesLayer = document.getElementById('pieces-layer');
        const statusText = document.getElementById('status-text');

        function initBoard() {
            document.getElementById('player-name-display').innerText = `${playerName} (آبی)`;
            POINTS.forEach(pt => {
                const pDiv = document.createElement('div');
                pDiv.className = 'point';
                pDiv.style.left = `${pt.x}px`;
                pDiv.style.top = `${pt.y}px`;
                pDiv.id = `pt-${pt.id}`;
                pDiv.onclick = () => handlePointClick(pt.id);
                boardEl.appendChild(pDiv);
            });
            setStatus(`نوبت شماست (${playerName}) - مهره بگذارید`);
            updateUI();
        }

        function updateUI() {
            const bHand = document.getElementById('blue-hand');
            const rHand = document.getElementById('red-hand');
            bHand.innerHTML = '';
            rHand.innerHTML = '';
            for(let i=0; i<state.blueHand; i++) bHand.appendChild(createPieceIcon('blue'));
            for(let i=0; i<state.redHand; i++) rHand.appendChild(createPieceIcon('red'));

            const graveyard = document.getElementById('graveyard');
            graveyard.innerHTML = '';
            for(let i=0; i<state.killedRed; i++) {
                const p = document.createElement('div');
                p.className = 'graveyard-piece red';
                graveyard.appendChild(p);
            }
            for(let i=0; i<state.killedBlue; i++) {
                const p = document.createElement('div');
                p.className = 'graveyard-piece blue';
                graveyard.appendChild(p);
            }

            POINTS.forEach(pt => {
                const ptEl = document.getElementById(`pt-${pt.id}`);
                ptEl.classList.remove('selected', 'killable', 'mill-highlight');
                
                if (state.selectedPoint === pt.id) {
                    ptEl.classList.add('selected');
                }
                if (state.isRemoving && state.board[pt.id] === 'red') {
                    ptEl.classList.add('killable');
                }
                if (state.highlightedMill.includes(pt.id)) {
                    ptEl.classList.add('mill-highlight');
                }
            });

            // Smooth sliding pieces layer
            piecesLayer.innerHTML = '';
            POINTS.forEach(pt => {
                const color = state.board[pt.id];
                if (color) {
                    const piece = document.createElement('div');
                    piece.className = `board-piece ${color}`;
                    piece.style.left = `${pt.x}px`;
                    piece.style.top = `${pt.y}px`;
                    piecesLayer.appendChild(piece);
                }
            });
        }

        function createPieceIcon(color) {
            const d = document.createElement('div');
            d.className = `piece-icon ${color}`;
            return d;
        }

        function setStatus(msg) {
            statusText.innerText = msg;
        }

        function checkWinCondition() {
            if (state.phase !== 'move') return false;

            let blueRemaining = POINTS.filter(p => state.board[p.id] === 'blue').length;
            let redRemaining = POINTS.filter(p => state.board[p.id] === 'red').length;

            if (state.killedRed >= 7 || redRemaining <= 2) {
                triggerWin(playerName, "آبی");
                return true;
            } else if (state.killedBlue >= 7 || blueRemaining <= 2) {
                triggerWin("کامپیوتر", "قرمز");
                return true;
            }
            return false;
        }

        function triggerWin(winnerName, pieceColor) {
            state.gameOver = true;
            confetti({ particleCount: 120, spread: 80, origin: { y: 0.6 } });
            
            document.getElementById('winner-text').innerHTML = `
                🏆 <b>${winnerName}</b> با مهره <b>${pieceColor}</b> برنده این نبرد شد!<br><br>
                لطفاً اگر می‌خواهید دوباره بازی کنید، روی دکمه زیر کلیک کنید.
            `;
            document.getElementById('winner-modal').style.display = 'flex';
        }

        function closeModalAndReset() {
            document.getElementById('winner-modal').style.display = 'none';
            resetGame();
        }

        function handlePointClick(id) {
            if (state.gameOver || state.turn !== 'blue') return;

            if (state.isRemoving) {
                if (state.board[id] === 'red') {
                    state.board[id] = null;
                    state.killedRed++;
                    state.isRemoving = false;
                    state.highlightedMill = [];
                    if (!checkWinCondition()) {
                        switchTurn();
                    }
                }
                updateUI();
                return;
            }

            if (state.phase === 'place') {
                if (state.board[id] === null && state.blueHand > 0) {
                    state.board[id] = 'blue';
                    if (checkNewMill(id, 'blue')) {
                        state.board[id] = null;
                        setStatus("⚠️ ساخت قطار قبل از اتمام تمام مهره‌ها مجاز نیست!");
                        return;
                    }
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
                        const fromPt = state.selectedPoint;
                        
                        // Check back move restriction
                        if (state.lastBrokenMillBlue && state.lastBrokenMillBlue.from === id && state.lastBrokenMillBlue.to === fromPt) {
                            setStatus("🚫 بازگشت به قطار قبلی مجاز نیست! ترکیب جدید بسازید.");
                            state.selectedPoint = null;
                            updateUI();
                            return;
                        }

                        // Temporarily break existing mill tracking for this piece
                        MILLS.forEach(m => {
                            if (m.includes(fromPt)) {
                                let key = m.slice().sort().join('-');
                                let idx = state.formedMillsBlue.indexOf(key);
                                if (idx !== -1) {
                                    state.formedMillsBlue.splice(idx, 1);
                                    state.lastBrokenMillBlue = { millKey: key, from: fromPt, to: id };
                                }
                            }
                        });

                        state.board[id] = 'blue';
                        state.board[fromPt] = null;
                        
                        const formedMill = getFormedMill(id, 'blue');
                        state.selectedPoint = null;

                        if (formedMill) {
                            state.isRemoving = true;
                            state.highlightedMill = formedMill;
                            setStatus("🔥 قطار جدید ساخته شد! یکی از مهره‌های قرمز را بسوزانید.");
                        } else {
                            if (!checkWinCondition()) {
                                switchTurn();
                            }
                        }
                    } else if (state.board[id] === 'blue') {
                        state.selectedPoint = id;
                    }
                }
            }
            updateUI();
        }

        function getFormedMill(ptId, color) {
            for (let mill of MILLS) {
                if (mill.includes(ptId) && mill.every(p => state.board[p] === color)) {
                    let millKey = mill.slice().sort().join('-');
                    let formedList = color === 'blue' ? state.formedMillsBlue : state.formedMillsRed;
                    if (!formedList.includes(millKey)) {
                        formedList.push(millKey);
                        return mill;
                    }
                }
            }
            return null;
        }

        function checkNewMill(ptId, color) {
            return getFormedMill(ptId, color) !== null;
        }

        function checkPhase() {
            if (state.blueHand === 0 && state.redHand === 0) {
                state.phase = 'move';
            }
        }

        function switchTurn() {
            if (state.gameOver) return;
            state.turn = state.turn === 'blue' ? 'red' : 'blue';
            if (!state.isRemoving) {
                setStatus(state.turn === 'blue' ? (state.phase === 'place' ? `نوبت ${playerName}: نقطه خالی را لمس کنید` : `نوبت ${playerName}: مهره را جابه‌جا کنید`) : "تفکر هوش مصنوعی قوی...");
            }
            updateUI();
            if (state.turn === 'red') {
                setTimeout(aiMove, 700);
            }
        }

        function aiMove() {
            if (state.gameOver) return;

            if (state.phase === 'place' && state.redHand > 0) {
                let emptyPoints = POINTS.map(p => p.id).filter(id => state.board[id] === null);
                let targetPt = null;

                for (let mill of MILLS) {
                    let blueInMill = mill.filter(p => state.board[p] === 'blue').length;
                    let emptyInMill = mill.filter(p => state.board[p] === null);
                    if (blueInMill === 2 && emptyInMill.length === 1) {
                        targetPt = emptyInMill[0];
                        break;
                    }
                }

                if (targetPt === null) {
                    targetPt = emptyPoints[Math.floor(Math.random() * emptyPoints.length)];
                }

                state.board[targetPt] = 'red';
                state.redHand--;
            } else {
                let redPieces = POINTS.map(p => p.id).filter(id => state.board[id] === 'red');
                let emptyPoints = POINTS.map(p => p.id).filter(id => state.board[id] === null);
                
                if (redPieces.length > 0 && emptyPoints.length > 0) {
                    let moved = false;
                    for (let f of redPieces) {
                        for (let t of emptyPoints) {
                            state.board[f] = null;
                            state.board[t] = 'red';
                            let formedMill = getFormedMill(t, 'red');
                            if (formedMill) {
                                moved = true;
                                state.highlightedMill = formedMill;
                                setStatus("🤖 کامپیوتر یک قطار ساخت!");
                                updateUI();

                                setTimeout(() => {
                                    let bluePiecesOnBoard = POINTS.map(p => p.id).filter(id => state.board[id] === 'blue');
                                    if (bluePiecesOnBoard.length > 0) {
                                        let killTarget = bluePiecesOnBoard[Math.floor(Math.random() * bluePiecesOnBoard.length)];
                                        state.board[killTarget] = null;
                                        state.killedBlue++;
                                    }
                                    state.highlightedMill = [];
                                    checkPhase();
                                    if (!checkWinCondition()) {
                                        state.turn = 'blue';
                                        setStatus(state.phase === 'place' ? `نوبت ${playerName}: نقطه خالی را لمس کنید` : `نوبت ${playerName}: مهره را جابه‌جا کنید`);
                                    }
                                    updateUI();
                                }, 1200);
                                return;
                            }
                            state.board[f] = 'red';
                            state.board[t] = null;
                        }
                        if (moved) break;
                    }

                    if (!moved) {
                        let from = redPieces[Math.floor(Math.random() * redPieces.length)];
                        let to = emptyPoints[Math.floor(Math.random() * emptyPoints.length)];
                        state.board[from] = null;
                        state.board[to] = 'red';
                    }
                }
            }

            checkPhase();
            if (!checkWinCondition()) {
                state.turn = 'blue';
                setStatus(state.phase === 'place' ? `نوبت ${playerName}: نقطه خالی را لمس کنید` : `نوبت ${playerName}: مهره را جابه‌جا کنید`);
            }
            updateUI();
        }

        function resetGame() {
            state = {
                board: Array(24).fill(null),
                blueHand: 9,
                redHand: 9,
                turn: 'blue',
                phase: 'place',
                selectedPoint: null,
                isRemoving: false,
                killedBlue: 0,
                killedRed: 0,
                formedMillsBlue: [],
                formedMillsRed: [],
                lastBrokenMillBlue: null,
                highlightedMill: [],
                gameOver: false
            };
            setStatus(`نوبت شماست (${playerName}) - مهره بگذارید`);
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
    app_url = WEBAPP_URL.strip()
    
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
            "⚔️ **بازی سه‌رگک:**\n\n🔹 **مرحله ۱:** مهره‌های خود (❌) را در خانه‌های خالی بنشانید.",
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

        if game['phase'] == 'place':
            if board[idx] == '':
                board[idx] = 'X'
                game['x_count'] += 1

                if check_win(board, 'X'):
                    await query.edit_message_text("🎉 **تبریک! شما برنده این نبرد شدید!**", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')
                    serekak_games.pop(user_id, None)
                    return

                if game['o_count'] < 3:
                    ai_idx = get_smart_ai_move(board)
                    if ai_idx is not None:
                        board[ai_idx] = 'O'
                        game['o_count'] += 1

                if check_win(board, 'O'):
                    await query.edit_message_text("🤖 **هوش مصنوعی برنده شد!**", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')
                    serekak_games.pop(user_id, None)
                    return

                if game['x_count'] == 3 and game['o_count'] == 3:
                    game['phase'] = 'move'
                    await query.edit_message_text(
                        "🔄 **تمام مهره‌ها کاشته شدند!**\nحالا وارد **فاز جابه‌جایی** شدید.",
                        reply_markup=get_serekak_keyboard(board),
                        parse_mode='Markdown'
                    )
                    return

                await query.edit_message_text("🎮 **نوبت شماست!** خانه خالی را انتخاب کنید.", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')

        elif game['phase'] == 'move':
            if game['selected'] is None:
                if board[idx] == 'X':
                    game['selected'] = idx
                    await query.edit_message_text("🟡 **مهره انتخاب شد!** خانه مقصد را انتخاب کن:", reply_markup=get_serekak_keyboard(board, selected=idx), parse_mode='Markdown')
            else:
                if board[idx] == '':
                    board[idx] = 'X'
                    board[game['selected']] = ''
                    game['selected'] = None

                    if check_win(board, 'X'):
                        await query.edit_message_text("🎉 **قطار کامل شد! شما برنده این میدان شدید!**", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')
                        serekak_games.pop(user_id, None)
                        return

                    ai_from, ai_to = get_smart_ai_shift(board)
                    if ai_from is not None and ai_to is not None:
                        board[ai_from] = ''
                        board[ai_to] = 'O'

                    if check_win(board, 'O'):
                        await query.edit_message_text("🤖 **هوش مصنوعی برنده شد!**", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')
                        serekak_games.pop(user_id, None)
                        return

                    await query.edit_message_text("🎮 **نوبت شماست!** مهره را جابه‌جا کنید.", reply_markup=get_serekak_keyboard(board), parse_mode='Markdown')
                elif board[idx] == 'X':
                    game['selected'] = idx
                    await query.edit_message_text("🟡 **مهره جدید انتخاب شد!** خانه مقصد را بزنید:", reply_markup=get_serekak_keyboard(board, selected=idx), parse_mode='Markdown')

    elif data == "friend_room_menu":
        kb = [
            [InlineKeyboardButton("➕ ساخت اتاق جدید", callback_data="create_room")],
            [InlineKeyboardButton("🔑 ورود با کد اتاق", callback_data="join_room")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")]
        ]
        await query.message.reply_text("👥 **بخش بازی با دوستان (دو نفره):**\nاتاق بسازید و کد آن را برای دوست خود بفرستید!", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data == "create_room":
        room_code = str(random.randint(1000, 9999))
        rooms[room_code] = {'host': user_id, 'guest': None}
        await query.message.reply_text(f"🔑 **اتاق ساخته شد!**\nکد اتاق شما: `{room_code}`\nاین کد را به دوستت بده تا وارد اتاق شود.", parse_mode='Markdown')

    elif data == "join_room":
        user_states[user_id] = 'awaiting_room_code'
        await query.message.reply_text("لطفاً کد ۴ رقمی اتاق دوستت رو بفرست:")

    elif data == "guide":
        guide_text = (
            "📖 **راهنمای بازی‌ها:**\n\n"
            "⚔️ **بازی سه‌رگک:**\n"
            "۳ مهره را جابه‌جا کنید تا قطار ساخته و برنده شوید.\n\n"
            "👑 **بازی نه‌رگک:**\n"
            "در فاز جابه‌جایی با ساخت هر قطار جدید، یک مهره حریف را می‌سوزانید. زمانی که مهره‌های حریف به ۲ برسد، برنده اعلام می‌شوید!"
        )
        await query.message.reply_text(guide_text, parse_mode='Markdown')

    elif data == "settings":
        await query.message.reply_text("⚙️ **تنظیمات:**\nدرجه سختی هوش مصنوعی روی **سطح بسیار سخت** تنظیم شده است.")

    elif data == "about":
        about_text = (
            "🤖 **درباره ربات:**\n\n"
            "خوش آمدی رفیق! این ربات با هدف ایجاد یک فضای کل‌کل و سرگرمی و خوش‌گذرانی آنلاین و رقابت با رفیقات و هوش مصنوعی طراحی شده بزن بترکون😂🔥\n\n"
            "طراحی و ساخت بات\n"
            "ldCactuc = نــوید\n"
            "@cactuc580"
        )
        await query.message.reply_text(about_text)

    elif data == "back_main":
        await start(update, context)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_states.get(user_id) == 'awaiting_room_code':
        if text in rooms:
            rooms[text]['guest'] = user_id
            user_states.pop(user_id, None)
            await update.message.reply_text(f"✅ با موفقیت وارد اتاق `{text}` شدید! بازی آنلاین شروع شد.", parse_mode='Markdown')
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
