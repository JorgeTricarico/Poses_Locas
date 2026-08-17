import cv2
import mediapipe as mp
import threading
import time
import math
import random
import numpy as np
import os

# =============================================
# CONFIGURACIÓN
# =============================================
ENABLE_SFX = False  # Deshabilitado por pedido del usuario (muy invasivos)

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
        snd.play()

RTSP_URL = "rtsp://jorge.tricarico:3424Trica@192.168.0.148:554/stream1"

class VideoCaptureAsync:
    def __init__(self, src=0):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.read_lock = threading.Lock()
    def is_opened(self): return self.cap.isOpened() and self.grabbed
    def release(self):
        if self.started: self.stop()
        self.cap.release()
    def start(self):
        if self.started: return None
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
        self.thread.join()

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

SKELETON_CONNECTIONS = [(L_SHOULDER, R_SHOULDER), (L_SHOULDER, L_HIP), (R_SHOULDER, R_HIP), (L_HIP, R_HIP), (L_SHOULDER, NOSE), (R_SHOULDER, NOSE)]
LEFT_ARM_CONNECTIONS = [(L_SHOULDER, L_ELBOW), (L_ELBOW, L_WRIST)]
RIGHT_ARM_CONNECTIONS = [(R_SHOULDER, R_ELBOW), (R_ELBOW, R_WRIST)]

# =============================================
# CHECKS (ESTÁTICOS)
# =============================================
def check_left_arm_up(lm): return lm[L_WRIST].y < lm[NOSE].y - 0.05
def check_right_arm_up(lm): return lm[R_WRIST].y < lm[NOSE].y - 0.05
def check_left_arm_down(lm): return lm[L_WRIST].y > lm[L_SHOULDER].y + 0.05
def check_right_arm_down(lm): return lm[R_WRIST].y > lm[R_SHOULDER].y + 0.05
def check_left_arm_horizontal(lm): return abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.12 and lm[L_WRIST].x < lm[L_SHOULDER].x - 0.08
def check_right_arm_horizontal(lm): return abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.12 and lm[R_WRIST].x > lm[R_SHOULDER].x + 0.08
def check_left_hand_on_hip(lm): return abs(lm[L_WRIST].x - lm[L_HIP].x) < 0.15 and abs(lm[L_WRIST].y - lm[L_HIP].y) < 0.15
def check_right_hand_on_hip(lm): return abs(lm[R_WRIST].x - lm[R_HIP].x) < 0.15 and abs(lm[R_WRIST].y - lm[R_HIP].y) < 0.15
def check_left_hand_on_head(lm): return abs(lm[L_WRIST].x - lm[NOSE].x) < 0.10 and abs(lm[L_WRIST].y - lm[NOSE].y) < 0.10
def check_right_hand_on_head(lm): return abs(lm[R_WRIST].x - lm[NOSE].x) < 0.10 and abs(lm[R_WRIST].y - lm[NOSE].y) < 0.10
def check_left_bicep(lm): return abs(lm[L_WRIST].x - lm[L_SHOULDER].x) < 0.10 and abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.15 and lm[L_ELBOW].x < lm[L_SHOULDER].x - 0.05
def check_right_bicep(lm): return abs(lm[R_WRIST].x - lm[R_SHOULDER].x) < 0.10 and abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.15 and lm[R_ELBOW].x > lm[R_SHOULDER].x + 0.05
def check_right_salute(lm): return abs(lm[R_WRIST].x - lm[R_EAR].x) < 0.10 and abs(lm[R_WRIST].y - lm[R_EAR].y) < 0.10

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
        self.initial_shoulder_order = None
        self.spin_start_time = 0

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
    import time
    
    if getattr(state, 'initial_shoulder_order', None) is None:
        state.initial_shoulder_order = left_is_right_of_right
        state.spin_start_time = time.time()
        
    if state.spin_phase == 0:
        if left_is_right_of_right != state.initial_shoulder_order:
            state.spin_phase = 1
        elif lm[L_SHOULDER].visibility < 0.2 and lm[R_SHOULDER].visibility < 0.2:
            state.spin_phase = 1
            
    elif state.spin_phase == 1:
        if time.time() - state.spin_start_time > 0.4:
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
        
    threshold = 0.15
    
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
# POSES
# =============================================
POSES = [
    # --- Dinámicas ---
    {
        'name': 'Baila! Mueve Caderas', 'color': (255, 100, 150),
        'dynamic': True, 'checks': check_shake_hips,
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.28, 0.42), R_ELBOW: (0.72, 0.42), L_WRIST: (0.40, 0.60), R_WRIST: (0.60, 0.60), L_HIP: (0.35, 0.65), R_HIP: (0.50, 0.65) },
    },
    {
        'name': 'Salto Mortal!', 'color': (100, 255, 100),
        'dynamic': True, 'checks': check_jump,
        'ref': { NOSE: (0.5, 0.05), L_SHOULDER: (0.38, 0.20), R_SHOULDER: (0.62, 0.20), L_ELBOW: (0.28, 0.35), R_ELBOW: (0.72, 0.35), L_WRIST: (0.20, 0.45), R_WRIST: (0.80, 0.45), L_HIP: (0.42, 0.50), R_HIP: (0.58, 0.50) },
    },
    {
        'name': 'Agacharse!', 'color': (100, 100, 255),
        'dynamic': True, 'checks': check_squat,
        'ref': { NOSE: (0.5, 0.40), L_SHOULDER: (0.38, 0.55), R_SHOULDER: (0.62, 0.55), L_ELBOW: (0.28, 0.70), R_ELBOW: (0.72, 0.70), L_WRIST: (0.35, 0.85), R_WRIST: (0.65, 0.85), L_HIP: (0.42, 0.85), R_HIP: (0.58, 0.85) },
    },
    {
        'name': 'Girando!', 'color': (255, 150, 0),
        'dynamic': True, 'checks': check_spin,
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.48, 0.30), R_SHOULDER: (0.52, 0.30), L_ELBOW: (0.45, 0.50), R_ELBOW: (0.55, 0.50), L_WRIST: (0.45, 0.70), R_WRIST: (0.55, 0.70), L_HIP: (0.48, 0.65), R_HIP: (0.52, 0.65) },
    },
    {
        'name': 'Mueve los Brazos!', 'color': (255, 50, 255),
        'dynamic': True, 'checks': check_flail_arms,
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.28, 0.15), R_ELBOW: (0.72, 0.45), L_WRIST: (0.20, 0.05), R_WRIST: (0.80, 0.60), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'De Lado a Lado!', 'color': (50, 255, 255),
        'dynamic': True, 'checks': check_move_side_to_side,
        'ref': { NOSE: (0.7, 0.12), L_SHOULDER: (0.58, 0.30), R_SHOULDER: (0.82, 0.30), L_ELBOW: (0.48, 0.45), R_ELBOW: (0.92, 0.45), L_WRIST: (0.55, 0.60), R_WRIST: (0.85, 0.60), L_HIP: (0.62, 0.65), R_HIP: (0.78, 0.65) },
    },
    {
        'name': 'Cabeza y Caderas!', 'color': (200, 255, 100),
        'dynamic': True, 'checks': check_hand_head_shake_hips,
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.25, 0.20), R_ELBOW: (0.72, 0.42), L_WRIST: (0.45, 0.10), R_WRIST: (0.60, 0.60), L_HIP: (0.35, 0.65), R_HIP: (0.50, 0.65) },
    },
    {
        'name': 'Salto con Brazos!', 'color': (100, 200, 255),
        'dynamic': True, 'checks': check_jump_arms_up,
        'ref': { NOSE: (0.5, 0.05), L_SHOULDER: (0.38, 0.20), R_SHOULDER: (0.62, 0.20), L_ELBOW: (0.32, 0.08), R_ELBOW: (0.68, 0.08), L_WRIST: (0.35, -0.05), R_WRIST: (0.65, -0.05), L_HIP: (0.42, 0.50), R_HIP: (0.58, 0.50) },
    },
    {
        'name': 'Giro y Cabeza!', 'color': (255, 150, 150),
        'dynamic': True, 'checks': check_spin_hand_head,
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.48, 0.30), R_SHOULDER: (0.52, 0.30), L_ELBOW: (0.35, 0.20), R_ELBOW: (0.55, 0.50), L_WRIST: (0.48, 0.10), R_WRIST: (0.55, 0.70), L_HIP: (0.48, 0.65), R_HIP: (0.52, 0.65) },
    },
    
    # --- Estáticas ---
    {
        'name': 'Brazos Arriba!', 'color': (0, 255, 100),
        'checks': {'left_arm': check_left_arm_up, 'right_arm': check_right_arm_up},
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.32, 0.18), R_ELBOW: (0.68, 0.18), L_WRIST: (0.35, 0.05), R_WRIST: (0.65, 0.05), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'T-Pose!', 'color': (255, 200, 0),
        'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_horizontal},
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.22, 0.30), R_ELBOW: (0.78, 0.30), L_WRIST: (0.08, 0.30), R_WRIST: (0.92, 0.30), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'Fuerte!', 'color': (255, 100, 50),
        'checks': {'left_arm': check_left_bicep, 'right_arm': check_right_bicep},
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.22, 0.30), R_ELBOW: (0.78, 0.30), L_WRIST: (0.32, 0.20), R_WRIST: (0.68, 0.20), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'Saludo Militar!', 'color': (50, 100, 255),
        'checks': {'left_arm': check_left_arm_down, 'right_arm': check_right_salute},
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.32, 0.45), R_ELBOW: (0.75, 0.30), L_WRIST: (0.35, 0.58), R_WRIST: (0.58, 0.12), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'Manos en la Cintura!', 'color': (255, 50, 100),
        'checks': {'left_arm': check_left_hand_on_hip, 'right_arm': check_right_hand_on_hip},
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.28, 0.48), R_ELBOW: (0.72, 0.48), L_WRIST: (0.42, 0.65), R_WRIST: (0.58, 0.65), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'Manos en la Cabeza!', 'color': (100, 50, 255),
        'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head},
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.25, 0.20), R_ELBOW: (0.75, 0.20), L_WRIST: (0.45, 0.10), R_WRIST: (0.55, 0.10), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'Diagonal Izquierda!', 'color': (150, 255, 50),
        'checks': {'left_arm': check_left_arm_down, 'right_arm': check_right_arm_up},
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.30, 0.45), R_ELBOW: (0.70, 0.15), L_WRIST: (0.25, 0.60), R_WRIST: (0.75, 0.05), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'Diagonal Derecha!', 'color': (255, 150, 50),
        'checks': {'left_arm': check_left_arm_up, 'right_arm': check_right_arm_down},
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.30, 0.15), R_ELBOW: (0.70, 0.45), L_WRIST: (0.25, 0.05), R_WRIST: (0.75, 0.60), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
]

# =============================================
# DIBUJO Y EFECTOS
# =============================================
def draw_reference(frame, pose_data, box_x, box_y, box_w, box_h):
    ref = pose_data.get('ref')
    if not ref: return
    overlay = frame.copy()
    cv2.rectangle(overlay, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (255, 255, 255), 2)
    points = {lm_id: (int(box_x + nx * box_w), int(box_y + ny * box_h)) for lm_id, (nx, ny) in ref.items()}
    for a, b in SKELETON_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (200, 200, 200), 2)
    for a, b in LEFT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (255, 255, 0), 3)
    for a, b in RIGHT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (255, 255, 0), 3)
    for pt in points.values(): cv2.circle(frame, pt, 4, (0, 255, 255), -1)
    if NOSE in points: cv2.circle(frame, points[NOSE], 10, (0, 255, 255), 2)

def get_point(lm, lm_id, w, h):
    return (int(lm[lm_id].x * w), int(lm[lm_id].y * h)) if lm[lm_id].visibility > 0.4 else None

def draw_skeleton_with_feedback(frame, lm, display_w, display_h, left_ok, right_ok):
    COLOR_OK = (0, 255, 0); COLOR_FAIL = (0, 0, 255); COLOR_BODY = (255, 255, 0)
    points = {lm_id: pt for lm_id in [NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP] if (pt := get_point(lm, lm_id, display_w, display_h))}
    
    # 1. Glow Overlay (Thick blurred lines)
    overlay = frame.copy()
    for a, b in SKELETON_CONNECTIONS:
        if a in points and b in points: cv2.line(overlay, points[a], points[b], COLOR_BODY, 12)
    left_color = COLOR_OK if left_ok else COLOR_FAIL
    for a, b in LEFT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(overlay, points[a], points[b], left_color, 16)
    right_color = COLOR_OK if right_ok else COLOR_FAIL
    for a, b in RIGHT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(overlay, points[a], points[b], right_color, 16)
    cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
    
    # 2. Inner Core (Thin white lines)
    for a, b in SKELETON_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (255,255,255), 3)
    for a, b in LEFT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (255,255,255), 4)
    for a, b in RIGHT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (255,255,255), 4)
    
    # 3. Dynamic pulsing joints
    pulse = int(math.sin(time.time() * 10) * 5)
    for lm_id, pt in points.items():
        color = left_color if lm_id in [L_SHOULDER, L_ELBOW, L_WRIST] else (right_color if lm_id in [R_SHOULDER, R_ELBOW, R_WRIST] else COLOR_BODY)
        base_r = 14 if color == COLOR_OK else 8
        r = max(4, base_r + pulse)
        cv2.circle(frame, pt, r + 4, color, -1)
        cv2.circle(frame, pt, r, (255, 255, 255), -1)
        
    if NOSE in points: 
        cv2.circle(frame, points[NOSE], max(14, 20 + pulse), COLOR_BODY, 3)
        
    # USER_REQ: Se quitó el texto "PERFECTO" o "X" de las manos para limpiar la vista.

class ParticleSystem:
    def __init__(self): self.particles = []
    def emit_confetti(self, display_w):
        colors = [(0,255,100), (255,200,0), (0,200,255), (255,0,200), (255,255,0)]
        for _ in range(40): self.particles.append({'x': float(random.randint(0, display_w)), 'y': float(random.randint(-50, 0)), 'dx': random.uniform(-2, 2), 'dy': random.uniform(3, 8), 'life': random.randint(30, 60), 'color': random.choice(colors), 'size': random.randint(4, 10)})
    def emit(self, x, y, color, count=20):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 15)
            self.particles.append({'x': float(x), 'y': float(y), 'dx': math.cos(angle)*speed, 'dy': math.sin(angle)*speed, 'life': random.randint(15, 35), 'color': color, 'size': random.randint(3, 7)})
    def update_and_draw(self, frame):
        for p in self.particles[:]:
            p['x'] += p['dx']; p['y'] += p['dy']; p['dy'] += 0.3; p['life'] -= 1
            if p['life'] <= 0: self.particles.remove(p)
            else: cv2.circle(frame, (int(p['x']), int(p['y'])), max(2, int(p['size'] * p['life']/30)), p['color'], -1)

class FloatingText:
    def __init__(self): self.texts = []
    def add(self, text, x, y, color, scale=1.5):
        self.texts.append({'text': text, 'x': x, 'y': float(y), 'color': color, 'life': 40, 'scale': scale})
    def update_and_draw(self, frame):
        for t in self.texts[:]:
            t['y'] -= 2; t['life'] -= 1
            if t['life'] <= 0: self.texts.remove(t)
            else:
                cv2.putText(frame, t['text'], (t['x']+2, int(t['y'])+2), cv2.FONT_HERSHEY_DUPLEX, t['scale'], (0,0,0), int(t['scale']*4))
                cv2.putText(frame, t['text'], (t['x'], int(t['y'])), cv2.FONT_HERSHEY_DUPLEX, t['scale'], t['color'], int(t['scale']*2))

def draw_progress_bar(frame, x, y, w, h, progress, color):
    cv2.rectangle(frame, (x, y), (x + w, y + h), (60, 60, 60), -1)
    if int(w * progress) > 0: cv2.rectangle(frame, (x, y), (x + int(w * progress), y + h), color, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)


COREOGRAFIAS = {
    'macarena.wav': [
        {'name': 'Brazo Der Adelante', 'checks': {'left_arm': check_left_arm_down, 'right_arm': check_right_arm_horizontal}, 'ref': {NOSE: (0.5, 0.12), R_SHOULDER: (0.62, 0.30), R_ELBOW: (0.8, 0.30), R_WRIST: (0.95, 0.30)}, 'color': (255, 200, 0)},
        {'name': 'Brazos Adelante', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_horizontal}, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.3), L_ELBOW: (0.2, 0.3), L_WRIST: (0.05, 0.3), R_SHOULDER: (0.62, 0.3), R_ELBOW: (0.8, 0.3), R_WRIST: (0.95, 0.3)}, 'color': (255, 200, 0)},
        {'name': 'Mano Der Cabeza', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.3), L_WRIST: (0.05, 0.3), R_SHOULDER: (0.62, 0.3), R_WRIST: (0.55, 0.12)}, 'color': (255, 200, 0)},
        {'name': 'Manos en la Cabeza!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.3), L_WRIST: (0.45, 0.12), R_SHOULDER: (0.62, 0.3), R_WRIST: (0.55, 0.12)}, 'color': (255, 200, 0)},
        {'name': 'Mano Der Cintura', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_hip}, 'ref': {NOSE: (0.5, 0.12), L_WRIST: (0.45, 0.12), R_SHOULDER: (0.62, 0.3), R_WRIST: (0.58, 0.65), R_HIP: (0.58, 0.65)}, 'color': (255, 200, 0)},
        {'name': 'Manos Cintura!', 'checks': {'left_arm': check_left_hand_on_hip, 'right_arm': check_right_hand_on_hip}, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.3), L_WRIST: (0.42, 0.65), L_HIP: (0.42, 0.65), R_SHOULDER: (0.62, 0.3), R_WRIST: (0.58, 0.65), R_HIP: (0.58, 0.65)}, 'color': (255, 200, 0)},
        {'name': 'Baila! Mueve Caderas', 'dynamic': True, 'checks': check_shake_hips, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.28, 0.42), R_ELBOW: (0.72, 0.42), L_WRIST: (0.40, 0.60), R_WRIST: (0.60, 0.60), L_HIP: (0.35, 0.65), R_HIP: (0.50, 0.65)}, 'color': (255, 100, 150)},
        {'name': 'Girando!', 'dynamic': True, 'checks': check_spin, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.48, 0.30), R_SHOULDER: (0.52, 0.30), L_ELBOW: (0.45, 0.50), R_ELBOW: (0.55, 0.50), L_WRIST: (0.45, 0.70), R_WRIST: (0.55, 0.70), L_HIP: (0.48, 0.65), R_HIP: (0.52, 0.65)}, 'color': (255, 150, 0)}
    ],
    'asereje.wav': [
        {'name': 'Cruzando Abajo', 'checks': {'left_arm': lambda lm: check_gesture_next(lm), 'right_arm': lambda lm: check_gesture_next(lm)}, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.45, 0.45), R_ELBOW: (0.55, 0.45), L_WRIST: (0.62, 0.30), R_WRIST: (0.38, 0.30), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65)}, 'color': (255, 100, 255)}, 
        {'name': 'Manos en la Cabeza!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.25, 0.20), R_ELBOW: (0.75, 0.20), L_WRIST: (0.45, 0.10), R_WRIST: (0.55, 0.10), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65)}, 'color': (100, 50, 255)},
        {'name': 'Baila! Mueve Caderas', 'dynamic': True, 'checks': check_shake_hips, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.28, 0.42), R_ELBOW: (0.72, 0.42), L_WRIST: (0.40, 0.60), R_WRIST: (0.60, 0.60), L_HIP: (0.35, 0.65), R_HIP: (0.50, 0.65)}, 'color': (255, 100, 150)},
        {'name': 'Mueve los Brazos!', 'dynamic': True, 'checks': check_flail_arms, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.28, 0.15), R_ELBOW: (0.72, 0.45), L_WRIST: (0.20, 0.05), R_WRIST: (0.80, 0.60), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65)}, 'color': (255, 50, 255)},
    ],
    'ymca.wav': [
        {'name': 'Letra Y!', 'checks': {'left_arm': check_left_arm_up, 'right_arm': check_right_arm_up}, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.32, 0.18), R_ELBOW: (0.68, 0.18), L_WRIST: (0.25, 0.05), R_WRIST: (0.75, 0.05)}, 'color': (255, 100, 100)},
        {'name': 'Letra M!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.25, 0.20), R_ELBOW: (0.75, 0.20), L_WRIST: (0.45, 0.10), R_WRIST: (0.55, 0.10)}, 'color': (100, 255, 100)},
        {'name': 'Letra C!', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_up}, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.30, 0.45), R_ELBOW: (0.70, 0.15), L_WRIST: (0.25, 0.60), R_WRIST: (0.75, 0.05)}, 'color': (100, 100, 255)},
        {'name': 'Letra A!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.38, 0.05), R_ELBOW: (0.62, 0.05), L_WRIST: (0.48, 0.0), R_WRIST: (0.52, 0.0)}, 'color': (255, 255, 100)},
    ]
}
COREOGRAFIAS['macarena_real.wav'] = COREOGRAFIAS['macarena.wav']
COREOGRAFIAS['macarena_vocal.wav'] = COREOGRAFIAS['macarena.wav']

# =============================================
def get_next_pose(current_pose, mode, song, coreo_idx):
    if mode == 'COREO' and song in COREOGRAFIAS:
        coreo_idx = (coreo_idx + 1) % len(COREOGRAFIAS[song])
        return COREOGRAFIAS[song][coreo_idx], coreo_idx
    else:
        return random.choice([p for p in POSES if p['name'] != current_pose['name']]), coreo_idx

# =============================================
# MAIN LOOP
# =============================================
def log_metric(mode, pose_name, time_taken, status):
    try:
        with open('metrics.csv', 'a') as f:
            f.write(f"{time.time()},{mode},{pose_name},{time_taken:.3f},{status}\n")
    except Exception as e:
        print(f"Error logging metric: {e}")
def main():
    cap = VideoCaptureAsync(0)
    if not cap.is_opened():
        cap.release()
        cap = VideoCaptureAsync(RTSP_URL)
    if not cap.is_opened():
        cap.release()
        return
    cap.start()
    
    pose_detector = mp_pose.Pose(model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence=0.5, enable_segmentation=False)
    display_w, display_h = 1280, 720
    WINDOW_NAME = "Poses Locas AR"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Optimizaciones: pre-asignar overlays pesados para evitar lag de recolección de basura
    fever_overlay = np.full((display_h, display_w, 3), (255, 0, 255), dtype=np.uint8)
    green_overlay = np.full((display_h, display_w, 3), (0, 255, 0), dtype=np.uint8)
    black_overlay = np.full((display_h, display_w, 3), (0, 0, 0), dtype=np.uint8)

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
    show_menu = True  # Arranca mostrando el menú
    
    score, streak, poses_completed = 0, 0, 0
    fever_gauge = 0
    fever_active = False
    fever_start_time = 0
    fever_duration = 10.0
    shake_time = 0
    multiplier = 1
    current_mode = 'LIBRE'
    current_song = menu_options[selected_idx]['file']
    coreo_idx = 0
    current_pose = random.choice(POSES)
    pose_start_time = time.time()
    match_start = None
    match_required = 0.6
    
    control_gesture_start = None
    control_gesture_required = 1.0
    
    particles = ParticleSystem()
    floating_texts = FloatingText()
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
        
        has_person = results.pose_landmarks is not None
        left_ok, right_ok = False, False
        
        # LOGICA DEL JUEGO (solo avanza si el menú está oculto)
        if not show_menu:
            if has_person:
                lm = results.pose_landmarks.landmark
                
                if check_gesture_next(lm):
                    if control_gesture_start is None: control_gesture_start = current_time
                    hold_progress = min(1.0, (current_time - control_gesture_start) / control_gesture_required)
                    draw_progress_bar(frame, (display_w-300)//2, display_h-150, 300, 20, hold_progress, (0, 100, 255))
                    cv2.putText(frame, "SALTANDO POSE...", ((display_w-300)//2, display_h-160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)
                    
                    if current_time - control_gesture_start >= control_gesture_required:
                        # USER_REQ: Mover textos a un costado para que no tapen el cuerpo
                        floating_texts.add("POSE SALTEADA!", 50, 400, (0, 100, 255), 1.5)
                        play_sound(snd_fail)
                        fever_gauge = max(0, fever_gauge - 25)
                        shake_time = current_time
                        log_metric(current_mode, current_pose['name'], current_time - pose_start_time, 'SKIPPED')
                        current_pose, coreo_idx = get_next_pose(current_pose, current_mode, current_song, coreo_idx)
                        pose_start_time = current_time
                        control_gesture_start, match_start, streak = None, None, 0
                        state.reset()
                else:
                    control_gesture_start = None
                    
                    if current_pose.get('dynamic'):
                        completed, events = current_pose['checks'](state, lm)
                        left_ok, right_ok = True, True  # Coloring skeleton OK
                        
                        # Process dynamic events (e.g. hits)
                        for e in events:
                            if e['type'] == 'hit':
                                play_sound(snd_punch)
                                px = int(e['x'] * display_w)
                                py = int(e['y'] * display_h)
                                particles.emit(px, py, (255, 50, 255), 25)
                                floating_texts.add("BOOM!", px - 50, py - 50, (255, 255, 0), 1.5)
                                
                        if completed:
                            streak += 1; poses_completed += 1
                            if not fever_active:
                                fever_gauge = min(100, fever_gauge + 15)
                                if fever_gauge >= 100:
                                    fever_active = True
                                    fever_start_time = current_time
                                    floating_texts.add("FEVER TIME!", display_w//2 - 150, display_h//2, (0, 255, 255), 3.0)
                            
                            multiplier = 3 if fever_active else (1 + int(streak // 3))
                            points = int(100 * multiplier)
                            score += points
                            
                            play_sound(snd_success)
                            particles.emit_confetti(display_w)
                            particles.emit(display_w // 2, display_h // 2, current_pose['color'], 40)
                            # USER_REQ: Mover textos a un costado para que no tapen el cuerpo
                            floating_texts.add(f"BAILASTE GENIAL! +{points}", 50, 400, (0, 255, 100), 2.0)
                            
                            show_success_flash = True
                            success_flash_time = current_time
                            log_metric(current_mode, current_pose['name'], current_time - pose_start_time, 'COMPLETED')
                            current_pose, coreo_idx = get_next_pose(current_pose, current_mode, current_song, coreo_idx)
                            pose_start_time = current_time
                            state.reset()
                    else:
                        left_ok = current_pose['checks']['left_arm'](lm)
                        right_ok = current_pose['checks']['right_arm'](lm)
                        
                        if left_ok and right_ok:
                            if match_start is None: match_start = current_time
                            hold_progress = min(1.0, (current_time - match_start) / match_required)
                            draw_progress_bar(frame, (display_w-300)//2, display_h-80, 300, 25, hold_progress, (0, 255, 0))
                            cv2.putText(frame, "MANTENE!", ((display_w-300)//2, display_h-90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                            if current_time - match_start >= match_required:
                                streak += 1; poses_completed += 1
                                if not fever_active:
                                    fever_gauge = min(100, fever_gauge + 15)
                                    if fever_gauge >= 100:
                                        fever_active = True
                                        fever_start_time = current_time
                                        floating_texts.add("FEVER TIME!", display_w//2 - 150, display_h//2, (0, 255, 255), 3.0)
                                
                                multiplier = 3 if fever_active else (1 + int(streak // 3))
                                points = int(100 * multiplier)
                                score += points
                                
                                play_sound(snd_success)
                                particles.emit_confetti(display_w)
                                particles.emit(display_w // 2, display_h // 2, current_pose['color'], 30)
                                # USER_REQ: Mover textos a un costado para que no tapen el cuerpo
                                floating_texts.add(f"GENIAL! +{points}", 50, 400, (0, 255, 100), 2.0)
                                if streak >= 3 and not fever_active: floating_texts.add(f"RACHA x{streak}!", 50, 460, (0, 255, 255), 1.5)
                                
                                show_success_flash = True
                                success_flash_time = current_time
                                log_metric(current_mode, current_pose['name'], current_time - pose_start_time, 'COMPLETED')
                                current_pose, coreo_idx = get_next_pose(current_pose, current_mode, current_song, coreo_idx)
                                pose_start_time = current_time
                                match_start = None
                                state.reset()
                        else:
                            match_start = None
                
                draw_skeleton_with_feedback(frame, lm, display_w, display_h, left_ok, right_ok)
                
                # Si es dinámica, dibujamos indicadores de los golpes
                if current_pose.get('dynamic') and state.center_x is not None:
                    cx = int(state.center_x * display_w)
                    cy = int((lm[L_HIP].y + lm[R_HIP].y) / 2.0 * display_h)
                    threshold_px = int(0.04 * display_w)
                    cv2.circle(frame, (cx, cy), 5, (255,255,255), -1)
                    cv2.line(frame, (cx - threshold_px, cy - 50), (cx - threshold_px, cy + 50), (0,255,255), 2)
                    cv2.line(frame, (cx + threshold_px, cy - 50), (cx + threshold_px, cy + 50), (0,255,255), 2)
                    cv2.putText(frame, f"GOLPES: {state.hip_hits}/6", ((display_w-200)//2, display_h-80), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 0, 255), 3)

            else:
                match_start, control_gesture_start = None, None
            
            # UI GLOBAL
            draw_reference(frame, current_pose, display_w - 220, 20, 200, 220)
            pose_text = current_pose['name']
            text_x = (display_w - cv2.getTextSize(pose_text, cv2.FONT_HERSHEY_DUPLEX, 2, 4)[0][0]) // 2
            cv2.putText(frame, pose_text, (text_x + 3, 73), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 0, 0), 6)
            cv2.putText(frame, pose_text, (text_x, 70), cv2.FONT_HERSHEY_DUPLEX, 2, current_pose['color'], 4)
            
            cv2.putText(frame, f"PUNTAJE: {score}", (30, 60), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 0), 8)
            cv2.putText(frame, f"PUNTAJE: {score}", (30, 60), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 255, 255), 3)
            cv2.putText(frame, "Gesto 'Wakanda' o Tecla 'N' / ESPACIO = Saltar | Tecla 'M' o 'C' = Menu", (30, display_h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
            
            # Fever Gauge and Multiplier UI
            cv2.putText(frame, f"MULTI: x{multiplier}", (30, 110), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 150, 255), 3)
            draw_progress_bar(frame, 30, 130, 200, 15, fever_gauge / 100.0, (255, 0, 255))
            if fever_active:
                cv2.putText(frame, "FEVER!", (240, 145), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 0, 255), 2)
            
            particles.update_and_draw(frame)
            floating_texts.update_and_draw(frame)
            
            if show_success_flash and current_time - success_flash_time < 0.3:
                cv2.addWeighted(green_overlay, 0.15, frame, 0.85, 0, frame)
            elif show_success_flash: show_success_flash = False
            
        # FEVER Y SCREEN SHAKE EFFECT
        if fever_active:
            if current_time - fever_start_time > fever_duration:
                fever_active = False
                fever_gauge = 0
                multiplier = 1
            else:
                cv2.addWeighted(fever_overlay, 0.2, frame, 0.8, 0, frame)
                
        if current_time - shake_time < 0.3:
            intensity = 20
            dx = random.randint(-intensity, intensity)
            dy = random.randint(-intensity, intensity)
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            frame = cv2.warpAffine(frame, M, (display_w, display_h))
            
        # ==================================
        # DIBUJAR MENU POR ENCIMA SI ESTÁ ACTIVO
        # ==================================
        if show_menu:
            cv2.addWeighted(black_overlay, 0.8, frame, 0.2, 0, frame)
            
            cv2.putText(frame, "MENU DE CONFIGURACION", (display_w//2 - 350, 150), cv2.FONT_HERSHEY_DUPLEX, 1.8, (0, 255, 255), 3)
            
            # USER_REQ: Scroll view para el menú
            max_visible = 6
            start_idx = max(0, selected_idx - max_visible // 2)
            end_idx = min(len(menu_options), start_idx + max_visible)
            if end_idx - start_idx < max_visible:
                start_idx = max(0, end_idx - max_visible)
                
            for i in range(start_idx, end_idx):
                opt = menu_options[i]
                color = (0, 255, 0) if i == selected_idx else (150, 150, 150)
                prefix = "-> " if i == selected_idx else "   "
                draw_i = i - start_idx
                cv2.putText(frame, prefix + opt['display'], (display_w//2 - 250, 250 + draw_i*70), cv2.FONT_HERSHEY_DUPLEX, 1.2, color, 3)
                
            cv2.putText(frame, "Usa ARRIBA/ABAJO para mover. ENTER para jugar.", (display_w//2 - 450, display_h - 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            
        cv2.imshow(WINDOW_NAME, frame)
        
        # PROCESAMIENTO DE TECLAS
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): 
            break
        elif key == ord('m') or key == ord('c'):
            show_menu = not show_menu
        elif key == ord('n') or key == 32:
            if not show_menu:
                floating_texts.add("POSE SALTEADA!", 50, 400, (0, 100, 255), 1.5)
                play_sound(snd_fail)
                fever_gauge = max(0, fever_gauge - 25)
                shake_time = current_time
                log_metric(current_mode, current_pose['name'], current_time - pose_start_time, 'SKIPPED')
                current_pose, coreo_idx = get_next_pose(current_pose, current_mode, current_song, coreo_idx)
                pose_start_time = current_time
                control_gesture_start, match_start, streak = None, None, 0
                state.reset()
            
        if show_menu:
            if key == 82 or key == ord('w'): # Up
                selected_idx = max(0, selected_idx - 1)
            elif key == 84 or key == ord('s'): # Down
                selected_idx = min(len(menu_options) - 1, selected_idx + 1)
            elif key == 13 or key == 32: # Enter or Space
                show_menu = False
                if HAS_AUDIO and menu_options[selected_idx]['file'] != "Sin Musica":
                    current_song = menu_options[selected_idx]['file']
                    current_mode = menu_options[selected_idx]['type']
                    coreo_idx = 0
                    if current_mode == 'COREO':
                        current_pose = COREOGRAFIAS[current_song][0]
                    else:
                        current_pose = random.choice(POSES)
                        
                    # USER_REQ: Canciones infinitas
                    pygame.mixer.music.load(current_song)
                    pygame.mixer.music.play(-1) # -1 significa loop infinito
                    pygame.mixer.music.set_volume(0.4)
                    
        # USER_REQ: Forzar bucle infinito. Si pygame frena la música por algún bug, la obligamos a arrancar de nuevo.
        if HAS_AUDIO and current_song and current_song != "Sin Musica" and not show_menu:
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)
                
        try:
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1: break
        except: break
    
    cap.stop()
    pose_detector.close()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
