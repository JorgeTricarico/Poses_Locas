const videoElement = document.getElementById('input-video');
const canvasElement = document.getElementById('output-canvas');
const canvasCtx = canvasElement.getContext('2d');
const scoreEl = document.getElementById('score');
const timerEl = document.getElementById('timer');
const instructionEl = document.getElementById('pose-instruction');
const progressBar = document.getElementById('progress-bar');
const startScreen = document.getElementById('start-screen');
const gameScreen = document.getElementById('game-screen');

function logError(msg) {
    const p = document.createElement('p');
    p.style.color = 'red';
    p.innerText = msg;
    p.style.backgroundColor = 'rgba(0,0,0,0.5)';
    p.style.padding = '10px';
    document.getElementById('start-screen').appendChild(p);
}

// Audio
const sndSuccess = new Audio('success_new.wav');
const sndFail = new Audio('fail.wav');

let isPlaying = false;
let isPaused = false;
let score = 0;
let currentPose = null;
let poseStartTime = 0;
let timeRemaining = 0;
let hipsHits = 0;
let lastHitSide = null;
let centerHipX = null;
let cameraRef = null;

let selectedSong = 'macarena.wav';
let difficultyTime = 6.0;
let gameMode = 'arcade';
let bgMusic = new Audio();
bgMusic.loop = true;

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
        if (selectedSong !== 'none') bgMusic.play().catch(e=>{});
        // Adjust start time to resume seamlessly
        poseStartTime = performance.now() - ((difficultyTime - timeRemaining) * 1000);
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

// LANDMARKS (MediaPipe JS format)
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

// POSES CHECKS (Same as Python version)
function check_left_arm_up(lm) { return lm[L_WRIST].y < lm[L_SHOULDER].y - 0.12; }
function check_right_arm_up(lm) { return lm[R_WRIST].y < lm[R_SHOULDER].y - 0.12; }
function check_left_arm_down(lm) { return lm[L_WRIST].y > lm[L_SHOULDER].y + 0.05; }
function check_right_arm_down(lm) { return lm[R_WRIST].y > lm[R_SHOULDER].y + 0.05; }
function check_left_arm_horizontal(lm) { return Math.abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.12 && lm[L_WRIST].x > lm[L_SHOULDER].x + 0.08; } 
function check_right_arm_horizontal(lm) { return Math.abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.12 && lm[R_WRIST].x < lm[R_SHOULDER].x - 0.08; }
function check_left_bicep(lm) { return Math.abs(lm[L_WRIST].x - lm[L_SHOULDER].x) < 0.10 && Math.abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.15 && lm[L_ELBOW].x > lm[L_SHOULDER].x + 0.05; }
function check_right_bicep(lm) { return Math.abs(lm[R_WRIST].x - lm[R_SHOULDER].x) < 0.10 && Math.abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.15 && lm[R_ELBOW].x < lm[R_SHOULDER].x - 0.05; }
function check_right_salute(lm) { return Math.abs(lm[R_WRIST].x - lm[R_EAR].x) < 0.10 && Math.abs(lm[R_WRIST].y - lm[R_EAR].y) < 0.10; }

function check_shake_hips(lm) {
    let hip_x = (lm[L_HIP].x + lm[R_HIP].x) / 2.0;
    if (centerHipX === null) {
        centerHipX = hip_x;
    } else {
        centerHipX = centerHipX * 0.98 + hip_x * 0.02;
    }
    const threshold = 0.025;
    if (hip_x > centerHipX + threshold && lastHitSide !== 'right') {
        lastHitSide = 'right';
        hipsHits += 1;
    } else if (hip_x < centerHipX - threshold && lastHitSide !== 'left') {
        lastHitSide = 'left';
        hipsHits += 1;
    }
    return hipsHits >= 6;
}

const POSES = [
    {
        name: 'Baila! Mueve Caderas', dynamic: true, color: '#ff477e', check: check_shake_hips,
        ref: { [NOSE]: [0.5, 0.12], [L_SHOULDER]: [0.38, 0.30], [R_SHOULDER]: [0.62, 0.30], [L_ELBOW]: [0.28, 0.42], [R_ELBOW]: [0.72, 0.42], [L_WRIST]: [0.40, 0.60], [R_WRIST]: [0.60, 0.60], [L_HIP]: [0.35, 0.65], [R_HIP]: [0.50, 0.65] }
    },
    {
        name: 'Brazos Arriba!', checks: { l: check_left_arm_up, r: check_right_arm_up }, color: '#00ff64',
        ref: { [NOSE]: [0.5, 0.12], [L_SHOULDER]: [0.38, 0.30], [R_SHOULDER]: [0.62, 0.30], [L_ELBOW]: [0.32, 0.18], [R_ELBOW]: [0.68, 0.18], [L_WRIST]: [0.35, 0.05], [R_WRIST]: [0.65, 0.05], [L_HIP]: [0.42, 0.65], [R_HIP]: [0.58, 0.65] }
    },
    {
        name: 'T-Pose!', checks: { l: check_left_arm_horizontal, r: check_right_arm_horizontal }, color: '#ffc800',
        ref: { [NOSE]: [0.5, 0.12], [L_SHOULDER]: [0.38, 0.30], [R_SHOULDER]: [0.62, 0.30], [L_ELBOW]: [0.22, 0.30], [R_ELBOW]: [0.78, 0.30], [L_WRIST]: [0.08, 0.30], [R_WRIST]: [0.92, 0.30], [L_HIP]: [0.42, 0.65], [R_HIP]: [0.58, 0.65] }
    },
    {
        name: 'Fuerte!', checks: { l: check_left_bicep, r: check_right_bicep }, color: '#ff6432',
        ref: { [NOSE]: [0.5, 0.12], [L_SHOULDER]: [0.38, 0.30], [R_SHOULDER]: [0.62, 0.30], [L_ELBOW]: [0.22, 0.30], [R_ELBOW]: [0.78, 0.30], [L_WRIST]: [0.32, 0.20], [R_WRIST]: [0.68, 0.20], [L_HIP]: [0.42, 0.65], [R_HIP]: [0.58, 0.65] }
    },
    {
        name: 'Saludo Militar!', checks: { l: check_left_arm_down, r: check_right_salute }, color: '#3264ff',
        ref: { [NOSE]: [0.5, 0.12], [L_SHOULDER]: [0.38, 0.30], [R_SHOULDER]: [0.62, 0.30], [L_ELBOW]: [0.32, 0.45], [R_ELBOW]: [0.75, 0.30], [L_WRIST]: [0.35, 0.58], [R_WRIST]: [0.58, 0.12], [L_HIP]: [0.42, 0.65], [R_HIP]: [0.58, 0.65] }
    }
];

function pickRandomPose() {
    currentPose = POSES[Math.floor(Math.random() * POSES.length)];
    instructionEl.innerText = currentPose.name;
    instructionEl.style.color = currentPose.color || '#ffb703';
    timeRemaining = difficultyTime;
    hipsHits = 0;
    lastHitSide = null;
    centerHipX = null;
    poseStartTime = performance.now();
}

function updateGameLoop() {
    if (!isPlaying) return;
    requestAnimationFrame(updateGameLoop);

    if (isPaused) return;

    if (currentPose) {
        if (gameMode === 'practice') {
            timerEl.innerText = "∞";
            progressBar.style.width = "100%";
        } else {
            let now = performance.now();
            let elapsed = (now - poseStartTime) / 1000;
            timeRemaining = Math.max(0, difficultyTime - elapsed);
            
            timerEl.innerText = timeRemaining.toFixed(1) + "s";
            
            if (timeRemaining <= 0) {
                // FAIL
                currentPose = null;
                handleFail();
            }
        }
    }
}

function handleSuccess() {
    sndSuccess.currentTime = 0;
    sndSuccess.play();
    score += 10;
    scoreEl.innerText = score;
    instructionEl.innerText = "¡EXCELENTE!";
    instructionEl.style.color = "#00ff00";
    
    // Confetti effect could go here
    setTimeout(pickRandomPose, 1500);
}

function handleFail() {
    sndFail.currentTime = 0;
    sndFail.play();
    instructionEl.innerText = "¡TIEMPO!";
    instructionEl.style.color = "#ff0000";
    setTimeout(pickRandomPose, 1500);
}

const SKELETON_CONNECTIONS = [[L_SHOULDER, R_SHOULDER], [L_SHOULDER, L_HIP], [R_SHOULDER, R_HIP], [L_HIP, R_HIP], [L_SHOULDER, NOSE], [R_SHOULDER, NOSE]];
const LEFT_ARM_CONNECTIONS = [[L_SHOULDER, L_ELBOW], [L_ELBOW, L_WRIST]];
const RIGHT_ARM_CONNECTIONS = [[R_SHOULDER, R_ELBOW], [R_ELBOW, R_WRIST]];

function drawCustomSkeleton(ctx, lm, l_ok, r_ok, offsetX, offsetY, w, h) {
    const pt = (id) => lm[id] && lm[id].visibility > 0.4 ? {x: offsetX + lm[id].x * w, y: offsetY + lm[id].y * h} : null;
    
    const points = {};
    [NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP].forEach(id => {
        let p = pt(id);
        if (p) points[id] = p;
    });

    const COLOR_OK = '#00ff00';
    const COLOR_FAIL = '#ff0000';
    const COLOR_BODY = '#ffff00';
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

    // 1. Glow Overlay (thick lines)
    ctx.globalAlpha = 0.5;
    drawLines(SKELETON_CONNECTIONS, COLOR_BODY, 12);
    drawLines(LEFT_ARM_CONNECTIONS, left_color, 16);
    drawLines(RIGHT_ARM_CONNECTIONS, right_color, 16);

    // 2. Inner core
    ctx.globalAlpha = 1.0;
    drawLines(SKELETON_CONNECTIONS, '#ffffff', 3);
    drawLines(LEFT_ARM_CONNECTIONS, '#ffffff', 4);
    drawLines(RIGHT_ARM_CONNECTIONS, '#ffffff', 4);

    // 3. Dynamic pulsing joints
    let pulse = Math.sin(Date.now() / 100) * 5;
    for (const [idStr, p] of Object.entries(points)) {
        let id = parseInt(idStr);
        let color = COLOR_BODY;
        if ([L_SHOULDER, L_ELBOW, L_WRIST].includes(id)) color = left_color;
        if ([R_SHOULDER, R_ELBOW, R_WRIST].includes(id)) color = right_color;
        
        let base_r = color === COLOR_OK ? 14 : 8;
        let r = Math.max(4, base_r + pulse);
        
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(p.x, p.y, r + 4, 0, 2 * Math.PI); ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 2 * Math.PI); ctx.fill();
    }
    
    if (points[NOSE]) {
        ctx.strokeStyle = COLOR_BODY;
        ctx.lineWidth = 3;
        ctx.beginPath(); ctx.arc(points[NOSE].x, points[NOSE].y, Math.max(14, 20 + pulse), 0, 2 * Math.PI); ctx.stroke();
    }
}

function drawReferenceSkeleton(ctx, pose, w, h) {
    if (!pose || !pose.ref) return;
    const boxW = Math.min(w * 0.25, 200);
    const boxH = boxW * 1.5;
    const boxX = 20; // Top left so it doesn't block right-hand UI elements on small screens
    const boxY = 80;
    
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(boxX, boxY, boxW, boxH);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.strokeRect(boxX, boxY, boxW, boxH);
    
    const pt = (id) => {
        if (!pose.ref[id]) return null;
        return {x: boxX + pose.ref[id][0] * boxW, y: boxY + pose.ref[id][1] * boxH};
    };
    
    const points = {};
    [NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP].forEach(id => {
        let p = pt(id);
        if (p) points[id] = p;
    });
    
    function drawLines(conns, color) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        conns.forEach(([a, b]) => {
            if (points[a] && points[b]) {
                ctx.moveTo(points[a].x, points[a].y);
                ctx.lineTo(points[b].x, points[b].y);
            }
        });
        ctx.stroke();
    }
    
    drawLines(SKELETON_CONNECTIONS, '#c8c8c8');
    drawLines(LEFT_ARM_CONNECTIONS, '#ffff00');
    drawLines(RIGHT_ARM_CONNECTIONS, '#ffff00');
    
    for (const p of Object.values(points)) {
        ctx.fillStyle = '#00ffff';
        ctx.beginPath(); ctx.arc(p.x, p.y, 4, 0, 2 * Math.PI); ctx.fill();
    }
}

function onResults(results) {
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    
    // El canvas ya está espejado por CSS (transform: scaleX(-1))
    // Así que dibujamos la imagen tal cual, y el CSS se encarga del efecto espejo
    
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
        let lm = results.poseLandmarks;
        let success = false;
        let l_ok = false;
        let r_ok = false;
        
        if (currentPose) {
            if (currentPose.dynamic) {
                l_ok = true; 
                r_ok = true;
                success = currentPose.check(lm);
                progressBar.style.width = (hipsHits / 6) * 100 + "%";
            } else {
                l_ok = currentPose.checks.l(lm);
                r_ok = currentPose.checks.r(lm);
                success = l_ok && r_ok;
                progressBar.style.width = success ? "100%" : "0%";
            }

            if (success) {
                currentPose = null;
                handleSuccess();
            }
        }
        
        // Dibujamos el esqueleto sobre las coordenadas crudas.
        // Como el canvas está espejado por CSS, esto se alineará perfectamente.
        drawCustomSkeleton(canvasCtx, lm, l_ok, r_ok, drawX, drawY, drawW, drawH);
    } else if (results.poseLandmarks && isPaused) {
        // Just draw the skeleton without checking success while paused
        drawCustomSkeleton(canvasCtx, results.poseLandmarks, false, false, drawX, drawY, drawW, drawH);
    }
    
    // Draw Reference Pose Box
    drawReferenceSkeleton(canvasCtx, currentPose, canvasElement.width, canvasElement.height);
    
    canvasCtx.restore();
}

function updateGameLoop() {
    if (!isPlaying) return;
    requestAnimationFrame(updateGameLoop);
    
    if (isPaused) return;

    if (currentPose) {
        if (gameMode === 'practice') {
            timerEl.innerText = "∞";
            progressBar.style.width = "100%";
        } else {
            let now = performance.now();
            let elapsed = (now - poseStartTime) / 1000;
            let left = timeRemaining - elapsed;
            
            if (left <= 0) {
                currentPose = null;
                handleFail();
            } else {
                timerEl.innerText = left.toFixed(1) + "s";
            }
        }
    }
}

let pose;
try {
    pose = new Pose({locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
    }});

    pose.setOptions({
        modelComplexity: 0,
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    });
    pose.onResults(onResults);
} catch(e) {
    logError("Error cargando IA: " + e.message);
}

document.getElementById('start-btn').addEventListener('click', () => {
    try {
        if (!pose) {
            alert("La inteligencia artificial no cargó correctamente. Revisa tu conexión a internet.");
            return;
        }

        // Solicitar pantalla completa
        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen().catch(e => {});
        } else if (document.documentElement.webkitRequestFullscreen) {
            document.documentElement.webkitRequestFullscreen().catch(e => {});
        }

        startScreen.classList.remove('active');
        gameScreen.classList.add('active'); // Asegurarnos de que el gameScreen sea visible
        
        canvasElement.width = window.innerWidth;
        canvasElement.height = window.innerHeight;

        // init sounds
        sndSuccess.play().catch(e=>{}); sndSuccess.pause(); sndSuccess.currentTime=0;
        sndFail.play().catch(e=>{}); sndFail.pause(); sndFail.currentTime=0;

        if (selectedSong !== 'none') {
            bgMusic.src = selectedSong;
            bgMusic.play().catch(e => logError("Error audio: " + e.message));
        }

        const camera = new Camera(videoElement, {
            onFrame: async () => {
                await pose.send({image: videoElement});
            },
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: 'user'
        });
        
        camera.start().then(() => {
            isPlaying = true;
            pickRandomPose();
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
