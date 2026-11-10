"""
Módulo de Geometría y Normalización Anatómica
"""

import math

# Índices MediaPipe Pose
NOSE = 0
L_EAR = 8   # Mirror mode: vista de cámara
R_EAR = 7
L_SHOULDER = 12
R_SHOULDER = 11
L_ELBOW = 14
R_ELBOW = 13
L_WRIST = 16
R_WRIST = 15
L_HIP = 24
R_HIP = 23

SKELETON_CONNECTIONS = [
    (L_SHOULDER, R_SHOULDER), (L_SHOULDER, L_HIP), (R_SHOULDER, R_HIP),
    (L_HIP, R_HIP), (L_SHOULDER, NOSE), (R_SHOULDER, NOSE)
]
LEFT_ARM_CONNECTIONS = [(L_SHOULDER, L_ELBOW), (L_ELBOW, L_WRIST)]
RIGHT_ARM_CONNECTIONS = [(R_SHOULDER, R_ELBOW), (R_ELBOW, R_WRIST)]


def get_body_unit(lm):
    """
    Distancia euclidiana entre hombros (BodyUnit). Invariante a estatura y distancia a cámara.
    """
    dx = lm[L_SHOULDER].x - lm[R_SHOULDER].x
    dy = lm[L_SHOULDER].y - lm[R_SHOULDER].y
    return max(0.10, math.hypot(dx, dy))


def calc_angle_2d(lm, a_id, b_id, c_id):
    """Ángulo articular en grados (0..180) en el vértice b_id."""
    ax, ay = lm[a_id].x, lm[a_id].y
    bx, by = lm[b_id].x, lm[b_id].y
    cx, cy = lm[c_id].x, lm[c_id].y
    rad = math.atan2(cy - by, cx - bx) - math.atan2(ay - by, ax - bx)
    ang = abs(math.degrees(rad))
    return 360.0 - ang if ang > 180.0 else ang


def distance_to_score(dist_val, target_dist, tolerance):
    """Convierte un error de distancia en score continuo [0.0, 1.0]."""
    if dist_val <= target_dist:
        return 1.0
    over = dist_val - target_dist
    return max(0.0, 1.0 - (over / max(1e-5, tolerance)))


def score_to_traffic_color(score):
    """Interpola en BGR: Rojo (0.0) -> Ámbar (0.5) -> Verde Neón (1.0)."""
    s = max(0.0, min(1.0, float(score)))
    if s < 0.5:
        t = s / 0.5
        return (int(50 * (1 - t)), int(50 + 160 * t), 255)
    else:
        t = (s - 0.5) / 0.5
        return (int(80 * t), int(210 + 45 * t), int(255 * (1 - t)))


def score_arm(check_fn, lm):
    """Evalúa la precisión de un brazo y retorna un score continuo [0.0..1.0]."""
    if check_fn(lm):
        return 1.0
    bu = get_body_unit(lm)
    fn_name = getattr(check_fn, '__name__', '')
    if 'up' in fn_name:
        wrist = lm[L_WRIST] if 'left' in fn_name else lm[R_WRIST]
        target_y = lm[NOSE].y - 0.05
        return distance_to_score(wrist.y, target_y, 0.6 * bu)
    elif 'horizontal' in fn_name:
        wrist = lm[L_WRIST] if 'left' in fn_name else lm[R_WRIST]
        shoulder = lm[L_SHOULDER] if 'left' in fn_name else lm[R_SHOULDER]
        return distance_to_score(abs(wrist.y - shoulder.y), 0.12, 0.4 * bu)
    return 0.35


def get_point(lm, lm_id, w, h):
    """Convierte un landmark normalizado en coordenadas de pantalla en píxeles."""
    return (int(lm[lm_id].x * w), int(lm[lm_id].y * h)) if lm[lm_id].visibility > 0.35 else None
