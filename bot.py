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
app.config['SECRET_KEY'] = 'cactus_game_final_secret_key_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ذخیره‌سازی اتاق‌های فعال و وضعیت بازی‌ها
active_rooms = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>🌵 CACTUS - بازی نه‌رگک / سه‌رگک (قطار)</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body {
            background-color: #0d1b2a;
            color: #ffffff;
            font-family: system-ui, -apple-system, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 10px;
            overflow: hidden;
        }

        .brand-title {
            font-size: 26px;
            font-weight: 900;
            letter-spacing: 4px;
            color: #2ec4b6;
            text-shadow: 0 0 10px rgba(46, 196, 182, 0.5);
            margin-bottom: 2px;
        }

        .screen { display: none; width: 100%; max-width: 360px; text-align: center; }
        .screen.active { display: flex; flex-direction: column; align-items: center; }

        .btn {
            width: 100%; padding: 12px; margin: 6px 0;
            background: linear-gradient(135deg, #1b263b, #415a77);
            color: #e0e1dd; border: 1.5px solid #2ec4b6; border-radius: 12px;
            font-size: 15px; font-weight: bold; cursor: pointer;
            transition: all 0.2s ease;
        }
        .btn:active { transform: scale(0.97); background: #2ec4b6; color: #0d1b2a; }

        .input-box {
            width: 100%; padding: 12px; margin: 8px 0;
            border-radius: 10px; border: 1px solid #2ec4b6;
            background: #1b263b; color: #fff; text-align: center; font-size: 18px;
        }

        .code-display-box {
            background: #1b263b; border: 2px dashed #2ec4b6; border-radius: 12px;
            padding: 14px; font-size: 28px; letter-spacing: 6px; color: #2ec4b6;
            margin: 10px 0; cursor: pointer; width: 100%;
        }

        /* کارت وضعیت و امتیازات دقیقا مطابق اسکرین‌شات شما */
        .status-header {
            width: 100%; max-width: 340px; margin-bottom: 6px;
        }
        .turn-badge {
            background: rgba(27, 38, 59, 0.8);
            border: 1px solid #2ec4b6;
            border-radius: 20px;
            padding: 6px 12px;
            font-size: 13px;
            color: #e0e1dd;
            margin-bottom: 8px;
            text-align: center;
        }
        .players-bar {
            display: flex;
            justify-content: space-between;
            background: #1b263b;
            border-radius: 10px;
            padding: 8px 14px;
            font-size: 13px;
            font-weight: bold;
            border: 1px solid #415a77;
        }
        .player-blue { color: #00b4d8; }
        .player-red { color: #ff4d6d; }

        /* تخته بازی اصلی */
        .board-container {
            position: relative; width: 340px; height: 340px;
            background: #1b263b; border-radius: 16px; border: 2px solid #415a77;
            box-shadow: 0 8px 24px rgba(0,0,0,0.6);
        }
        .board-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
        .board-svg line, .board-svg rect { stroke: #415a77; stroke-width: 2; fill: none; }
        
        /* دایره مرکز برای مهره‌های سوخته */
        .center-circle {
            stroke: #2ec4b6;
            stroke-width: 1.5;
            stroke-dasharray: 4 3;
            fill: rgba(46, 196, 182, 0.05);
        }

        /* نقاط تخته */
        .point {
            position: absolute; width: 22px; height: 22px; border-radius: 50%;
            background: rgba(65, 90, 119, 0.3); border: 1.5px solid #2ec4b6;
            transform: translate(-50%, -50%); z-index: 2; cursor: pointer;
        }

        /* مهره‌ها - اندازه متناسب و جابه‌جایی روان */
        .piece {
            position: absolute; width: 20px; height: 20px; border-radius: 50%;
            transform: translate(-50%, -50%); z-index: 3;
            transition: left 0.35s cubic-bezier(0.25, 1, 0.5, 1), top 0.35s cubic-bezier(0.25, 1, 0.5, 1);
            cursor: pointer;
        }
        .piece.blue { background: #00b4d8; box-shadow: 0 0 8px #00b4d8; }
        .piece.red { background: #ff4d6d; box-shadow: 0 0 8px #ff4d6d; }
        .piece.selected { border: 2px solid #ffffff; box-shadow: 0 0 12px #ffffff; transform: translate(-50%, -50%) scale(1.2); }

        .toast {
            position: fixed; bottom: 20px; background: #2ec4b6; color: #0d1b2a;
            padding: 8px 16px; border-radius: 8px; font-weight: bold; font-size: 13px;
            display: none; z-index: 99;
        }
    </style>
</head>
<body>

    <div class="brand-title">CACTUS</div>
    <div id="toast" class="toast">کد اتاق کپی شد!</div>

    <!-- ۱. منوی اصلی -->
    <div id="screen-main" class="screen active">
        <h3 style="margin-bottom: 15px; color: #e0e1dd;">🎮 انتخاب حالت بازی</h3>
        <button class="btn" onclick="showScreen('screen-mode-select')">👥 بازی آنلاین با دوست</button>
        <button class="btn" onclick="startAIGame()">🤖 بازی با کامپیوتر (آفلاین)</button>
    </div>

    <!-- ۲. انتخاب سبک (سه‌رگک / نه‌رگک) -->
    <div id="screen-mode-select" class="screen">
        <h3 style="margin-bottom: 12px; color: #2ec4b6;">نوع بازی را انتخاب کنید:</h3>
        <button class="btn" onclick="selectMode('sere')">⚔️ بازی سه‌رگک (۳ مهره)</button>
        <button class="btn" onclick="selectMode('nael')">👑 بازی نه‌رگک (۹ مهره)</button>
        <button class="btn" style="border-color:#ff4d6d; color:#ff4d6d;" onclick="showScreen('screen-main')">🔙 بازگشت</button>
    </div>

    <!-- ۳. اتاق آنلاین -->
    <div id="screen-room-action" class="screen">
        <h3 id="mode-title" style="margin-bottom: 10px; color:#2ec4b6;"></h3>
        <button class="btn" onclick="createNewRoom()">➕ ساخت اتاق جدید</button>
        <div style="margin: 10px 0; width: 100%;">
            <input type="number" id="room-code-input" class="input-box" placeholder="کد ۴ رقمی را وارد کنید">
            <button class="btn" onclick="joinRoomByCode()">🔑 ورود به اتاق</button>
        </div>
        <button class="btn" style="border-color:#ff4d6d; color:#ff4d6d;" onclick="showScreen('screen-mode-select')">🔙 بازگشت</button>
    </div>

    <!-- ۴. کد اتاق -->
    <div id="screen-room-created" class="screen">
        <h3 style="color: #2ec4b6;">اتاق آماده است! 🎉</h3>
        <p style="margin: 6px 0; color: #aaa; font-size: 12px;">روی کد زیر بزنید تا کپی شود:</p>
        <div id="created-code" class="code-display-box" onclick="copyCode()">----</div>
        <p style="font-size: 12px; color: #e0a96d;">به محض اینکه دوستتان کد را بزند، بازی شروع می‌شود.</p>
        <button class="btn" style="border-color:#ff4d6d; color:#ff4d6d; margin-top: 10px;" onclick="showScreen('screen-room-action')">🔙 لغو</button>
    </div>

    <!-- ۵. صفحه اصلی تخته بازی -->
    <div id="screen-board" class="screen">
        <div class="status-header">
            <div class="turn-badge" id="status-turn">نوبت شماست!</div>
            <div class="players-bar">
                <span class="player-blue" id="p1-label">شما (آبی): <b id="p1-count">9</b></span>
                <span class="player-red" id="p2-label">حریف (قرمز): <b id="p2-count">9</b></span>
            </div>
        </div>

        <div class="board-container" id="board">
            <svg class="board-svg" viewBox="0 0 340 340">
                <!-- خطوط تخته -->
                <rect x="20" y="20" width="300" height="300" />
                <rect x="75" y="75" width="190" height="190" />
                <rect x="130" y="130" width="80" height="80" />
                <line x1="170" y1="20" x2="170" y2="130" />
                <line x1="170" y1="210" x2="170" y2="320" />
                <line x1="20" y1="170" x2="130" y2="170" />
                <line x1="210" y1="170" x2="320" y2="170" />
                <!-- دایره مرکز برای مهره‌های سوخته -->
                <circle cx="170" cy="170" r="35" class="center-circle" />
            </svg>
            <div id="pieces-layer"></div>
        </div>

        <button class="btn" style="margin-top: 10px; background: #ff4d6d; color: #fff; border: none;" onclick="restartGame()">شروع مجدد بازی</button>
    </div>

    <script>
        const socket = io();
        const tg = window.Telegram?.WebApp;
        if (tg) tg.expand();

        let currentRoom = null;
        let gameMode = 'nael'; // 'sere' or 'nael'
        let isAI = false;
        let myColor = 'blue';
        let selectedPieceIndex = null;
        let isRemoveMode = false;
        let previousMove = null; // برای جلوگیری از حرکت تکراری (بک)

        // افکت‌های صوتی
        const sndPlace = new Audio('https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3');
        const sndMove = new Audio('https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3');
        const sndRemove = new Audio('https://assets.mixkit.co/active_storage/sfx/2573/2573-preview.mp3');

        // ۲۴ نقطه استاندارد تخته
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

        // همسایه‌های مجاز
        const ADJACENT = {
            0:[1,7], 1:[0,2,9], 2:[1,3], 3:[2,4,11], 4:[3,5], 5:[4,6,13], 6:[5,7], 7:[0,6,15],
            8:[9,15], 9:[1,8,10,17], 10:[9,11], 11:[3,10,12,19], 12:[11,13], 13:[5,12,14,21], 14:[13,15], 15:[7,8,14,23],
            16:[17,23], 17:[9,16,18], 18:[17,19], 19:[11,18,20], 20:[19,21], 21:[13,20,22], 22:[21,23], 23:[15,16,22]
        };

        // ترکیب‌های ۳‌تایی (قطار)
        const LINES = [
            [0,1,2], [2,3,4], [4,5,6], [6,7,0],
            [8,9,10], [10,11,12], [12,13,14], [14,15,8],
            [16,17,18], [18,19,20], [20,21,22], [22,23,16],
            [1,9,17], [3,11,19], [5,13,21], [7,15,23]
        ];

        let gameState = {
            board: Array(24).fill(null),
            blueUnplaced: 9,
            redUnplaced: 9,
            turn: 'blue',
            phase: 'place', // 'place' یا 'move'
            deadBlue: 0,
            deadRed: 0
        };

        function showScreen(id) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById(id).classList.add('active');
        }

        function selectMode(mode) {
            gameMode = mode;
            const maxP = mode === 'sere' ? 3 : 9;
            gameState.blueUnplaced = maxP;
            gameState.redUnplaced = maxP;
            document.getElementById('mode-title').innerText = mode === 'sere' ? 'سبک: سه‌رگک' : 'سبک: نه‌رگک';
            showScreen('screen-room-action');
        }

        function createNewRoom() {
            isAI = false;
            currentRoom = Math.floor(1000 + Math.random() * 9000).toString();
            document.getElementById('created-code').innerText = currentRoom;
            showScreen('screen-room-created');
            socket.emit('create_or_join', { room: currentRoom, mode: gameMode });
        }

        function copyCode() {
            const code = document.getElementById('created-code').innerText;
            navigator.clipboard.writeText(code).then(() => {
                const t = document.getElementById('toast');
                t.style.display = 'block';
                setTimeout(() => t.style.display = 'none', 2000);
            });
        }

        function joinRoomByCode() {
            isAI = false;
            const code = document.getElementById('room-code-input').value.trim();
            if (code.length === 4) {
                currentRoom = code;
                socket.emit('create_or_join', { room: currentRoom });
            } else {
                alert("کد ۴ رقمی را وارد کنید!");
            }
        }

        function startAIGame() {
            isAI = true;
            myColor = 'blue';
            initBoard();
            showScreen('screen-board');
            render();
        }

        // ساخت نقاط کلیک تخته
        const boardEl = document.getElementById('board');
        const piecesLayer = document.getElementById('pieces-layer');
        POINTS.forEach(pt => {
            const div = document.createElement('div');
            div.className = 'point';
            div.style.left = `${pt.x}px`;
            div.style.top = `${pt.y}px`;
            div.onclick = () => handlePointClick(pt.id);
            boardEl.appendChild(div);
        });

        function handlePointClick(id) {
            if (!isAI && gameState.turn !== myColor) return;

            // اگر حالت حذف مهره حریف فعال باشد
            if (isRemoveMode) {
                const opponentColor = gameState.turn === 'blue' ? 'red' : 'blue';
                if (gameState.board[id] === opponentColor) {
                    removePiece(id);
                    isRemoveMode = false;
                    switchTurn();
                    syncState();
                }
                return;
            }

            // مرحله ۱: گذاردن مهره
            if (gameState.phase === 'place') {
                if (gameState.board[id] === null) {
                    const activeColor = gameState.turn;
                    if (activeColor === 'blue' && gameState.blueUnplaced > 0) {
                        gameState.board[id] = 'blue';
                        gameState.blueUnplaced--;
                        sndPlace.play();
                    } else if (activeColor === 'red' && gameState.redUnplaced > 0) {
                        gameState.board[id] = 'red';
                        gameState.redUnplaced--;
                        sndPlace.play();
                    }

                    if (checkMill(id, activeColor)) {
                        isRemoveMode = true;
                        sndRemove.play();
                        render();
                        return;
                    }

                    checkPhaseChange();
                    switchTurn();
                    syncState();
                }
            }
            // مرحله ۲: جابه‌جایی کشویی
            else if (gameState.phase === 'move') {
                const activeColor = gameState.turn;
                if (selectedPieceIndex === null) {
                    if (gameState.board[id] === activeColor) {
                        selectedPieceIndex = id;
                        render();
                    }
                } else {
                    if (id === selectedPieceIndex) {
                        selectedPieceIndex = null;
                        render();
                    } else if (gameState.board[id] === null && ADJACENT[selectedPieceIndex].includes(id)) {
                        // قانون ضد بک/بازگشت تکراری
                        if (previousMove && previousMove.from === id && previousMove.to === selectedPieceIndex) {
                            alert("حرکت تکراری مجاز نیست!");
                            return;
                        }

                        gameState.board[id] = activeColor;
                        gameState.board[selectedPieceIndex] = null;
                        previousMove = { from: selectedPieceIndex, to: id };
                        selectedPieceIndex = null;
                        sndMove.play();

                        if (checkMill(id, activeColor)) {
                            isRemoveMode = true;
                            sndRemove.play();
                            render();
                            return;
                        }

                        switchTurn();
                        syncState();
                    }
                }
            }
        }

        function removePiece(id) {
            const removedColor = gameState.board[id];
            gameState.board[id] = null;
            if (removedColor === 'blue') gameState.deadBlue++;
            if (removedColor === 'red') gameState.deadRed++;
            sndRemove.play();
        }

        function checkMill(id, color) {
            return LINES.some(line => line.includes(id) && line.every(p => gameState.board[p] === color));
        }

        function checkPhaseChange() {
            if (gameState.blueUnplaced === 0 && gameState.redUnplaced === 0) {
                gameState.phase = 'move';
            }
        }

        function switchTurn() {
            gameState.turn = gameState.turn === 'blue' ? 'red' : 'blue';
            if (isAI && gameState.turn === 'red') {
                setTimeout(makeAIMove, 600);
            }
        }

        function makeAIMove() {
            if (isRemoveMode) {
                const blueIndices = gameState.board.map((v, i) => v === 'blue' ? i : null).filter(v => v !== null);
                if (blueIndices.length > 0) {
                    removePiece(blueIndices[0]);
                    isRemoveMode = false;
                    switchTurn();
                    render();
                }
                return;
            }

            if (gameState.phase === 'place') {
                const emptyIndices = gameState.board.map((v, i) => v === null ? i : null).filter(v => v !== null);
                if (emptyIndices.length > 0 && gameState.redUnplaced > 0) {
                    const choice = emptyIndices[Math.floor(Math.random() * emptyIndices.length)];
                    gameState.board[choice] = 'red';
                    gameState.redUnplaced--;
                    sndPlace.play();

                    if (checkMill(choice, 'red')) {
                        isRemoveMode = true;
                        makeAIMove();
                        return;
                    }

                    checkPhaseChange();
                    switchTurn();
                    render();
                }
            } else {
                const redIndices = gameState.board.map((v, i) => v === 'red' ? i : null).filter(v => v !== null);
                for (let from of redIndices) {
                    const validMoves = ADJACENT[from].filter(to => gameState.board[to] === null);
                    if (validMoves.length > 0) {
                        const to = validMoves[0];
                        gameState.board[to] = 'red';
                        gameState.board[from] = null;
                        sndMove.play();

                        if (checkMill(to, 'red')) {
                            isRemoveMode = true;
                            makeAIMove();
                            return;
                        }

                        switchTurn();
                        render();
                        break;
                    }
                }
            }
        }

        function syncState() {
            render();
            if (!isAI && currentRoom) {
                socket.emit('update_game', { room: currentRoom, state: gameState });
            }
        }

        function render() {
            piecesLayer.innerHTML = '';

            // رندر مهره‌های روی تخته
            POINTS.forEach(pt => {
                const color = gameState.board[pt.id];
                if (color) {
                    const p = document.createElement('div');
                    p.className = `piece ${color} ${selectedPieceIndex === pt.id ? 'selected' : ''}`;
                    p.style.left = `${pt.x}px`;
                    p.style.top = `${pt.y}px`;
                    p.onclick = () => handlePointClick(pt.id);
                    piecesLayer.appendChild(p);
                }
            });

            // رندر مهره‌های سوخته در دایره مرکز
            for (let i = 0; i < gameState.deadBlue; i++) {
                const p = document.createElement('div');
                p.className = 'piece blue';
                p.style.left = `${155 + (i * 6)}px`;
                p.style.top = `165px`;
                piecesLayer.appendChild(p);
            }
            for (let i = 0; i < gameState.deadRed; i++) {
                const p = document.createElement('div');
                p.className = 'piece red';
                p.style.left = `${155 + (i * 6)}px`;
                p.style.top = `178px`;
                piecesLayer.appendChild(p);
            }

            // بروزرسانی کارت وضعیت بالا
            document.getElementById('p1-count').innerText = gameState.phase === 'place' ? gameState.blueUnplaced : 9 - gameState.deadBlue;
            document.getElementById('p2-count').innerText = gameState.phase === 'place' ? gameState.redUnplaced : 9 - gameState.deadRed;

            const turnEl = document.getElementById('status-turn');
            if (isRemoveMode) {
                turnEl.innerText = "⚡ قطار ساخته شد! یک مهره از حریف بردارید.";
                turnEl.style.borderColor = "#ff2a55";
            } else if (gameState.turn === myColor) {
                turnEl.innerText = gameState.phase === 'place' ? "🔴 نوبت شماست: مهره را بگذارید" : "🔴 نوبت شماست: مهره را جابه‌جا کنید";
                turnEl.style.borderColor = "#00b4d8";
            } else {
                turnEl.innerText = "⏳ نوبت حریف است...";
                turnEl.style.borderColor = "#ff4d6d";
            }
        }

        function initBoard() {
            const maxP = gameMode === 'sere' ? 3 : 9;
            gameState = {
                board: Array(24).fill(null),
                blueUnplaced: maxP,
                redUnplaced: maxP,
                turn: 'blue',
                phase: 'place',
                deadBlue: 0,
                deadRed: 0
            };
            selectedPieceIndex = null;
            isRemoveMode = false;
        }

        function restartGame() {
            initBoard();
            syncState();
        }

        // رویدادهای Socket.IO
        socket.on('set_color', (data) => {
            myColor = data.color;
        });

        socket.on('start_game_board', (data) => {
            showScreen('screen-board');
            gameState = data.state;
            render();
        });

        socket.on('sync_game', (state) => {
            gameState = state;
            render();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('create_or_join')
def handle_create_or_join(data):
    room = data['room']
    join_room(room)

    if room not in active_rooms:
        max_p = 3 if data.get('mode') == 'sere' else 9
        active_rooms[room] = {
            'players': [],
            'state': {
                'board': [None] * 24,
                'blueUnplaced': max_p,
                'redUnplaced': max_p,
                'turn': 'blue',
                'phase': 'place',
                'deadBlue': 0,
                'deadRed': 0
            }
        }

    room_data = active_rooms[room]
    if request.sid not in room_data['players'] and len(room_data['players']) < 2:
        room_data['players'].append(request.sid)

    if len(room_data['players']) == 1:
        emit('set_color', {'color': 'blue'})
    elif len(room_data['players']) == 2:
        emit('set_color', {'color': 'red'}, to=room_data['players'][1])
        # هدایت هم‌زمان هر دو بازیکن به تخته بازی بدون معطلی
        socketio.emit('start_game_board', room_data, room=room)

@socketio.on('update_game')
def handle_update_game(data):
    room = data['room']
    state = data['state']
    if room in active_rooms:
        active_rooms[room]['state'] = state
        socketio.emit('sync_game', state, room=room)

# ==========================================
# 2. TELEGRAM BOT (ربات تلگرام با دکمه‌های پاسخگو)
# ==========================================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.onrender.com")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🎮 ورود به بازی قطار (CACTUS)", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📖 راهنمای بازی", callback_data="guide"), InlineKeyboardButton("ℹ️ درباره ربات", callback_data="about")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")]
    ]
    msg = "👑 **سلام! به مرکز بازی‌های استراتژیک (CACTUS) خوش آمدید.**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "guide":
        guide_text = (
            "📖 **راهنمای جامع بازی قطار (CACTUS):**\n\n"
            "⚔️ **سه‌رگک (۳ مهره):** هر بازیکن ۳ مهره دارد. با ساخت ۳ مهره در یک خط، مهره حریف را بردارید.\n\n"
            "👑 **نه‌رگک (۹ مهره):** هر بازیکن ۹ مهره دارد. بازی شامل دو مرحله گذاردن و جابه‌جایی کشویی است."
        )
        await query.message.reply_text(guide_text, parse_mode='Markdown')

    elif query.data == "about":
        about_text = (
            "ℹ️ **درباره ربات:**\n\n"
            "پلتفرم آنلاین اجرای بازی‌های استراتژیک و فکری قطار به‌صورت زنده.\n\n"
            "👤 **سازنده و توسعه‌دهنده:** نوید\n"
            "🆔 **آیدی پشتیبانی:** @Navid_Admin"
        )
        await query.message.reply_text(about_text, parse_mode='Markdown')

    elif query.data == "settings":
        await query.message.reply_text("⚙️ **تنظیمات:**\nصداها و جلوه‌های بصری فعال هستند.")

if __name__ == '__main__':
    import threading
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.run_polling()
