const canvas = document.getElementById('gameCanvas');
const context = canvas.getContext('2d');
const scoreElement = document.getElementById('score');

const COLS = 10; // Počet stĺpcov
const ROWS = 20; // Počet riadkov
const BLOCK_SIZE = 30; // Veľkosť bloku v pixeloch

// Nastavenie veľkosti canvasu
canvas.width = COLS * BLOCK_SIZE;
canvas.height = ROWS * BLOCK_SIZE;

// Farby - index zodpovedá hodnote v mriežke
const COLORS = [
    null,       // 0 - Prázdne
    'cyan',     // 1 - I
    'blue',     // 2 - J
    'orange',   // 3 - L
    'yellow',   // 4 - O
    'lime',     // 5 - S
    'purple',   // 6 - T
    'red'       // 7 - Z
];

// Tvary Tetromino (definície tvarov a ich rotácií)
// Každý tvar je pole rotácií, každá rotácia je 2D pole (maticu)
const TETROMINOES = {
    'I': {
        colorIndex: 1,
        shape: [
            [0, 0, 0, 0],
            [1, 1, 1, 1],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ]
    },
    'J': {
        colorIndex: 2,
        shape: [
            [1, 0, 0],
            [1, 1, 1],
            [0, 0, 0]
        ]
    },
    'L': {
        colorIndex: 3,
        shape: [
            [0, 0, 1],
            [1, 1, 1],
            [0, 0, 0]
        ]
    },
    'O': {
        colorIndex: 4,
        shape: [
            [1, 1],
            [1, 1]
        ]
    },
    'S': {
        colorIndex: 5,
        shape: [
            [0, 1, 1],
            [1, 1, 0],
            [0, 0, 0]
        ]
    },
    'T': {
        colorIndex: 6,
        shape: [
            [0, 1, 0],
            [1, 1, 1],
            [0, 0, 0]
        ]
    },
    'Z': {
        colorIndex: 7,
        shape: [
            [1, 1, 0],
            [0, 1, 1],
            [0, 0, 0]
        ]
    }
};

let board = []; // Herná plocha (mriežka)
let score = 0;
let currentPiece; // Aktuálny padajúci dielik (objekt)
let currentX, currentY; // Pozícia ľavého horného rohu matice dielika
let gameOver = false;
let gamePaused = false;
let dropStart = Date.now();
let dropInterval = 1000; // ms - rýchlosť pádu

// Inicializácia herného poľa (všetko prázdne - 0)
function createBoard() {
    return Array.from({ length: ROWS }, () => Array(COLS).fill(0));
}

// Vykreslenie herného poľa
function drawBoard() {
    board.forEach((row, y) => {
        row.forEach((value, x) => {
            drawBlock(x, y, COLORS[value]);
        });
    });
}

// Vykreslenie jedného bloku
function drawBlock(x, y, color) {
    if (color) {
        context.fillStyle = color;
        context.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
        context.strokeStyle = '#333'; // Tmavší okraj
        context.strokeRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
    } else {
        // Vykreslenie pozadia pre prázdne bunky (mriežka)
        context.fillStyle = '#e0e0e0'; // Farba pozadia canvasu
        context.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
        context.strokeStyle = '#d0d0d0'; // Svetlejšia mriežka
        context.strokeRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
    }
}

// Vykreslenie aktuálneho dielika
function drawPiece() {
    if (!currentPiece) return;
    const shape = currentPiece.shape;
    const color = COLORS[currentPiece.colorIndex];
    shape.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value) {
                drawBlock(currentX + x, currentY + y, color);
            }
        });
    });
}

// Generovanie náhodného dielika
function spawnPiece() {
    const pieceNames = Object.keys(TETROMINOES);
    const randomPieceName = pieceNames[Math.floor(Math.random() * pieceNames.length)];
    const newPieceData = TETROMINOES[randomPieceName];

    currentPiece = { // Vytvoríme kópiu, aby sme nemenili originál
        shape: newPieceData.shape.map(row => [...row]), // Hlboká kópia matice
        colorIndex: newPieceData.colorIndex
    };

    // Štartovacia pozícia (hore, v strede)
    currentX = Math.floor(COLS / 2) - Math.floor(currentPiece.shape[0].length / 2);
    currentY = 0;

    // Kontrola, či je možné dielik umiestniť (Game Over?)
    if (collision(0, 0, currentPiece.shape)) {
        gameOver = true;
        // alert('Game Over! Skóre: ' + score);
        console.log('Game Over! Skóre: ' + score);
    }
}

// Rotácia dielika
function rotatePiece() {
    if (!currentPiece) return;
    const shape = currentPiece.shape;
    const N = shape.length;
    const newShape = Array.from({ length: N }, () => Array(N).fill(0));

    // Transponovanie a otočenie riadkov
    for (let y = 0; y < N; y++) {
        for (let x = 0; x < N; x++) {
            newShape[x][N - 1 - y] = shape[y][x];
        }
    }

    // Skontroluj kolízie po rotácii (aj prípadné posunutie od steny)
    let kick = 0;
    if (collision(0, 0, newShape)) {
        kick = currentX + N / 2 < COLS / 2 ? 1 : -1; // Posuň od steny
         if (collision(kick, 0, newShape)) {
             // Skús posunúť ešte ďalej (napr. pre I kus)
             kick = kick * 2;
             if (collision(kick, 0, newShape)) {
                return; // Rotácia nie je možná
             }
         }
    }
    // Ak rotácia (s prípadným posunom) je možná
    currentX += kick;
    currentPiece.shape = newShape;
}

// Pohyb dielika
function movePiece(dx, dy) {
    if (!currentPiece || gameOver || gamePaused) return false;
    if (!collision(dx, dy, currentPiece.shape)) {
        currentX += dx;
        currentY += dy;
        return true; // Pohyb úspešný
    } else if (dy === 1) {
        // Kolízia pri pohybe dole -> uzamkni dielik
        lockPiece();
        spawnPiece(); // Vygeneruj nový
        return false; // Pohyb neúspešný (dielik bol uzamknutý)
    }
    return false; // Pohyb neúspešný (kolízia do strany alebo nahor)
}

// Kontrola kolízie
function collision(dx, dy, shape) {
    if (!shape) return true; // Ak nie je tvar, je kolízia
    for (let y = 0; y < shape.length; y++) {
        for (let x = 0; x < shape[0].length; x++) {
            // Skontroluj len bloky, ktoré sú súčasťou tvaru
            if (shape[y][x]) {
                let newX = currentX + x + dx;
                let newY = currentY + y + dy;

                // 1. Kolízia so stenami
                if (newX < 0 || newX >= COLS || newY >= ROWS) {
                    return true;
                }
                // 2. Kolízia s podlahou (pri pohybe nadol, inak by newY >= ROWS bolo odchytené vyššie)
                 if (newY < 0) { // Pre prípad rotácie na vrchu
                     continue;
                 }
                // 3. Kolízia s inými uzamknutými dielikmi na ploche
                if (board[newY] && board[newY][newX] !== 0) {
                    return true;
                }
            }
        }
    }
    return false; // Žiadna kolízia
}

// Uzamknutie dielika na mieste
function lockPiece() {
    if (!currentPiece) return;
    const shape = currentPiece.shape;
    shape.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value) {
                let boardX = currentX + x;
                let boardY = currentY + y;
                // Zabezpečenie proti zápisu mimo poľa (aj keď by kolízia mala zabrániť)
                if (boardY >= 0 && boardY < ROWS && boardX >= 0 && boardX < COLS) {
                    board[boardY][boardX] = currentPiece.colorIndex;
                }
            }
        });
    });
    currentPiece = null; // Aktuálny dielik už neexistuje
    clearLines(); // Skontroluj a vyčisti plné riadky
}

// Čistenie plných riadkov
function clearLines() {
    let linesCleared = 0;
    for (let y = ROWS - 1; y >= 0; y--) {
        if (board[y].every(cell => cell !== 0)) {
            // Riadok je plný
            linesCleared++;
            // Posuň všetky riadky nad ním dole
            for (let k = y; k > 0; k--) {
                board[k] = board[k - 1];
            }
            // Najvrchnejší riadok bude nový prázdny
            board[0] = Array(COLS).fill(0);
            // Keďže sme riadok odstránili, musíme skontrolovať ten istý index znova
            y++;
        }
    }
    // Aktualizácia skóre
    if (linesCleared > 0) {
        // Jednoduchý systém skórovania
        score += linesCleared * 100 * linesCleared; // Bonus za viac riadkov naraz
        scoreElement.textContent = score;
        // Zvýšenie rýchlosti (voliteľné)
        // dropInterval = Math.max(200, dropInterval - linesCleared * 10); // Rýchlejšie
    }
}

// Herná slučka
function gameLoop(timestamp) {
    if (gameOver) {
        context.fillStyle = 'rgba(0, 0, 0, 0.75)';
        context.fillRect(0, canvas.height / 2 - 30, canvas.width, 60);
        context.font = '24px Arial';
        context.fillStyle = 'white';
        context.textAlign = 'center';
        context.fillText('Game Over! Skóre: ' + score, canvas.width / 2, canvas.height / 2);
        context.font = '16px Arial';
        context.fillText('Stlač Enter pre novú hru', canvas.width / 2, canvas.height / 2 + 25);
        return; // Zastav slučku
    }
    if (gamePaused) {
        context.fillStyle = 'rgba(0, 0, 0, 0.75)';
        context.fillRect(0, canvas.height / 2 - 30, canvas.width, 60);
        context.font = '24px Arial';
        context.fillStyle = 'white';
        context.textAlign = 'center';
        context.fillText('Pauza (P)', canvas.width / 2, canvas.height / 2);
         requestAnimationFrame(gameLoop);
        return; // Pokračuj v requestovaní, ale nevykonávaj logiku
    }

    let now = Date.now();
    let delta = now - dropStart;

    if (delta > dropInterval) {
        movePiece(0, 1); // Posuň dielik dole
        dropStart = Date.now(); // Resetuj časovač pádu
    }

    // Vyčisti canvas
    // context.clearRect(0, 0, canvas.width, canvas.height); // Toto prekreslí mriežku na bielo, lepšie je prefarbiť
    context.fillStyle = '#e0e0e0'; // Farba pozadia
    context.fillRect(0, 0, canvas.width, canvas.height);

    // Vykresli herné pole (uzamknuté dieliky a mriežku)
    drawBoard();

    // Vykresli aktuálny padajúci dielik
    drawPiece();

    // Požiadaj o ďalší frame
    requestAnimationFrame(gameLoop);
}

// Ovládanie klávesnicou
document.addEventListener('keydown', (event) => {
    if (gameOver) {
        if (event.key === 'Enter') {
            resetGame();
            requestAnimationFrame(gameLoop);
        }
        return;
    }

    if (event.key === 'p' || event.key === 'P') {
        gamePaused = !gamePaused;
        if (!gamePaused) {
            dropStart = Date.now(); // Aby po pauze hneď nespadol
             requestAnimationFrame(gameLoop); // Reštartuj slučku, ak bola pozastavená
        }
        return;
    }

     if (gamePaused) return; // V pauze nereaguj na iné klávesy

    switch (event.key) {
        case 'ArrowLeft':
            movePiece(-1, 0);
            break;
        case 'ArrowRight':
            movePiece(1, 0);
            break;
        case 'ArrowDown':
            if (movePiece(0, 1)) { // Ak bol pohyb úspešný
               // Zrýchlený pád - resetuj časovač, aby hneď skúsil ďalší krok
               dropStart = Date.now();
               score += 1; // Malý bonus za manuálny pád
               scoreElement.textContent = score;
            }
            break;
        case 'ArrowUp': // Rotácia (napr. šípkou hore)
        case ' ': // Rotácia (medzerníkom)
            rotatePiece();
            break;
        // Môžeme pridať klávesu pre okamžitý pád (hard drop)
        // case ' ': // Ak ArrowUp je rotácia
        //    while(movePiece(0, 1)) { score += 2; } // Opakuj pád, kým nenarazí
        //    scoreElement.textContent = score;
        //    break;
    }
});

// Reset hry
function resetGame() {
    board = createBoard();
    score = 0;
    scoreElement.textContent = score;
    gameOver = false;
    gamePaused = false;
    dropInterval = 1000;
    spawnPiece(); // Vygeneruj prvý dielik
    dropStart = Date.now();
}

// Štart hry
resetGame();
requestAnimationFrame(gameLoop); // Spustí hernú slučku

console.log("Tetris Základ inicializovaný.");