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
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.started = False
        self.is_mock = True
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
        # Canvas estilizado neutral sin texto crudo previo al flip horizontal
        frame = np.full((self.height, self.width, 3), (25, 20, 35), dtype=np.uint8)
        # Marco de calibración geométrico simétrico
        cv2.rectangle(frame, (60, 60), (self.width - 60, self.height - 60), (45, 38, 60), 2)
        r = int(32 + 12 * math.sin(t * 3.5))
        cv2.circle(frame, (self.width // 2, self.height // 2), r, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.circle(frame, (self.width // 2, self.height // 2), max(5, r // 3), (255, 120, 0), -1, cv2.LINE_AA)
        return True, frame


class VideoCaptureAsync:
    """Captura de video en hilo secundario independiente con soporte robusto V4L2 y MJPG."""
    def __init__(self, src=0, width=1280, height=720):
        self.src = src
        self.width = width
        self.height = height
        self.is_mock = False
        self.started = False
        self.read_lock = threading.Lock()
        self.grabbed = False
        self.frame = None

        # En Linux/V4L2, pasar cv2.CAP_V4L2 si src es entero
        if isinstance(self.src, int):
            try:
                self.cap = cv2.VideoCapture(self.src, cv2.CAP_V4L2)
            except Exception:
                self.cap = cv2.VideoCapture(self.src)

            # Configurar FourCC MJPG prioritariamente para cámaras USB en Linux/RPi
            try:
                fourcc_mjpg = cv2.VideoWriter_fourcc(*'MJPG')
                self.cap.set(cv2.CAP_PROP_FOURCC, fourcc_mjpg)
            except Exception:
                pass

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        else:
            self.cap = cv2.VideoCapture(self.src)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Bucle de warm-up y resiliencia: sensores USB requieren estabilizar stream
        if self.cap.isOpened():
            for attempt in range(12):
                grabbed, frame = self.cap.read()
                if grabbed and frame is not None and frame.size > 0:
                    self.grabbed = True
                    self.frame = frame
                    break
                time.sleep(0.08)

            # Fallback si 1280x720 falló: probar resolución nativa de fallback (640x480)
            if not self.grabbed and isinstance(self.src, int):
                try:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    for _ in range(6):
                        grabbed, frame = self.cap.read()
                        if grabbed and frame is not None and frame.size > 0:
                            self.grabbed = True
                            self.frame = frame
                            break
                        time.sleep(0.06)
                except Exception:
                    pass

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
