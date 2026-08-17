import cv2
import mediapipe as mp
import threading
import time
import math
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
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def generate_frames():
    cap = VideoCaptureAsync(RTSP_URL).start()
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        min_detection_confidence=0.7, 
        min_tracking_confidence=0.7, 
        max_num_hands=1
    )
    mp_draw = mp.solutions.drawing_utils
    
    is_active = True
    display_w, display_h = 640, 480
    cursor_x, cursor_y = display_w // 2, display_h // 2
    alpha = 0.5
    
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
            
        frame = cv2.resize(frame, (display_w, display_h))
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = hands.process(rgb_frame)
        
        cursor_color = (0, 255, 0)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Control con UNA SOLA MANO:
                # El puntero sigue a la punta del dedo índice (punto 8)
                # El click se activa juntando pulgar (4) e índice (8)
                index_tip = hand_landmarks.landmark[8]
                thumb_tip = hand_landmarks.landmark[4]
                
                target_x, target_y = int(index_tip.x * display_w), int(index_tip.y * display_h)
                
                # Movimiento suave (Exponential smoothing)
                cursor_x = int(alpha * target_x + (1 - alpha) * cursor_x)
                cursor_y = int(alpha * target_y + (1 - alpha) * cursor_y)
                
                # Detectar pellizco (distancia menor a 0.05 en coords normalizadas)
                d = dist(index_tip, thumb_tip)
                if d < 0.05:
                    cursor_color = (0, 0, 255)
                    cv2.putText(frame, "CLICK!", (cursor_x + 20, cursor_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        if is_active:
            cv2.circle(frame, (cursor_x, cursor_y), 15, cursor_color, -1)
            cv2.circle(frame, (cursor_x, cursor_y), 15, (255, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MediaPipe Mouse - Simulador</title>
    <style>
        body { background-color: #222; color: white; font-family: sans-serif; text-align: center; }
        img { border: 5px solid #444; border-radius: 10px; max-width: 100%; height: auto; }
        h1 { color: #00ffcc; }
        p { font-size: 1.1em; color: #ccc; }
        .instructions { background: #333; padding: 15px; border-radius: 8px; display: inline-block; text-align: left;}
        .highlight { color: #ffeb3b; font-weight: bold;}
    </style>
</head>
<body>
    <h1>MediaPipe Mouse - Alta Precision</h1>
    <div class="instructions">
        <p>🔴 <b>Mouse:</b> El círculo verde seguirá a la punta de tu <span class="highlight">dedo índice</span>.</p>
        <p>🔴 <b>Click:</b> Haz un <span class="highlight">pellizco</span> (junta la punta del pulgar con la del índice) para hacer Click.</p>
    </div>
    <br><br>
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
