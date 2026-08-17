import cv2
import mediapipe as mp
import threading
import time
import math
from evdev import UInput, ecodes

RTSP_URL = "rtsp://jorge.tricarico:3424Trica@192.168.0.148:554/stream1"

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

def main():
    print("Iniciando camara...")
    cap = VideoCaptureAsync(RTSP_URL).start()
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        min_detection_confidence=0.7, 
        min_tracking_confidence=0.7, 
        max_num_hands=1
    )
    
    print("Configurando mouse virtual a nivel Kernel (UInput)...")
    cap_dict = {
        ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y],
        ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT]
    }
    ui = UInput(cap_dict, name='spock-virtual-mouse')
    
    prev_x, prev_y = None, None
    is_clicking = False
    
    # Sensibilidad base y factor de aceleracion
    BASE_SENSITIVITY = 1800  # Multiplicador base (10% de pantalla movida = ~180 pixeles)
    ACCEL_FACTOR = 40.0      # Curva de aceleracion para movimientos rapidos
    
    print("=========================================")
    print(" TODO LISTO! Controlando el mouse de Linux")
    print(" Mueve la mano para el cursor.")
    print(" Pellizca para hacer click.")
    print("=========================================")
    
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
            
        frame = cv2.resize(frame, (640, 480))
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            
            index_tip = hand_landmarks.landmark[8]
            thumb_tip = hand_landmarks.landmark[4]
            
            # Invertimos X porque la camara frontal actua como espejo
            curr_x = -index_tip.x 
            curr_y = index_tip.y
            
            if prev_x is not None and prev_y is not None:
                dx = curr_x - prev_x
                dy = curr_y - prev_y
                
                # Velocidad del movimiento para calcular la aceleracion
                speed = math.hypot(dx, dy)
                
                # ECUACION DE ACELERACION (Se mueve mas si mueves mas rapido)
                multiplier = 1.0 + (speed * ACCEL_FACTOR)
                
                move_x = int(dx * BASE_SENSITIVITY * multiplier)
                move_y = int(dy * BASE_SENSITIVITY * multiplier)
                
                if move_x != 0 or move_y != 0:
                    ui.write(ecodes.EV_REL, ecodes.REL_X, move_x)
                    ui.write(ecodes.EV_REL, ecodes.REL_Y, move_y)
                    ui.syn()
            
            prev_x, prev_y = curr_x, curr_y
            
            # Click (Pellizco)
            d = math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y)
            if d < 0.05 and not is_clicking:
                is_clicking = True
                ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1) # Mouse Down
                ui.syn()
                print("CLICK INICIADO (Boton presionado)")
            elif d > 0.07 and is_clicking:
                is_clicking = False
                ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0) # Mouse Up
                ui.syn()
                print("CLICK LIBERADO (Boton soltado)")
        else:
            prev_x, prev_y = None, None
            if is_clicking:
                is_clicking = False
                ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
                ui.syn()

if __name__ == '__main__':
    main()
