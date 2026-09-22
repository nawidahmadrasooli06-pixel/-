import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, join_room, emit
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==========================================
# 1. SERVER & REAL-TIME WEBSOCKET CONFIG
# ==========================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'cactuc_game_master_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ذخیره وضعیت زنده اتاق‌های بازی
game_rooms = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>CACTUC - بازی قطار (نه‌رگک)</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body {
            background-color: #0b132b;
            color: #ffffff;
            font-family: system-ui, -apple-system, sans-serif;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            min-height: 100vh; padding: 10px; overflow: hidden;
        }

        .brand-title {
            font-size: 26px; font-weight: 900; letter-spacing: 4px;
            color: #48cae4; text-shadow: 0 0 12px rgba(72, 202, 228, 0.6); margin-bottom: 6px;
        }

        .screen { display: none; width: 100%; max-width: 360px; text-align: center; }
        .screen.active { display: flex; flex-direction: column; align-items: center; }

        .btn {
            width: 100%; padding: 12px; margin: 6px 0;
            background: linear-gradient(135deg, #1c2541, #3a506b);
            color: #ffffff; border: 1.5px solid #48cae4; border-radius: 12px;
            font-size: 15px; font-weight: bold; cursor: pointer; transition: all 0.2s ease;
        }
        .btn:active { transform: scale(0.97); background: #48cae4; color: #0b132b; }

        .input-box {
            width: 100%; padding: 12px; margin: 8px 0;
            border-radius: 10px; border: 1px solid #48cae4;
            background: #1c2541; color: #fff; text-align: center; font-size: 18px;
        }

        .code-box {
            background: #1c2541; border: 2px dashed #48cae4; border-radius: 12px;
            padding: 12px; font-size: 26px; letter-spacing: 6px; color: #48cae4;
            margin: 10px 0; cursor: pointer; width: 100%;
        }

        .status-badge {
            background: rgba(28, 37, 65, 0.95); border: 1.5px solid #48cae4;
            border-radius: 20px; padding: 8px 14px; font-size: 13px; font-weight: bold;
            color: #fff; margin-bottom: 8px; width: 100%; box-shadow: 0 0 10px rgba(72, 202, 228, 0.2);
        }

        .players-panel {
            display: flex; justify-content: space-between; align-items: center;
            width: 100%; background: #1c2541; border-radius: 12px;
            padding: 8px 12px; margin-bottom: 10px; border: 1px solid #3a506b;
        }

        .unplaced-container { display: flex; gap: 4px; align-items: center; margin-top: 4px; }
        .dot-mini {
            width: 14px; height: 14px; border-radius: 50%; display: flex;
            align-items: center; justify-content: center; font-size: 8px; font-weight: bold; color: #fff;
        }
        .dot-mini.blue { background: #00b4d8; box-shadow: 0 0 4px #00b4d8; }
        .dot-mini.red { background: #ff4d6d; box-shadow: 0 0 4px #ff4d6d; }
        .dot-mini.active-turn { animation: pulse 1s infinite alternate; }

        @keyframes pulse {
            0% { transform: scale(1); opacity: 0.6; }
            100% { transform: scale(1.25); opacity: 1; filter: brightness(1.3); }
        }

        /* تخته بزرگ و استاندارد */
        .board-container {
            position: relative; width: 340px; height: 340px;
            background: #1c2541; border-radius: 18px; border: 2px solid #3a506b;
            box-shadow: 0 10px 30px rgba(0,0,0,0.7);
        }
        .board-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
        .board-svg line, .board-svg rect { stroke: #3a506b; stroke-width: 2.5; fill: none; }
        
        .center-circle {
            stroke: #48cae4; stroke-width: 1.5; stroke-dasharray: 4 3; fill: rgba(72, 202, 228, 0.05);
        }

        .point {
            position: absolute; width: 24px; height: 24px; border-radius: 50%;
            background: rgba(58, 80, 107, 0.4); border: 1.5px solid #48cae4;
            transform: translate(-50%, -50%); z-index: 2; cursor: pointer;
        }

        .piece {
            position: absolute; width: 22px; height: 22px; border-radius: 50%;
            transform: translate(-50%, -50%); z-index: 3;
            transition: all 0.5s cubic-bezier(0.25, 1, 0.5, 1); cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            font-size: 8px; font-weight: bold; color: #fff;
        }
        .piece.blue { background: #00b4d8; box-shadow: 0 0 8px #00b4d8; }
        .piece.red { background: #ff4d6d; box-shadow: 0 0 8px #ff4d6d; }
        
        .piece.selected {
            border: 2px solid #ffea00; box-shadow: 0 0 14px #ffea00;
            transform: translate(-50%, -50%) scale(1.3); z-index: 4;
        }
        .piece.mill { filter: brightness(0.4); border: 1.5px solid #ffea00; }
        .piece.dead {
            width: 14px; height: 14px; z-index: 2; opacity: 0.85;
            transition: all 0.8s ease-in-out;
        }

        .toast {
            position: fixed; bottom: 20px; background: #48cae4; color: #0b132b;
            padding: 8px 16px; border-radius: 8px; font-weight: bold; font-size: 13px;
            display: none; z-index: 99; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>

    <div class="brand-title">CACTUC</div>
    <div id="toast" class="toast">پیام سیستم</div>

    <!-- ۱. فرم دریافت نام کاربر -->
    <div id="screen-name" class="screen active">
        <h3 style="margin-bottom: 12px; color: #48cae4;">نام خود را وارد کنید:</h3>
        <input type="text" id="player-name-input" class="input-box" placeholder="مثال: نوید">
        <button class="btn" onclick="savePlayerName()">ورود به بازی</button>
    </div>

    <!-- ۲. منوی اصلی -->
    <div id="screen-main" class="screen">
        <h3 id="welcome-msg" style="margin-bottom: 12px; color: #fff;"></h3>
        <button id="rejoin-btn" class="btn" style="display:none; background: #2a9d8f; border-color: #2a9d8f;" onclick="rejoinGame()">▶️ ادامه بازی قبلی</button>
        <button class="btn" onclick="showScreen('screen-room-action')">👥 بازی آنلاین با دوست</button>
        <button class="btn" onclick="startAIGame()">🤖 بازی با کامپیوتر (آفلاین)</button>
    </div>

    <!-- ۳. ساخت / ورود به اتاق -->
    <div id="screen-room-action" class="screen">
        <button class="btn" onclick="createNewRoom()">➕ ساخت اتاق جدید</button>
        <div style="margin: 10px 0; width: 100%;">
            <input type="number" id="room-code-input" class="input-box" placeholder="کد ۴ رقمی">
            <button class="btn" onclick="joinRoomByCode()">🔑 ورود به اتاق</button>
        </div>
        <button class="btn" style="border-color:#ff4d6d; color:#ff4d6d;" onclick="showScreen('screen-main')">🔙 بازگشت</button>
    </div>

    <!-- ۴. نمایش کد اتاق -->
    <div id="screen-room-created" class="screen">
        <h3 style="color: #48cae4;">کد اتاق شما:</h3>
        <div id="created-code" class="code-box" onclick="copyCode()">----</div>
        <p style="font-size: 12px; color: #aaa;">کد را برای دوستتان بفرستید. با ورود او بازی شروع می‌شود.</p>
    </div>

    <!-- ۵. تخته اصلی بازی -->
    <div id="screen-board" class="screen">
        <div class="status-badge" id="status-turn">نوبت شماست!</div>

        <div class="players-panel">
            <div>
                <span id="p1-name" style="color:#00b4d8; font-weight:bold;">بازیکن ۱</span>
                <div class="unplaced-container" id="p1-dots"></div>
            </div>
            <div>
                <span id="p2-name" style="color:#ff4d6d; font-weight:bold;">بازیکن ۲</span>
                <div class="unplaced-container" id="p2-dots"></div>
            </div>
        </div>

        <div class="board-container" id="board">
            <svg class="board-svg" viewBox="0 0 340 340">
                <rect x="20" y="20" width="300" height="300" />
                <rect x="75" y="75" width="190" height="190" />
                <rect x="130" y="130" width="80" height="80" />
                <line x1="170" y1="20" x2="170" y2="130" />
                <line x1="170" y1="210" x2="170" y2="320" />
                <line x1="20" y1="170" x2="130" y2="170" />
                <line x1="210" y1="170" x2="320" y2="170" />
                <circle cx="170" cy="170" r="35" class="center-circle" />
            </svg>
            <div id="pieces-layer"></div>
        </div>

        <button class="btn" style="margin-top: 12px; background: #ff4d6d; border: none;" onclick="restartGame()">شروع مجدد / پاک کردن این تخته</button>
    </div>

    <script>
        const socket = io();
        const tg = window.Telegram?.WebApp;
        if (tg) tg.expand();

        let playerName = localStorage.getItem('cactuc_player_name') || '';
        let currentRoom = localStorage.getItem('cactuc_last_room') || null;
        let isAI = false;
        let myColor = 'blue';
        let selectedIndex = null;
        let isRemoveMode = false;
        let activeMillPoints = [];

        const sndPlace = new Audio('https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3');
        const sndMove = new Audio('https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3');
        const sndRemove = new Audio('https://assets.mixkit.co/active_storage/sfx/2573/2573-preview.mp3');

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

        const ADJACENT = {
            0:[1,7], 1:[0,2,9], 2:[1,3], 3:[2,4,11], 4:[3,5], 5:[4,6,13], 6:[5,7], 7:[0,6,15],
            8:[9,15], 9:[1,8,10,17], 10:[9,11], 11:[3,10,12,19], 12:[11,13], 13:[5,12,14,21], 14:[13,15], 15:[7,8,14,23],
            16:[17,23], 17:[9,16,18], 18:[17,19], 19:[11,18,20], 20:[19,21], 21:[13,20,22], 22:[21,23], 23:[15,16,22]
        };

        const LINES = [
            [0,1,2], [2,3,4], [4,5,6], [6,7,0],
            [8,9,10], [10,11,12], [12,13,14], [14,15,8],
            [16,17,18], [18,19,20], [20,21,22], [22,23,16],
            [1,9,17], [3,11,19], [5,13,21], [7,15,23]
        ];

        let gameState = {
            board: Array(24).fill(null),
            blueUnplaced: 9, redUnplaced: 9,
            turn: 'blue', phase: 'place',
            deadBlue: 0, deadRed: 0,
            p1Name: 'بازیکن ۱', p2Name: 'بازیکن ۲',
            lastMills: { blue: [], red: [] },
            isFinished: false
        };

        window.onload = () => {
            if (playerName) {
                document.getElementById('welcome-msg').innerText = `سلام ${playerName} عزیز 👋`;
                showScreen('screen-main');
                checkRejoinStatus();
            } else {
                showScreen('screen-name');
            }
        };

        function checkRejoinStatus() {
            const isFinished = localStorage.getItem('cactuc_game_finished') === 'true';
            if (currentRoom && !isFinished) {
                document.getElementById('rejoin-btn').style.display = 'block';
            } else {
                document.getElementById('rejoin-btn').style.display = 'none';
            }
        }

        function savePlayerName() {
            const val = document.getElementById('player-name-input').value.trim();
            if (val) {
                playerName = val;
                localStorage.setItem('cactuc_player_name', playerName);
                document.getElementById('welcome-msg').innerText = `سلام ${playerName} عزیز 👋`;
                showScreen('screen-main');
            }
        }

        function showScreen(id) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById(id).classList.add('active');
        }

        function createNewRoom() {
            isAI = false;
            currentRoom = Math.floor(1000 + Math.random() * 9000).toString();
            localStorage.setItem('cactuc_last_room', currentRoom);
            localStorage.setItem('cactuc_game_finished', 'false');
            document.getElementById('created-code').innerText = currentRoom;
            showScreen('screen-room-created');
            socket.emit('join_game', { room: currentRoom, playerName });
        }

        function joinRoomByCode() {
            isAI = false;
            const code = document.getElementById('room-code-input').value.trim();
            if (code.length === 4) {
                currentRoom = code;
                localStorage.setItem('cactuc_last_room', currentRoom);
                localStorage.setItem('cactuc_game_finished', 'false');
                socket.emit('join_game', { room: currentRoom, playerName });
            }
        }

        function rejoinGame() {
            if (currentRoom) {
                socket.emit('join_game', { room: currentRoom, playerName });
            }
        }

        function startAIGame() {
            isAI = true; myColor = 'blue';
            localStorage.setItem('cactuc_game_finished', 'false');
            gameState = {
                board: Array(24).fill(null),
                blueUnplaced: 9, redUnplaced: 9,
                turn: 'blue', phase: 'place',
                deadBlue: 0, deadRed: 0,
                p1Name: playerName, p2Name: 'کامپیوتر (سخت)',
                lastMills: { blue: [], red: [] },
                isFinished: false
            };
            showScreen('screen-board');
            render();
        }

        const boardEl = document.getElementById('board');
        const piecesLayer = document.getElementById('pieces-layer');
        POINTS.forEach(pt => {
            const div = document.createElement('div');
            div.className = 'point';
            div.style.left = `${pt.x}px`; div.style.top = `${pt.y}px`;
            div.onclick = () => handlePointClick(pt.id);
            boardEl.appendChild(div);
        });

        function handlePointClick(id) {
            if (!isAI && gameState.turn !== myColor) return;

            if (isRemoveMode) {
                const opp = gameState.turn === 'blue' ? 'red' : 'blue';
                if (gameState.board[id] === opp) {
                    removePiece(id);
                    isRemoveMode = false;
                    activeMillPoints = [];
                    switchTurn();
                    sync();
                }
                return;
            }

            if (gameState.phase === 'place') {
                if (gameState.board[id] === null) {
                    const c = gameState.turn;
                    if (c === 'blue' && gameState.blueUnplaced > 0) { gameState.board[id] = 'blue'; gameState.blueUnplaced--; }
                    else if (c === 'red' && gameState.redUnplaced > 0) { gameState.board[id] = 'red'; gameState.redUnplaced--; }
                    sndPlace.play();

                    checkPhase();
                    switchTurn();
                    sync();
                }
            }
            else if (gameState.phase === 'move') {
                const c = gameState.turn;
                if (selectedIndex === null) {
                    if (gameState.board[id] === c) {
                        selectedIndex = id;
                        render();
                    }
                } else {
                    if (id === selectedIndex) {
                        selectedIndex = null;
                        render();
                    } else if (gameState.board[id] === null && ADJACENT[selectedIndex].includes(id)) {
                        gameState.board[id] = c;
                        gameState.board[selectedIndex] = null;
                        const fromPos = selectedIndex;
                        selectedIndex = null;
                        sndMove.play();

                        const mill = checkNewMill(id, c, fromPos);
                        if (mill) {
                            isRemoveMode = true;
                            activeMillPoints = mill;
                            sndRemove.play();
                            render();
                            return;
                        }

                        switchTurn();
                        sync();
                    }
                }
            }
        }

        function checkNewMill(id, color, fromPos) {
            for (let line of LINES) {
                if (line.includes(id) && line.every(p => gameState.board[p] === color)) {
                    const millKey = line.sort().join('-');
                    const prevMills = gameState.lastMills[color] || [];
                    if (prevMills.includes(millKey) && line.includes(fromPos)) {
                        showToast("❌ راه برگشت تکراری! باید قطار جدید بسازید.");
                        return null;
                    }
                    gameState.lastMills[color].push(millKey);
                    return line;
                }
            }
            return null;
        }

        function removePiece(id) {
            const c = gameState.board[id];
            gameState.board[id] = null;
            if (c === 'blue') gameState.deadBlue++;
            if (c === 'red') gameState.deadRed++;
            sndRemove.play();

            if (gameState.deadBlue >= 7 || gameState.deadRed >= 7) {
                gameState.isFinished = true;
                localStorage.setItem('cactuc_game_finished', 'true');
                showToast("🎉 بازی به پایان رسید!");
            }
        }

        function checkPhase() {
            if (gameState.blueUnplaced === 0 && gameState.redUnplaced === 0) {
                gameState.phase = 'move';
            }
        }

        function switchTurn() {
            gameState.turn = gameState.turn === 'blue' ? 'red' : 'blue';
            if (isAI && gameState.turn === 'red' && !gameState.isFinished) {
                setTimeout(makeHardAIMove, 700);
            }
        }

        function makeHardAIMove() {
            if (isRemoveMode) {
                const oppIdxs = gameState.board.map((v, i) => v === 'blue' ? i : null).filter(v => v !== null);
                if (oppIdxs.length) { removePiece(oppIdxs[0]); isRemoveMode = false; activeMillPoints = []; switchTurn(); render(); }
                return;
            }

            if (gameState.phase === 'place') {
                const empty = gameState.board.map((v, i) => v === null ? i : null).filter(v => v !== null);
                if (empty.length) {
                    const pick = empty[Math.floor(Math.random() * empty.length)];
                    gameState.board[pick] = 'red';
                    gameState.redUnplaced--;
                    sndPlace.play();
                    checkPhase(); switchTurn(); render();
                }
            } else {
                const redIdxs = gameState.board.map((v, i) => v === 'red' ? i : null).filter(v => v !== null);
                for (let from of redIdxs) {
                    const valid = ADJACENT[from].filter(to => gameState.board[to] === null);
                    if (valid.length) {
                        const to = valid[0];
                        gameState.board[to] = 'red'; gameState.board[from] = null;
                        sndMove.play();
                        const mill = checkNewMill(to, 'red', from);
                        if (mill) { isRemoveMode = true; activeMillPoints = mill; makeHardAIMove(); return; }
                        switchTurn(); render(); break;
                    }
                }
            }
        }

        function sync() {
            render();
            if (!isAI && currentRoom) {
                socket.emit('update_board', { room: currentRoom, state: gameState });
            }
        }

        function render() {
            piecesLayer.innerHTML = '';

            POINTS.forEach(pt => {
                const color = gameState.board[pt.id];
                if (color) {
                    const p = document.createElement('div');
                    const isSelected = selectedIndex === pt.id;
                    const isMill = activeMillPoints.includes(pt.id);
                    const initial = color === 'blue' ? gameState.p1Name[0] : gameState.p2Name[0];
                    p.className = `piece ${color} ${isSelected ? 'selected' : ''} ${isMill ? 'mill' : ''}`;
                    p.style.left = `${pt.x}px`; p.style.top = `${pt.y}px`;
                    p.innerText = initial || '';
                    p.onclick = () => handlePointClick(pt.id);
                    piecesLayer.appendChild(p);
                }
            });

            // مهره‌های سوخته با انیمیشن ملایم در دایره وسط
            for (let i = 0; i < gameState.deadBlue; i++) {
                const p = document.createElement('div');
                p.className = 'piece blue dead';
                p.style.left = `${155 + (i * 4)}px`; p.style.top = `162px`;
                piecesLayer.appendChild(p);
            }
            for (let i = 0; i < gameState.deadRed; i++) {
                const p = document.createElement('div');
                p.className = 'piece red dead';
                p.style.left = `${155 + (i * 4)}px`; p.style.top = `176px`;
                piecesLayer.appendChild(p);
            }

            // مهره‌های نچیده شده بالای صفحه
            const p1Dots = document.getElementById('p1-dots');
            const p2Dots = document.getElementById('p2-dots');
            p1Dots.innerHTML = ''; p2Dots.innerHTML = '';
            const p1Init = gameState.p1Name[0] || '۱';
            const p2Init = gameState.p2Name[0] || '۲';

            for (let i = 0; i < gameState.blueUnplaced; i++) {
                const active = gameState.turn === 'blue' ? 'active-turn' : '';
                p1Dots.innerHTML += `<div class="dot-mini blue ${active}">${p1Init}</div>`;
            }
            for (let i = 0; i < gameState.redUnplaced; i++) {
                const active = gameState.turn === 'red' ? 'active-turn' : '';
                p2Dots.innerHTML += `<div class="dot-mini red ${active}">${p2Init}</div>`;
            }

            document.getElementById('p1-name').innerText = gameState.p1Name || 'بازیکن ۱';
            document.getElementById('p2-name').innerText = gameState.p2Name || 'بازیکن ۲';

            const turnEl = document.getElementById('status-turn');
            if (isRemoveMode) {
                turnEl.innerText = "🔥 قطار ساخته شد! یکی از مهره‌های حریف را بزنید.";
                turnEl.style.borderColor = "#ff2a55";
            } else if (gameState.turn === myColor) {
                turnEl.innerText = `🔴 نوبت شماست (${gameState.p1Name})!`;
                turnEl.style.borderColor = "#00b4d8";
            } else {
                turnEl.innerText = `⏳ نوبت حریف است (${gameState.p2Name})...`;
                turnEl.style.borderColor = "#ff4d6d";
            }
        }

        function restartGame() {
            localStorage.setItem('cactuc_game_finished', 'true');
            gameState.board = Array(24).fill(null);
            gameState.blueUnplaced = 9; gameState.redUnplaced = 9;
            gameState.deadBlue = 0; gameState.deadRed = 0;
            gameState.phase = 'place'; gameState.turn = 'blue';
            gameState.lastMills = { blue: [], red: [] };
            gameState.isFinished = false;
            sync();
            showScreen('screen-main');
            checkRejoinStatus();
        }

        function copyCode() {
            navigator.clipboard.writeText(currentRoom).then(() => showToast("کد اتاق کپی شد!"));
        }

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg; t.style.display = 'block';
            setTimeout(() => t.style.display = 'none', 2500);
        }

        socket.on('player_assigned', (data) => { myColor = data.color; });
        socket.on('start_game', (data) => { showScreen('screen-board'); gameState = data.state; render(); });
        socket.on('board_updated', (state) => { gameState = state; render(); });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('join_game')
def handle_join_game(data):
    room = data['room']
    p_name = data.get('playerName', 'بازیکن')
    join_room(room)

    if room not in game_rooms:
        game_rooms[room] = {
            'players': [],
            'state': {
                'board': [None] * 24,
                'blueUnplaced': 9, 'redUnplaced': 9,
                'turn': 'blue', 'phase': 'place',
                'deadBlue': 0, 'deadRed': 0,
                'p1Name': p_name, 'p2Name': 'در حال انتظار...',
                'lastMills': {'blue': [], 'red': []},
                'isFinished': False
            }
        }

    r_data = game_rooms[room]
    if request.sid not in r_data['players']:
        if len(r_data['players']) < 2:
            r_data['players'].append(request.sid)

    if r_data['players'][0] == request.sid:
        r_data['state']['p1Name'] = p_name
        emit('player_assigned', {'color': 'blue'})
    else:
        r_data['state']['p2Name'] = p_name
        emit('player_assigned', {'color': 'red'})

    if len(r_data['players']) == 2:
        socketio.emit('start_game', r_data, room=room)
    else:
        emit('board_updated', r_data['state'])

@socketio.on('update_board')
def handle_update_board(data):
    room = data['room']
    state = data['state']
    if room in game_rooms:
        game_rooms[room]['state'] = state
        socketio.emit('board_updated', state, room=room)

# ==========================================
# 2. TELEGRAM BOT
# ==========================================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.onrender.com")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🎮 ورود به بازی قطار", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📖 راهنمای بازی", callback_data="guide"), InlineKeyboardButton("ℹ️ درباره ربات", callback_data="about")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")]
    ]
    msg = "👑 **به ربات بازی قطار (CACTUC) خوش آمدید.**\nبرای شروع بازی روی دکمه زیر کلیک کنید:"
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "guide":
        guide_text = (
            "📖 **راهنمای بازی قطار (نه‌رگک):**\n\n"
            "۱. هر بازیکن ۹ مهره در اختیار دارد.\n"
            "۲. در مرحله چیدمان قطار ساخته نمی‌شود.\n"
            "۳. پس از چیدن تمام مهره‌ها، با تشکیل قطار می‌توانید مهره حریف را بسوزانید.\n"
            "۴. ساخت قطارهای تکراری با رفت‌وبرگشت ممنوع است."
        )
        await query.message.reply_text(guide_text, parse_mode='Markdown')

    elif query.data == "about":
        await query.message.reply_text("ℹ️ **درباره ربات:**\nپلتفرم آنلاین و زنده بازی قطار CACTUC.\nسازنده: نوید", parse_mode='Markdown')

    elif query.data == "settings":
        await query.message.reply_text("⚙️ **تنظیمات:** کلیه سیستم‌های صوتی و آنلاین فعال می‌باشند.")

if __name__ == '__main__':
    import threading
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.run_polling()
