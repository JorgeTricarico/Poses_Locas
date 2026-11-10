"""
Módulo de Captura de Video (Asíncrona y Mock para Entornos Headless/Test)
"""

import cv2
import threading
import time
import math
import numpy as np


class MockVideoCapture:
    """Emulador de cámara cuando no hay hardware USB disponible o para tests headless."""
    def __init__(self):
        self.started = False
        self.read_lock = threading.Lock()
        self.t0 = time.time()

    def is_opened(self):
        return True

    def release(self):
        self.stop()

    def start(self):
        self.started = True
        return self

    def stop(self):
        self.started = False

    def read(self):
        t = time.time() - self.t0
        frame = np.full((720, 1280, 3), (25, 20, 35), dtype=np.uint8)
        cv2.putText(frame, "POSES LOCAS AR - MODO DEMO", (330, 320), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "Camara web no detectada. Conecte su camara USB.", (320, 380), cv2.FONT_HERSHEY_DUPLEX, 0.7, (200, 200, 200), 1, cv2.LINE_AA)
        r = int(25 + 10 * math.sin(t * 4))
        cv2.circle(frame, (640, 480), r, (0, 255, 0), -1, cv2.LINE_AA)
        return True, frame


class VideoCaptureAsync:
    """Captura de video en hilo secundario independiente para garantizar 30-60 FPS fluidos."""
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

    def is_opened(self):
        return self.cap.isOpened() and self.grabbed

    def release(self):
        if self.started:
            self.stop()
        self.cap.release()

    def start(self):
        if self.started:
            return self
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
