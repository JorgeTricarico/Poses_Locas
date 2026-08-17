import cv2
import mediapipe as mp
import threading
import time
import math
import random
import numpy as np
from flask import Flask, render_template_string, Response

RTSP_URL = "rtsp://jorge.tricarico:3424Trica@192.168.0.148:554/stream1"
app = Flask(__name__)

class VideoCaptureAsync:
    def __init__(self, src=0):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.read_lock = threading.Lock()
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
# CRIATURAS
# =============================================

CREATURE_TYPES = [
    {'name': 'fantasma',   'color': (255,255,255), 'accent': (200,200,255), 'points': 100, 'eye_color': (50,50,50)},
    {'name': 'murcielago', 'color': (80,40,120),   'accent': (150,80,200),  'points': 150, 'eye_color': (0,0,255)},
    {'name': 'calavera',   'color': (220,220,220), 'accent': (180,180,180), 'points': 200, 'eye_color': (0,0,0)},
    {'name': 'calabaza',   'color': (0,120,255),   'accent': (0,80,200),    'points': 100, 'eye_color': (0,255,255)},
    {'name': 'ojo',        'color': (200,200,255), 'accent': (0,0,200),     'points': 300, 'eye_color': (0,0,0)},
    {'name': 'slime',      'color': (0,220,80),    'accent': (0,180,60),    'points': 50,  'eye_color': (0,0,0)},
]

POP_TEXTS = {
    'fantasma': 'BUUU!', 'murcielago': 'SPLAT!', 'calavera': 'CRACK!',
    'calabaza': 'SMASH!', 'ojo': 'SPLORCH!', 'slime': 'GLORP!',
}

def draw_ghost(frame, cx, cy, r, ctype, phase):
    color = ctype['color']
    cv2.ellipse(frame, (cx, cy - r//4), (r, r), 0, 180, 360, color, -1)
    cv2.rectangle(frame, (cx - r, cy - r//4), (cx + r, cy + r//2), color, -1)
    wave_pts = []
    for i in range(9):
        wx = cx - r + (2 * r * i) // 8
        wy = cy + r//2 + int(math.sin(phase + i * math.pi / 2) * r//4)
        wave_pts.append([wx, wy])
    wave_pts.append([cx + r, cy - r//4])
    wave_pts.append([cx - r, cy - r//4])
    cv2.fillPoly(frame, [np.array(wave_pts, np.int32)], color)
    eye_r = max(r//5, 3)
    cv2.circle(frame, (cx - r//3, cy - r//4), eye_r, ctype['eye_color'], -1)
    cv2.circle(frame, (cx + r//3, cy - r//4), eye_r, ctype['eye_color'], -1)
    cv2.ellipse(frame, (cx, cy + r//6), (r//5, r//6), 0, 0, 360, ctype['eye_color'], -1)

def draw_bat(frame, cx, cy, r, ctype, phase):
    color = ctype['color']
    wing_flap = int(math.sin(phase * 3) * r//3)
    cv2.ellipse(frame, (cx, cy), (r//2, int(r*0.7)), 0, 0, 360, color, -1)
    wing_l = np.array([[cx-r//3,cy],[cx-r-r//3,cy-r//2+wing_flap],[cx-r//2,cy-r//4+wing_flap//2],[cx-r,cy+r//4+wing_flap],[cx-r//4,cy+r//3]], np.int32)
    wing_r = np.array([[cx+r//3,cy],[cx+r+r//3,cy-r//2+wing_flap],[cx+r//2,cy-r//4+wing_flap//2],[cx+r,cy+r//4+wing_flap],[cx+r//4,cy+r//3]], np.int32)
    cv2.fillPoly(frame, [wing_l], color)
    cv2.fillPoly(frame, [wing_r], color)
    cv2.circle(frame, (cx-r//5,cy-r//6), max(r//6,2), ctype['eye_color'], -1)
    cv2.circle(frame, (cx+r//5,cy-r//6), max(r//6,2), ctype['eye_color'], -1)

def draw_skull(frame, cx, cy, r, ctype, phase):
    color = ctype['color']
    cv2.ellipse(frame, (cx, cy-r//6), (r, int(r*0.85)), 0, 0, 360, color, -1)
    jaw_open = int(abs(math.sin(phase*2)) * r//6)
    cv2.ellipse(frame, (cx, cy+r//2+jaw_open), (int(r*0.7), r//3), 0, 0, 360, color, -1)
    cv2.ellipse(frame, (cx-r//3,cy-r//4), (r//4,r//3), 0, 0, 360, ctype['eye_color'], -1)
    cv2.ellipse(frame, (cx+r//3,cy-r//4), (r//4,r//3), 0, 0, 360, ctype['eye_color'], -1)
    cv2.circle(frame, (cx-r//3,cy-r//4), max(r//8,2), (0,0,200), -1)
    cv2.circle(frame, (cx+r//3,cy-r//4), max(r//8,2), (0,0,200), -1)

def draw_pumpkin(frame, cx, cy, r, ctype, phase):
    color = ctype['color']
    cv2.ellipse(frame, (cx, cy), (r, int(r*0.85)), 0, 0, 360, color, -1)
    cv2.rectangle(frame, (cx-r//8, cy-r-r//6), (cx+r//8, cy-int(r*0.75)), (0,100,0), -1)
    eye_l = np.array([[cx-r//2,cy-r//4],[cx-r//4,cy-r//2],[cx-r//6,cy-r//6]], np.int32)
    eye_r = np.array([[cx+r//2,cy-r//4],[cx+r//4,cy-r//2],[cx+r//6,cy-r//6]], np.int32)
    cv2.fillPoly(frame, [eye_l], ctype['eye_color'])
    cv2.fillPoly(frame, [eye_r], ctype['eye_color'])

def draw_eyeball(frame, cx, cy, r, ctype, phase):
    cv2.circle(frame, (cx,cy), r, ctype['color'], -1)
    iris_r = int(r*0.5)
    look_x = cx + int(math.sin(phase)*r*0.2)
    look_y = cy + int(math.cos(phase*0.7)*r*0.2)
    cv2.circle(frame, (look_x,look_y), iris_r, ctype['accent'], -1)
    cv2.circle(frame, (look_x,look_y), int(r*0.25), (0,0,0), -1)
    cv2.circle(frame, (look_x-iris_r//3, look_y-iris_r//3), max(r//8,2), (255,255,255), -1)

def draw_slime(frame, cx, cy, r, ctype, phase):
    color = ctype['color']
    squish = math.sin(phase*4)*0.15
    w, h = int(r*(1+squish)), int(r*(1-squish))
    cv2.ellipse(frame, (cx,cy), (w,h), 0, 0, 360, color, -1)
    cv2.ellipse(frame, (cx-w//4,cy-h//3), (w//4,h//4), -20, 0, 360, (150,255,180), -1)
    eye_r = max(r//4,4)
    cv2.circle(frame, (cx-w//4,cy-h//6), eye_r, (255,255,255), -1)
    cv2.circle(frame, (cx+w//4,cy-h//6), eye_r, (255,255,255), -1)
    cv2.circle(frame, (cx-w//4,cy-h//6), eye_r//2, (0,0,0), -1)
    cv2.circle(frame, (cx+w//4,cy-h//6), eye_r//2, (0,0,0), -1)
    cv2.ellipse(frame, (cx, cy+h//4), (w//4, h//6), 0, 0, 180, (0,0,0), 2)

DRAW_FUNCTIONS = {
    'fantasma': draw_ghost, 'murcielago': draw_bat, 'calavera': draw_skull,
    'calabaza': draw_pumpkin, 'ojo': draw_eyeball, 'slime': draw_slime,
}

def spawn_creature(display_w, display_h):
    ctype = random.choice(CREATURE_TYPES)
    return {
        'x': random.randint(50, display_w - 50), 'y': display_h + 50,
        'r': random.randint(25, 45), 'speed': random.randint(3, 8),
        'type': ctype, 'wobble_offset': random.uniform(0, 2*math.pi),
        'wobble_speed': random.uniform(0.05, 0.12),
    }

def generate_frames():
    cap = VideoCaptureAsync(RTSP_URL).start()
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7, max_num_hands=2)
    mp_draw = mp.solutions.drawing_utils
    
    display_w, display_h = 640, 480
    creatures = []
    particles = []
    pop_texts = []
    score = 0
    lives = 5
    game_over = False
    last_wave = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
            
        frame = cv2.resize(frame, (display_w, display_h))
        frame = cv2.flip(frame, 1) 
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        current_time = time.time()
        
        if not game_over:
            # Spawn frecuente
            if random.randint(1, 6) == 1:
                creatures.append(spawn_creature(display_w, display_h))
            # Oleadas
            if current_time - last_wave > 4.0:
                for _ in range(random.randint(2, 4)):
                    creatures.append(spawn_creature(display_w, display_h))
                last_wave = current_time
                
            for c in creatures:
                c['y'] -= c['speed']
                c['x'] += int(math.sin(current_time * 5 * c['wobble_speed'] + c['wobble_offset']) * 3)
                c['x'] = max(c['r'], min(display_w - c['r'], c['x']))
                
            for c in creatures[:]:
                if c['y'] + c['r'] < 0:
                    creatures.remove(c)
                    lives -= 1
                    if lives <= 0:
                        game_over = True
            
        # Dibujar criaturas
        phase = current_time
        for c in creatures:
            draw_fn = DRAW_FUNCTIONS.get(c['type']['name'])
            if draw_fn:
                draw_fn(frame, c['x'], int(c['y']), c['r'], c['type'], phase + c['wobble_offset'])
        
        # Partículas
        for p in particles[:]:
            p['x'] += p['dx']; p['y'] += p['dy']; p['dy'] += 0.5; p['life'] -= 1
            if p['life'] <= 0: particles.remove(p)
            else: cv2.circle(frame, (int(p['x']),int(p['y'])), max(2,p['life']//2), p['color'], -1)
        
        # Textos flotantes
        for pt in pop_texts[:]:
            pt['y'] -= 2; pt['life'] -= 1
            if pt['life'] <= 0: pop_texts.remove(pt)
            else:
                cv2.putText(frame, pt['text'], (pt['x']-30, int(pt['y'])), cv2.FONT_HERSHEY_DUPLEX, 0.7, pt['color'], 2)
                cv2.putText(frame, f"+{pt['points']}", (pt['x']-15, int(pt['y'])+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1)
                
        # Interacción con manos
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                index_tip = hand_landmarks.landmark[8]
                ix, iy = int(index_tip.x * display_w), int(index_tip.y * display_h)
                cv2.circle(frame, (ix, iy), 10, (0, 255, 255), -1)
                
                if not game_over:
                    for c in creatures[:]:
                        if dist((ix, iy), (c['x'], c['y'])) < c['r']:
                            ctype = c['type']
                            creatures.remove(c)
                            score += ctype['points']
                            for _ in range(15):
                                angle = random.uniform(0, 2*math.pi)
                                spd = random.uniform(5, 15)
                                particles.append({'x':ix,'y':iy,'dx':math.cos(angle)*spd,'dy':math.sin(angle)*spd,'life':random.randint(10,25),'color':random.choice([ctype['color'],ctype['accent'],(255,255,255)])})
                            pop_texts.append({'text': POP_TEXTS.get(ctype['name'],'POP!'), 'x':ix, 'y':float(iy), 'life':25, 'color':ctype['color'], 'points':ctype['points']})
                            cv2.circle(frame, (ix, iy), c['r'] + 20, (255,255,255), 4)
                            
        # UI
        cv2.putText(frame, f"PUNTAJE: {score}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
        cv2.putText(frame, f"VIDAS: {lives}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        if game_over:
            cv2.putText(frame, "GAME OVER!", (display_w//2 - 120, display_h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
            cv2.putText(frame, "Pellizca para reiniciar", (display_w//2 - 120, display_h//2 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            if results.multi_hand_landmarks:
                hand = results.multi_hand_landmarks[0]
                thumb, index = hand.landmark[4], hand.landmark[8]
                if math.hypot(thumb.x - index.x, thumb.y - index.y) < 0.05:
                    score = 0; lives = 5; creatures.clear(); game_over = False

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Monster Pop AR - Caza Monstruos!</title>
    <style>
        body { background-color: #111; color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; margin-top: 20px;}
        img { border: 8px solid #333; border-radius: 15px; box-shadow: 0px 0px 20px rgba(0,255,255,0.2); max-width: 100%; height: auto; }
        h1 { color: #00e5ff; text-transform: uppercase; letter-spacing: 2px;}
        p { font-size: 1.2em; color: #aaa; }
        .highlight { color: #ffeb3b; font-weight: bold;}
    </style>
</head>
<body>
    <h1>👻 Monster Pop AR - Caza Monstruos! 👹</h1>
    <p>Usa la punta de tu <span class="highlight">dedo índice</span> para atrapar fantasmas, calaveras, calabazas y más criaturas!</p>
    <img src="/video_feed">
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
