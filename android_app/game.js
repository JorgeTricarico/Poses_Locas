// =====================================================================
// POSES LOCAS - CLIENTE WEB / ANDROID PWA / SMART TV (PARIDAD TOTAL)
// =====================================================================

const videoElement = document.getElementById('input-video');
const canvasElement = document.getElementById('output-canvas');
const canvasCtx = canvasElement.getContext('2d');
const scoreEl = document.getElementById('score');
const timerEl = document.getElementById('timer');
const comboEl = document.getElementById('combo-pill');
const feverBar = document.getElementById('fever-bar');
const instructionEl = document.getElementById('pose-instruction');
const progressBar = document.getElementById('progress-bar');
const queueStrip = document.getElementById('queue-strip');
const startScreen = document.getElementById('start-screen');
const gameScreen = document.getElementById('game-screen');

function logError(msg) {
    const p = document.createElement('p');
    p.style.color = '#ff477e';
    p.style.backgroundColor = 'rgba(0,0,0,0.7)';
    p.style.padding = '8px';
    p.style.borderRadius = '8px';
    p.innerText = msg;
    document.getElementById('start-screen').appendChild(p);
}

// Audio
const sndSuccess = new Audio('success_new.wav');
const sndFail = new Audio('fail.wav');

let isPlaying = false;
let isPaused = false;
let score = 0;
let streak = 0;
let feverMeter = 0.0;
let isFever = false;
let feverEndTime = 0;

let currentPose = null;
let poseQueue = [];
let coreoIndex = 0;
let lastLoopTimestamp = performance.now();
let timeRemaining = 0.0;
let holdProgress = 0.0;

let selectedSong = 'macarena.wav';
let difficultyTime = 6.0;
let gameMode = 'arcade';
let bgMusic = new Audio();
bgMusic.loop = true;
let cameraRef = null;

// LANDMARKS MediaPipe
const NOSE = 0;
const L_EAR = 7;
const R_EAR = 8;
const L_SHOULDER = 11;
const R_SHOULDER = 12;
const L_ELBOW = 13;
const R_ELBOW = 14;
const L_WRIST = 15;
const R_WRIST = 16;
const L_HIP = 23;
const R_HIP = 24;

// Normalización y helper anatómico
function getBodyUnit(lm) {
    const dx = lm[L_SHOULDER].x - lm[R_SHOULDER].x;
    const dy = lm[L_SHOULDER].y - lm[R_SHOULDER].y;
    return Math.max(0.10, Math.hypot(dx, dy));
}

// Helper para dibujar texto sobre canvas espejado por CSS sin que se lea al revés
function drawMirroredText(ctx, text, x, y, font, fillStyle, strokeStyle = '#000') {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(-1, 1);
    ctx.font = font;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    if (strokeStyle) {
        ctx.lineWidth = 4;
        ctx.strokeStyle = strokeStyle;
        ctx.strokeText(text, 0, 0);
    }
    ctx.fillStyle = fillStyle;
    ctx.fillText(text, 0, 0);
    ctx.restore();
}

// =====================================================================
// DETECTORES DE POSES (ESTÁTICOS Y DINÁMICOS)
// En el canvas espejado con MediaPipe JS sin flip previo:
// L_WRIST (15) es la muñeca del lado izquierdo de la imagen
// =====================================================================
function check_left_arm_up(lm) { return lm[L_WRIST].y < lm[NOSE].y - 0.05; }
function check_right_arm_up(lm) { return lm[R_WRIST].y < lm[NOSE].y - 0.05; }
function check_left_arm_down(lm) { return lm[L_WRIST].y > lm[L_SHOULDER].y + 0.05; }
function check_right_arm_down(lm) { return lm[R_WRIST].y > lm[R_SHOULDER].y + 0.05; }
function check_left_arm_horizontal(lm) {
    return Math.abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.12 && lm[L_WRIST].x < lm[L_SHOULDER].x - 0.08;
}
function check_right_arm_horizontal(lm) {
    return Math.abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.12 && lm[R_WRIST].x > lm[R_SHOULDER].x + 0.08;
}
function check_left_hand_on_hip(lm) {
    return Math.abs(lm[L_WRIST].x - lm[L_HIP].x) < 0.15 && Math.abs(lm[L_WRIST].y - lm[L_HIP].y) < 0.15;
}
function check_right_hand_on_hip(lm) {
    return Math.abs(lm[R_WRIST].x - lm[R_HIP].x) < 0.15 && Math.abs(lm[R_WRIST].y - lm[R_HIP].y) < 0.15;
}
function check_left_hand_on_head(lm) {
    return (Math.abs(lm[L_WRIST].x - lm[NOSE].x) < 0.14 || Math.abs(lm[L_WRIST].x - lm[L_EAR].x) < 0.14) &&
           (Math.abs(lm[L_WRIST].y - lm[NOSE].y) < 0.14 || Math.abs(lm[L_WRIST].y - lm[L_EAR].y) < 0.14);
}
function check_right_hand_on_head(lm) {
    return (Math.abs(lm[R_WRIST].x - lm[NOSE].x) < 0.14 || Math.abs(lm[R_WRIST].x - lm[R_EAR].x) < 0.14) &&
           (Math.abs(lm[R_WRIST].y - lm[NOSE].y) < 0.14 || Math.abs(lm[R_WRIST].y - lm[R_EAR].y) < 0.14);
}
function check_left_bicep(lm) {
    return Math.abs(lm[L_WRIST].x - lm[L_SHOULDER].x) < 0.10 && Math.abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.15 && lm[L_ELBOW].x < lm[L_SHOULDER].x - 0.05;
}
function check_right_bicep(lm) {
    return Math.abs(lm[R_WRIST].x - lm[R_SHOULDER].x) < 0.10 && Math.abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.15 && lm[R_ELBOW].x > lm[R_SHOULDER].x + 0.05;
}
function check_right_salute(lm) {
    return Math.abs(lm[R_WRIST].x - lm[R_EAR].x) < 0.12 && Math.abs(lm[R_WRIST].y - lm[R_EAR].y) < 0.12;
}
function check_left_arm_y(lm) {
    return lm[L_WRIST].y < lm[NOSE].y && lm[L_WRIST].x < lm[L_SHOULDER].x - 0.10;
}
function check_right_arm_y(lm) {
    return lm[R_WRIST].y < lm[NOSE].y && lm[R_WRIST].x > lm[R_SHOULDER].x + 0.10;
}
function check_left_arm_o(lm) {
    return lm[L_WRIST].y < lm[NOSE].y - 0.05 && Math.abs(lm[L_WRIST].x - lm[NOSE].x) < 0.12;
}
function check_right_arm_o(lm) {
    return lm[R_WRIST].y < lm[NOSE].y - 0.05 && Math.abs(lm[R_WRIST].x - lm[NOSE].x) < 0.12;
}
function check_monkey_left(lm) {
    const bu = getBodyUnit(lm);
    const d = Math.hypot(lm[L_WRIST].x - lm[L_SHOULDER].x, lm[L_WRIST].y - lm[L_SHOULDER].y);
    return d < 0.45 * bu && lm[L_ELBOW].x < lm[L_SHOULDER].x - 0.25 * bu;
}
function check_monkey_right(lm) {
    const bu = getBodyUnit(lm);
    const d = Math.hypot(lm[R_WRIST].x - lm[R_SHOULDER].x, lm[R_WRIST].y - lm[R_SHOULDER].y);
    return d < 0.45 * bu && lm[R_ELBOW].x > lm[R_SHOULDER].x + 0.25 * bu;
}
function check_airplane_left(lm) {
    return check_left_arm_horizontal(lm) && (lm[L_SHOULDER].y - lm[R_SHOULDER].y > 0.04);
}
function check_airplane_right(lm) {
    return check_right_arm_horizontal(lm) && (lm[L_SHOULDER].y - lm[R_SHOULDER].y > 0.04);
}

// Estados Dinámicos
class MobilePlayerState {
    constructor() { this.reset(); }
    reset() {
        this.hipHits = 0;
        this.lastSide = null;
        this.centerX = null;
        this.centerY = null;
        this.jumpPhase = 0;
        this.armHits = 0;
        this.lastArmPos = null;
        this.moveHits = 0;
    }
}
const pState = new MobilePlayerState();

function check_shake_hips(lm) {
    const hipX = (lm[L_HIP].x + lm[R_HIP].x) / 2.0;
    if (pState.centerX === null) pState.centerX = hipX;
    else pState.centerX = pState.centerX * 0.98 + hipX * 0.02;
    const th = 0.025;
    if (hipX > pState.centerX + th && pState.lastSide !== 'right') {
        pState.lastSide = 'right'; pState.hipHits++;
    } else if (hipX < pState.centerX - th && pState.lastSide !== 'left') {
        pState.lastSide = 'left'; pState.hipHits++;
    }
    return pState.hipHits >= 6;
}

function check_shake_head(lm) {
    const noseX = lm[NOSE].x;
    if (pState.centerX === null) pState.centerX = noseX;
    else pState.centerX = pState.centerX * 0.96 + noseX * 0.04;
    const th = 0.020;
    if (noseX > pState.centerX + th && pState.lastSide !== 'right') {
        pState.lastSide = 'right'; pState.hipHits++;
    } else if (noseX < pState.centerX - th && pState.lastSide !== 'left') {
        pState.lastSide = 'left'; pState.hipHits++;
    }
    return pState.hipHits >= 6;
}

function check_jump(lm) {
    const hipY = (lm[L_HIP].y + lm[R_HIP].y) / 2.0;
    if (pState.centerY === null) pState.centerY = hipY;
    else if (pState.jumpPhase === 0) pState.centerY = pState.centerY * 0.95 + hipY * 0.05;
    const th = 0.07;
    if (pState.jumpPhase === 0 && hipY < pState.centerY - th) pState.jumpPhase = 1;
    else if (pState.jumpPhase === 1 && hipY > pState.centerY - 0.02) pState.jumpPhase = 2;
    return pState.jumpPhase >= 2;
}

function check_squat(lm) {
    const hipY = (lm[L_HIP].y + lm[R_HIP].y) / 2.0;
    if (pState.centerY === null) pState.centerY = hipY;
    else if (pState.jumpPhase === 0) pState.centerY = pState.centerY * 0.95 + hipY * 0.05;
    const th = 0.08;
    if (pState.jumpPhase === 0 && hipY > pState.centerY + th) pState.jumpPhase = 1;
    else if (pState.jumpPhase === 1 && hipY < pState.centerY + 0.02) pState.jumpPhase = 2;
    return pState.jumpPhase >= 2;
}

function check_flail_arms(lm) {
    const lUp = lm[L_WRIST].y < lm[L_SHOULDER].y;
    const rUp = lm[R_WRIST].y < lm[R_SHOULDER].y;
    const curr = (lUp && rUp) ? 'up' : ((!lUp && !rUp) ? 'down' : 'mid');
    if (pState.lastArmPos === null) pState.lastArmPos = curr;
    if (curr === 'up' && pState.lastArmPos !== 'up') {
        pState.lastArmPos = 'up'; pState.armHits++;
    } else if (curr === 'down' && pState.lastArmPos !== 'down') {
        pState.lastArmPos = 'down'; pState.armHits++;
    }
    return pState.armHits >= 6;
}

function check_boxer_jabs(lm) {
    const bu = getBodyUnit(lm);
    const diffY = lm[L_WRIST].y - lm[R_WRIST].y;
    if (Math.abs(diffY) > 0.18 * bu) {
        const curr = diffY < 0 ? 'ljab' : 'rjab';
        if (pState.lastArmPos !== curr) {
            pState.lastArmPos = curr; pState.armHits++;
        }
    }
    return pState.armHits >= 6;
}

function check_air_guitar(lm) {
    const bu = getBodyUnit(lm);
    const handY = lm[R_WRIST].y;
    if (pState.lastArmPos === null) pState.lastArmPos = handY;
    if (Math.abs(handY - pState.lastArmPos) > 0.15 * bu) {
        pState.lastArmPos = handY; pState.armHits++;
    }
    return pState.armHits >= 6;
}

// =====================================================================
// CATÁLOGO DE 18 POSES Y COREOGRAFÍAS
// =====================================================================
const POSES = [
    // Dinámicas
    { name: 'Baila! Mueve Caderas', dynamic: true, check: check_shake_hips, color: '#ff477e' },
    { name: 'Mueve la Cabeza!', dynamic: true, check: check_shake_head, color: '#00ff64' },
    { name: 'Boxeo Rapido!', dynamic: true, check: check_boxer_jabs, color: '#00d4ff' },
    { name: 'Salto Mortal!', dynamic: true, check: check_jump, color: '#ffb703' },
    { name: 'Agacharse!', dynamic: true, check: check_squat, color: '#38b000' },
    { name: 'Mueve los Brazos!', dynamic: true, check: check_flail_arms, color: '#ff007f' },
    { name: 'Guitarra Rock!', dynamic: true, check: check_air_guitar, color: '#ffc800' },
    
    // Estáticas
    { name: 'Brazos Arriba!', checks: { l: check_left_arm_up, r: check_right_arm_up }, color: '#00ff64' },
    { name: 'T-Pose!', checks: { l: check_left_arm_horizontal, r: check_right_arm_horizontal }, color: '#ffc800' },
    { name: 'Fuerte!', checks: { l: check_left_bicep, r: check_right_bicep }, color: '#ff6432' },
    { name: 'Saludo Militar!', checks: { l: check_left_arm_down, r: check_right_salute }, color: '#3264ff' },
    { name: 'Letra Y!', checks: { l: check_left_arm_y, r: check_right_arm_y }, color: '#ff69b4' },
    { name: 'Letra O!', checks: { l: check_left_arm_o, r: check_right_arm_o }, color: '#00ffff' },
    { name: 'Pose de Mono!', checks: { l: check_monkey_left, r: check_monkey_right }, color: '#ffd700' },
    { name: 'Fiebre Disco!', checks: { l: check_left_hand_on_hip, r: check_right_arm_up }, color: '#e056fd' },
    { name: 'Avion Supersonico!', checks: { l: check_airplane_left, r: check_airplane_right }, color: '#686de0' },
    { name: 'Manos en Cintura!', checks: { l: check_left_hand_on_hip, r: check_right_hand_on_hip }, color: '#f0932b' },
    { name: 'Manos en Cabeza!', checks: { l: check_left_hand_on_head, r: check_right_hand_on_head }, color: '#badc58' }
];

const COREOGRAFIAS = {
    'macarena.wav': [
        { name: 'Brazo Der Adelante', checks: { l: check_left_arm_down, r: check_right_arm_horizontal }, color: '#ffb703' },
        { name: 'Brazos Adelante', checks: { l: check_left_arm_horizontal, r: check_right_arm_horizontal }, color: '#ffb703' },
        { name: 'Mano Der Cabeza', checks: { l: check_left_arm_horizontal, r: check_right_hand_on_head }, color: '#ffb703' },
        { name: 'Manos en Cabeza!', checks: { l: check_left_hand_on_head, r: check_right_hand_on_head }, color: '#ffb703' },
        { name: 'Mano Der Cintura', checks: { l: check_left_hand_on_head, r: check_right_hand_on_hip }, color: '#ffb703' },
        { name: 'Manos en Cintura!', checks: { l: check_left_hand_on_hip, r: check_right_hand_on_hip }, color: '#ffb703' },
        { name: 'Baila! Mueve Caderas', dynamic: true, check: check_shake_hips, color: '#ff477e' }
    ],
    'asereje.wav': [
        { name: 'Manos en Cabeza!', checks: { l: check_left_hand_on_head, r: check_right_hand_on_head }, color: '#ff477e' },
        { name: 'Baila! Mueve Caderas', dynamic: true, check: check_shake_hips, color: '#ff477e' },
        { name: 'Mueve los Brazos!', dynamic: true, check: check_flail_arms, color: '#00d4ff' }
    ],
    'ymca.wav': [
        { name: 'Letra Y!', checks: { l: check_left_arm_y, r: check_right_arm_y }, color: '#ff69b4' },
        { name: 'Letra M!', checks: { l: check_left_hand_on_head, r: check_right_hand_on_head }, color: '#00ff64' },
        { name: 'Letra C!', checks: { l: check_left_arm_horizontal, r: check_right_arm_up }, color: '#00d4ff' },
        { name: 'Letra A!', checks: { l: check_left_hand_on_head, r: check_right_hand_on_head }, color: '#ffb703' }
    ]
};

// =====================================================================
// PARTÍCULAS 2D EN CANVAS
// =====================================================================
class MobileParticles {
    constructor() { this.particles = []; }
    burst(x, y, color, count = 25) {
        for (let i = 0; i < count; i++) {
            const ang = Math.random() * Math.PI * 2;
            const spd = 3 + Math.random() * 8;
            this.particles.push({
                x: x, y: y,
                vx: Math.cos(ang) * spd,
                vy: Math.sin(ang) * spd,
                color: color,
                life: 30 + Math.random() * 20,
                maxLife: 50,
                size: 4 + Math.random() * 5
            });
        }
    }
    updateAndDraw(ctx) {
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.vy += 0.25; // Gravedad
            p.life--;
            if (p.life <= 0) {
                this.particles.splice(i, 1);
                continue;
            }
            const alpha = p.life / p.maxLife;
            ctx.save();
            ctx.globalAlpha = alpha;
            ctx.fillStyle = p.color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size * alpha, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }
    }
}
const particleSys = new MobileParticles();

// =====================================================================
// GESTIÓN DE COLA Y PRÓXIMAS POSES
// =====================================================================
function fillQueue() {
    if (gameMode === 'coreo') {
        const songKey = selectedSong in COREOGRAFIAS ? selectedSong : 'macarena.wav';
        const list = COREOGRAFIAS[songKey] || POSES;
        while (poseQueue.length < 4) {
            poseQueue.push(list[coreoIndex % list.length]);
            coreoIndex++;
        }
    } else {
        while (poseQueue.length < 4) {
            const rand = POSES[Math.floor(Math.random() * POSES.length)];
            poseQueue.push(rand);
        }
    }
}

function updateQueueUI() {
    if (!queueStrip) return;
    queueStrip.innerHTML = '';
    poseQueue.forEach((p, idx) => {
        const card = document.createElement('div');
        card.className = 'queue-card' + (idx === 0 ? ' active' : '');
        card.style.borderColor = idx === 0 ? (p.color || '#00d4ff') : 'rgba(255,255,255,0.2)';
        card.innerHTML = `<span style="color:${p.color || '#fff'}">${idx === 0 ? '▶' : '•'}</span> <span>${p.name}</span>`;
        queueStrip.appendChild(card);
    });
}

function nextPose() {
    fillQueue();
    currentPose = poseQueue.shift();
    fillQueue();
    updateQueueUI();

    instructionEl.innerText = currentPose.name;
    instructionEl.style.color = currentPose.color || '#ffb703';
    instructionEl.style.borderColor = currentPose.color || '#00d4ff';

    timeRemaining = difficultyTime;
    holdProgress = 0.0;
    pState.reset();
}

function handleSuccess() {
    sndSuccess.currentTime = 0;
    sndSuccess.play().catch(e => {});

    streak++;
    const multi = isFever ? 3 : (streak >= 5 ? 2 : 1);
    const addedPoints = 100 * multi;
    score += addedPoints;
    scoreEl.innerText = score.toLocaleString();
    comboEl.innerText = `🔥 Combo x${streak}`;

    // Aumento de medidor Fever
    if (!isFever) {
        feverMeter = Math.min(1.0, feverMeter + 0.20);
        feverBar.style.width = (feverMeter * 100) + '%';
        if (feverMeter >= 1.0) {
            activateFever();
        }
    }

    instructionEl.innerText = `¡EXCELENTE! +${addedPoints}`;
    instructionEl.style.color = "#00ff64";

    // Disparar partículas desde el centro
    particleSys.burst(canvasElement.width / 2, canvasElement.height / 3, currentPose ? currentPose.color : '#00d4ff', 40);

    setTimeout(() => {
        if (isPlaying && !isPaused) nextPose();
    }, 900);
}

function handleFail() {
    sndFail.currentTime = 0;
    sndFail.play().catch(e => {});

    streak = 0;
    comboEl.innerText = `🔥 Combo x0`;
    instructionEl.innerText = "¡TIEMPO!";
    instructionEl.style.color = "#ff477e";

    setTimeout(() => {
        if (isPlaying && !isPaused) nextPose();
    }, 1100);
}

function activateFever() {
    isFever = true;
    feverEndTime = performance.now() + 8000;
    comboEl.innerText = "⚡ FEVER x3!";
    comboEl.style.background = "linear-gradient(90deg, #ff477e, #00d4ff)";
}

// =====================================================================
// EVENTOS Y CONTROLES UI
// =====================================================================
document.querySelectorAll('.song-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.song-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedSong = btn.getAttribute('data-song');
    });
});

document.getElementById('config-btn').addEventListener('click', () => {
    document.getElementById('config-modal').classList.add('active');
});

document.getElementById('close-config-btn').addEventListener('click', () => {
    document.getElementById('config-modal').classList.remove('active');
});

document.querySelectorAll('#diff-group .opt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('#diff-group .opt-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        difficultyTime = parseFloat(btn.getAttribute('data-val'));
    });
});

document.querySelectorAll('#mode-group .opt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('#mode-group .opt-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        gameMode = btn.getAttribute('data-val');
    });
});

gameScreen.addEventListener('click', (e) => {
    if (e.target.id === 'exit-btn') return;
    if (!isPlaying) return;

    isPaused = !isPaused;
    if (isPaused) {
        document.getElementById('pause-overlay').style.display = 'flex';
        bgMusic.pause();
    } else {
        document.getElementById('pause-overlay').style.display = 'none';
        if (selectedSong !== 'none') bgMusic.play().catch(e => {});
        lastLoopTimestamp = performance.now();
    }
});

document.getElementById('exit-btn').addEventListener('click', () => {
    isPlaying = false;
    isPaused = false;
    bgMusic.pause();
    document.getElementById('pause-overlay').style.display = 'none';
    gameScreen.classList.remove('active');
    startScreen.classList.add('active');
    if (cameraRef) {
        cameraRef.stop();
        cameraRef = null;
    }
});

// =====================================================================
// BUCLE PRINCIPAL UNIFICADO (SIN DUPLICADOS)
// =====================================================================
function updateGameLoop() {
    if (!isPlaying) return;
    requestAnimationFrame(updateGameLoop);

    const now = performance.now();
    const dt = Math.min(0.1, (now - lastLoopTimestamp) / 1000);
    lastLoopTimestamp = now;

    if (isPaused) return;

    // Gestión de Fever Mode
    if (isFever) {
        const leftFever = Math.max(0, (feverEndTime - now) / 8000);
        feverBar.style.width = (leftFever * 100) + '%';
        if (leftFever <= 0) {
            isFever = false;
            feverMeter = 0.0;
            feverBar.style.width = '0%';
            comboEl.innerText = `🔥 Combo x${streak}`;
            comboEl.style.background = "rgba(255, 183, 3, 0.25)";
        }
    }

    if (currentPose) {
        if (gameMode === 'practice') {
            timerEl.innerText = "∞";
        } else {
            timeRemaining = Math.max(0, timeRemaining - dt);
            timerEl.innerText = timeRemaining.toFixed(1) + "s";
            if (timeRemaining <= 0) {
                currentPose = null;
                progressBar.style.width = '0%';
                handleFail();
            }
        }
    }
}

// Conexiones de esqueleto
const SKELETON_CONNECTIONS = [[L_SHOULDER, R_SHOULDER], [L_SHOULDER, L_HIP], [R_SHOULDER, R_HIP], [L_HIP, R_HIP], [L_SHOULDER, NOSE], [R_SHOULDER, NOSE]];
const LEFT_ARM_CONNECTIONS = [[L_SHOULDER, L_ELBOW], [L_ELBOW, L_WRIST]];
const RIGHT_ARM_CONNECTIONS = [[R_SHOULDER, R_ELBOW], [R_ELBOW, R_WRIST]];

function drawCustomSkeleton(ctx, lm, l_ok, r_ok, offsetX, offsetY, w, h) {
    const pt = (id) => lm[id] && lm[id].visibility > 0.35 ? { x: offsetX + lm[id].x * w, y: offsetY + lm[id].y * h } : null;

    const points = {};
    [NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP].forEach(id => {
        const p = pt(id);
        if (p) points[id] = p;
    });

    const COLOR_OK = '#00ff64';
    const COLOR_FAIL = '#ff477e';
    const COLOR_BODY = '#00d4ff';
    const left_color = l_ok ? COLOR_OK : COLOR_FAIL;
    const right_color = r_ok ? COLOR_OK : COLOR_FAIL;

    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    function drawLines(conns, color, width) {
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.beginPath();
        conns.forEach(([a, b]) => {
            if (points[a] && points[b]) {
                ctx.moveTo(points[a].x, points[a].y);
                ctx.lineTo(points[b].x, points[b].y);
            }
        });
        ctx.stroke();
    }

    // Resplandor
    ctx.globalAlpha = 0.45;
    drawLines(SKELETON_CONNECTIONS, COLOR_BODY, 10);
    drawLines(LEFT_ARM_CONNECTIONS, left_color, 14);
    drawLines(RIGHT_ARM_CONNECTIONS, right_color, 14);

    // Núcleo
    ctx.globalAlpha = 1.0;
    drawLines(SKELETON_CONNECTIONS, '#ffffff', 3);
    drawLines(LEFT_ARM_CONNECTIONS, '#ffffff', 4);
    drawLines(RIGHT_ARM_CONNECTIONS, '#ffffff', 4);

    // Articulaciones
    const pulse = Math.sin(Date.now() / 120) * 3;
    for (const [idStr, p] of Object.entries(points)) {
        const id = parseInt(idStr);
        let color = COLOR_BODY;
        if ([L_SHOULDER, L_ELBOW, L_WRIST].includes(id)) color = left_color;
        if ([R_SHOULDER, R_ELBOW, R_WRIST].includes(id)) color = right_color;

        const base_r = (color === COLOR_OK) ? 12 : 7;
        const r = Math.max(4, base_r + pulse);

        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(p.x, p.y, r + 3, 0, 2 * Math.PI); ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 2 * Math.PI); ctx.fill();
    }

    if (points[NOSE]) {
        ctx.strokeStyle = COLOR_BODY;
        ctx.lineWidth = 3;
        ctx.beginPath(); ctx.arc(points[NOSE].x, points[NOSE].y, Math.max(12, 18 + pulse), 0, 2 * Math.PI); ctx.stroke();
    }
}

// =====================================================================
// RESULTADOS MEDIAPIPE Y AUDITORÍA EN TIEMPO REAL
// =====================================================================
function onResults(results) {
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);

    const videoRatio = results.image.width / results.image.height;
    const canvasRatio = canvasElement.width / canvasElement.height;
    let drawW, drawH, drawX, drawY;

    if (canvasRatio > videoRatio) {
        drawW = canvasElement.width;
        drawH = drawW / videoRatio;
        drawX = 0;
        drawY = (canvasElement.height - drawH) / 2;
    } else {
        drawH = canvasElement.height;
        drawW = drawH * videoRatio;
        drawY = 0;
        drawX = (canvasElement.width - drawW) / 2;
    }

    canvasCtx.drawImage(results.image, drawX, drawY, drawW, drawH);

    if (results.poseLandmarks && isPlaying && !isPaused) {
        const lm = results.poseLandmarks;
        let l_ok = false;
        let r_ok = false;
        let poseSuccess = false;

        if (currentPose) {
            if (currentPose.dynamic) {
                l_ok = true;
                r_ok = true;
                poseSuccess = currentPose.check(lm);
                const hits = pState.hipHits || pState.armHits || pState.jumpPhase || 0;
                progressBar.style.width = Math.min(100, (hits / 6) * 100) + "%";
            } else {
                l_ok = currentPose.checks.l ? currentPose.checks.l(lm) : true;
                r_ok = currentPose.checks.r ? currentPose.checks.r(lm) : true;
                const match = l_ok && r_ok;

                // Acumulador de Dwell-Time con Grace Decay (0.40s continuo para validar)
                const dt = 0.033;
                if (match) {
                    holdProgress = Math.min(1.0, holdProgress + dt / 0.40);
                } else {
                    holdProgress = Math.max(0.0, holdProgress - dt * 0.70);
                }
                progressBar.style.width = (holdProgress * 100) + "%";
                poseSuccess = holdProgress >= 1.0;
            }

            if (poseSuccess) {
                currentPose = null;
                handleSuccess();
            }
        }

        drawCustomSkeleton(canvasCtx, lm, l_ok, r_ok, drawX, drawY, drawW, drawH);
    } else if (results.poseLandmarks && isPaused) {
        drawCustomSkeleton(canvasCtx, results.poseLandmarks, false, false, drawX, drawY, drawW, drawH);
    }

    // Actualizar partículas
    particleSys.updateAndDraw(canvasCtx);

    canvasCtx.restore();
}

let pose;
try {
    pose = new Pose({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
    });

    pose.setOptions({
        modelComplexity: 0,
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    });
    pose.onResults(onResults);
} catch (e) {
    logError("Error cargando IA MediaPipe: " + e.message);
}

document.getElementById('start-btn').addEventListener('click', () => {
    try {
        if (!pose) {
            alert("La inteligencia artificial no cargó correctamente. Revisa tu conexión a internet.");
            return;
        }

        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen().catch(e => {});
        } else if (document.documentElement.webkitRequestFullscreen) {
            document.documentElement.webkitRequestFullscreen().catch(e => {});
        }

        startScreen.classList.remove('active');
        gameScreen.classList.add('active');

        canvasElement.width = window.innerWidth;
        canvasElement.height = window.innerHeight;

        sndSuccess.play().catch(e => {}); sndSuccess.pause(); sndSuccess.currentTime = 0;
        sndFail.play().catch(e => {}); sndFail.pause(); sndFail.currentTime = 0;

        if (selectedSong !== 'none') {
            bgMusic.src = selectedSong;
            bgMusic.play().catch(e => logError("Audio: " + e.message));
        }

        cameraRef = new Camera(videoElement, {
            onFrame: async () => {
                await pose.send({ image: videoElement });
            },
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: 'user'
        });

        cameraRef.start().then(() => {
            isPlaying = true;
            score = 0;
            streak = 0;
            feverMeter = 0.0;
            isFever = false;
            coreoIndex = 0;
            poseQueue = [];
            scoreEl.innerText = "0";
            nextPose();
            lastLoopTimestamp = performance.now();
            updateGameLoop();
        }).catch(err => {
            alert("Error al iniciar cámara: " + err);
            logError("Cámara: " + err);
        });
    } catch (e) {
        alert("Error crítico: " + e.message);
        logError("Start error: " + e.message);
    }
});

window.addEventListener('resize', () => {
    canvasElement.width = window.innerWidth;
    canvasElement.height = window.innerHeight;
});
