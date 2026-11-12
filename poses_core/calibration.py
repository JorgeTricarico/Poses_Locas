"""
=====================================================================
POSES LOCAS AR — SUBSISTEMA DE CALIBRACIÓN PRE-JUEGO
=====================================================================
Fase interactiva previa al inicio de cada partida:
  - Paso 1: Centrado del jugador en la cámara y detección de escala base.
  - Paso 2: T-Pose para calibración de envergadura lateral y BodyUnit.
  - Paso 3: Brazos arriba para alcance vertical y comprobación de techo.
  - Paso 4: Confirmación y cuenta regresiva de inicio.
=====================================================================
"""

import time
import math
import cv2
import numpy as np

from .geometry import (
    NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW,
    L_WRIST, R_WRIST, L_HIP, R_HIP, get_body_unit
)
from .detectors import (
    check_left_arm_horizontal, check_right_arm_horizontal,
    check_left_arm_up, check_right_arm_up
)
from .rendering import blend_rect_roi, draw_progress_bar, draw_full_body_stickman


class CalibrationStep:
    CENTER = 0
    T_POSE = 1
    ARMS_UP = 2
    READY = 3


class CalibrationData:
    """Contenedor de métricas biométricas calibradas del jugador."""
    def __init__(self):
        self.center_x = 0.50
        self.body_unit = 0.24
        self.arm_span = 0.70
        self.reach_y = 0.12
        self.is_calibrated = False
        self.timestamp = 0.0

    def apply_defaults(self):
        self.center_x = 0.50
        self.body_unit = 0.24
        self.arm_span = 0.70
        self.reach_y = 0.12
        self.is_calibrated = True
        self.timestamp = time.time()


class CalibrationManager:
    """
    Controlador y máquina de estados para la calibración pre-juego.
    Garantiza que la cámara y el jugador estén en rango antes de puntuar.
    """
    def __init__(self):
        self.data = CalibrationData()
        self.active = False
        self.step = CalibrationStep.CENTER
        self.hold_time = 0.0
        self.required_times = {
            CalibrationStep.CENTER: 1.0,
            CalibrationStep.T_POSE: 1.2,
            CalibrationStep.ARMS_UP: 1.0,
            CalibrationStep.READY: 0.8
        }
        self.feedback_msg = "PARATE EN EL CENTRO DE LA CAMARA"
        self.step_start_time = 0.0

    def start(self):
        """Inicia el ciclo de calibración pre-juego."""
        self.active = True
        self.step = CalibrationStep.CENTER
        self.hold_time = 0.0
        self.step_start_time = time.time()
        self.feedback_msg = "PARATE EN EL CENTRO DE LA CAMARA"

    def skip(self):
        """Salta la calibración aplicando valores seguros por defecto."""
        self.active = False
        self.step = CalibrationStep.READY
        if not self.data.is_calibrated:
            self.data.apply_defaults()
        return True

    def is_active(self):
        return self.active

    def get_progress(self):
        req = self.required_times.get(self.step, 1.0)
        return min(1.0, max(0.0, self.hold_time / max(0.1, req)))

    def update(self, dt, lm, current_time):
        """
        Actualiza el estado cinético de calibración.
        Retorna True cuando la calibración termina y la partida puede comenzar.
        """
        if not self.active:
            return True

        if lm is None:
            self.hold_time = max(0.0, self.hold_time - dt * 1.5)
            self.feedback_msg = "NO SE DETECTA JUGADOR EN CAMARA"
            return False

        bu = get_body_unit(lm)

        # -------------------------------------------------------------
        # PASO 1: CENTRADO
        # -------------------------------------------------------------
        if self.step == CalibrationStep.CENTER:
            nose_x = lm[NOSE].x
            in_center = (0.35 <= nose_x <= 0.65)
            shoulders_vis = (lm[L_SHOULDER].visibility > 0.4 and lm[R_SHOULDER].visibility > 0.4)

            if in_center and shoulders_vis:
                self.hold_time += dt
                self.feedback_msg = "MANTEN LA POSICION CENTRADA..."
                if self.hold_time >= self.required_times[CalibrationStep.CENTER]:
                    self.data.center_x = (lm[L_SHOULDER].x + lm[R_SHOULDER].x) / 2.0
                    self.data.body_unit = bu
                    self.step = CalibrationStep.T_POSE
                    self.hold_time = 0.0
                    self.feedback_msg = "ABRE LOS BRAZOS EN T!"
            else:
                self.hold_time = max(0.0, self.hold_time - dt * 2.0)
                if nose_x < 0.35:
                    self.feedback_msg = "MUEVETE UN PASO A LA DERECHA ->"
                elif nose_x > 0.65:
                    self.feedback_msg = "<- MUEVETE UN PASO A LA IZQUIERDA"
                else:
                    self.feedback_msg = "PARATE DE FRENTE A LA CAMARA"

        # -------------------------------------------------------------
        # PASO 2: T-POSE (BRAZOS EN CRUZ HORIZONTAL)
        # -------------------------------------------------------------
        elif self.step == CalibrationStep.T_POSE:
            l_horiz = check_left_arm_horizontal(lm)
            r_horiz = check_right_arm_horizontal(lm)

            # Verificación de márgenes de pantalla
            l_wrist_x = lm[L_WRIST].x
            r_wrist_x = lm[R_WRIST].x
            cutoff = (l_wrist_x < 0.04 or r_wrist_x > 0.96)

            if l_horiz and r_horiz:
                if cutoff:
                    self.feedback_msg = "DA UN PASO ATRAS PARA QUE ENTREN TUS MANOS"
                    self.hold_time = max(0.0, self.hold_time - dt)
                else:
                    self.hold_time += dt
                    self.feedback_msg = "MANTEN LA T-POSE..."
                    if self.hold_time >= self.required_times[CalibrationStep.T_POSE]:
                        self.data.arm_span = abs(r_wrist_x - l_wrist_x)
                        self.data.body_unit = (self.data.body_unit + bu) / 2.0
                        self.step = CalibrationStep.ARMS_UP
                        self.hold_time = 0.0
                        self.feedback_msg = "LEVANTA AMBOS BRAZOS AL CIELO!"
            else:
                self.hold_time = max(0.0, self.hold_time - dt * 2.0)
                self.feedback_msg = "EXTIENDE AMBOS BRAZOS HORIZONTALES (T)"

        # -------------------------------------------------------------
        # PASO 3: BRAZOS ARRIBA
        # -------------------------------------------------------------
        elif self.step == CalibrationStep.ARMS_UP:
            l_up = check_left_arm_up(lm)
            r_up = check_right_arm_up(lm)
            min_wrist_y = min(lm[L_WRIST].y, lm[R_WRIST].y)

            if l_up and r_up:
                self.hold_time += dt
                self.feedback_msg = "BRAZOS ARRIBA BIEN ALTO..."
                if self.hold_time >= self.required_times[CalibrationStep.ARMS_UP]:
                    self.data.reach_y = min_wrist_y
                    self.data.is_calibrated = True
                    self.data.timestamp = current_time
                    self.step = CalibrationStep.READY
                    self.hold_time = 0.0
                    self.feedback_msg = "CALIBRADO CON EXITO! PREPARATE..."
            else:
                self.hold_time = max(0.0, self.hold_time - dt * 2.0)
                self.feedback_msg = "LEVANTA AMBOS BRAZOS BIEN ALTO"

        # -------------------------------------------------------------
        # PASO 4: CUENTA REGRESIVA FINAL
        # -------------------------------------------------------------
        elif self.step == CalibrationStep.READY:
            self.hold_time += dt
            if self.hold_time >= self.required_times[CalibrationStep.READY]:
                self.active = False
                return True

        return False

    def draw(self, frame, display_w, display_h, current_time):
        """
        Renderiza el HUD de calibración con guías anatómicas y feedback visual.
        """
        if not self.active:
            return

        # Sombra de fondo general sutil para destacar las guías
        blend_rect_roi(frame, 0, 0, display_w, display_h, (10, 8, 15), 0.55)

        # 1. BANNER SUPERIOR DE PROGRESO
        bx, by, bw, bh = display_w // 2 - 340, 20, 680, 102
        blend_rect_roi(frame, bx, by, bw, bh, (20, 20, 32), 0.90)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 220, 255), 2)

        step_idx = min(3, self.step + 1)
        step_title = (
            "CALIBRACION PRE-JUEGO [PASO 1/3]: CENTRO" if self.step == CalibrationStep.CENTER else (
                "CALIBRACION PRE-JUEGO [PASO 2/3]: T-POSE" if self.step == CalibrationStep.T_POSE else (
                    "CALIBRACION PRE-JUEGO [PASO 3/3]: BRAZOS AL CIELO" if self.step == CalibrationStep.ARMS_UP else
                    "CALIBRACION COMPLETADA! LISTOS..."
                )
            )
        )
        (tw, _), _ = cv2.getTextSize(step_title, cv2.FONT_HERSHEY_DUPLEX, 0.72, 2)
        cv2.putText(frame, step_title, (bx + (bw - tw) // 2, by + 30), cv2.FONT_HERSHEY_DUPLEX, 0.72, (0, 255, 255), 2, cv2.LINE_AA)

        # Barra de progreso de mantención
        prog = self.get_progress()
        bar_w = bw - 60
        bar_x = bx + 30
        bar_y = by + 42
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 18), (45, 45, 60), -1)
        if prog > 0:
            fill_col = (0, 255, 120) if self.step != CalibrationStep.READY else (0, 215, 255)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * prog), bar_y + 18), fill_col, -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 18), (255, 255, 255), 1)

        # Mensaje de feedback instructivo
        (mw, _), _ = cv2.getTextSize(self.feedback_msg, cv2.FONT_HERSHEY_SIMPLEX, 0.54, 2)
        cv2.putText(frame, self.feedback_msg, (bx + (bw - mw) // 2, by + 86), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (255, 255, 255), 2, cv2.LINE_AA)

        # 2. GUÍAS CINÉTICAS EN EL VIEWPORT
        cx = display_w // 2
        cy = display_h // 2

        if self.step == CalibrationStep.CENTER:
            # Guía de caja central y línea vertical
            gx1 = int(display_w * 0.35)
            gx2 = int(display_w * 0.65)
            cv2.line(frame, (cx, 130), (cx, display_h - 100), (0, 220, 255), 1, cv2.LINE_AA)
            cv2.rectangle(frame, (gx1, 140), (gx2, display_h - 90), (0, 255, 200), 2)
            cv2.putText(frame, "ZONA CENTRAL", (cx - 70, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 200), 1, cv2.LINE_AA)

        elif self.step == CalibrationStep.T_POSE:
            # Guía horizontal de apertura de brazos
            y_t = int(display_h * 0.36)
            cv2.line(frame, (80, y_t), (display_w - 80, y_t), (0, 255, 120), 2, cv2.LINE_AA)
            cv2.arrowedLine(frame, (cx - 50, y_t), (100, y_t), (0, 255, 120), 3, tipLength=0.15)
            cv2.arrowedLine(frame, (cx + 50, y_t), (display_w - 100, y_t), (0, 255, 120), 3, tipLength=0.15)
            cv2.putText(frame, "< BRAZO IZQ", (110, y_t - 14), cv2.FONT_HERSHEY_DUPLEX, 0.54, (0, 255, 120), 1, cv2.LINE_AA)
            cv2.putText(frame, "BRAZO DER >", (display_w - 240, y_t - 14), cv2.FONT_HERSHEY_DUPLEX, 0.54, (0, 255, 120), 1, cv2.LINE_AA)

        elif self.step == CalibrationStep.ARMS_UP:
            # Flechas indicadoras al techo
            y_ceil = int(display_h * 0.18)
            cv2.line(frame, (120, y_ceil), (display_w - 120, y_ceil), (255, 200, 0), 1, cv2.LINE_AA)
            cv2.arrowedLine(frame, (cx - 140, cy), (cx - 140, y_ceil + 20), (0, 255, 120), 3, tipLength=0.25)
            cv2.arrowedLine(frame, (cx + 140, cy), (cx + 140, y_ceil + 20), (0, 255, 120), 3, tipLength=0.25)
            cv2.putText(frame, "ALTO AL CIELO", (cx - 70, y_ceil - 12), cv2.FONT_HERSHEY_DUPLEX, 0.54, (255, 220, 0), 1, cv2.LINE_AA)

        elif self.step == CalibrationStep.READY:
            # Gran confirmación de listo
            cv2.circle(frame, (cx, cy), 90, (0, 255, 120), 4, cv2.LINE_AA)
            cv2.putText(frame, "!VAMOS!", (cx - 65, cy + 15), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 255), 2, cv2.LINE_AA)

        # 3. TARJETA COACH DE REFERENCIA (TOP-RIGHT)
        rx, ry, rw, rh = display_w - 230, 20, 210, 160
        blend_rect_roi(frame, rx, ry, rw, rh, (20, 18, 30), 0.85)
        cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (255, 200, 0), 2)

        # Generar pose de stickman de referencia según el paso
        pts = {
            'nose': (0.50, 0.16),
            'ls': (0.36, 0.32), 'rs': (0.64, 0.32),
            'lh': (0.42, 0.60), 'rh': (0.58, 0.60),
            'lk': (0.42, 0.75), 'rk': (0.58, 0.75),
            'la': (0.42, 0.88), 'ra': (0.58, 0.88)
        }
        if self.step == CalibrationStep.CENTER:
            pts['le'] = (0.30, 0.44)
            pts['lw'] = (0.28, 0.58)
            pts['re'] = (0.70, 0.44)
            pts['rw'] = (0.72, 0.58)
        elif self.step == CalibrationStep.T_POSE:
            pts['le'] = (0.22, 0.32)
            pts['lw'] = (0.10, 0.32)
            pts['re'] = (0.78, 0.32)
            pts['rw'] = (0.90, 0.32)
        elif self.step == CalibrationStep.ARMS_UP or self.step == CalibrationStep.READY:
            pts['le'] = (0.28, 0.20)
            pts['lw'] = (0.24, 0.08)
            pts['re'] = (0.72, 0.20)
            pts['rw'] = (0.76, 0.08)

        draw_full_body_stickman(frame, rx + 10, ry + 10, rw - 20, rh - 20, pts, (0, 255, 200))

        # 4. TECLA PARA SALTAR EN EL BORDE INFERIOR
        blend_rect_roi(frame, display_w // 2 - 220, display_h - 48, 440, 36, (20, 20, 30), 0.80)
        cv2.rectangle(frame, (display_w // 2 - 220, display_h - 48), (display_w // 2 + 220, display_h - 12), (180, 180, 200), 1)
        cv2.putText(frame, "[ENTER o TECLA C: SALTAR CALIBRACION]", (display_w // 2 - 195, display_h - 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 230, 245), 1, cv2.LINE_AA)
