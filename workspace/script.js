const canvas = document.getElementById('tetris-board');
const context = canvas.getContext('2d');
const scoreElement = document.getElementById('score');
const startButton = document.getElementById('start-button');
const gameOverElement = document.getElementById('game-over');

const COLS = 10;
const ROWS = 20;
const BLOCK_SIZE = 24; // canvas.width / COLS, canvas.height / ROWS

// Adjust canvas size based on constants
canvas.width = COLS * BLOCK_SIZE;
canvas.height = ROWS * BLOCK_SIZE;

context.scale(BLOCK_SIZE, BLOCK_SIZE);

let board = createBoard(ROWS, COLS);
let score = 0;
let gameOver = false;
let gameInterval = null;
let dropStart = Date.now();

const COLORS = [
    null,        // 0 - Empty
    '#FF0D72',   // 1 - I
    '#0DC2FF',   // 2 - J
    '#0DFF72',   // 3 - L
    '#F538FF',   // 4 - O
    '#FF8E0D',   // 5 - S
    '#FFE138',   // 6 - T
    '#3877FF'    // 7 - Z
];

const TETROMINOES = {
    'I': [
        [0, 0, 0, 0],
        [1, 1, 1, 1],
        [0, 0, 0, 0],
        [0, 0, 0, 0]
    ],
    'J': [
        [2, 0, 0],
        [2, 2, 2],
        [0, 0, 0],
    ],
    'L': [
        [0, 0, 3],
        [3, 3, 3],
        [0, 0, 0],
    ],
    'O': [
        [4, 4],
        [4, 4],
    ],
    'S': [
        [0, 5, 5],
        [5, 5, 0],
        [0, 0, 0],
    ],
    'T': [
        [0, 6, 0],
        [6, 6, 6],
        [0, 0, 0],
    ],
    'Z': [
        [7, 7, 0],
        [0, 7, 7],
        [0, 0, 0],
    ]
};

let player = {
    pos: { x: 0, y: 0 },
    matrix: null,
    score: 0
};

function createBoard(rows, cols) {
    const matrix = [];
    while (rows--) {
        matrix.push(new Array(cols).fill(0));
    }
    return matrix;
}

function drawMatrix(matrix, offset) {
    matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                context.fillStyle = COLORS[value];
                context.fillRect(x + offset.x,
                                 y + offset.y,
                                 1, 1);
                 // Add a subtle border to blocks
                 context.strokeStyle = '#333';
                 context.lineWidth = 0.05;
                 context.strokeRect(x + offset.x, y + offset.y, 1, 1);
            }
        });
    });
}

function draw() {
    // Clear canvas (draw background)
    context.fillStyle = '#000'; // Or use background color matching CSS
    context.fillRect(0, 0, canvas.width / BLOCK_SIZE, canvas.height / BLOCK_SIZE);

    drawMatrix(board, { x: 0, y: 0 }); // Draw settled pieces
    drawMatrix(player.matrix, player.pos); // Draw current player piece
}

function merge(board, player) {
    player.matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                board[y + player.pos.y][x + player.pos.x] = value;
            }
        });
    });
}

function rotate(matrix, dir) {
    for (let y = 0; y < matrix.length; ++y) {
        for (let x = 0; x < y; ++x) {
            [matrix[x][y], matrix[y][x]] = [matrix[y][x], matrix[x][y]];
        }
    }
    if (dir > 0) {
        matrix.forEach(row => row.reverse());
    } else {
        matrix.reverse();
    }
}

function playerDrop() {
    player.pos.y++;
    if (collide(board, player)) {
        player.pos.y--;
        merge(board, player);
        playerReset();
        boardSweep();
        updateScoreDisplay();
    }
    dropStart = Date.now();
}

function playerMove(offset) {
    player.pos.x += offset;
    if (collide(board, player)) {
        player.pos.x -= offset;
    }
}

function playerRotate(dir) {
    const pos = player.pos.x;
    let offset = 1;
    rotate(player.matrix, dir);
    while (collide(board, player)) {
        player.pos.x += offset;
        offset = -(offset + (offset > 0 ? 1 : -1));
        if (offset > player.matrix[0].length) {
            rotate(player.matrix, -dir); // Rotate back
            player.pos.x = pos; // Reset position
            return;
        }
    }
}

function collide(board, player) {
    const [m, o] = [player.matrix, player.pos];
    for (let y = 0; y < m.length; ++y) {
        for (let x = 0; x < m[y].length; ++x) {
            if (m[y][x] !== 0 &&
               (board[y + o.y] &&
                board[y + o.y][x + o.x]) !== 0) {
                return true;
            }
        }
    }
    return false;
}

function playerReset() {
    const tetrominoes = 'IJLOSTZ';
    const randTetromino = tetrominoes[Math.floor(Math.random() * tetrominoes.length)];
    player.matrix = TETROMINOES[randTetromino];
    player.pos.y = 0;
    player.pos.x = Math.floor(COLS / 2) - Math.floor(player.matrix[0].length / 2);

    if (collide(board, player)) {
        // Game Over
        gameOver = true;
        gameOverElement.classList.remove('hidden');
        if (gameInterval) clearInterval(gameInterval);
        startButton.disabled = false; // Allow restarting
        startButton.textContent = 'Restart Game';
    }
}

function boardSweep() {
    let rowCount = 1;
    outer: for (let y = board.length - 1; y > 0; --y) {
        for (let x = 0; x < board[y].length; ++x) {
            if (board[y][x] === 0) {
                continue outer; // Found an empty cell, row is not full
            }
        }
        // If we get here, the row is full
        const row = board.splice(y, 1)[0].fill(0);
        board.unshift(row);
        ++y; // Check the new row at this index again

        score += rowCount * 10;
        rowCount *= 2; // Points increase for multiple lines at once
    }
}

function updateScoreDisplay() {
    scoreElement.innerText = score;
}

function update(time = 0) {
    if (gameOver) return;

    const now = Date.now();
    const deltaTime = now - dropStart;

    if (deltaTime > 1000) { // Drop every second (adjust for difficulty)
        playerDrop();
    }

    draw();
}

function startGame() {
    board = createBoard(ROWS, COLS);
    score = 0;
    updateScoreDisplay();
    gameOver = false;
    gameOverElement.classList.add('hidden');
    playerReset(); // Get the first piece

    if (gameInterval) clearInterval(gameInterval);
    gameInterval = setInterval(update, 50); // ~20 FPS game loop for drawing/checking
    dropStart = Date.now();
    startButton.disabled = true;
    startButton.textContent = 'Start Game'; // Reset button text
    canvas.focus(); // Focus canvas for key events if needed, though document listener is used
}

document.addEventListener('keydown', event => {
    if (gameOver) return;

    if (event.key === 'ArrowLeft') {
        playerMove(-1);
    } else if (event.key === 'ArrowRight') {
        playerMove(1);
    } else if (event.key === 'ArrowDown') {
        playerDrop();
    } else if (event.key === 'ArrowUp' || event.key === 'q') { // Rotate counter-clockwise
        playerRotate(-1);
    } else if (event.key === 'w' || event.key === 'e') { // Rotate clockwise (common alternative)
        playerRotate(1);
    }
});

startButton.addEventListener('click', startGame);

// Initial setup message or draw empty board
draw();
console.log("Tetris initialized. Press Start Game.");
