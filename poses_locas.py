import cv2
import mediapipe as mp
import threading
import time
import math
import random
import numpy as np
import os
from collections import deque

# =============================================
# CONFIGURACIÓN Y ENTORNO
# =============================================
ENABLE_SFX = False  # Deshabilitado por pedido del usuario (muy invasivos)
RTSP_URL = os.environ.get("POSES_RTSP_URL", "")

# =============================================
# AUDIO SETUP (PyGame)
# =============================================
try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()
    
    snd_success = pygame.mixer.Sound('success_new.wav') if os.path.exists('success_new.wav') else None
    snd_fail = pygame.mixer.Sound('fail.wav') if os.path.exists('fail.wav') else None
    snd_punch = pygame.mixer.Sound('punch_new.wav') if os.path.exists('punch_new.wav') else None
    
    HAS_AUDIO = True
except Exception as e:
    print(f"No se pudo cargar audio: {e}")
    HAS_AUDIO = False
    snd_success = None
    snd_fail = None
    snd_punch = None

def play_sound(snd):
    if HAS_AUDIO and snd and ENABLE_SFX:
        try:
            snd.play()
        except Exception:
            pass

# =============================================
# CAPTURA DE VÍDEO (CÁMARA FÍSICA / RTSP / MOCK)
# =============================================
class MockVideoCapture:
    def __init__(self):
        self.started = False
        self.read_lock = threading.Lock()
        self.t0 = time.time()
    def is_opened(self): return True
    def release(self): self.stop()
    def start(self):
        self.started = True
        return self
    def stop(self): self.started = False
    def read(self):
        t = time.time() - self.t0
        frame = np.full((720, 1280, 3), (25, 20, 35), dtype=np.uint8)
        cv2.putText(frame, "POSES LOCAS AR - MODO DEMO", (330, 320), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "Camara web no detectada. Conecte su camara USB.", (320, 380), cv2.FONT_HERSHEY_DUPLEX, 0.7, (200, 200, 200), 1, cv2.LINE_AA)
        r = int(25 + 10 * math.sin(t * 4))
        cv2.circle(frame, (640, 480), r, (0, 255, 0), -1, cv2.LINE_AA)
        return True, frame

class VideoCaptureAsync:
    def __init__(self, src=0):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        if isinstance(self.src, int):
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.grabbed = False
        self.frame = None
        for _ in range(15):
            if self.cap.isOpened():
                self.grabbed, self.frame = self.cap.read()
                if self.grabbed and self.frame is not None:
                    break
            time.sleep(0.08)
        self.started = False
        self.read_lock = threading.Lock()
    def is_opened(self): return self.cap.isOpened() and self.grabbed
    def release(self):
        if self.started: self.stop()
        self.cap.release()
    def start(self):
        if self.started: return self
        self.started = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self
    def update(self):
        while self.started:
            grabbed, frame = self.cap.read()
            with self.read_lock:
                self.grabbed = grabbed
                self.frame = frame
    def read(self):
        with self.read_lock:
            frame = self.frame.copy() if self.frame is not None else None
            grabbed = self.grabbed
        return grabbed, frame
    def stop(self):
        self.started = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=0.5)

# =============================================
# MEDIAPIPE SETUP
# =============================================
mp_pose = mp.solutions.pose
LM = mp_pose.PoseLandmark
NOSE = LM.NOSE
L_EAR = LM.RIGHT_EAR
R_EAR = LM.LEFT_EAR

L_SHOULDER = LM.RIGHT_SHOULDER
R_SHOULDER = LM.LEFT_SHOULDER
L_ELBOW = LM.RIGHT_ELBOW
R_ELBOW = LM.LEFT_ELBOW
L_WRIST = LM.RIGHT_WRIST
R_WRIST = LM.LEFT_WRIST
L_HIP = LM.RIGHT_HIP
R_HIP = LM.LEFT_HIP

SKELETON_CONNECTIONS = [
    (L_SHOULDER, R_SHOULDER), (L_SHOULDER, L_HIP), (R_SHOULDER, R_HIP),
    (L_HIP, R_HIP), (L_SHOULDER, NOSE), (R_SHOULDER, NOSE)
]
LEFT_ARM_CONNECTIONS = [(L_SHOULDER, L_ELBOW), (L_ELBOW, L_WRIST)]
RIGHT_ARM_CONNECTIONS = [(R_SHOULDER, R_ELBOW), (R_ELBOW, R_WRIST)]

# =============================================
# MOTOR ANATÓMICO (NORMALIZACIÓN BODYUNIT Y SCORES)
# =============================================
def get_body_unit(lm):
    """
    Distancia euclidiana entre hombros (BodyUnit). Invariante a estatura y distancia a camara.
    """
    dx = lm[L_SHOULDER].x - lm[R_SHOULDER].x
    dy = lm[L_SHOULDER].y - lm[R_SHOULDER].y
    return max(0.10, math.hypot(dx, dy))

def calc_angle_2d(lm, a_id, b_id, c_id):
    """Angulo articular en grados (0..180) en el vertice b_id."""
    ax, ay = lm[a_id].x, lm[a_id].y
    bx, by = lm[b_id].x, lm[b_id].y
    cx, cy = lm[c_id].x, lm[c_id].y
    rad = math.atan2(cy - by, cx - bx) - math.atan2(ay - by, ax - bx)
    ang = abs(math.degrees(rad))
    return 360.0 - ang if ang > 180.0 else ang

def distance_to_score(dist_val, target_dist, tolerance):
    """Convierte un error de distancia en score continuo [0.0, 1.0]."""
    if dist_val <= target_dist:
        return 1.0
    over = dist_val - target_dist
    return max(0.0, 1.0 - (over / max(1e-5, tolerance)))

def score_to_traffic_color(score):
    """Interpola en BGR: Rojo (0.0) -> Ambar (0.5) -> Verde Neon (1.0)."""
    s = max(0.0, min(1.0, float(score)))
    if s < 0.5:
        t = s / 0.5
        return (int(50 * (1 - t)), int(50 + 160 * t), 255)
    else:
        t = (s - 0.5) / 0.5
        return (int(80 * t), int(210 + 45 * t), int(255 * (1 - t)))

# =============================================
# CHECKS ESTÁTICOS (BOOLEANOS Y CONTINUOS)
# =============================================
def check_left_arm_up(lm): return lm[L_WRIST].y < lm[NOSE].y - 0.05
def check_right_arm_up(lm): return lm[R_WRIST].y < lm[NOSE].y - 0.05
def check_left_arm_down(lm): return lm[L_WRIST].y > lm[L_SHOULDER].y + 0.05
def check_right_arm_down(lm): return lm[R_WRIST].y > lm[R_SHOULDER].y + 0.05
def check_left_arm_horizontal(lm): return abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.12 and lm[L_WRIST].x < lm[L_SHOULDER].x - 0.08
def check_right_arm_horizontal(lm): return abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.12 and lm[R_WRIST].x > lm[R_SHOULDER].x + 0.08
def check_left_hand_on_hip(lm): return abs(lm[L_WRIST].x - lm[L_HIP].x) < 0.15 and abs(lm[L_WRIST].y - lm[L_HIP].y) < 0.15
def check_right_hand_on_hip(lm): return abs(lm[R_WRIST].x - lm[R_HIP].x) < 0.15 and abs(lm[R_WRIST].y - lm[R_HIP].y) < 0.15
def check_left_hand_on_head(lm): return (abs(lm[L_WRIST].x - lm[NOSE].x) < 0.12 or abs(lm[L_WRIST].x - lm[L_EAR].x) < 0.12) and (abs(lm[L_WRIST].y - lm[NOSE].y) < 0.12 or abs(lm[L_WRIST].y - lm[L_EAR].y) < 0.12)
def check_right_hand_on_head(lm): return (abs(lm[R_WRIST].x - lm[NOSE].x) < 0.12 or abs(lm[R_WRIST].x - lm[R_EAR].x) < 0.12) and (abs(lm[R_WRIST].y - lm[NOSE].y) < 0.12 or abs(lm[R_WRIST].y - lm[R_EAR].y) < 0.12)
def check_left_bicep(lm): return abs(lm[L_WRIST].x - lm[L_SHOULDER].x) < 0.10 and abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.15 and lm[L_ELBOW].x < lm[L_SHOULDER].x - 0.05
def check_right_bicep(lm): return abs(lm[R_WRIST].x - lm[R_SHOULDER].x) < 0.10 and abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.15 and lm[R_ELBOW].x > lm[R_SHOULDER].x + 0.05
def check_right_salute(lm): return abs(lm[R_WRIST].x - lm[R_EAR].x) < 0.12 and abs(lm[R_WRIST].y - lm[R_EAR].y) < 0.12

# Nuevas poses recuperadas y expresivas
def check_left_arm_y(lm): return lm[L_WRIST].y < lm[NOSE].y and lm[L_WRIST].x < lm[L_SHOULDER].x - 0.10
def check_right_arm_y(lm): return lm[R_WRIST].y < lm[NOSE].y and lm[R_WRIST].x > lm[R_SHOULDER].x + 0.10
def check_left_arm_o(lm): return lm[L_WRIST].y < lm[NOSE].y - 0.05 and abs(lm[L_WRIST].x - lm[NOSE].x) < 0.12
def check_right_arm_o(lm): return lm[R_WRIST].y < lm[NOSE].y - 0.05 and abs(lm[R_WRIST].x - lm[NOSE].x) < 0.12

def check_monkey_left(lm):
    bu = get_body_unit(lm)
    near_shoulder = math.hypot(lm[L_WRIST].x - lm[L_SHOULDER].x, lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.45 * bu
    elbow_out = lm[L_ELBOW].x < lm[L_SHOULDER].x - 0.25 * bu
    return near_shoulder and elbow_out

def check_monkey_right(lm):
    bu = get_body_unit(lm)
    near_shoulder = math.hypot(lm[R_WRIST].x - lm[R_SHOULDER].x, lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.45 * bu
    elbow_out = lm[R_ELBOW].x > lm[R_SHOULDER].x + 0.25 * bu
    return near_shoulder and elbow_out

def check_airplane_left(lm):
    return check_left_arm_horizontal(lm) and (lm[L_SHOULDER].y - lm[R_SHOULDER].y > 0.04)

def check_airplane_right(lm):
    return check_right_arm_horizontal(lm) and (lm[L_SHOULDER].y - lm[R_SHOULDER].y > 0.04)

# Evaluador de score continuo para iluminar el esqueleto en semaforo
def score_arm(check_fn, lm):
    if check_fn(lm):
        return 1.0
    # Si la funcion fallo, medimos proximidad aproximada segun tipo
    bu = get_body_unit(lm)
    if 'up' in check_fn.__name__:
        wrist = lm[L_WRIST] if 'left' in check_fn.__name__ else lm[R_WRIST]
        target_y = lm[NOSE].y - 0.05
        return distance_to_score(wrist.y, target_y, 0.6 * bu)
    elif 'horizontal' in check_fn.__name__:
        wrist = lm[L_WRIST] if 'left' in check_fn.__name__ else lm[R_WRIST]
        shoulder = lm[L_SHOULDER] if 'left' in check_fn.__name__ else lm[R_SHOULDER]
        return distance_to_score(abs(wrist.y - shoulder.y), 0.12, 0.4 * bu)
    return 0.35

# =============================================
# CHECKS DINÁMICOS (HISTORIAL Y ESTADO)
# =============================================
class PlayerState:
    def __init__(self):
        self.reset()
    def reset(self):
        self.hip_hits = 0
        self.last_hit_side = None
        self.center_x = None
        self.center_y = None
        self.jump_phase = 0
        self.spin_phase = 0
        self.arm_hits = 0
        self.last_arm_pos = None
        self.move_hits = 0
        self.last_move_pos = None
        self.freeze_reference = None
        self.initial_shoulder_order = None
        self.spin_start_time = 0
        self.global_center_x = None
        self.global_last_side = None
        self.last_groove_time = 0

def check_shake_hips(state, lm):
    events = []
    hip_x = (lm[L_HIP].x + lm[R_HIP].x) / 2.0
    hip_y = (lm[L_HIP].y + lm[R_HIP].y) / 2.0
    
    if state.center_x is None:
        state.center_x = hip_x
    else:
        state.center_x = state.center_x * 0.98 + hip_x * 0.02
        
    threshold = 0.025
    if hip_x > state.center_x + threshold and state.last_hit_side != 'right':
        state.last_hit_side = 'right'
        state.hip_hits += 1
        events.append({'type': 'hit', 'side': 'right', 'x': hip_x, 'y': hip_y})
    elif hip_x < state.center_x - threshold and state.last_hit_side != 'left':
        state.last_hit_side = 'left'
        state.hip_hits += 1
        events.append({'type': 'hit', 'side': 'left', 'x': hip_x, 'y': hip_y})
        
    completed = state.hip_hits >= 6
    return completed, events

def check_shake_head(state, lm):
    events = []
    nose_x = lm[NOSE].x
    nose_y = lm[NOSE].y
    if state.center_x is None:
        state.center_x = nose_x
    else:
        state.center_x = state.center_x * 0.96 + nose_x * 0.04
        
    threshold = 0.020
    if nose_x > state.center_x + threshold and state.last_hit_side != 'right':
        state.last_hit_side = 'right'
        state.hip_hits += 1
        events.append({'type': 'hit', 'side': 'right', 'x': nose_x, 'y': nose_y})
    elif nose_x < state.center_x - threshold and state.last_hit_side != 'left':
        state.last_hit_side = 'left'
        state.hip_hits += 1
        events.append({'type': 'hit', 'side': 'left', 'x': nose_x, 'y': nose_y})
    completed = state.hip_hits >= 6
    return completed, events

def check_jump(state, lm):
    events = []
    hip_y = (lm[L_HIP].y + lm[R_HIP].y) / 2.0
    if state.center_y is None:
        state.center_y = hip_y
    else:
        if state.jump_phase == 0:
            state.center_y = state.center_y * 0.95 + hip_y * 0.05
            
    threshold = 0.08
    if state.jump_phase == 0:
        if hip_y < state.center_y - threshold:
            state.jump_phase = 1
            events.append({'type': 'hit', 'side': 'center', 'x': 0.5, 'y': hip_y})
    elif state.jump_phase == 1:
        if hip_y > state.center_y - 0.02:
            state.jump_phase = 2
            
    completed = state.jump_phase >= 2
    return completed, events

def check_squat(state, lm):
    events = []
    hip_y = (lm[L_HIP].y + lm[R_HIP].y) / 2.0
    if state.center_y is None:
        state.center_y = hip_y
    else:
        if state.jump_phase == 0:
            state.center_y = state.center_y * 0.995 + hip_y * 0.005
            
    threshold = 0.12
    if state.jump_phase == 0:
        if hip_y > state.center_y + threshold:
            state.jump_phase = 1
            events.append({'type': 'hit', 'side': 'center', 'x': 0.5, 'y': hip_y})
    elif state.jump_phase == 1:
        if hip_y < state.center_y + 0.02:
            state.jump_phase = 2
            
    completed = state.jump_phase >= 2
    return completed, events

def check_spin(state, lm):
    events = []
    left_is_right_of_right = lm[L_SHOULDER].x > lm[R_SHOULDER].x
    if getattr(state, 'initial_shoulder_order', None) is None:
        state.initial_shoulder_order = left_is_right_of_right
        state.spin_start_time = time.time()
        
    if state.spin_phase == 0:
        if left_is_right_of_right != state.initial_shoulder_order:
            state.spin_phase = 1
        elif lm[L_SHOULDER].visibility < 0.2 and lm[R_SHOULDER].visibility < 0.2:
            state.spin_phase = 1
    elif state.spin_phase == 1:
        if time.time() - state.spin_start_time > 0.35:
            if left_is_right_of_right == state.initial_shoulder_order and lm[L_SHOULDER].visibility > 0.4 and lm[R_SHOULDER].visibility > 0.4:
                state.spin_phase = 2
                events.append({'type': 'hit', 'side': 'center', 'x': lm[NOSE].x, 'y': lm[NOSE].y})
            
    completed = state.spin_phase >= 2
    return completed, events

def check_flail_arms(state, lm):
    events = []
    l_arm_up = lm[L_WRIST].y < lm[L_SHOULDER].y
    r_arm_up = lm[R_WRIST].y < lm[R_SHOULDER].y
    current_pos = 'up' if (l_arm_up and r_arm_up) else ('down' if not l_arm_up and not r_arm_up else 'mid')
    if state.last_arm_pos is None:
        state.last_arm_pos = current_pos
        
    if current_pos == 'up' and state.last_arm_pos != 'up':
        state.last_arm_pos = 'up'
        state.arm_hits += 1
        events.append({'type': 'hit', 'side': 'up', 'x': 0.5, 'y': 0.2})
    elif current_pos == 'down' and state.last_arm_pos != 'down':
        state.last_arm_pos = 'down'
        state.arm_hits += 1
        events.append({'type': 'hit', 'side': 'down', 'x': 0.5, 'y': 0.8})
        
    completed = state.arm_hits >= 6
    return completed, events

def check_move_side_to_side(state, lm):
    events = []
    nose_x = lm[NOSE].x
    if state.center_x is None:
        state.center_x = nose_x
    else:
        state.center_x = state.center_x * 0.99 + nose_x * 0.01
        
    threshold = 0.12
    if nose_x > state.center_x + threshold and state.last_hit_side != 'right':
        state.last_hit_side = 'right'
        state.move_hits += 1
        events.append({'type': 'hit', 'side': 'right', 'x': nose_x, 'y': lm[NOSE].y})
    elif nose_x < state.center_x - threshold and state.last_hit_side != 'left':
        state.last_hit_side = 'left'
        state.move_hits += 1
        events.append({'type': 'hit', 'side': 'left', 'x': nose_x, 'y': lm[NOSE].y})
        
    completed = state.move_hits >= 4
    return completed, events

def check_boxer_jabs(state, lm):
    events = []
    bu = get_body_unit(lm)
    diff_y = lm[L_WRIST].y - lm[R_WRIST].y
    if abs(diff_y) > 0.18 * bu:
        curr = 'left_jab' if diff_y < 0 else 'right_jab'
        if state.last_arm_pos != curr:
            state.last_arm_pos = curr
            state.arm_hits += 1
            pt = lm[L_WRIST] if curr == 'left_jab' else lm[R_WRIST]
            events.append({'type': 'hit', 'side': curr, 'x': pt.x, 'y': pt.y})
    completed = state.arm_hits >= 6
    return completed, events

def check_air_guitar(state, lm):
    events = []
    # Una mano alta (mastil) y otra rasgueando cerca de cadera
    bu = get_body_unit(lm)
    hand_y = lm[R_WRIST].y
    if state.last_arm_pos is None:
        state.last_arm_pos = hand_y
    if abs(hand_y - state.last_arm_pos) > 0.15 * bu:
        state.last_arm_pos = hand_y
        state.arm_hits += 1
        events.append({'type': 'hit', 'side': 'guitar', 'x': lm[R_WRIST].x, 'y': lm[R_WRIST].y})
    completed = state.arm_hits >= 6
    return completed, events

def check_hand_head_shake_hips(state, lm):
    hand_on_head = check_left_hand_on_head(lm) or check_right_hand_on_head(lm)
    if not hand_on_head: return False, []
    return check_shake_hips(state, lm)

def check_jump_arms_up(state, lm):
    arms_up = check_left_arm_up(lm) and check_right_arm_up(lm)
    if not arms_up: return False, []
    return check_jump(state, lm)

def check_spin_hand_head(state, lm):
    hand_on_head = check_left_hand_on_head(lm) or check_right_hand_on_head(lm)
    if not hand_on_head: return False, []
    return check_spin(state, lm)

def check_gesture_next(lm):
    l_cross = abs(lm[L_WRIST].x - lm[R_SHOULDER].x) < 0.15 and abs(lm[L_WRIST].y - lm[R_SHOULDER].y) < 0.15
    r_cross = abs(lm[R_WRIST].x - lm[L_SHOULDER].x) < 0.15 and abs(lm[R_WRIST].y - lm[L_SHOULDER].y) < 0.15
    return l_cross and r_cross

# =============================================
# UTILIDADES GRÁFICAS Y CARGADOR DE ILUSTRACIONES
# =============================================
def blend_rect_roi(frame, x, y, w, h, bgr_color, alpha=0.6):
    fh, fw = frame.shape[:2]
    x1, y1 = max(0, int(x)), max(0, int(y))
    x2, y2 = min(fw, int(x + w)), min(fh, int(y + h))
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    rect = np.full_like(roi, bgr_color, dtype=np.uint8)
    cv2.addWeighted(rect, alpha, roi, 1.0 - alpha, 0, roi)

ICON_CACHE = {}
def load_pose_illustration_clean(filename_no_ext, size=(160, 160), bg_color=(30, 25, 38)):
    cache_key = (filename_no_ext, size, bg_color)
    if cache_key in ICON_CACHE:
        return ICON_CACHE[cache_key]
    path = f"{filename_no_ext}.jpg"
    if not os.path.exists(path):
        ICON_CACHE[cache_key] = None
        return None
    img = cv2.imread(path)
    if img is None:
        ICON_CACHE[cache_key] = None
        return None
    img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners = [int(gray[0, 0]), int(gray[0, -1]), int(gray[-1, 0]), int(gray[-1, -1])]
    bg_brightness = sum(corners) / 4.0
    if bg_brightness > 200:
        _, mask = cv2.threshold(gray, 238, 255, cv2.THRESH_BINARY_INV)
    else:
        _, mask = cv2.threshold(gray, 22, 255, cv2.THRESH_BINARY)
    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    alpha = (mask.astype(np.float32) / 255.0)[..., None]
    bg_card = np.full_like(img, bg_color, dtype=np.uint8)
    res = (img.astype(np.float32) * alpha + bg_card.astype(np.float32) * (1.0 - alpha)).astype(np.uint8)
    ICON_CACHE[cache_key] = res
    return res

def draw_star_icon(frame, cx, cy, r, color):
    pts = np.array([
        [cx, cy - r], [cx + r // 3, cy - r // 3], [cx + r, cy],
        [cx + r // 3, cy + r // 3], [cx, cy + r], [cx - r // 3, cy + r // 3],
        [cx - r, cy], [cx - r // 3, cy - r // 3]
    ], np.int32)
    cv2.fillPoly(frame, [pts], color, cv2.LINE_AA)

def draw_bolt_icon(frame, cx, cy, r, color):
    pts = np.array([
        [cx + 3, cy - r], [cx - r + 2, cy + 2], [cx - 1, cy + 2],
        [cx - 3, cy + r], [cx + r - 2, cy - 2], [cx + 1, cy - 2]
    ], np.int32)
    cv2.fillPoly(frame, [pts], color, cv2.LINE_AA)

SONG_BPM = {
    'macarena.wav': 103,
    'macarena_real.wav': 103,
    'macarena_vocal.wav': 103,
    'asereje.wav': 106,
    'ymca.wav': 127,
    'danza_kuduro.wav': 130,
    'waka_waka.wav': 127,
    'despacito.wav': 89,
}
def get_beat_pulse(current_time, song_name):
    bpm = SONG_BPM.get(song_name, 110)
    beats_per_sec = bpm / 60.0
    phase = (current_time * beats_per_sec) % 1.0
    return math.exp(-phase * 4.5)

# =============================================
# COACH VIVO CON PIERNAS, PISO Y FLECHAS DE INTENCIÓN
# =============================================
def draw_full_body_stickman(frame, x, y, w, h, pts, arm_color, body_color=(210, 210, 220), show_floor=True):
    def p(key):
        nx, ny = pts[key]
        return (int(x + nx * w), int(y + ny * h))

    if show_floor:
        fy = int(y + h * 0.92)
        cv2.line(frame, (int(x + w * 0.12), fy), (int(x + w * 0.88), fy), (90, 90, 115), 2, cv2.LINE_AA)

    torso_conns = [('ls', 'rs'), ('ls', 'lh'), ('rs', 'rh'), ('lh', 'rh')]
    leg_conns = [('lh', 'lk'), ('lk', 'la'), ('rh', 'rk'), ('rk', 'ra')]
    arm_conns = [('ls', 'le'), ('le', 'lw'), ('rs', 're'), ('re', 'rw')]

    if all(k in pts for k in ['ls', 'rs', 'rh', 'lh']):
        poly = np.array([p('ls'), p('rs'), p('rh'), p('lh')], np.int32)
        cv2.fillPoly(frame, [poly], (55, 55, 75))

    for a, b in torso_conns + leg_conns:
        if a in pts and b in pts:
            cv2.line(frame, p(a), p(b), body_color, 3, cv2.LINE_AA)
    for a, b in arm_conns:
        if a in pts and b in pts:
            cv2.line(frame, p(a), p(b), arm_color, 5, cv2.LINE_AA)
            cv2.line(frame, p(a), p(b), (255, 255, 255), 2, cv2.LINE_AA)

    for k in ['lw', 'rw']:
        if k in pts:
            cv2.circle(frame, p(k), 5, arm_color, -1, cv2.LINE_AA)
            cv2.circle(frame, p(k), 2, (255, 255, 255), -1, cv2.LINE_AA)

    if 'nose' in pts:
        r_head = max(7, int(w * 0.08))
        cv2.circle(frame, p('nose'), r_head, arm_color, 2, cv2.LINE_AA)
        cv2.circle(frame, p('nose'), max(3, r_head - 4), (240, 240, 255), -1, cv2.LINE_AA)

def get_animated_ref_points(pose_data, t):
    base_ref = pose_data.get('ref', {})
    pts = {}
    key_map = {NOSE: 'nose', L_SHOULDER: 'ls', R_SHOULDER: 'rs', L_ELBOW: 'le', R_ELBOW: 're', L_WRIST: 'lw', R_WRIST: 'rw', L_HIP: 'lh', R_HIP: 'rh'}
    for k, v in base_ref.items():
        if k in key_map:
            pts[key_map[k]] = (float(v[0]), float(v[1]))
            
    lh = pts.get('lh', (0.42, 0.60))
    rh = pts.get('rh', (0.58, 0.60))
    name = pose_data.get('name', '')

    if 'Caderas' in name:
        sway = math.sin(t * 7.0) * 0.09
        pts['lh'] = (lh[0] + sway, lh[1])
        pts['rh'] = (rh[0] + sway, rh[1])
    elif 'Lado a Lado' in name:
        step = math.sin(t * 4.5) * 0.14
        for k in list(pts.keys()): pts[k] = (pts[k][0] + step, pts[k][1])
    elif 'Salto' in name:
        bounce = -abs(math.sin(t * 5.5)) * 0.16
        for k in list(pts.keys()): pts[k] = (pts[k][0], pts[k][1] + bounce)
    elif 'Agacharse' in name:
        squat_down = abs(math.sin(t * 4.0)) * 0.16
        for k in list(pts.keys()): pts[k] = (pts[k][0], pts[k][1] + squat_down)
    elif 'Mueve los Brazos' in name:
        wave = math.sin(t * 8.0) * 0.20
        if 'lw' in pts: pts['lw'] = (pts['lw'][0], 0.30 + wave)
        if 'rw' in pts: pts['rw'] = (pts['rw'][0], 0.30 - wave)
    elif 'Gir' in name:
        spin_cos = math.cos(t * 4.5)
        for k in list(pts.keys()):
            dx = pts[k][0] - 0.5
            pts[k] = (0.5 + dx * spin_cos, pts[k][1])
    elif 'Boxeo' in name:
        jab = math.sin(t * 10.0) * 0.10
        if 'lw' in pts: pts['lw'] = (0.38 - jab, 0.24 - abs(jab)*0.2)
        if 'rw' in pts: pts['rw'] = (0.62 + jab, 0.24 - abs(jab)*0.2)

    lh_now = pts.get('lh', (0.42, 0.60))
    rh_now = pts.get('rh', (0.58, 0.60))
    is_squat = 'Agacharse' in name
    spread = 0.08 if is_squat else 0.0
    foot_y = 0.90 if 'Salto' not in name else min(0.90, lh_now[1] + 0.26)
    knee_y = (lh_now[1] + foot_y) * 0.5

    pts['lk'] = (lh_now[0] - spread, knee_y)
    pts['rk'] = (rh_now[0] + spread, knee_y)
    pts['la'] = (0.38, foot_y)
    pts['ra'] = (0.62, foot_y)
    return pts

def draw_intent_arrows_in_box(frame, pose_data, box_x, box_y, box_w, box_h, t):
    name = pose_data.get('name', '')
    col = pose_data.get('color', (0, 255, 255))
    cx = box_x + box_w // 2
    cy = box_y + box_h // 2
    if 'Caderas' in name or 'Lado a Lado' in name:
        y_arr = box_y + int(box_h * 0.62)
        off = int(math.sin(t * 7.0) * 7)
        cv2.arrowedLine(frame, (cx - 15 + off, y_arr), (box_x + 15, y_arr), col, 3, tipLength=0.4)
        cv2.arrowedLine(frame, (cx + 15 + off, y_arr), (box_x + box_w - 15, y_arr), col, 3, tipLength=0.4)
    elif 'Salto' in name:
        cv2.arrowedLine(frame, (box_x + 20, cy + 20), (box_x + 20, box_y + 20), (0, 255, 120), 3, tipLength=0.4)
        cv2.arrowedLine(frame, (box_x + box_w - 20, cy + 20), (box_x + box_w - 20, box_y + 20), (0, 255, 120), 3, tipLength=0.4)
    elif 'Agacharse' in name:
        cv2.arrowedLine(frame, (box_x + 20, box_y + 30), (box_x + 20, cy + 30), (100, 180, 255), 3, tipLength=0.4)
        cv2.arrowedLine(frame, (box_x + box_w - 20, box_y + 30), (box_x + box_w - 20, cy + 30), (100, 180, 255), 3, tipLength=0.4)
    elif 'Gir' in name:
        cv2.ellipse(frame, (cx, cy + 15), (box_w // 3, 16), 0, -20, 240, (0, 215, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, "360", (cx - 20, box_y + box_h - 15), cv2.FONT_HERSHEY_DUPLEX, 0.60, (0, 215, 255), 1, cv2.LINE_AA)

# =============================================
# AR ANCHORED GHOST SILHOUETTE & ANILLOS MAGNÉTICOS
# =============================================
def compute_body_anchored_targets(lm, pose_data, display_w, display_h):
    ref = pose_data.get('ref')
    if not ref or L_SHOULDER not in ref or R_SHOULDER not in ref:
        return {}
    if lm[L_SHOULDER].visibility < 0.35 or lm[R_SHOULDER].visibility < 0.35:
        return {}

    p_ls = (lm[L_SHOULDER].x * display_w, lm[L_SHOULDER].y * display_h)
    p_rs = (lm[R_SHOULDER].x * display_w, lm[R_SHOULDER].y * display_h)
    player_cx = (p_ls[0] + p_rs[0]) / 2.0
    player_cy = (p_ls[1] + p_rs[1]) / 2.0
    player_sw = max(40.0, math.hypot(p_rs[0] - p_ls[0], p_rs[1] - p_ls[1]))

    r_ls = ref[L_SHOULDER]
    r_rs = ref[R_SHOULDER]
    ref_cx = (r_ls[0] + r_rs[0]) / 2.0
    ref_cy = (r_ls[1] + r_rs[1]) / 2.0
    ref_sw = max(0.08, math.hypot(r_rs[0] - r_ls[0], r_rs[1] - r_ls[1]))

    scale = player_sw / ref_sw
    anchored = {}
    for lm_id, (rx, ry) in ref.items():
        ax = int(player_cx + (rx - ref_cx) * scale)
        ay = int(player_cy + (ry - ref_cy) * scale * 0.95)
        anchored[lm_id] = (max(10, min(display_w - 10, ax)), max(10, min(display_h - 10, ay)))
    return anchored

def draw_ghost_and_target_rings(frame, lm, pose_data, display_w, display_h, left_score, right_score):
    if pose_data.get('is_freeze'):
        return
    anchored = compute_body_anchored_targets(lm, pose_data, display_w, display_h)
    if not anchored:
        return

    ghost_col = (255, 220, 100)
    for a, b in LEFT_ARM_CONNECTIONS + RIGHT_ARM_CONNECTIONS:
        if a in anchored and b in anchored:
            cv2.line(frame, anchored[a], anchored[b], ghost_col, 4, cv2.LINE_AA)

    pulse = int(math.sin(time.time() * 8.0) * 3)
    for wrist_id, s in [(L_WRIST, left_score), (R_WRIST, right_score)]:
        if wrist_id in anchored:
            tx, ty = anchored[wrist_id]
            col = (0, 255, 100) if s >= 0.85 else ((0, 200, 255) if s >= 0.45 else ghost_col)
            r = max(14, (24 + pulse if s < 0.85 else 18))
            cv2.circle(frame, (tx, ty), r, col, 3, cv2.LINE_AA)
            cv2.circle(frame, (tx, ty), 4, col, -1, cv2.LINE_AA)

            pt_real = get_point(lm, wrist_id, display_w, display_h)
            if pt_real and s < 0.85:
                cv2.arrowedLine(frame, pt_real, (tx, ty), (0, 200, 255), 2, cv2.LINE_AA, tipLength=0.25)

# =============================================
# ESQUELETO SEMÁFORO Y ESTELAS DE ENERGÍA
# =============================================
def get_point(lm, lm_id, w, h):
    return (int(lm[lm_id].x * w), int(lm[lm_id].y * h)) if lm[lm_id].visibility > 0.35 else None

class HandTrailSystem:
    def __init__(self, maxlen=8):
        self.left_trail = deque(maxlen=maxlen)
        self.right_trail = deque(maxlen=maxlen)
    def update_and_draw(self, frame, lm, display_w, display_h, left_col, right_col):
        lp = get_point(lm, L_WRIST, display_w, display_h)
        rp = get_point(lm, R_WRIST, display_w, display_h)
        if lp: self.left_trail.append(lp)
        elif self.left_trail: self.left_trail.popleft()
        if rp: self.right_trail.append(rp)
        elif self.right_trail: self.right_trail.popleft()

        for trail, col in [(self.left_trail, left_col), (self.right_trail, right_col)]:
            pts = list(trail)
            for i in range(1, len(pts)):
                th = max(2, int((i / len(pts)) * 12))
                cv2.line(frame, pts[i - 1], pts[i], col, th, cv2.LINE_AA)

def draw_skeleton_with_feedback(frame, lm, display_w, display_h, left_ok, right_ok, left_score=None, right_score=None):
    COLOR_BODY = (255, 255, 0)
    # Soporte retrocompatible: si no se pasan scores continuos, se derivan de left_ok/right_ok
    ls = left_score if left_score is not None else (1.0 if left_ok else 0.0)
    rs = right_score if right_score is not None else (1.0 if right_ok else 0.0)

    left_color = score_to_traffic_color(ls)
    right_color = score_to_traffic_color(rs)

    points = {lm_id: pt for lm_id in [NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP]
              if (pt := get_point(lm, lm_id, display_w, display_h))}

    # Glow Overlay
    overlay = frame.copy()
    for a, b in SKELETON_CONNECTIONS:
        if a in points and b in points: cv2.line(overlay, points[a], points[b], COLOR_BODY, 12, cv2.LINE_AA)
    for a, b in LEFT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(overlay, points[a], points[b], left_color, 16, cv2.LINE_AA)
    for a, b in RIGHT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(overlay, points[a], points[b], right_color, 16, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

    # Core lines
    for a, b in SKELETON_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (255, 255, 255), 3, cv2.LINE_AA)
    for a, b in LEFT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (255, 255, 255), 4, cv2.LINE_AA)
    for a, b in RIGHT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (255, 255, 255), 4, cv2.LINE_AA)

    # Joints
    pulse = int(math.sin(time.time() * 9.0) * 4)
    for lm_id, pt in points.items():
        col = left_color if lm_id in [L_SHOULDER, L_ELBOW, L_WRIST] else (right_color if lm_id in [R_SHOULDER, R_ELBOW, R_WRIST] else COLOR_BODY)
        base_r = 13 if (lm_id in [L_WRIST, R_WRIST] and (ls >= 0.85 or rs >= 0.85)) else 8
        r = max(4, base_r + pulse)
        cv2.circle(frame, pt, r + 3, col, -1, cv2.LINE_AA)
        cv2.circle(frame, pt, r, (255, 255, 255), -1, cv2.LINE_AA)

    if NOSE in points:
        cv2.circle(frame, points[NOSE], max(14, 20 + pulse), COLOR_BODY, 3, cv2.LINE_AA)

class ParticleSystem:
    def __init__(self): self.particles = []
    def emit_confetti(self, display_w, gold_only=False):
        colors = [(0, 215, 255), (0, 240, 255)] if gold_only else [(0,255,100), (255,200,0), (0,200,255), (255,0,200), (255,255,0)]
        for _ in range(45):
            self.particles.append({
                'x': float(random.randint(0, display_w)), 'y': float(random.randint(-40, 0)),
                'dx': random.uniform(-2.5, 2.5), 'dy': random.uniform(3, 8),
                'life': random.randint(30, 60), 'color': random.choice(colors), 'size': random.randint(4, 9)
            })
    def emit(self, x, y, color, count=20):
        for _ in range(count):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(3, 14)
            self.particles.append({
                'x': float(x), 'y': float(y), 'dx': math.cos(ang) * spd, 'dy': math.sin(ang) * spd,
                'life': random.randint(15, 32), 'color': color, 'size': random.randint(3, 7)
            })
    def update_and_draw(self, frame):
        for p in self.particles[:]:
            p['x'] += p['dx']; p['y'] += p['dy']; p['dy'] += 0.3; p['life'] -= 1
            if p['life'] <= 0: self.particles.remove(p)
            else:
                sz = max(2, int(p['size'] * p['life'] / 30))
                cv2.circle(frame, (int(p['x']), int(p['y'])), sz, p['color'], -1, cv2.LINE_AA)

class FloatingText:
    def __init__(self): self.texts = []
    def add(self, text, x, y, color, scale=1.4):
        self.texts.append({'text': text, 'x': x, 'y': float(y), 'color': color, 'life': 42, 'scale': scale})
    def update_and_draw(self, frame):
        for t in self.texts[:]:
            t['y'] -= 1.8; t['life'] -= 1
            if t['life'] <= 0: self.texts.remove(t)
            else:
                cv2.putText(frame, t['text'], (int(t['x'])+2, int(t['y'])+2), cv2.FONT_HERSHEY_DUPLEX, t['scale'], (0,0,0), int(t['scale']*3)+1, cv2.LINE_AA)
                cv2.putText(frame, t['text'], (int(t['x']), int(t['y'])), cv2.FONT_HERSHEY_DUPLEX, t['scale'], t['color'], max(1, int(t['scale']*2)), cv2.LINE_AA)

def draw_progress_bar(frame, x, y, w, h, progress, color):
    cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 65), -1)
    if int(w * progress) > 0:
        cv2.rectangle(frame, (x, y), (x + int(w * progress), y + h), color, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)

# =============================================
# CATÁLOGO EXPANDIDO DE POSES (18 POSES + ILUSTRACIONES)
# =============================================
POSES = [
    # --- Dinámicas ---
    {
        'name': 'Baila! Mueve Caderas', 'color': (255, 100, 180), 'icon_name': 'pose_caderas',
        'dynamic': True, 'checks': check_shake_hips,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.44), R_ELBOW: (0.74, 0.44), L_WRIST: (0.38, 0.60), R_WRIST: (0.62, 0.60), L_HIP: (0.34, 0.62), R_HIP: (0.50, 0.62) },
    },
    {
        'name': 'Mueve la Cabeza!', 'color': (140, 255, 80), 'icon_name': 'pose_cabeza',
        'dynamic': True, 'checks': check_shake_head,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.30, 0.45), R_ELBOW: (0.70, 0.45), L_WRIST: (0.35, 0.60), R_WRIST: (0.65, 0.60), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'Boxeo Rapido!', 'color': (80, 130, 255),
        'dynamic': True, 'checks': check_boxer_jabs,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.28, 0.42), R_ELBOW: (0.72, 0.30), L_WRIST: (0.42, 0.24), R_WRIST: (0.62, 0.16), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'Salto Mortal!', 'color': (80, 255, 120),
        'dynamic': True, 'checks': check_jump,
        'ref': { NOSE: (0.5, 0.08), L_SHOULDER: (0.36, 0.24), R_SHOULDER: (0.64, 0.24), L_ELBOW: (0.24, 0.15), R_ELBOW: (0.76, 0.15), L_WRIST: (0.18, 0.05), R_WRIST: (0.82, 0.05), L_HIP: (0.42, 0.48), R_HIP: (0.58, 0.48) },
    },
    {
        'name': 'Agacharse!', 'color': (100, 180, 255),
        'dynamic': True, 'checks': check_squat,
        'ref': { NOSE: (0.5, 0.34), L_SHOULDER: (0.36, 0.48), R_SHOULDER: (0.64, 0.48), L_ELBOW: (0.26, 0.62), R_ELBOW: (0.74, 0.62), L_WRIST: (0.35, 0.74), R_WRIST: (0.65, 0.74), L_HIP: (0.40, 0.72), R_HIP: (0.60, 0.72) },
    },
    {
        'name': 'Girando!', 'color': (255, 160, 0),
        'dynamic': True, 'checks': check_spin,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.46, 0.32), R_SHOULDER: (0.54, 0.32), L_ELBOW: (0.36, 0.46), R_ELBOW: (0.64, 0.46), L_WRIST: (0.32, 0.58), R_WRIST: (0.68, 0.58), L_HIP: (0.46, 0.62), R_HIP: (0.54, 0.62) },
    },
    {
        'name': 'Mueve los Brazos!', 'color': (255, 60, 255),
        'dynamic': True, 'checks': check_flail_arms,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.18), R_ELBOW: (0.74, 0.45), L_WRIST: (0.20, 0.05), R_WRIST: (0.80, 0.60), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'De Lado a Lado!', 'color': (50, 255, 255),
        'dynamic': True, 'checks': check_move_side_to_side,
        'ref': { NOSE: (0.68, 0.14), L_SHOULDER: (0.56, 0.32), R_SHOULDER: (0.80, 0.32), L_ELBOW: (0.48, 0.45), R_ELBOW: (0.90, 0.45), L_WRIST: (0.54, 0.60), R_WRIST: (0.86, 0.60), L_HIP: (0.60, 0.62), R_HIP: (0.76, 0.62) },
    },
    {
        'name': 'Guitarra Rock!', 'color': (0, 255, 120),
        'dynamic': True, 'checks': check_air_guitar,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.22, 0.36), R_ELBOW: (0.72, 0.46), L_WRIST: (0.10, 0.30), R_WRIST: (0.55, 0.56), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    
    # --- Estáticas con Ilustraciones pose_*.jpg ---
    {
        'name': 'Brazos Arriba!', 'color': (0, 255, 120), 'icon_name': 'pose_brazos',
        'checks': {'left_arm': check_left_arm_up, 'right_arm': check_right_arm_up},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.28, 0.18), R_ELBOW: (0.72, 0.18), L_WRIST: (0.32, 0.05), R_WRIST: (0.68, 0.05), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'T-Pose!', 'color': (255, 210, 0), 'icon_name': 'pose_tpose',
        'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_horizontal},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.22, 0.32), R_ELBOW: (0.78, 0.32), L_WRIST: (0.08, 0.32), R_WRIST: (0.92, 0.32), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'Fuerte!', 'color': (255, 110, 50), 'icon_name': 'pose_fuerte',
        'checks': {'left_arm': check_left_bicep, 'right_arm': check_right_bicep},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.22, 0.32), R_ELBOW: (0.78, 0.32), L_WRIST: (0.32, 0.20), R_WRIST: (0.68, 0.20), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'Saludo Militar!', 'color': (60, 120, 255), 'icon_name': 'pose_saludo',
        'checks': {'left_arm': check_left_arm_down, 'right_arm': check_right_salute},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.30, 0.45), R_ELBOW: (0.74, 0.30), L_WRIST: (0.32, 0.58), R_WRIST: (0.58, 0.14), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'Letra Y!', 'color': (255, 100, 220), 'icon_name': 'pose_letra_y',
        'checks': {'left_arm': check_left_arm_y, 'right_arm': check_right_arm_y},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.18), R_ELBOW: (0.74, 0.18), L_WRIST: (0.16, 0.05), R_WRIST: (0.84, 0.05), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'Letra O!', 'color': (100, 240, 255), 'icon_name': 'pose_letra_o',
        'checks': {'left_arm': check_left_arm_o, 'right_arm': check_right_arm_o},
        'ref': { NOSE: (0.5, 0.20), L_SHOULDER: (0.36, 0.36), R_SHOULDER: (0.64, 0.36), L_ELBOW: (0.30, 0.14), R_ELBOW: (0.70, 0.14), L_WRIST: (0.44, 0.04), R_WRIST: (0.56, 0.04), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'Pose de Mono!', 'color': (0, 200, 255),
        'checks': {'left_arm': check_monkey_left, 'right_arm': check_monkey_right},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.16, 0.35), R_ELBOW: (0.84, 0.35), L_WRIST: (0.36, 0.40), R_WRIST: (0.64, 0.40), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'Fiebre Disco!', 'color': (255, 90, 255),
        'checks': {'left_arm': check_left_hand_on_hip, 'right_arm': check_right_arm_up},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.24, 0.46), R_ELBOW: (0.74, 0.18), L_WRIST: (0.40, 0.58), R_WRIST: (0.86, 0.05), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
    {
        'name': 'Avion Supersonico!', 'color': (100, 255, 200),
        'checks': {'left_arm': check_airplane_left, 'right_arm': check_airplane_right},
        'ref': { NOSE: (0.48, 0.16), L_SHOULDER: (0.34, 0.36), R_SHOULDER: (0.62, 0.28), L_ELBOW: (0.18, 0.42), R_ELBOW: (0.76, 0.22), L_WRIST: (0.06, 0.48), R_WRIST: (0.92, 0.16), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
    },
]

COREOGRAFIAS = {
    'macarena.wav': [
        {'name': 'Brazo Der Adelante', 'checks': {'left_arm': check_left_arm_down, 'right_arm': check_right_arm_horizontal}, 'ref': {NOSE: (0.5, 0.14), R_SHOULDER: (0.62, 0.32), R_ELBOW: (0.8, 0.32), R_WRIST: (0.95, 0.32)}, 'color': (255, 200, 0)},
        {'name': 'Brazos Adelante', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_horizontal}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), L_ELBOW: (0.2, 0.32), L_WRIST: (0.05, 0.32), R_SHOULDER: (0.62, 0.32), R_ELBOW: (0.8, 0.32), R_WRIST: (0.95, 0.32)}, 'color': (255, 200, 0)},
        {'name': 'Mano Der Cabeza', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), L_WRIST: (0.05, 0.32), R_SHOULDER: (0.62, 0.32), R_WRIST: (0.55, 0.14)}, 'color': (255, 200, 0)},
        {'name': 'Manos en la Cabeza!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), L_WRIST: (0.45, 0.14), R_SHOULDER: (0.62, 0.32), R_WRIST: (0.55, 0.14)}, 'color': (255, 200, 0)},
        {'name': 'Mano Der Cintura', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_hip}, 'ref': {NOSE: (0.5, 0.14), L_WRIST: (0.45, 0.14), R_SHOULDER: (0.62, 0.32), R_WRIST: (0.58, 0.62), R_HIP: (0.58, 0.62)}, 'color': (255, 200, 0)},
        {'name': 'Manos Cintura!', 'checks': {'left_arm': check_left_hand_on_hip, 'right_arm': check_right_hand_on_hip}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), L_WRIST: (0.42, 0.62), L_HIP: (0.42, 0.62), R_SHOULDER: (0.62, 0.32), R_WRIST: (0.58, 0.62), R_HIP: (0.58, 0.62)}, 'color': (255, 200, 0)},
        {'name': 'Baila! Mueve Caderas', 'dynamic': True, 'checks': check_shake_hips, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.44), R_ELBOW: (0.74, 0.44), L_WRIST: (0.38, 0.60), R_WRIST: (0.62, 0.60), L_HIP: (0.34, 0.62), R_HIP: (0.50, 0.62)}, 'color': (255, 100, 180)},
        {'name': 'Girando!', 'dynamic': True, 'checks': check_spin, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.46, 0.32), R_SHOULDER: (0.54, 0.32), L_ELBOW: (0.36, 0.46), R_ELBOW: (0.64, 0.46), L_WRIST: (0.32, 0.58), R_WRIST: (0.68, 0.58), L_HIP: (0.46, 0.62), R_HIP: (0.54, 0.62)}, 'color': (255, 160, 0)}
    ],
    'asereje.wav': [
        {'name': 'Cruzando Abajo', 'checks': {'left_arm': lambda lm: check_gesture_next(lm), 'right_arm': lambda lm: check_gesture_next(lm)}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.45, 0.45), R_ELBOW: (0.55, 0.45), L_WRIST: (0.62, 0.32), R_WRIST: (0.38, 0.32), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62)}, 'color': (255, 100, 255)}, 
        {'name': 'Manos en la Cabeza!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.25, 0.20), R_ELBOW: (0.75, 0.20), L_WRIST: (0.45, 0.12), R_WRIST: (0.55, 0.12), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62)}, 'color': (100, 50, 255)},
        {'name': 'Baila! Mueve Caderas', 'dynamic': True, 'checks': check_shake_hips, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.44), R_ELBOW: (0.74, 0.44), L_WRIST: (0.38, 0.60), R_WRIST: (0.62, 0.60), L_HIP: (0.34, 0.62), R_HIP: (0.50, 0.62)}, 'color': (255, 100, 180)},
        {'name': 'Mueve los Brazos!', 'dynamic': True, 'checks': check_flail_arms, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.18), R_ELBOW: (0.74, 0.45), L_WRIST: (0.20, 0.05), R_WRIST: (0.80, 0.60), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62)}, 'color': (255, 50, 255)},
    ],
    'ymca.wav': [
        {'name': 'Letra Y!', 'checks': {'left_arm': check_left_arm_y, 'right_arm': check_right_arm_y}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.26, 0.18), R_ELBOW: (0.74, 0.18), L_WRIST: (0.16, 0.05), R_WRIST: (0.84, 0.05)}, 'color': (255, 100, 100)},
        {'name': 'Letra M!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.25, 0.20), R_ELBOW: (0.75, 0.20), L_WRIST: (0.45, 0.12), R_WRIST: (0.55, 0.12)}, 'color': (100, 255, 100)},
        {'name': 'Letra C!', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_up}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.30, 0.45), R_ELBOW: (0.70, 0.15), L_WRIST: (0.25, 0.60), R_WRIST: (0.75, 0.05)}, 'color': (100, 100, 255)},
        {'name': 'Letra A!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.38, 0.08), R_ELBOW: (0.62, 0.08), L_WRIST: (0.48, 0.02), R_WRIST: (0.52, 0.02)}, 'color': (255, 255, 100)},
    ]
}
COREOGRAFIAS['macarena_real.wav'] = COREOGRAFIAS['macarena.wav']
COREOGRAFIAS['macarena_vocal.wav'] = COREOGRAFIAS['macarena.wav']

# =============================================
# COLA DE POSES Y MODIFICADORES DINÁMICOS
# =============================================
def shift_queue(pose_queue, mode, song, coreo_idx):
    pose_queue.pop(0)
    if mode == 'COREO' and song in COREOGRAFIAS:
        coreo_idx = (coreo_idx + 1) % len(COREOGRAFIAS[song])
        p = dict(COREOGRAFIAS[song][coreo_idx])
        p['variant'] = 'NORMAL'
    else:
        roll = random.random()
        if roll < 0.12 and (not pose_queue or pose_queue[-1].get('name') != 'CONGELADOS!'):
            p = {'name': 'CONGELADOS!', 'color': (255, 90, 90), 'is_freeze': True, 'variant': 'NORMAL'}
        else:
            candidates = [x for x in POSES if not pose_queue or x['name'] != pose_queue[-1]['name']]
            p = dict(random.choice(candidates))
            # Modificadores de Variabilidad
            var_roll = random.random()
            if var_roll < 0.15 and not p.get('dynamic'):
                p['variant'] = 'SPEED'  # Pose Relampago
            elif var_roll < 0.27:
                p['variant'] = 'GOLD'   # Gold Move
            else:
                p['variant'] = 'NORMAL'

    pose_queue.append(p)
    return pose_queue[0], coreo_idx

def get_dynamic_progress(pose_name, state):
    """Retorna (actual, meta, etiqueta) según la pose dinámica activa."""
    if 'Caderas' in pose_name:
        return state.hip_hits, 6, f"CADERAS: {state.hip_hits}/6"
    elif 'Cabeza' in pose_name:
        return state.hip_hits, 6, f"CABEZA: {state.hip_hits}/6"
    elif 'Lado a Lado' in pose_name:
        return state.move_hits, 4, f"PASOS: {state.move_hits}/4"
    elif 'Brazos' in pose_name:
        return state.arm_hits, 6, f"BRAZOS: {state.arm_hits}/6"
    elif 'Boxeo' in pose_name:
        return state.arm_hits, 6, f"JABS: {state.arm_hits}/6"
    elif 'Guitarra' in pose_name:
        return state.arm_hits, 6, f"ROCK: {state.arm_hits}/6"
    elif 'Salto' in pose_name:
        return state.jump_phase, 2, "SALTA!" if state.jump_phase == 0 else "ATERRIZA!"
    elif 'Agacharse' in pose_name:
        return state.jump_phase, 2, "BAJA!" if state.jump_phase == 0 else "SUBE!"
    elif 'Gir' in pose_name:
        return state.spin_phase, 2, "GIRA 360!" if state.spin_phase == 0 else "COMPLETA EL GIRO!"
    return 0, 1, ""

# =============================================
# LOG METRICS
# =============================================
def log_metric(mode, pose_name, time_taken, status):
    try:
        with open('metrics.csv', 'a', encoding='utf-8') as f:
            f.write(f"{time.time()},{mode},{pose_name},{time_taken:.3f},{status}\n")
    except Exception as e:
        print(f"Error logging metric: {e}")

# =============================================
# BUCLE PRINCIPAL (MAIN ENGINE)
# =============================================
def main():
    cap = None
    target_cams = [0, 1, 2]
    if RTSP_URL:
        target_cams.append(RTSP_URL)
        
    for cam_id in target_cams:
        test_cap = VideoCaptureAsync(cam_id)
        if test_cap.is_opened():
            cap = test_cap
            print(f"Camara abierta correctamente en origen: {cam_id}")
            break
        test_cap.release()

    if cap is None or not cap.is_opened():
        print("No se detecto camara fisica/RTSP. Iniciando modo Demo / Camara Virtual...")
        cap = MockVideoCapture()

    cap.start()
    
    pose_detector = mp_pose.Pose(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        enable_segmentation=False
    )
    display_w, display_h = 1280, 720
    WINDOW_NAME = "Poses Locas AR"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    fever_overlay = np.full((display_h, display_w, 3), (255, 0, 255), dtype=np.uint8)
    green_overlay = np.full((display_h, display_w, 3), (0, 255, 0), dtype=np.uint8)
    gold_overlay = np.full((display_h, display_w, 3), (0, 215, 255), dtype=np.uint8)

    menu_options = []
    sfx_files = {'success.wav', 'success_new.wav', 'fail.wav', 'punch.wav', 'punch_new.wav', 'music.wav'}
    wav_files = [f for f in os.listdir('.') if f.endswith('.wav') and f not in sfx_files]
    wav_files.sort()
    for f in wav_files:
        name_display = f.replace('.wav', '').replace('_', ' ').upper()
        menu_options.append({'file': f, 'type': 'LIBRE', 'display': f"[LIBRE] {name_display}"})
        if f in COREOGRAFIAS:
            menu_options.append({'file': f, 'type': 'COREO', 'display': f"[COREO] {name_display}"})
            
    if not menu_options:
        menu_options = [{'file': 'Sin Musica', 'type': 'LIBRE', 'display': 'Sin Musica'}]

    selected_idx = 0
    show_menu = True
    
    score, streak, poses_completed = 0, 0, 0
    fever_gauge = 0
    fever_active = False
    fever_start_time = 0
    fever_duration = 10.0
    shake_time = 0
    multiplier = 1
    current_mode = 'LIBRE'
    current_song = menu_options[selected_idx]['file']
    coreo_idx = -1
    pose_queue = []
    for _ in range(5):
        if current_mode == 'COREO' and current_song in COREOGRAFIAS:
            coreo_idx = (coreo_idx + 1) % len(COREOGRAFIAS[current_song])
            p = dict(COREOGRAFIAS[current_song][coreo_idx])
            p['variant'] = 'NORMAL'
        else:
            candidates = [x for x in POSES if not pose_queue or x['name'] != pose_queue[-1]['name']]
            p = dict(random.choice(candidates))
            p['variant'] = 'NORMAL'
        pose_queue.append(p)
    current_pose = pose_queue[0]

    # Acumulador con Grace Decay para dwell time
    hold_progress = 0.0
    last_frame_time = time.time()
    pose_start_time = time.time()
    control_gesture_start = None
    control_gesture_required = 0.8
    queue_slide_offset = 0.0

    # Menú cinético a distancia
    menu_left_start = None
    menu_right_start = None
    menu_both_start = None
    menu_confirm_required = 0.9

    particles = ParticleSystem()
    floating_texts = FloatingText()
    hand_trails = HandTrailSystem(maxlen=8)
    show_success_flash = False
    success_flash_time = 0
    state = PlayerState()
    
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
        
        frame = cv2.resize(frame, (display_w, display_h))
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose_detector.process(rgb_frame)
        current_time = time.time()
        dt = min(0.1, current_time - last_frame_time)
        last_frame_time = current_time

        # Slide Lerp para el carril inferior
        queue_slide_offset *= 0.82
        
        has_person = results.pose_landmarks is not None
        left_score, right_score = 0.0, 0.0
        left_ok, right_ok = False, False
        pulse = get_beat_pulse(current_time, current_song)
        
        # =========================================================
        # MODO JUEGO ACTIVO (show_menu == False)
        # =========================================================
        if not show_menu:
            if has_person:
                lm = results.pose_landmarks.landmark
                bu = get_body_unit(lm)

                # Gesto Saltar Pose (Wakanda X en pecho)
                if check_gesture_next(lm):
                    if control_gesture_start is None: control_gesture_start = current_time
                    skip_prog = min(1.0, (current_time - control_gesture_start) / control_gesture_required)
                    blend_rect_roi(frame, (display_w - 320) // 2, 80, 320, 40, (20, 20, 30), 0.85)
                    draw_progress_bar(frame, (display_w - 300) // 2, 88, 300, 22, skip_prog, (0, 100, 255))
                    cv2.putText(frame, "SALTANDO POSE...", ((display_w - 280) // 2, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 150, 255), 2, cv2.LINE_AA)
                    
                    if current_time - control_gesture_start >= control_gesture_required:
                        floating_texts.add("POSE SALTEADA!", 40, 310, (0, 100, 255), 1.3)
                        play_sound(snd_fail)
                        fever_gauge = max(0, fever_gauge - 20)
                        shake_time = current_time
                        log_metric(current_mode, current_pose['name'], current_time - pose_start_time, 'SKIPPED')
                        current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx)
                        pose_start_time = current_time
                        control_gesture_start, hold_progress, streak = None, 0.0, 0
                        queue_slide_offset = 240.0
                        state.reset()
                else:
                    control_gesture_start = None

                    # --- POSE: CONGELADOS! ---
                    if current_pose.get('is_freeze'):
                        left_score, right_score = 1.0, 1.0
                        left_ok, right_ok = True, True
                        if hold_progress == 0.0 and state.freeze_reference is None:
                            state.freeze_reference = [{"x": lm[kp].x, "y": lm[kp].y} for kp in [NOSE, L_WRIST, R_WRIST, L_HIP, R_HIP]]

                        movement = 0.0
                        if state.freeze_reference:
                            for i, kp in enumerate([NOSE, L_WRIST, R_WRIST, L_HIP, R_HIP]):
                                dx = lm[kp].x - state.freeze_reference[i]["x"]
                                dy = lm[kp].y - state.freeze_reference[i]["y"]
                                movement += math.hypot(dx, dy)
                                
                        time_left = max(0.0, 3.0 - (current_time - pose_start_time))
                        blend_rect_roi(frame, 400, 18, 480, 85, (15, 15, 30), 0.85)
                        cv2.rectangle(frame, (400, 18), (880, 103), (0, 215, 255), 2)
                        cv2.putText(frame, f"CONGELADOS! {time_left:.1f}s", (435, 58), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 255), 2, cv2.LINE_AA)
                        draw_progress_bar(frame, 425, 70, 430, 20, time_left / 3.0, (0, 215, 255))
                        
                        if movement > 0.22:
                            floating_texts.add("TE MOVISTE!", 40, 310, (60, 60, 255), 1.8)
                            play_sound(snd_fail)
                            fever_gauge = max(0, fever_gauge - 40)
                            shake_time = current_time
                            streak = 0
                            log_metric(current_mode, 'CONGELADOS!', current_time - pose_start_time, 'FAILED')
                            current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx)
                            pose_start_time = current_time
                            hold_progress = 0.0
                            queue_slide_offset = 240.0
                            state.reset()
                        elif time_left <= 0:
                            multiplier = 3 if fever_active else (1 + int(streak // 3))
                            points = int(1000 * multiplier)
                            score += points
                            poses_completed += 1
                            streak += 1
                            if not fever_active:
                                fever_gauge = min(100, fever_gauge + 20)
                                if fever_gauge >= 100:
                                    fever_active = True
                                    fever_start_time = current_time
                                    floating_texts.add("FEVER TIME!", display_w//2 - 160, 220, (0, 255, 255), 2.4)
                            particles.emit(display_w // 2, 340, (255, 255, 255), 45)
                            floating_texts.add(f"SOBREVIVISTE! +{points}", 40, 310, (0, 255, 120), 1.8)
                            play_sound(snd_success)
                            log_metric(current_mode, 'CONGELADOS!', current_time - pose_start_time, 'COMPLETED')
                            current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx)
                            pose_start_time = current_time
                            hold_progress = 0.0
                            queue_slide_offset = 240.0
                            state.reset()

                    # --- POSES DINÁMICAS ---
                    elif current_pose.get('dynamic'):
                        completed, events = current_pose['checks'](state, lm)
                        left_score, right_score = 1.0, 1.0
                        left_ok, right_ok = True, True
                        
                        for e in events:
                            if e['type'] == 'hit':
                                play_sound(snd_punch)
                                px = int(e['x'] * display_w)
                                py = int(e['y'] * display_h)
                                particles.emit(px, py, current_pose['color'], 24)
                                floating_texts.add("HIT! +20", px - 40, py - 30, (0, 255, 255), 1.2)
                                score += 20
                                
                        if completed:
                            time_taken = current_time - pose_start_time
                            streak += 1
                            poses_completed += 1
                            multiplier = 3 if fever_active else (1 + int(streak // 3))

                            # Tiers de juicio
                            is_gold = current_pose.get('variant') == 'GOLD'
                            is_speed = current_pose.get('variant') == 'SPEED'
                            if time_taken <= 2.2 or is_speed:
                                tier_text = "PERFECTO!!"
                                tier_col = (0, 215, 255)
                                base_pts = 150 * (2 if is_speed else 1)
                                fever_add = 25
                            elif time_taken <= 3.8:
                                tier_text = "GENIAL!"
                                tier_col = (0, 255, 120)
                                base_pts = 100
                                fever_add = 15
                            else:
                                tier_text = "BIEN!"
                                tier_col = (255, 230, 0)
                                base_pts = 70
                                fever_add = 10

                            if is_gold:
                                base_pts += 500
                                fever_add += 30

                            points = int(base_pts * multiplier)
                            score += points
                            if not fever_active:
                                fever_gauge = min(100, fever_gauge + fever_add)
                                if fever_gauge >= 100:
                                    fever_active = True
                                    fever_start_time = current_time
                                    floating_texts.add("FEVER TIME!", display_w//2 - 160, 220, (0, 255, 255), 2.4)

                            play_sound(snd_success)
                            particles.emit_confetti(display_w, gold_only=is_gold)
                            particles.emit(display_w // 2, 340, current_pose['color'], 35)
                            floating_texts.add(f"{tier_text} +{points}", 40, 310, tier_col, 1.8)
                            show_success_flash = True
                            success_flash_time = current_time
                            log_metric(current_mode, current_pose['name'], time_taken, 'COMPLETED')
                            current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx)
                            pose_start_time = current_time
                            queue_slide_offset = 240.0
                            state.reset()

                    # --- POSES ESTÁTICAS CON ACUMULADOR GRACE DECAY ---
                    else:
                        left_check = current_pose['checks']['left_arm']
                        right_check = current_pose['checks']['right_arm']
                        left_ok = left_check(lm)
                        right_ok = right_check(lm)
                        left_score = score_arm(left_check, lm)
                        right_score = score_arm(right_check, lm)

                        # Bonus Pasivo de Groove
                        hip_x = (lm[L_HIP].x + lm[R_HIP].x) / 2.0
                        if state.global_center_x is None:
                            state.global_center_x = hip_x
                        else:
                            state.global_center_x = state.global_center_x * 0.98 + hip_x * 0.02
                        if abs(hip_x - state.global_center_x) > 0.025 and current_time - state.last_groove_time > 0.45:
                            state.last_groove_time = current_time
                            score += 15
                            floating_texts.add("GROOVE CADERA +15", 40, 355, (255, 120, 255), 0.72)
                            particles.emit(int(hip_x * display_w), int(lm[L_HIP].y * display_h), (255, 100, 255), 10)

                        # Dwell time con Grace Decay
                        is_speed = current_pose.get('variant') == 'SPEED'
                        req_time = 0.35 if is_speed else 0.55
                        if left_ok and right_ok:
                            hold_progress = min(1.0, hold_progress + (dt / req_time))
                        else:
                            decay = 0.6 if (left_ok or right_ok) else 1.2
                            hold_progress = max(0.0, hold_progress - decay * dt)

                        if hold_progress >= 1.0:
                            time_taken = current_time - pose_start_time
                            streak += 1
                            poses_completed += 1
                            multiplier = 3 if fever_active else (1 + int(streak // 3))

                            is_gold = current_pose.get('variant') == 'GOLD'
                            if time_taken <= 1.9 or is_speed:
                                tier_text = "PERFECTO!!"
                                tier_col = (0, 215, 255)
                                base_pts = 150 * (2 if is_speed else 1)
                                fever_add = 25
                            elif time_taken <= 3.6:
                                tier_text = "GENIAL!"
                                tier_col = (0, 255, 120)
                                base_pts = 100
                                fever_add = 15
                            else:
                                tier_text = "BIEN!"
                                tier_col = (255, 230, 0)
                                base_pts = 70
                                fever_add = 10

                            if is_gold:
                                base_pts += 500
                                fever_add += 30

                            points = int(base_pts * multiplier)
                            score += points
                            if not fever_active:
                                fever_gauge = min(100, fever_gauge + fever_add)
                                if fever_gauge >= 100:
                                    fever_active = True
                                    fever_start_time = current_time
                                    floating_texts.add("FEVER TIME!", display_w//2 - 160, 220, (0, 255, 255), 2.4)

                            play_sound(snd_success)
                            particles.emit_confetti(display_w, gold_only=is_gold)
                            particles.emit(display_w // 2, 340, current_pose['color'], 30)
                            floating_texts.add(f"{tier_text} +{points}", 40, 310, tier_col, 1.8)
                            if streak >= 3 and not fever_active:
                                floating_texts.add(f"RACHA x{streak}!", 40, 360, (0, 255, 255), 1.2)

                            show_success_flash = True
                            success_flash_time = current_time
                            log_metric(current_mode, current_pose['name'], time_taken, 'COMPLETED')
                            current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx)
                            pose_start_time = current_time
                            hold_progress = 0.0
                            queue_slide_offset = 240.0
                            state.reset()

                # Dibujo AR Central (Ghost Silhouette + Anillos + Esqueleto Semáforo + Estelas)
                draw_ghost_and_target_rings(frame, lm, current_pose, display_w, display_h, left_score, right_score)
                draw_skeleton_with_feedback(frame, lm, display_w, display_h, left_ok, right_ok, left_score, right_score)
                hand_trails.update_and_draw(frame, lm, display_w, display_h, score_to_traffic_color(left_score), score_to_traffic_color(right_score))

            else:
                control_gesture_start = None
                hold_progress = max(0.0, hold_progress - 1.0 * dt)

            # =========================================================
            # RENDERIZADO DEL HUD (MAPA DE 5 ZONAS LIBRE DE COLISIONES)
            # =========================================================

            # --- ZONA 1: TOP-LEFT HUD (Score, Racha/Multi, Barra Fever) ---
            blend_rect_roi(frame, 20, 18, 290, 132, (18, 15, 25), 0.78)
            cv2.rectangle(frame, (20, 18), (310, 150), (0, 220, 255), 2)
            cv2.putText(frame, f"PUNTAJE: {score:,}", (35, 58), cv2.FONT_HERSHEY_DUPLEX, 0.95, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, f"RACHA x{streak}  |  MULTI x{multiplier}", (35, 95), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 200, 255), 2, cv2.LINE_AA)
            cv2.rectangle(frame, (35, 112), (225, 132), (55, 55, 70), -1)
            fever_w = int(190 * (fever_gauge / 100.0))
            if fever_w > 0:
                cv2.rectangle(frame, (35, 112), (35 + fever_w, 132), (255, 50, 255), -1)
            cv2.rectangle(frame, (35, 112), (225, 132), (255, 255, 255), 2)
            cv2.putText(frame, f"FEVER {fever_gauge}%", (234, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 130, 255), 1, cv2.LINE_AA)

            # --- ZONA 2: TOP-CENTER BANNER (Nombre Pose + Barra Progreso) ---
            bx, by, bw, bh = 385, 18, 465, 102
            blend_rect_roi(frame, bx, by, bw, bh, (15, 15, 25), 0.82)
            banner_col = (0, 215, 255) if current_pose.get('variant') == 'GOLD' else ((255, 230, 0) if current_pose.get('variant') == 'SPEED' else current_pose.get('color', (0, 255, 120)))
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), banner_col, 2)
            
            pname = current_pose.get('name', '')
            (tw, _), _ = cv2.getTextSize(pname, cv2.FONT_HERSHEY_DUPLEX, 0.98, 2)
            cv2.putText(frame, pname, (bx + (bw - tw) // 2, by + 40), cv2.FONT_HERSHEY_DUPLEX, 0.98, banner_col, 2, cv2.LINE_AA)
            
            if current_pose.get('dynamic'):
                cur_act, cur_target, lbl = get_dynamic_progress(pname, state)
                prog_val = min(1.0, cur_act / max(1, cur_target))
                cv2.rectangle(frame, (bx + 28, by + 52), (bx + bw - 28, by + 74), (45, 45, 60), -1)
                cv2.rectangle(frame, (bx + 28, by + 52), (bx + 28 + int((bw - 56) * prog_val), by + 74), banner_col, -1)
                cv2.rectangle(frame, (bx + 28, by + 52), (bx + bw - 28, by + 74), (255, 255, 255), 2)
                cv2.putText(frame, lbl, (bx + 40, by + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
            elif not current_pose.get('is_freeze'):
                cv2.rectangle(frame, (bx + 28, by + 52), (bx + bw - 28, by + 74), (45, 45, 60), -1)
                cv2.rectangle(frame, (bx + 28, by + 52), (bx + 28 + int((bw - 56) * hold_progress), by + 74), (0, 210, 110), -1)
                cv2.rectangle(frame, (bx + 28, by + 52), (bx + bw - 28, by + 74), (255, 255, 255), 2)
                cv2.putText(frame, f"MANTENE: {int(hold_progress * 100)}% (Grace Buffer Activo)", (bx + 60, by + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (210, 255, 220), 1, cv2.LINE_AA)

            # --- ZONA 3: TOP-RIGHT DUAL REFERENCE CARD (Ilustración pose_*.jpg + Coach Vivo) ---
            rx, ry, rw, rh = 900, 18, 356, 200
            blend_rect_roi(frame, rx, ry, rw, rh, (20, 18, 30), 0.85)
            cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (255, 200, 0), 2)
            
            icon_name = current_pose.get('icon_name')
            illus = load_pose_illustration_clean(icon_name, size=(155, 155)) if icon_name else None
            if illus is not None:
                frame[ry + 12:ry + 12 + 155, rx + 12:rx + 12 + 155] = illus
                cv2.rectangle(frame, (rx + 12, ry + 12), (rx + 167, ry + 167), (90, 90, 115), 1)
                stick_x, stick_w = rx + 180, 160
            else:
                stick_x, stick_w = rx + 25, 305
                
            ref_pts = get_animated_ref_points(current_pose, current_time)
            draw_full_body_stickman(frame, stick_x, ry + 10, stick_w, 158, ref_pts, banner_col)
            draw_intent_arrows_in_box(frame, current_pose, stick_x, ry + 10, stick_w, 158, current_time)
            cv2.putText(frame, "ILUSTRACION + COACH VIVO", (rx + 42, ry + 190), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1, cv2.LINE_AA)

            # --- ZONA 5: CARRIL INFERIOR 2.0 (PICTO-CARDS + DESLIZAMIENTO SUAVE) ---
            lane_y = 588
            blend_rect_roi(frame, 0, lane_y - 26, display_w, 26, (10, 10, 18), 0.78)
            cv2.putText(frame, "Gesto Brazos en X = Saltar Pose  |  Manos Arriba en Menu = Jugar  |  BPM Beat-Sync: 103 BPM",
                        (28, lane_y - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 210, 230), 1, cv2.LINE_AA)

            blend_rect_roi(frame, 0, lane_y, display_w, display_h - lane_y, (18, 16, 26), 0.92)
            cv2.line(frame, (0, lane_y), (display_w, lane_y), (0, 255, 255), 2)

            for i, p in enumerate(pose_queue):
                cx = int(22 + i * 248 + queue_slide_offset)
                cy = lane_y + 12
                cw, ch = 236, 108
                if cx > display_w: break
                
                is_active_card = (i == 0)
                card_col = (0, 215, 255) if p.get('variant') == 'GOLD' else ((255, 230, 0) if p.get('variant') == 'SPEED' else p.get('color', (200, 200, 200)))
                bg = (65, 25, 85) if is_active_card else (35, 32, 48)
                blend_rect_roi(frame, cx, cy, cw, ch, bg, 0.9)
                cv2.rectangle(frame, (cx, cy), (cx + cw, cy + ch), card_col, 3 if is_active_card else 1)

                # Mini-stickman dentro de la tarjeta
                cv2.rectangle(frame, (cx + 6, cy + 6), (cx + 82, cy + ch - 6), (22, 20, 30), -1)
                pts_card = get_animated_ref_points(p, current_time)
                draw_full_body_stickman(frame, cx + 8, cy + 8, 72, ch - 16, pts_card, card_col, show_floor=True)

                # Etiquetas y títulos
                tag = "AHORA!" if is_active_card else "SIGUIENTE"
                if p.get('variant') == 'GOLD': tag += " GOLD +500"
                elif p.get('variant') == 'SPEED': tag += " RELAMPAGO x2"
                elif p.get('dynamic'): tag += " (RITMO)"
                else: tag += " (HOLD)"
                
                tx_off = cx + 90
                if p.get('variant') == 'GOLD':
                    draw_star_icon(frame, cx + 98, cy + 28, 8, card_col)
                    tx_off = cx + 112
                elif p.get('variant') == 'SPEED':
                    draw_bolt_icon(frame, cx + 98, cy + 28, 8, card_col)
                    tx_off = cx + 112

                cv2.putText(frame, tag, (tx_off, cy + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.48, card_col, 1, cv2.LINE_AA)
                
                words = p['name'].split()
                if len(words) >= 3:
                    cv2.putText(frame, " ".join(words[:2]), (cx + 90, cy + 66), cv2.FONT_HERSHEY_DUPLEX, 0.54, (255, 255, 255), 1, cv2.LINE_AA)
                    cv2.putText(frame, " ".join(words[2:]), (cx + 90, cy + 92), cv2.FONT_HERSHEY_DUPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
                else:
                    cv2.putText(frame, p['name'], (cx + 90, cy + 72), cv2.FONT_HERSHEY_DUPLEX, 0.56, (255, 255, 255), 1, cv2.LINE_AA)

            particles.update_and_draw(frame)
            floating_texts.update_and_draw(frame)

            if show_success_flash and current_time - success_flash_time < 0.25:
                overlay_flash = gold_overlay if current_pose.get('variant') == 'GOLD' else green_overlay
                cv2.addWeighted(overlay_flash, 0.15, frame, 0.85, 0, frame)
            elif show_success_flash:
                show_success_flash = False

        # =========================================================
        # FEVER & SCREEN SHAKE EFFECTS
        # =========================================================
        if fever_active:
            if current_time - fever_start_time > fever_duration:
                fever_active = False
                fever_gauge = 0
                multiplier = 1
            else:
                cv2.addWeighted(fever_overlay, 0.18, frame, 0.82, 0, frame)
                
        if current_time - shake_time < 0.28:
            dx = random.randint(-16, 16)
            dy = random.randint(-16, 16)
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            frame = cv2.warpAffine(frame, M, (display_w, display_h))

        # =========================================================
        # MENÚ KINÉTICO (CONTROL A 3 METROS CON MANOS + TECLADO)
        # =========================================================
        if show_menu:
            blend_rect_roi(frame, 0, 0, display_w, display_h, (12, 10, 18), 0.82)
            cv2.putText(frame, "MENU DE CANCIONES Y COREOGRAFIAS", (display_w//2 - 380, 120), cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "Controla con tus manos a distancia o con flechas del teclado", (display_w//2 - 370, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (200, 220, 240), 1, cv2.LINE_AA)

            # Botones kinéticos en pantalla
            cv2.circle(frame, (120, 340), 55, (255, 180, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, "MANO IZQ", (72, 332), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 200, 50), 1, cv2.LINE_AA)
            cv2.putText(frame, "SUBIR", (86, 358), cv2.FONT_HERSHEY_DUPLEX, 0.54, (255, 255, 255), 1, cv2.LINE_AA)

            cv2.circle(frame, (display_w - 120, 340), 55, (255, 180, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, "MANO DER", (display_w - 168, 332), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 200, 50), 1, cv2.LINE_AA)
            cv2.putText(frame, "BAJAR", (display_w - 152, 358), cv2.FONT_HERSHEY_DUPLEX, 0.54, (255, 255, 255), 1, cv2.LINE_AA)

            # Scroll view de opciones
            max_visible = 5
            start_idx = max(0, selected_idx - max_visible // 2)
            end_idx = min(len(menu_options), start_idx + max_visible)
            if end_idx - start_idx < max_visible:
                start_idx = max(0, end_idx - max_visible)

            for i in range(start_idx, end_idx):
                opt = menu_options[i]
                is_sel = (i == selected_idx)
                color = (0, 255, 120) if is_sel else (150, 150, 165)
                prefix = "->  " if is_sel else "    "
                draw_i = i - start_idx
                oy = 230 + draw_i * 68
                if is_sel:
                    blend_rect_roi(frame, display_w//2 - 320, oy - 42, 640, 56, (30, 40, 60), 0.85)
                    cv2.rectangle(frame, (display_w//2 - 320, oy - 42), (display_w//2 + 320, oy + 14), (0, 255, 120), 2)
                cv2.putText(frame, prefix + opt['display'], (display_w//2 - 290, oy), cv2.FONT_HERSHEY_DUPLEX, 1.0, color, 2, cv2.LINE_AA)

            # Barra kinética de inicio (ambos brazos arriba)
            confirm_prog = 0.0
            if has_person:
                lm = results.pose_landmarks.landmark
                # Mano izquierda arriba = scroll up con debounce
                l_up = check_left_arm_up(lm) and not check_right_arm_up(lm)
                r_up = check_right_arm_up(lm) and not check_left_arm_up(lm)
                both_up = check_left_arm_up(lm) and check_right_arm_up(lm)

                if both_up:
                    if menu_both_start is None: menu_both_start = current_time
                    confirm_prog = min(1.0, (current_time - menu_both_start) / menu_confirm_required)
                    if confirm_prog >= 1.0:
                        show_menu = False
                        current_song = menu_options[selected_idx]['file']
                        current_mode = menu_options[selected_idx]['type']
                        menu_both_start = None
                        pose_start_time = current_time
                        if HAS_AUDIO:
                            if current_song == "Sin Musica": pygame.mixer.music.stop()
                            else:
                                pygame.mixer.music.load(current_song)
                                pygame.mixer.music.play(-1)
                                pygame.mixer.music.set_volume(0.4)
                else:
                    menu_both_start = None

                if l_up:
                    if menu_left_start is None:
                        menu_left_start = current_time
                        selected_idx = max(0, selected_idx - 1)
                else:
                    menu_left_start = None

                if r_up:
                    if menu_right_start is None:
                        menu_right_start = current_time
                        selected_idx = min(len(menu_options) - 1, selected_idx + 1)
                else:
                    menu_right_start = None

            # Render de barra de confirmación
            blend_rect_roi(frame, display_w//2 - 300, display_h - 110, 600, 48, (20, 20, 30), 0.85)
            cv2.rectangle(frame, (display_w//2 - 300, display_h - 110), (display_w//2 + 300, display_h - 62), (255, 255, 255), 2)
            if confirm_prog > 0:
                cv2.rectangle(frame, (display_w//2 - 296, display_h - 106), (display_w//2 - 296 + int(592 * confirm_prog), display_h - 66), (0, 255, 120), -1)
            cv2.putText(frame, "AMBOS BRAZOS ARRIBA O ENTER = ¡JUGAR!", (display_w//2 - 250, display_h - 78), cv2.FONT_HERSHEY_DUPLEX, 0.68, (0, 0, 0) if confirm_prog > 0.5 else (255, 255, 255), 2, cv2.LINE_AA)

        cv2.imshow(WINDOW_NAME, frame)
        
        # PROCESAMIENTO DE TECLADO (FALLBACK)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): 
            break
        elif key == ord('m') or key == ord('c'):
            show_menu = not show_menu
        elif key == ord('n') or key == 32:
            if not show_menu:
                floating_texts.add("POSE SALTEADA!", 40, 310, (0, 100, 255), 1.3)
                play_sound(snd_fail)
                fever_gauge = max(0, fever_gauge - 20)
                shake_time = current_time
                log_metric(current_mode, current_pose['name'], current_time - pose_start_time, 'SKIPPED')
                current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx)
                pose_start_time = current_time
                control_gesture_start, hold_progress, streak = None, 0.0, 0
                queue_slide_offset = 240.0
                state.reset()
            
        if show_menu:
            if key == 82 or key == ord('w'):
                selected_idx = max(0, selected_idx - 1)
            elif key == 84 or key == ord('s'):
                selected_idx = min(len(menu_options) - 1, selected_idx + 1)
            elif key == 13 or key == 32:
                show_menu = False
                current_song = menu_options[selected_idx]['file']
                current_mode = menu_options[selected_idx]['type']
                coreo_idx = -1
                pose_queue = []
                for _ in range(5):
                    if current_mode == 'COREO' and current_song in COREOGRAFIAS:
                        coreo_idx = (coreo_idx + 1) % len(COREOGRAFIAS[current_song])
                        p = dict(COREOGRAFIAS[current_song][coreo_idx])
                        p['variant'] = 'NORMAL'
                    else:
                        candidates = [x for x in POSES if not pose_queue or x['name'] != pose_queue[-1]['name']]
                        p = dict(random.choice(candidates))
                        p['variant'] = 'NORMAL'
                    pose_queue.append(p)
                current_pose = pose_queue[0]
                hold_progress = 0.0
                pose_start_time = current_time
                queue_slide_offset = 240.0
                
                if HAS_AUDIO:
                    if current_song == "Sin Musica":
                        pygame.mixer.music.stop()
                    else:
                        pygame.mixer.music.load(current_song)
                        pygame.mixer.music.play(-1)
                        pygame.mixer.music.set_volume(0.4)
                    
        if HAS_AUDIO and current_song and current_song != "Sin Musica" and not show_menu:
            if not pygame.mixer.music.get_busy():
                try: pygame.mixer.music.play(-1)
                except Exception: pass
                
        try:
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1: break
        except Exception: break
    
    cap.stop()
    pose_detector.close()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
