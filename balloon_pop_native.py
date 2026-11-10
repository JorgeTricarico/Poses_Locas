import cv2
import mediapipe as mp
import threading
import time
import math
import random
import numpy as np

RTSP_URL = "rtsp://jorge.tricarico:3424Trica@192.168.0.148:554/stream1"

class VideoCaptureAsync:
    def __init__(self, src=0):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.read_lock = threading.Lock()
    def is_opened(self):
        return self.cap.isOpened() and self.grabbed
    def release(self):
        if self.started:
            self.stop()
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

def dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

# =============================================
# CRIATURAS - Cada una se dibuja diferente
# =============================================

CREATURE_TYPES = [
    {
        'name': 'fantasma',
        'color': (255, 255, 255),   # Blanco
        'accent': (200, 200, 255),  # Lavanda
        'points': 100,
        'eye_color': (50, 50, 50),
    },
    {
        'name': 'murcielago',
        'color': (80, 40, 120),     # Morado oscuro
        'accent': (150, 80, 200),   # Morado claro
        'points': 150,
        'eye_color': (0, 0, 255),   # Rojo
    },
    {
        'name': 'calavera',
        'color': (220, 220, 220),   # Gris claro
        'accent': (180, 180, 180),
        'points': 200,
        'eye_color': (0, 0, 0),
    },
    {
        'name': 'araña',
        'color': (40, 40, 40),      # Negro
        'accent': (80, 0, 0),       # Rojo oscuro
        'points': 250,
        'eye_color': (0, 0, 255),   # Rojo brillante
    },
    {
        'name': 'calabaza',
        'color': (0, 120, 255),     # Naranja (BGR)
        'accent': (0, 80, 200),
        'points': 100,
        'eye_color': (0, 255, 255), # Amarillo
    },
    {
        'name': 'ojo',
        'color': (200, 200, 255),   # Blanco rosado
        'accent': (0, 0, 200),      # Rojo iris
        'points': 300,
        'eye_color': (0, 0, 0),
    },
    {
        'name': 'slime',
        'color': (0, 220, 80),      # Verde brillante
        'accent': (0, 180, 60),
        'points': 50,
        'eye_color': (0, 0, 0),
    },
    {
        'name': 'demonio',
        'color': (0, 0, 200),       # Rojo oscuro
        'accent': (0, 0, 255),      # Rojo brillante
        'points': 350,
        'eye_color': (0, 255, 255), # Amarillo
    },
]


def draw_ghost(frame, cx, cy, r, ctype, phase):
    """Fantasma flotante con cola ondulada"""
    color = ctype['color']
    # Cuerpo principal - semicirculo arriba
    cv2.ellipse(frame, (cx, cy - r//4), (r, r), 0, 180, 360, color, -1)
    # Rectangulo del cuerpo
    cv2.rectangle(frame, (cx - r, cy - r//4), (cx + r, cy + r//2), color, -1)
    # Cola ondulada abajo
    wave_pts = []
    num_waves = 4
    for i in range(num_waves * 2 + 1):
        wx = cx - r + (2 * r * i) // (num_waves * 2)
        wy = cy + r//2 + int(math.sin(phase + i * math.pi / 2) * r//4)
        wave_pts.append([wx, wy])
    wave_pts.append([cx + r, cy - r//4])
    wave_pts.append([cx - r, cy - r//4])
    pts = np.array(wave_pts, np.int32)
    cv2.fillPoly(frame, [pts], color)
    # Ojos
    eye_r = max(r//5, 4)
    cv2.circle(frame, (cx - r//3, cy - r//4), eye_r, ctype['eye_color'], -1)
    cv2.circle(frame, (cx + r//3, cy - r//4), eye_r, ctype['eye_color'], -1)
    # Pupila
    pupil_r = max(eye_r//2, 2)
    cv2.circle(frame, (cx - r//3, cy - r//4), pupil_r, (0,0,0), -1)
    cv2.circle(frame, (cx + r//3, cy - r//4), pupil_r, (0,0,0), -1)
    # Boca sorprendida
    cv2.ellipse(frame, (cx, cy + r//6), (r//5, r//6), 0, 0, 360, ctype['eye_color'], -1)


def draw_bat(frame, cx, cy, r, ctype, phase):
    """Murciélago con alas que se mueven"""
    color = ctype['color']
    wing_flap = int(math.sin(phase * 3) * r//3)
    # Cuerpo ovalado
    cv2.ellipse(frame, (cx, cy), (r//2, int(r*0.7)), 0, 0, 360, color, -1)
    # Ala izquierda
    wing_l = np.array([
        [cx - r//3, cy],
        [cx - r - r//3, cy - r//2 + wing_flap],
        [cx - r//2, cy - r//4 + wing_flap//2],
        [cx - r, cy + r//4 + wing_flap],
        [cx - r//4, cy + r//3],
    ], np.int32)
    cv2.fillPoly(frame, [wing_l], color)
    # Ala derecha
    wing_r = np.array([
        [cx + r//3, cy],
        [cx + r + r//3, cy - r//2 + wing_flap],
        [cx + r//2, cy - r//4 + wing_flap//2],
        [cx + r, cy + r//4 + wing_flap],
        [cx + r//4, cy + r//3],
    ], np.int32)
    cv2.fillPoly(frame, [wing_r], color)
    # Ojos rojos brillantes
    eye_r = max(r//6, 3)
    cv2.circle(frame, (cx - r//5, cy - r//6), eye_r, ctype['eye_color'], -1)
    cv2.circle(frame, (cx + r//5, cy - r//6), eye_r, ctype['eye_color'], -1)
    # Orejas puntiagudas
    ear_l = np.array([[cx - r//4, cy - int(r*0.6)], [cx - r//2, cy - r], [cx, cy - int(r*0.5)]], np.int32)
    ear_r = np.array([[cx + r//4, cy - int(r*0.6)], [cx + r//2, cy - r], [cx, cy - int(r*0.5)]], np.int32)
    cv2.fillPoly(frame, [ear_l], color)
    cv2.fillPoly(frame, [ear_r], color)


def draw_skull(frame, cx, cy, r, ctype, phase):
    """Calavera con mandíbula"""
    color = ctype['color']
    # Cabeza ovalada
    cv2.ellipse(frame, (cx, cy - r//6), (r, int(r*0.85)), 0, 0, 360, color, -1)
    # Mandíbula
    jaw_open = int(abs(math.sin(phase * 2)) * r//6)
    cv2.ellipse(frame, (cx, cy + r//2 + jaw_open), (int(r*0.7), r//3), 0, 0, 360, color, -1)
    # Cuencas de los ojos (oscuras)
    cv2.ellipse(frame, (cx - r//3, cy - r//4), (r//4, r//3), 0, 0, 360, ctype['eye_color'], -1)
    cv2.ellipse(frame, (cx + r//3, cy - r//4), (r//4, r//3), 0, 0, 360, ctype['eye_color'], -1)
    # Brillo rojo en los ojos
    cv2.circle(frame, (cx - r//3, cy - r//4), max(r//8, 2), (0, 0, 200), -1)
    cv2.circle(frame, (cx + r//3, cy - r//4), max(r//8, 2), (0, 0, 200), -1)
    # Nariz triangular
    nose = np.array([[cx, cy + r//10], [cx - r//8, cy + r//4], [cx + r//8, cy + r//4]], np.int32)
    cv2.fillPoly(frame, [nose], ctype['eye_color'])
    # Dientes
    for i in range(5):
        tx = cx - r//2 + (r * i) // 4
        cv2.rectangle(frame, (tx, cy + r//3 + jaw_open), (tx + r//6, cy + r//2 + jaw_open), color, -1)
        cv2.rectangle(frame, (tx, cy + r//3 + jaw_open), (tx + r//6, cy + r//2 + jaw_open), (0,0,0), 1)


def draw_spider(frame, cx, cy, r, ctype, phase):
    """Araña con patas que se mueven"""
    color = ctype['color']
    # Abdomen
    cv2.ellipse(frame, (cx, cy + r//4), (int(r*0.6), int(r*0.5)), 0, 0, 360, color, -1)
    # Cabeza
    cv2.circle(frame, (cx, cy - r//3), int(r*0.4), color, -1)
    # Patas (4 a cada lado)
    for i in range(4):
        angle_offset = math.sin(phase * 3 + i) * 0.3
        # Pata izquierda
        mid_x = cx - r - int(math.cos(0.5 + angle_offset) * r//2)
        mid_y = cy - r//4 + i * r//3 + int(math.sin(phase * 3 + i) * 5)
        end_x = mid_x - r//3
        end_y = mid_y + r//2
        cv2.line(frame, (cx - int(r*0.5), cy - r//4 + i * r//3), (mid_x, mid_y), color, max(r//12, 2))
        cv2.line(frame, (mid_x, mid_y), (end_x, end_y), color, max(r//12, 2))
        # Pata derecha
        mid_x = cx + r + int(math.cos(0.5 + angle_offset) * r//2)
        end_x = mid_x + r//3
        cv2.line(frame, (cx + int(r*0.5), cy - r//4 + i * r//3), (mid_x, mid_y), color, max(r//12, 2))
        cv2.line(frame, (mid_x, mid_y), (end_x, end_y), color, max(r//12, 2))
    # Ojos multiples (como araña)
    for ex, ey in [(-r//5, -r//3), (r//5, -r//3), (-r//8, -r//2), (r//8, -r//2)]:
        cv2.circle(frame, (cx + ex, cy + ey), max(r//10, 2), ctype['eye_color'], -1)
    # Colmillos
    cv2.line(frame, (cx - r//8, cy - r//6), (cx - r//6, cy + r//8), (200, 200, 200), max(r//12, 2))
    cv2.line(frame, (cx + r//8, cy - r//6), (cx + r//6, cy + r//8), (200, 200, 200), max(r//12, 2))


def draw_pumpkin(frame, cx, cy, r, ctype, phase):
    """Calabaza de Halloween con cara tallada"""
    color = ctype['color']
    # Forma de calabaza (ovalada con segmentos)
    cv2.ellipse(frame, (cx, cy), (r, int(r*0.85)), 0, 0, 360, color, -1)
    # Segmentos (líneas verticales suaves)
    for sx in [-r//2, 0, r//2]:
        cv2.ellipse(frame, (cx + sx, cy), (r//8, int(r*0.85)), 0, 0, 360, ctype['accent'], 2)
    # Tallo
    cv2.rectangle(frame, (cx - r//8, cy - r - r//6), (cx + r//8, cy - int(r*0.75)), (0, 100, 0), -1)
    # Ojos triangulares tallados
    eye_l = np.array([[cx - r//2, cy - r//4], [cx - r//4, cy - r//2], [cx - r//6, cy - r//6]], np.int32)
    eye_r = np.array([[cx + r//2, cy - r//4], [cx + r//4, cy - r//2], [cx + r//6, cy - r//6]], np.int32)
    cv2.fillPoly(frame, [eye_l], ctype['eye_color'])
    cv2.fillPoly(frame, [eye_r], ctype['eye_color'])
    # Boca tallada con dientes
    mouth_pts = np.array([
        [cx - r//2, cy + r//6],
        [cx - r//3, cy + r//2],
        [cx - r//6, cy + r//4],
        [cx, cy + r//2],
        [cx + r//6, cy + r//4],
        [cx + r//3, cy + r//2],
        [cx + r//2, cy + r//6],
    ], np.int32)
    cv2.fillPoly(frame, [mouth_pts], ctype['eye_color'])
    # Brillo flickering en ojos
    if int(phase * 10) % 3 != 0:
        cv2.circle(frame, (cx - r//3, cy - r//3), max(r//10, 2), (0, 200, 255), -1)
        cv2.circle(frame, (cx + r//3, cy - r//3), max(r//10, 2), (0, 200, 255), -1)


def draw_eyeball(frame, cx, cy, r, ctype, phase):
    """Ojo gigante flotante que mira en distintas direcciones"""
    # Esclerótica (blanco del ojo)
    cv2.circle(frame, (cx, cy), r, ctype['color'], -1)
    cv2.circle(frame, (cx, cy), r, (150, 150, 180), 2)
    # Venas
    for i in range(6):
        angle = i * math.pi / 3 + phase * 0.5
        vx = cx + int(math.cos(angle) * r * 0.7)
        vy = cy + int(math.sin(angle) * r * 0.7)
        cv2.line(frame, (cx, cy), (vx, vy), (0, 0, 180), 1)
    # Iris
    iris_r = int(r * 0.5)
    look_x = cx + int(math.sin(phase) * r * 0.2)
    look_y = cy + int(math.cos(phase * 0.7) * r * 0.2)
    cv2.circle(frame, (look_x, look_y), iris_r, ctype['accent'], -1)
    # Pupila
    pupil_r = int(r * 0.25)
    cv2.circle(frame, (look_x, look_y), pupil_r, (0, 0, 0), -1)
    # Brillo
    cv2.circle(frame, (look_x - iris_r//3, look_y - iris_r//3), max(r//8, 2), (255, 255, 255), -1)


def draw_slime(frame, cx, cy, r, ctype, phase):
    """Slime gelatinoso que rebota"""
    color = ctype['color']
    squish = math.sin(phase * 4) * 0.15
    w = int(r * (1.0 + squish))
    h = int(r * (1.0 - squish))
    # Cuerpo gelatinoso
    cv2.ellipse(frame, (cx, cy), (w, h), 0, 0, 360, color, -1)
    # Brillo (highlight)
    cv2.ellipse(frame, (cx - w//4, cy - h//3), (w//4, h//4), -20, 0, 360, (150, 255, 180), -1)
    # Gotas cayendo
    for i in range(3):
        dx = random.randint(-w//2, w//2)
        dy = r + random.randint(0, r//3)
        dr = max(r//8, 3)
        cv2.circle(frame, (cx + dx, cy + dy), dr, color, -1)
    # Ojos grandes kawaii
    eye_r = max(r//4, 5)
    cv2.circle(frame, (cx - w//4, cy - h//6), eye_r, (255, 255, 255), -1)
    cv2.circle(frame, (cx + w//4, cy - h//6), eye_r, (255, 255, 255), -1)
    cv2.circle(frame, (cx - w//4, cy - h//6), eye_r//2, ctype['eye_color'], -1)
    cv2.circle(frame, (cx + w//4, cy - h//6), eye_r//2, ctype['eye_color'], -1)
    # Sonrisa
    cv2.ellipse(frame, (cx, cy + h//4), (w//4, h//6), 0, 0, 180, ctype['eye_color'], 2)


def draw_demon(frame, cx, cy, r, ctype, phase):
    """Demonio con cuernos y aura de fuego"""
    color = ctype['color']
    # Aura de fuego (detrás)
    for i in range(5):
        aura_r = r + r//4 + i * 3
        alpha_color = (0, int(80 + i * 30), int(200 + i * 10))
        angle = phase * 2 + i * 1.2
        ox = int(math.sin(angle) * 3)
        oy = int(math.cos(angle) * 3)
        cv2.circle(frame, (cx + ox, cy + oy), aura_r, alpha_color, 2)
    # Cabeza
    cv2.circle(frame, (cx, cy), r, color, -1)
    # Cuernos
    horn_l = np.array([[cx - r//2, cy - r + r//6], [cx - r, cy - r - r//2], [cx - r//6, cy - r + r//4]], np.int32)
    horn_r = np.array([[cx + r//2, cy - r + r//6], [cx + r, cy - r - r//2], [cx + r//6, cy - r + r//4]], np.int32)
    cv2.fillPoly(frame, [horn_l], (0, 0, 100))
    cv2.fillPoly(frame, [horn_r], (0, 0, 100))
    # Ojos amarillos con pupilas verticales
    eye_r = max(r//4, 4)
    cv2.circle(frame, (cx - r//3, cy - r//6), eye_r, ctype['eye_color'], -1)
    cv2.circle(frame, (cx + r//3, cy - r//6), eye_r, ctype['eye_color'], -1)
    # Pupilas de gato (verticales)
    cv2.ellipse(frame, (cx - r//3, cy - r//6), (max(eye_r//4, 1), eye_r), 0, 0, 360, (0,0,0), -1)
    cv2.ellipse(frame, (cx + r//3, cy - r//6), (max(eye_r//4, 1), eye_r), 0, 0, 360, (0,0,0), -1)
    # Sonrisa maligna
    cv2.ellipse(frame, (cx, cy + r//3), (r//2, r//4), 0, 0, 180, (0, 0, 0), -1)
    # Dientitos
    for i in range(4):
        tx = cx - r//3 + (2 * r // 3 * i) // 3
        cv2.line(frame, (tx, cy + r//3), (tx, cy + r//3 + r//6), (255, 255, 255), max(r//12, 2))


# Mapa de funciones de dibujo
DRAW_FUNCTIONS = {
    'fantasma': draw_ghost,
    'murcielago': draw_bat,
    'calavera': draw_skull,
    'araña': draw_spider,
    'calabaza': draw_pumpkin,
    'ojo': draw_eyeball,
    'slime': draw_slime,
    'demonio': draw_demon,
}

# Textos de explosión por criatura
POP_TEXTS = {
    'fantasma': 'BUUU!',
    'murcielago': 'SPLAT!',
    'calavera': 'CRACK!',
    'araña': 'SQUISH!',
    'calabaza': 'SMASH!',
    'ojo': 'SPLORCH!',
    'slime': 'GLORP!',
    'demonio': 'BOOM!',
}


# Dividimos la pantalla en carriles para distribuir mejor
SPAWN_LANES = 8  # Cantidad de carriles horizontales
_last_lanes = []  # Historial de carriles recientes para evitar repetir

def spawn_creature(display_w, display_h):
    """Crea una nueva criatura aleatoria, distribuida en carriles"""
    ctype = random.choice(CREATURE_TYPES)
    
    # Elegir carril evitando los últimos usados
    margin = 100
    lane_width = (display_w - 2 * margin) // SPAWN_LANES
    available_lanes = [i for i in range(SPAWN_LANES) if i not in _last_lanes]
    if not available_lanes:
        available_lanes = list(range(SPAWN_LANES))
        _last_lanes.clear()
    
    lane = random.choice(available_lanes)
    _last_lanes.append(lane)
    if len(_last_lanes) > 3:
        _last_lanes.pop(0)
    
    # Posición X dentro del carril con algo de variación
    lane_center = margin + lane * lane_width + lane_width // 2
    x = lane_center + random.randint(-lane_width // 4, lane_width // 4)
    x = max(margin, min(display_w - margin, x))
    
    return {
        'x': x,
        'y': display_h + 100,
        'r': random.randint(40, 90),
        'speed': random.randint(3, 8),
        'type': ctype,
        'wobble_offset': random.uniform(0, 2 * math.pi),
        'wobble_speed': random.uniform(0.05, 0.12),
        'spawn_time': time.time(),
    }


def main():
    # Intentar cámara USB primero, luego RTSP
    print("Buscando cámara USB...")
    cap = VideoCaptureAsync(0)
    if not cap.is_opened():
        cap.release()
        print("Cámara USB no encontrada. Buscando cámara Tapo...")
        cap = VideoCaptureAsync(RTSP_URL)
    
    if not cap.is_opened():
        cap.release()
        print("No se encontró ninguna cámara.")
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(frame, "No hay camara", (300, 360), cv2.FONT_HERSHEY_DUPLEX, 3, (0, 0, 255), 5)
        cv2.imshow("Monster Pop AR - Caza Monstruos!", frame)
        cv2.waitKey(4000)
        cv2.destroyAllWindows()
        return
    
    cap.start()
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5, 
        max_num_hands=4
    )
    mp_draw = mp.solutions.drawing_utils
    
    display_w, display_h = 1280, 720
    
    creatures = []
    particles = []
    pop_texts = []  # Textos flotantes de explosión
    score = 0
    last_wave_time = time.time()
    combo = 0
    combo_timer = 0
    
    cv2.namedWindow("Monster Pop AR - Caza Monstruos!", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Monster Pop AR - Caza Monstruos!", display_w, display_h)
    
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
            
        frame = cv2.resize(frame, (display_w, display_h))
        frame = cv2.flip(frame, 1) # Efecto espejo natural
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = hands.process(rgb_frame)
        current_time = time.time()
        
        # =============================
        # SPAWN: Caudal controlado
        # =============================
        MAX_CREATURES = 12  # Máximo de criaturas en pantalla a la vez
        
        # Spawn individual: 1 de cada 15 frames (~2 por segundo a 30fps)
        if len(creatures) < MAX_CREATURES and random.randint(1, 15) == 1:
            creatures.append(spawn_creature(display_w, display_h))
        
        # Oleadas cada 6 segundos: aparecen 2-3 criaturas
        if current_time - last_wave_time > 6.0 and len(creatures) < MAX_CREATURES:
            wave_size = random.randint(2, 3)
            for _ in range(wave_size):
                if len(creatures) < MAX_CREATURES:
                    creatures.append(spawn_creature(display_w, display_h))
                last_wave_time = current_time
            
        # Mover criaturas hacia arriba con wobble
        for c in creatures:
            c['y'] -= c['speed']
            c['x'] += int(math.sin(current_time * 5 * c['wobble_speed'] + c['wobble_offset']) * 4)
            # Mantener dentro de pantalla horizontalmente
            c['x'] = max(c['r'], min(display_w - c['r'], c['x']))
            
        # Eliminar criaturas que escapan
        for c in creatures[:]:
            if c['y'] + c['r'] < -50:
                creatures.remove(c)
        
        # =============================
        # DIBUJAR CRIATURAS
        # =============================
        phase = current_time  # Fase de animación basada en tiempo
        for c in creatures:
            ctype = c['type']
            draw_fn = DRAW_FUNCTIONS.get(ctype['name'])
            if draw_fn:
                # Fase individual para que cada criatura se anime diferente
                individual_phase = phase + c['wobble_offset']
                draw_fn(frame, c['x'], int(c['y']), c['r'], ctype, individual_phase)
                
        # =============================
        # PARTICULAS DE EXPLOSION
        # =============================
        for p in particles[:]:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['dy'] += 0.5  # Gravedad
            p['life'] -= 1
            if p['life'] <= 0:
                particles.remove(p)
            else:
                size = max(2, p['life']//2)
                cv2.circle(frame, (int(p['x']), int(p['y'])), size, p['color'], -1)
                
        # =============================
        # TEXTOS FLOTANTES
        # =============================
        for pt in pop_texts[:]:
            pt['y'] -= 3  # Flotar hacia arriba
            pt['life'] -= 1
            if pt['life'] <= 0:
                pop_texts.remove(pt)
            else:
                alpha = min(255, pt['life'] * 8)
                scale = 1.0 + (30 - pt['life']) * 0.02
                cv2.putText(frame, pt['text'], (pt['x'] - 50, int(pt['y'])), 
                           cv2.FONT_HERSHEY_DUPLEX, scale, pt['color'], 4)
                cv2.putText(frame, pt['text'], (pt['x'] - 50, int(pt['y'])), 
                           cv2.FONT_HERSHEY_DUPLEX, scale, (255, 255, 255), 2)
                # Mostrar puntos
                pts_text = f"+{pt['points']}"
                cv2.putText(frame, pts_text, (pt['x'] - 20, int(pt['y']) + 35), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                
        # =============================
        # COMBO TIMER
        # =============================
        if combo > 1 and current_time - combo_timer < 2.0:
            combo_text = f"COMBO x{combo}!"
            cv2.putText(frame, combo_text, (display_w//2 - 100, 150), 
                       cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 0), 8)
            cv2.putText(frame, combo_text, (display_w//2 - 100, 150), 
                       cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 255, 255), 3)
        elif current_time - combo_timer >= 2.0:
            combo = 0
                
        # =============================
        # INTERACCION CON MANOS
        # =============================
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                hand_points = [(int(lm.x * display_w), int(lm.y * display_h)) for lm in hand_landmarks.landmark]
                
                # Esferas de energía en las yemas
                for tip_idx in [4, 8, 12, 16, 20]:
                    tx, ty = hand_points[tip_idx]
                    # Aura brillante
                    cv2.circle(frame, (tx, ty), 18, (0, 100, 255), 2)
                    cv2.circle(frame, (tx, ty), 12, (0, 200, 255), -1)
                    cv2.circle(frame, (tx, ty), 6, (0, 255, 255), -1)
                
                # Colisiones con CUALQUIER punto de la mano
                for c in creatures[:]:
                    popped = False
                    pop_x, pop_y = 0, 0
                    
                    for px, py in hand_points:
                        if dist((px, py), (c['x'], c['y'])) < c['r']:
                            popped = True
                            pop_x, pop_y = px, py
                            break
                            
                    if popped:
                        ctype = c['type']
                        creatures.remove(c)
                        
                        # Combo
                        combo += 1
                        combo_timer = current_time
                        combo_multiplier = min(combo, 5)
                        points = ctype['points'] * combo_multiplier
                        score += points
                        
                        # Partículas de explosión (más y más coloridas)
                        pop_color = ctype['color']
                        accent = ctype['accent']
                        for _ in range(25):
                            angle = random.uniform(0, 2 * math.pi)
                            speed = random.uniform(5, 25)
                            particles.append({
                                'x': pop_x, 'y': pop_y,
                                'dx': math.cos(angle) * speed,
                                'dy': math.sin(angle) * speed,
                                'life': random.randint(15, 35),
                                'color': random.choice([pop_color, accent, (255,255,255)])
                            })
                            
                        # Texto de explosión flotante
                        pop_text = POP_TEXTS.get(ctype['name'], 'POP!')
                        pop_texts.append({
                            'text': pop_text,
                            'x': pop_x,
                            'y': float(pop_y),
                            'life': 30,
                            'color': pop_color,
                            'points': points,
                        })
                        
                        # Flash de impacto
                        cv2.circle(frame, (pop_x, pop_y), c['r'] + 20, (255, 255, 255), 4)
                        cv2.circle(frame, (pop_x, pop_y), c['r'] + 35, ctype['accent'], 2)
                            
        # =============================
        # UI - PUNTAJE
        # =============================
        # Sombra
        cv2.putText(frame, f"PUNTAJE: {score}", (30, 80), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 0, 0), 10)
        # Texto principal
        cv2.putText(frame, f"PUNTAJE: {score}", (30, 80), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 255, 255), 4)
        
        # Contador de criaturas en pantalla
        cv2.putText(frame, f"Criaturas: {len(creatures)}", (30, 130), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 5)
        cv2.putText(frame, f"Criaturas: {len(creatures)}", (30, 130), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 255), 2)

        cv2.imshow("Monster Pop AR - Caza Monstruos!", frame)
        
        # Manejo correcto del cierre (Q o click en la X de la ventana)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        try:
            if cv2.getWindowProperty("Monster Pop AR - Caza Monstruos!", cv2.WND_PROP_VISIBLE) < 1:
                break
        except:
            break
            
    cap.stop()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
