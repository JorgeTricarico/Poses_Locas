"""
Módulo de Renderizado Gráfico, Feedback AR y Efectos Visuales
"""

import os
import cv2
import numpy as np
import math
import time
import random
from collections import deque

from .geometry import (
    NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP,
    SKELETON_CONNECTIONS, LEFT_ARM_CONNECTIONS, RIGHT_ARM_CONNECTIONS,
    score_to_traffic_color, get_point
)

# Cache de iconos en memoria
ICON_CACHE = {}


# =====================================================================
# UTILIDADES GRÁFICAS BÁSICAS
# =====================================================================
def blend_rect_roi(frame, x, y, w, h, bgr_color, alpha=0.6):
    """Aplica alpha blending en una ROI rectangular."""
    fh, fw = frame.shape[:2]
    x1, y1 = max(0, int(x)), max(0, int(y))
    x2, y2 = min(fw, int(x + w)), min(fh, int(y + h))
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    rect = np.full_like(roi, bgr_color, dtype=np.uint8)
    cv2.addWeighted(rect, alpha, roi, 1.0 - alpha, 0, roi)


def load_pose_illustration_clean(filename_no_ext, size=(160, 160), bg_color=(30, 25, 38)):
    """Carga y limpia el fondo blanco o negro de una pose_*.jpg para fusionarla suavemente."""
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
    """Dibuja un icono vectorial de estrella."""
    pts = np.array([
        [cx, cy - r], [cx + r // 3, cy - r // 3], [cx + r, cy],
        [cx + r // 3, cy + r // 3], [cx, cy + r], [cx - r // 3, cy + r // 3],
        [cx - r, cy], [cx - r // 3, cy - r // 3]
    ], np.int32)
    cv2.fillPoly(frame, [pts], color, cv2.LINE_AA)


def draw_bolt_icon(frame, cx, cy, r, color):
    """Dibuja un icono vectorial de rayo de velocidad."""
    pts = np.array([
        [cx + 3, cy - r], [cx - r + 2, cy + 2], [cx - 1, cy + 2],
        [cx - 3, cy + r], [cx + r - 2, cy - 2], [cx + 1, cy - 2]
    ], np.int32)
    cv2.fillPoly(frame, [pts], color, cv2.LINE_AA)


def draw_progress_bar(frame, x, y, w, h, progress, color):
    """Dibuja una barra de progreso estilizada con borde blanco."""
    cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 65), -1)
    if int(w * progress) > 0:
        cv2.rectangle(frame, (x, y), (x + int(w * progress), y + h), color, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)


# =====================================================================
# COACH VIVO CON PIERNAS, PISO Y FLECHAS DE INTENCIÓN
# =====================================================================
def draw_full_body_stickman(frame, x, y, w, h, pts, arm_color, body_color=(210, 210, 220), show_floor=True):
    """Dibuja un stickman anatómico completo con articulaciones y línea de suelo."""
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
    """
    Calcula puntos cinemáticos animados biomecánicamente coherentes para el Coach Vivo.
    Garantiza:
      - Simetría bilateral en movimientos de cadera (izquierda <-> derecha balanceado).
      - Preservación de la longitud de piernas sin estiramiento deformado de pies.
      - Apoyo de pies natural con flexión orgánica de rodillas y contrapposto de columna.
    """
    base_ref = pose_data.get('ref', {})
    pts = {}
    key_map = {
        NOSE: 'nose', L_SHOULDER: 'ls', R_SHOULDER: 'rs',
        L_ELBOW: 'le', R_ELBOW: 're', L_WRIST: 'lw', R_WRIST: 'rw',
        L_HIP: 'lh', R_HIP: 'rh'
    }
    for k, v in base_ref.items():
        if k in key_map:
            pts[key_map[k]] = (float(v[0]), float(v[1]))

    name = pose_data.get('name', '')
    floor_y = 0.90
    la_x = 0.40
    ra_x = 0.60

    # =================================================================
    # 1. BAILA! MUEVE CADERAS (OSCILACIÓN RÍTMICA BILATERAL IZQ <-> DER)
    # =================================================================
    if 'Caderas' in name:
        sway = math.sin(t * 5.5) * 0.10  # Oscila simétricamente entre -0.10 (IZQ) y +0.10 (DER)
        pelvis_tilt = sway * 0.025        # Elevación natural de la cresta ilíaca

        # Caderas centradas en 0.50 con balanceo completo a ambos lados
        pts['lh'] = (0.42 + sway, 0.60 + pelvis_tilt)
        pts['rh'] = (0.58 + sway, 0.60 - pelvis_tilt)

        # Contrapeso dinámico de hombros (contrapposto natural)
        pts['ls'] = (0.36 - sway * 0.30, 0.32 - pelvis_tilt * 0.7)
        pts['rs'] = (0.64 - sway * 0.30, 0.32 + pelvis_tilt * 0.7)

        # Cabeza compensada
        pts['nose'] = (0.50 - sway * 0.15, 0.14)

        # Brazos en cadera balanceándose en consonancia
        if 'lw' in pts: pts['lw'] = (0.34 + sway * 0.7, 0.58 + pelvis_tilt)
        if 'rw' in pts: pts['rw'] = (0.66 + sway * 0.7, 0.58 - pelvis_tilt)
        if 'le' in pts: pts['le'] = (0.23 + sway * 0.4, 0.45)
        if 're' in pts: pts['re'] = (0.77 + sway * 0.4, 0.45)

        # Pies plantados firmes en el suelo (¡sin estirar ni deformar!)
        la_y = floor_y
        ra_y = floor_y

        # Rodillas con cinemática inversa suave
        lk_x = pts['lh'][0] * 0.65 + la_x * 0.35
        rk_x = pts['rh'][0] * 0.65 + ra_x * 0.35
        lk_y = 0.75 + max(0.0, sway) * 0.04
        rk_y = 0.75 + max(0.0, -sway) * 0.04

        pts['lk'] = (lk_x, lk_y)
        pts['rk'] = (rk_x, rk_y)
        pts['la'] = (la_x, la_y)
        pts['ra'] = (ra_x, ra_y)
        return pts

    # =================================================================
    # 2. DE LADO A LADO (PASO TRASLACIONAL COMPLETO)
    # =================================================================
    elif 'Lado a Lado' in name:
        step = math.sin(t * 4.0) * 0.12
        for k in list(pts.keys()):
            pts[k] = (pts[k][0] + step, pts[k][1])
        la_x += step
        ra_x += step
        pts['lk'] = (pts['lh'][0] * 0.6 + la_x * 0.4, 0.75)
        pts['rk'] = (pts['rh'][0] * 0.6 + ra_x * 0.4, 0.75)
        pts['la'] = (la_x, floor_y)
        pts['ra'] = (ra_x, floor_y)
        return pts

    # =================================================================
    # 3. SALTO MORTAL (CICLO NATURAL: CARGA -> VUELO -> AMORTIGUACIÓN)
    # =================================================================
    elif 'Salto' in name:
        phase = (t * 4.5) % (2.0 * math.pi)
        sin_p = math.sin(phase)
        is_air = sin_p > 0.0
        jump_y = -sin_p * 0.16 if is_air else 0.0

        for k in list(pts.keys()):
            pts[k] = (pts[k][0], pts[k][1] + jump_y)

        if is_air:
            la_y = floor_y + jump_y * 0.85
            ra_y = floor_y + jump_y * 0.85
            lk_y = 0.75 + jump_y * 0.90
            rk_y = 0.75 + jump_y * 0.90
        else:
            cushion = abs(sin_p) * 0.04
            la_y = floor_y
            ra_y = floor_y
            lk_y = 0.75 + cushion
            rk_y = 0.75 + cushion

        pts['lk'] = (pts['lh'][0], lk_y)
        pts['rk'] = (pts['rh'][0], rk_y)
        pts['la'] = (la_x, la_y)
        pts['ra'] = (ra_x, ra_y)
        return pts

    # =================================================================
    # 4. AGACHARSE (SQUAT ERGONÓMICO CON APERTURA DE RODILLAS)
    # =================================================================
    elif 'Agacharse' in name:
        squat = abs(math.sin(t * 3.5)) * 0.14
        for k in list(pts.keys()):
            pts[k] = (pts[k][0], pts[k][1] + squat)

        la_x, ra_x = 0.36, 0.64
        pts['lk'] = (0.32, 0.75 + squat * 0.5)
        pts['rk'] = (0.68, 0.75 + squat * 0.5)
        pts['la'] = (la_x, floor_y)
        pts['ra'] = (ra_x, floor_y)
        return pts

    # =================================================================
    # 5. MUEVE LA CABEZA (NODDING Y TILT RÍTMICO)
    # =================================================================
    elif 'Cabeza' in name:
        nod_x = math.sin(t * 6.0) * 0.08
        nod_y = abs(math.cos(t * 6.0)) * 0.03
        pts['nose'] = (0.50 + nod_x, 0.14 + nod_y)
        pts['ls'] = (0.36, 0.32 + nod_y * 0.3)
        pts['rs'] = (0.64, 0.32 + nod_y * 0.3)
        pts['lk'] = (0.41, 0.75)
        pts['rk'] = (0.59, 0.75)
        pts['la'] = (la_x, floor_y)
        pts['ra'] = (ra_x, floor_y)
        return pts

    # =================================================================
    # 6. BALANCEO SUAVE FLOW (YOGA / MINDFULNESS FLOW)
    # =================================================================
    elif 'Flow' in name or 'Balanceo' in name:
        flow = math.sin(t * 3.2) * 0.06
        for k in ['nose', 'ls', 'rs', 'le', 're', 'lw', 'rw', 'lh', 'rh']:
            if k in pts:
                pts[k] = (pts[k][0] + flow, pts[k][1])
        pts['lk'] = (pts['lh'][0] * 0.7 + la_x * 0.3, 0.75)
        pts['rk'] = (pts['rh'][0] * 0.7 + ra_x * 0.3, 0.75)
        pts['la'] = (la_x, floor_y)
        pts['ra'] = (ra_x, floor_y)
        return pts

    # =================================================================
    # 7. BOXEO RÁPIDO (JABS ALTERNADOS IZQ / DER CON GUARDIA)
    # =================================================================
    elif 'Boxeo' in name:
        jab = math.sin(t * 8.5)
        if jab > 0.1:
            pts['lw'] = (0.46 + jab * 0.12, 0.22)
            pts['le'] = (0.38, 0.28)
            pts['rw'] = (0.64, 0.28)
            pts['re'] = (0.72, 0.38)
        elif jab < -0.1:
            pts['rw'] = (0.54 - abs(jab) * 0.12, 0.22)
            pts['re'] = (0.62, 0.28)
            pts['lw'] = (0.36, 0.28)
            pts['le'] = (0.28, 0.38)
        pts['lk'] = (0.41, 0.75)
        pts['rk'] = (0.59, 0.75)
        pts['la'] = (la_x, floor_y)
        pts['ra'] = (ra_x, floor_y)
        return pts

    # =================================================================
    # 8. MUEVE LOS BRAZOS / GIRANDO / GUITARRA
    # =================================================================
    elif 'Mueve los Brazos' in name:
        arm_wave = math.sin(t * 6.5) * 0.18
        # Hombros nivelados y estables
        pts['ls'] = (0.36, 0.32)
        pts['rs'] = (0.64, 0.32)
        # Brazo izquierdo: codo y muñeca se mueven en perfecta continuidad anatómica
        pts['le'] = (0.24, 0.28 + arm_wave * 0.55)
        pts['lw'] = (0.16, 0.16 + arm_wave)
        # Brazo derecho: oscila en antifase armónica (bombeo rítmico alternado)
        pts['re'] = (0.76, 0.28 - arm_wave * 0.55)
        pts['rw'] = (0.84, 0.16 - arm_wave)
        # Base corporal firme sin distorsión
        pts['lk'] = (0.41, 0.75)
        pts['rk'] = (0.59, 0.75)
        pts['la'] = (la_x, floor_y)
        pts['ra'] = (ra_x, floor_y)
        return pts
    elif 'Gir' in name:
        spin_cos = math.cos(t * 4.5)
        for k in list(pts.keys()):
            dx = pts[k][0] - 0.50
            pts[k] = (0.50 + dx * spin_cos, pts[k][1])
    elif 'Guitarra' in name:
        strum = math.sin(t * 9.0) * 0.08
        if 'rw' in pts: pts['rw'] = (0.55 + strum, 0.56 + abs(strum)*0.5)

    # Para poses estáticas: respiración y presencia orgánica
    breathe = math.sin(t * 3.0) * 0.008
    if 'ls' in pts and 'rs' in pts and not pose_data.get('dynamic'):
        pts['ls'] = (pts['ls'][0] - breathe, pts['ls'][1] - breathe)
        pts['rs'] = (pts['rs'][0] + breathe, pts['rs'][1] - breathe)

    # Rodillas y tobillos base sin deformación
    lh_now = pts.get('lh', (0.42, 0.60))
    rh_now = pts.get('rh', (0.58, 0.60))
    pts['lk'] = (lh_now[0] * 0.65 + la_x * 0.35, 0.75)
    pts['rk'] = (rh_now[0] * 0.65 + ra_x * 0.35, 0.75)
    pts['la'] = (la_x, floor_y)
    pts['ra'] = (ra_x, floor_y)
    return pts


def draw_intent_arrows_in_box(frame, pose_data, box_x, box_y, box_w, box_h, t):
    """
    Dibuja flechas e indicadores visuales dinámicos que comunican con claridad
    absoluta la intención del movimiento (ambos lados, ritmo y dirección).
    """
    name = pose_data.get('name', '')
    col = pose_data.get('color', (0, 255, 255))
    cx = box_x + box_w // 2
    cy = box_y + box_h // 2

    # --- CADERAS: INDICADOR BILATERAL CON GUÍA Y FLECHAS ALTERNADAS IZQ <-> DER ---
    if 'Caderas' in name:
        y_arr = box_y + int(box_h * 0.60)
        sway_val = math.sin(t * 5.5)

        # Carril guía horizontal sutil
        cv2.line(frame, (box_x + 16, y_arr), (box_x + box_w - 16, y_arr), (60, 60, 80), 1, cv2.LINE_AA)
        cv2.circle(frame, (cx, y_arr), 3, (140, 140, 160), -1)

        if sway_val > 0.08:
            # Movimiento hacia la DERECHA: Flecha pulsante a la derecha con texto guía
            tip_x = int(cx + 8 + (box_w * 0.36) * min(1.0, sway_val * 1.3))
            cv2.arrowedLine(frame, (cx + 4, y_arr), (tip_x, y_arr), (0, 220, 255), 3, tipLength=0.35)
            cv2.putText(frame, "DER >", (box_x + box_w - 52, y_arr - 8), cv2.FONT_HERSHEY_DUPLEX, 0.42, (0, 220, 255), 1, cv2.LINE_AA)
        elif sway_val < -0.08:
            # Movimiento hacia la IZQUIERDA: Flecha pulsante a la izquierda con texto guía
            tip_x = int(cx - 8 - (box_w * 0.36) * min(1.0, abs(sway_val) * 1.3))
            cv2.arrowedLine(frame, (cx - 4, y_arr), (tip_x, y_arr), (255, 100, 220), 3, tipLength=0.35)
            cv2.putText(frame, "< IZQ", (box_x + 10, y_arr - 8), cv2.FONT_HERSHEY_DUPLEX, 0.42, (255, 100, 220), 1, cv2.LINE_AA)
        else:
            # Centro / Transición rítmica
            cv2.circle(frame, (cx, y_arr), 5, (0, 255, 200), -1, cv2.LINE_AA)

    elif 'Lado a Lado' in name:
        y_arr = box_y + int(box_h * 0.72)
        step_val = math.sin(t * 4.0)
        cv2.line(frame, (box_x + 16, y_arr), (box_x + box_w - 16, y_arr), (60, 60, 80), 1, cv2.LINE_AA)
        if step_val > 0.08:
            cv2.arrowedLine(frame, (cx, y_arr), (box_x + box_w - 18, y_arr), col, 3, tipLength=0.35)
            cv2.putText(frame, "PASO DER >>", (cx - 15, y_arr - 8), cv2.FONT_HERSHEY_DUPLEX, 0.40, col, 1, cv2.LINE_AA)
        elif step_val < -0.08:
            cv2.arrowedLine(frame, (cx, y_arr), (box_x + 18, y_arr), col, 3, tipLength=0.35)
            cv2.putText(frame, "<< PASO IZQ", (box_x + 12, y_arr - 8), cv2.FONT_HERSHEY_DUPLEX, 0.40, col, 1, cv2.LINE_AA)

    elif 'Cabeza' in name:
        y_head = box_y + int(box_h * 0.16)
        nod_val = math.sin(t * 6.0)
        if nod_val > 0.08:
            cv2.arrowedLine(frame, (cx + 12, y_head), (cx + 38, y_head), (140, 255, 80), 2, tipLength=0.4)
        elif nod_val < -0.08:
            cv2.arrowedLine(frame, (cx - 12, y_head), (cx - 38, y_head), (140, 255, 80), 2, tipLength=0.4)

    elif 'Salto' in name:
        jump_pulse = int(math.sin(t * 4.5) * 8)
        cv2.arrowedLine(frame, (box_x + 20, cy + 25 + jump_pulse), (box_x + 20, box_y + 15), (0, 255, 120), 3, tipLength=0.4)
        cv2.arrowedLine(frame, (box_x + box_w - 20, cy + 25 + jump_pulse), (box_x + box_w - 20, box_y + 15), (0, 255, 120), 3, tipLength=0.4)

    elif 'Agacharse' in name:
        squat_pulse = int(abs(math.sin(t * 3.5)) * 10)
        cv2.arrowedLine(frame, (box_x + 20, box_y + 25), (box_x + 20, cy + 25 + squat_pulse), (100, 180, 255), 3, tipLength=0.4)
        cv2.arrowedLine(frame, (box_x + box_w - 20, box_y + 25), (box_x + box_w - 20, cy + 25 + squat_pulse), (100, 180, 255), 3, tipLength=0.4)

    elif 'Gir' in name:
        cv2.ellipse(frame, (cx, cy + 15), (box_w // 3, 16), 0, -20, 240, (0, 215, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, "360", (cx - 20, box_y + box_h - 15), cv2.FONT_HERSHEY_DUPLEX, 0.60, (0, 215, 255), 1, cv2.LINE_AA)

    elif 'Boxeo' in name:
        jab_v = math.sin(t * 8.5)
        y_jab = box_y + int(box_h * 0.28)
        if jab_v > 0.1:
            cv2.arrowedLine(frame, (cx - 15, y_jab), (cx + 25, y_jab), (80, 130, 255), 2, tipLength=0.4)
        elif jab_v < -0.1:
            cv2.arrowedLine(frame, (cx + 15, y_jab), (cx - 25, y_jab), (80, 130, 255), 2, tipLength=0.4)

    elif 'Mueve los Brazos' in name:
        wave_arr = math.sin(t * 6.5)
        arr_ly = int(cy - 12 - wave_arr * 20)
        arr_ry = int(cy - 12 + wave_arr * 20)
        if wave_arr > 0:
            cv2.arrowedLine(frame, (box_x + 18, arr_ly + 20), (box_x + 18, arr_ly - 10), (0, 255, 120), 2, tipLength=0.45)
        else:
            cv2.arrowedLine(frame, (box_x + 18, arr_ly - 20), (box_x + 18, arr_ly + 10), (255, 100, 220), 2, tipLength=0.45)
        if wave_arr < 0:
            cv2.arrowedLine(frame, (box_x + box_w - 18, arr_ry + 20), (box_x + box_w - 18, arr_ry - 10), (0, 255, 120), 2, tipLength=0.45)
        else:
            cv2.arrowedLine(frame, (box_x + box_w - 18, arr_ry - 20), (box_x + box_w - 18, arr_ry + 10), (255, 100, 220), 2, tipLength=0.45)
        cv2.putText(frame, "ARRIBA / ABAJO", (cx - 42, box_y + box_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)


# =====================================================================
# AR GHOST SILHOUETTE & ANILLOS MAGNÉTICOS
# =====================================================================
def compute_body_anchored_targets(lm, pose_data, display_w, display_h):
    """Ancla los objetivos de la silueta Ghost directamente a la escala corporal del jugador."""
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
    """Dibuja la silueta Ghost translúcida y anillos magnéticos con vector de corrección."""
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


def draw_skeleton_with_feedback(frame, lm, display_w, display_h, left_ok, right_ok, left_score=None, right_score=None):
    """Renderiza el esqueleto semáforo continuo del jugador con resplandor neón."""
    COLOR_BODY = (255, 255, 0)
    ls = left_score if left_score is not None else (1.0 if left_ok else 0.0)
    rs = right_score if right_score is not None else (1.0 if right_ok else 0.0)

    left_color = score_to_traffic_color(ls)
    right_color = score_to_traffic_color(rs)

    points = {lm_id: pt for lm_id in [NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP]
              if (pt := get_point(lm, lm_id, display_w, display_h))}

    overlay = frame.copy()
    for a, b in SKELETON_CONNECTIONS:
        if a in points and b in points:
            cv2.line(overlay, points[a], points[b], COLOR_BODY, 12, cv2.LINE_AA)
    for a, b in LEFT_ARM_CONNECTIONS:
        if a in points and b in points:
            cv2.line(overlay, points[a], points[b], left_color, 16, cv2.LINE_AA)
    for a, b in RIGHT_ARM_CONNECTIONS:
        if a in points and b in points:
            cv2.line(overlay, points[a], points[b], right_color, 16, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

    for a, b in SKELETON_CONNECTIONS:
        if a in points and b in points:
            cv2.line(frame, points[a], points[b], (255, 255, 255), 3, cv2.LINE_AA)
    for a, b in LEFT_ARM_CONNECTIONS:
        if a in points and b in points:
            cv2.line(frame, points[a], points[b], (255, 255, 255), 4, cv2.LINE_AA)
    for a, b in RIGHT_ARM_CONNECTIONS:
        if a in points and b in points:
            cv2.line(frame, points[a], points[b], (255, 255, 255), 4, cv2.LINE_AA)

    pulse = int(math.sin(time.time() * 9.0) * 4)
    for lm_id, pt in points.items():
        col = left_color if lm_id in [L_SHOULDER, L_ELBOW, L_WRIST] else (right_color if lm_id in [R_SHOULDER, R_ELBOW, R_WRIST] else COLOR_BODY)
        base_r = 13 if (lm_id in [L_WRIST, R_WRIST] and (ls >= 0.85 or rs >= 0.85)) else 8
        r = max(4, base_r + pulse)
        cv2.circle(frame, pt, r + 3, col, -1, cv2.LINE_AA)
        cv2.circle(frame, pt, r, (255, 255, 255), -1, cv2.LINE_AA)

    if NOSE in points:
        cv2.circle(frame, points[NOSE], max(14, 20 + pulse), COLOR_BODY, 3, cv2.LINE_AA)


# =====================================================================
# SISTEMAS DE EFECTOS (ESTELAS, PARTÍCULAS Y TEXTOS FLOTANTES)
# =====================================================================
class HandTrailSystem:
    """Estelas de energía de muñecas estilo Just Dance / Beat Saber."""
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


class ParticleSystem:
    """Sistema de partículas físicas 2D para confeti y explosiones."""
    def __init__(self):
        self.particles = []

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
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['dy'] += 0.3
            p['life'] -= 1
            if p['life'] <= 0:
                self.particles.remove(p)
            else:
                sz = max(2, int(p['size'] * p['life'] / 30))
                cv2.circle(frame, (int(p['x']), int(p['y'])), sz, p['color'], -1, cv2.LINE_AA)


class FloatingText:
    """Textos ascendentes translúcidos para feedback de combos y bonificaciones."""
    def __init__(self):
        self.texts = []

    def add(self, text, x, y, color, scale=1.4):
        self.texts.append({'text': text, 'x': x, 'y': float(y), 'color': color, 'life': 42, 'scale': scale})

    def update_and_draw(self, frame):
        for t in self.texts[:]:
            t['y'] -= 1.8
            t['life'] -= 1
            if t['life'] <= 0:
                self.texts.remove(t)
            else:
                cv2.putText(frame, t['text'], (int(t['x'])+2, int(t['y'])+2), cv2.FONT_HERSHEY_DUPLEX, t['scale'], (0,0,0), int(t['scale']*3)+1, cv2.LINE_AA)
                cv2.putText(frame, t['text'], (int(t['x']), int(t['y'])), cv2.FONT_HERSHEY_DUPLEX, t['scale'], t['color'], max(1, int(t['scale']*2)), cv2.LINE_AA)
