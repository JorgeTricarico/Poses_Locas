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

def draw_monster(frame, x, y, r, color, type_idx):
    if type_idx == 0: # Cíclope (1 ojo grande)
        cv2.circle(frame, (x, y), r, color, -1)
        cv2.circle(frame, (x, y - int(r*0.2)), int(r*0.4), (255,255,255), -1)
        cv2.circle(frame, (x, y - int(r*0.2)), int(r*0.15), (0,0,0), -1)
    elif type_idx == 1: # Dos ojos
        cv2.circle(frame, (x, y), r, color, -1)
        cv2.circle(frame, (x - int(r*0.4), y - int(r*0.2)), int(r*0.25), (255,255,255), -1)
        cv2.circle(frame, (x + int(r*0.4), y - int(r*0.2)), int(r*0.25), (255,255,255), -1)
        cv2.circle(frame, (x - int(r*0.4), y - int(r*0.2)), int(r*0.1), (0,0,0), -1)
        cv2.circle(frame, (x + int(r*0.4), y - int(r*0.2)), int(r*0.1), (0,0,0), -1)
    else: # Slime cuadrado con ojo rojo
        cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), color, -1)
        cv2.circle(frame, (x, y - int(r*0.2)), int(r*0.4), (255,255,255), -1)
        cv2.circle(frame, (x, y - int(r*0.2)), int(r*0.1), (0,0,255), -1)
    # Borde blanco
    if type_idx != 2:
        cv2.circle(frame, (x, y), r, (255, 255, 255), 3)
    else:
        cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), (255, 255, 255), 3)

def main():
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
        cv2.imshow("Monstruos AR", frame)
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
    
    monsters = []
    particles = []
    score = 0
    colors = [
        (0, 0, 255), (0, 255, 0), (255, 0, 0), 
        (0, 255, 255), (255, 0, 255), (0, 165, 255)
    ]
    
    cv2.namedWindow("Monstruos AR", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Monstruos AR", display_w, display_h)
    
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
            
        frame = cv2.resize(frame, (display_w, display_h))
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = hands.process(rgb_frame)
        
        # Aparecer monstruos
        if random.randint(1, 10) == 1:
            monsters.append({
                'x': random.randint(80, display_w - 80),
                'y': display_h + 100,
                'r': random.randint(50, 90), 
                'speed': random.randint(5, 12),
                'color': random.choice(colors),
                'wobble_offset': random.uniform(0, 2 * math.pi),
                'wobble_speed': random.uniform(0.05, 0.1),
                'type': random.randint(0, 2)
            })
            
        for m in monsters:
            m['y'] -= m['speed']
            m['x'] += int(math.sin(time.time() * 5 * m['wobble_speed'] + m['wobble_offset']) * 4)
            
        for m in monsters[:]:
            if m['y'] + m['r'] < -50:
                monsters.remove(m)
        
        for m in monsters:
            draw_monster(frame, m['x'], int(m['y']), m['r'], m['color'], m['type'])
            
        for p in particles[:]:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['dy'] += 0.5
            p['life'] -= 1
            if p['life'] <= 0:
                particles.remove(p)
            else:
                cv2.circle(frame, (int(p['x']), int(p['y'])), max(2, p['life']//2), p['color'], -1)
                
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                hand_points = [(int(lm.x * display_w), int(lm.y * display_h)) for lm in hand_landmarks.landmark]
                
                for tip_idx in [4, 8, 12, 16, 20]:
                    tx, ty = hand_points[tip_idx]
                    cv2.circle(frame, (tx, ty), 12, (0, 255, 255), -1)
                
                for m in monsters[:]:
                    popped = False
                    pop_x, pop_y = 0, 0
                    
                    for px, py in hand_points:
                        if dist((px, py), (m['x'], m['y'])) < m['r']:
                            popped = True
                            pop_x, pop_y = px, py
                            break
                            
                    if popped:
                        monsters.remove(m)
                        score += 100 
                        
                        for _ in range(25):
                            angle = random.uniform(0, 2 * math.pi)
                            speed = random.uniform(5, 25)
                            particles.append({
                                'x': pop_x, 'y': pop_y,
                                'dx': math.cos(angle) * speed,
                                'dy': math.sin(angle) * speed,
                                'life': random.randint(15, 30),
                                'color': m['color']
                            })
                            
                        cv2.putText(frame, "SMASH!", (pop_x - 50, pop_y - 50), cv2.FONT_HERSHEY_DUPLEX, 2, m['color'], 5)
                        cv2.putText(frame, "SMASH!", (pop_x - 50, pop_y - 50), cv2.FONT_HERSHEY_DUPLEX, 2, (255,255,255), 2)
                            
        cv2.putText(frame, f"PUNTAJE: {score}", (30, 80), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 0, 0), 10)
        cv2.putText(frame, f"PUNTAJE: {score}", (30, 80), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 255, 255), 4)

        cv2.imshow("Monstruos AR", frame)
        
        # Manejo correcto del cierre de ventana (Evita que se re-abra infinitamente)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        try:
            # Si el usuario hace click en la "X" de la ventana, la propiedad de visibilidad cae a 0
            if cv2.getWindowProperty("Monstruos AR", cv2.WND_PROP_VISIBLE) < 1:
                break
        except:
            break
            
    cap.stop()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
