"""
Catálogo Central de Poses, Perfiles de Experiencia, Coreografías y Mapeo Rítmico
"""

import math
from .geometry import (
    NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP
)
from .detectors import (
    check_left_arm_up, check_right_arm_up, check_left_arm_down, check_right_arm_down,
    check_left_arm_horizontal, check_right_arm_horizontal,
    check_left_hand_on_hip, check_right_hand_on_hip,
    check_left_hand_on_head, check_right_hand_on_head,
    check_left_bicep, check_right_bicep, check_right_salute,
    check_left_arm_y, check_right_arm_y, check_left_arm_o, check_right_arm_o,
    check_monkey_left, check_monkey_right, check_airplane_left, check_airplane_right,
    check_contralateral_left_to_right, check_namaste_center, check_clock_arms_9_12,
    check_egyptian_left_up_right_down, check_gentle_sway,
    check_shake_hips, check_shake_head, check_jump, check_squat,
    check_spin, check_flail_arms, check_move_side_to_side,
    check_boxer_jabs, check_air_guitar, check_gesture_next
)

# =====================================================================
# TEMPO MUSICAL (BPM)
# =====================================================================
SONG_BPM = {
    'macarena.wav': 103,
    'macarena_real.wav': 103,
    'macarena_vocal.wav': 103,
    'asereje.wav': 106,
    'ymca.wav': 127,
    'danza_kuduro.wav': 130,
    'waka_waka.wav': 127,
    'despacito.wav': 89,
}


def get_beat_pulse(current_time, song_name):
    """Calcula el pulso rítmico exponencial amortiguado en cada frame."""
    bpm = SONG_BPM.get(song_name, 110)
    beats_per_sec = bpm / 60.0
    phase = (current_time * beats_per_sec) % 1.0
    return math.exp(-phase * 4.5)


# =====================================================================
# CATÁLOGO EXPANDIDO DE 23 POSES
# =====================================================================
POSES = [
    # --- Dinámicas ---
    {
        'name': 'Baila! Mueve Caderas', 'color': (255, 100, 180), 'icon_name': 'pose_caderas',
        'dynamic': True, 'checks': check_shake_hips,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.44), R_ELBOW: (0.74, 0.44), L_WRIST: (0.36, 0.58), R_WRIST: (0.64, 0.58), L_HIP: (0.42, 0.60), R_HIP: (0.58, 0.60) },
        'tags': ['junior', 'cardio', 'dance', 'fun']
    },
    {
        'name': 'Mueve la Cabeza!', 'color': (140, 255, 80), 'icon_name': 'pose_cabeza',
        'dynamic': True, 'checks': check_shake_head,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.30, 0.45), R_ELBOW: (0.70, 0.45), L_WRIST: (0.35, 0.60), R_WRIST: (0.65, 0.60), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'fun', 'gentle']
    },
    {
        'name': 'Balanceo Suave Flow!', 'color': (140, 220, 255),
        'dynamic': True, 'checks': check_gentle_sway,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.28, 0.38), R_ELBOW: (0.72, 0.38), L_WRIST: (0.35, 0.45), R_WRIST: (0.65, 0.45), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['cognitive', 'zen', 'gentle']
    },
    {
        'name': 'Boxeo Rapido!', 'color': (80, 130, 255),
        'dynamic': True, 'checks': check_boxer_jabs,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.28, 0.42), R_ELBOW: (0.72, 0.30), L_WRIST: (0.42, 0.24), R_WRIST: (0.62, 0.16), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['cardio', 'athletic']
    },
    {
        'name': 'Salto Mortal!', 'color': (80, 255, 120),
        'dynamic': True, 'checks': check_jump,
        'ref': { NOSE: (0.5, 0.08), L_SHOULDER: (0.36, 0.24), R_SHOULDER: (0.64, 0.24), L_ELBOW: (0.24, 0.15), R_ELBOW: (0.76, 0.15), L_WRIST: (0.18, 0.05), R_WRIST: (0.82, 0.05), L_HIP: (0.42, 0.48), R_HIP: (0.58, 0.48) },
        'tags': ['cardio', 'athletic']
    },
    {
        'name': 'Agacharse!', 'color': (100, 180, 255),
        'dynamic': True, 'checks': check_squat,
        'ref': { NOSE: (0.5, 0.34), L_SHOULDER: (0.36, 0.48), R_SHOULDER: (0.64, 0.48), L_ELBOW: (0.26, 0.62), R_ELBOW: (0.74, 0.62), L_WRIST: (0.35, 0.74), R_WRIST: (0.65, 0.74), L_HIP: (0.40, 0.72), R_HIP: (0.60, 0.72) },
        'tags': ['cardio', 'athletic']
    },
    {
        'name': 'Girando!', 'color': (255, 160, 0),
        'dynamic': True, 'checks': check_spin,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.46, 0.32), R_SHOULDER: (0.54, 0.32), L_ELBOW: (0.36, 0.46), R_ELBOW: (0.64, 0.46), L_WRIST: (0.32, 0.58), R_WRIST: (0.68, 0.58), L_HIP: (0.46, 0.62), R_HIP: (0.54, 0.62) },
        'tags': ['cardio', 'athletic']
    },
    {
        'name': 'Mueve los Brazos!', 'color': (255, 60, 255),
        'dynamic': True, 'checks': check_flail_arms,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.18), R_ELBOW: (0.74, 0.45), L_WRIST: (0.20, 0.05), R_WRIST: (0.80, 0.60), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'fun', 'cardio']
    },
    {
        'name': 'De Lado a Lado!', 'color': (50, 255, 255),
        'dynamic': True, 'checks': check_move_side_to_side,
        'ref': { NOSE: (0.50, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.28, 0.45), R_ELBOW: (0.72, 0.45), L_WRIST: (0.34, 0.60), R_WRIST: (0.66, 0.60), L_HIP: (0.42, 0.60), R_HIP: (0.58, 0.60) },
        'tags': [], 'disabled': True  # Desactivada por solicitud del usuario (removida de niños y pruebas estáticas)
    },
    {
        'name': 'Guitarra Rock!', 'color': (0, 255, 120),
        'dynamic': True, 'checks': check_air_guitar,
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.22, 0.36), R_ELBOW: (0.72, 0.46), L_WRIST: (0.10, 0.30), R_WRIST: (0.55, 0.56), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'fun', 'cardio']
    },
    
    # --- Poses Cognitivas y de Coordinación (Bajo Impacto, Cruces Contralaterales) ---
    {
        'name': 'Cruzado al Oido!', 'color': (255, 120, 180),
        'checks': {'left_arm': check_contralateral_left_to_right, 'right_arm': check_right_arm_down},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.45, 0.22), R_ELBOW: (0.70, 0.45), L_WRIST: (0.56, 0.17), R_WRIST: (0.65, 0.60), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['cognitive', 'zen', 'gentle']
    },
    {
        'name': 'Reloj 9 y 12!', 'color': (0, 240, 255),
        'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_up},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.22, 0.32), R_ELBOW: (0.72, 0.18), L_WRIST: (0.08, 0.32), R_WRIST: (0.68, 0.05), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['cognitive', 'zen', 'gentle']
    },
    {
        'name': 'Namaste Zen!', 'color': (120, 255, 150),
        'checks': {'left_arm': check_namaste_center, 'right_arm': check_namaste_center},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.25, 0.45), R_ELBOW: (0.75, 0.45), L_WRIST: (0.47, 0.45), R_WRIST: (0.53, 0.45), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['cognitive', 'zen', 'gentle']
    },
    {
        'name': 'Marco Egipcio!', 'color': (255, 200, 50),
        'checks': {'left_arm': check_egyptian_left_up_right_down, 'right_arm': check_egyptian_left_up_right_down},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.22, 0.32), R_ELBOW: (0.78, 0.42), L_WRIST: (0.35, 0.18), R_WRIST: (0.65, 0.55), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['cognitive', 'zen', 'gentle']
    },

    # --- Estáticas Lúdicas e Ilustradas pose_*.jpg ---
    {
        'name': 'Brazos Arriba!', 'color': (0, 255, 120), 'icon_name': 'pose_brazos',
        'checks': {'left_arm': check_left_arm_up, 'right_arm': check_right_arm_up},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.28, 0.18), R_ELBOW: (0.72, 0.18), L_WRIST: (0.32, 0.05), R_WRIST: (0.68, 0.05), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'fun', 'zen', 'gentle']
    },
    {
        'name': 'T-Pose!', 'color': (255, 210, 0), 'icon_name': 'pose_tpose',
        'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_horizontal},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.22, 0.32), R_ELBOW: (0.78, 0.32), L_WRIST: (0.08, 0.32), R_WRIST: (0.92, 0.32), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'fun', 'zen', 'gentle']
    },
    {
        'name': 'Fuerte!', 'color': (255, 110, 50), 'icon_name': 'pose_fuerte',
        'checks': {'left_arm': check_left_bicep, 'right_arm': check_right_bicep},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.22, 0.32), R_ELBOW: (0.78, 0.32), L_WRIST: (0.32, 0.20), R_WRIST: (0.68, 0.20), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'fun', 'cardio']
    },
    {
        'name': 'Saludo Militar!', 'color': (60, 120, 255), 'icon_name': 'pose_saludo',
        'checks': {'left_arm': check_left_arm_down, 'right_arm': check_right_salute},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.30, 0.45), R_ELBOW: (0.74, 0.30), L_WRIST: (0.32, 0.58), R_WRIST: (0.58, 0.14), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'cognitive', 'zen', 'gentle']
    },
    {
        'name': 'Letra Y!', 'color': (255, 100, 220), 'icon_name': 'pose_letra_y',
        'checks': {'left_arm': check_left_arm_y, 'right_arm': check_right_arm_y},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.18), R_ELBOW: (0.74, 0.18), L_WRIST: (0.16, 0.05), R_WRIST: (0.84, 0.05), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'fun', 'gentle']
    },
    {
        'name': 'Letra O!', 'color': (100, 240, 255), 'icon_name': 'pose_letra_o',
        'checks': {'left_arm': check_left_arm_o, 'right_arm': check_right_arm_o},
        'ref': { NOSE: (0.5, 0.20), L_SHOULDER: (0.36, 0.36), R_SHOULDER: (0.64, 0.36), L_ELBOW: (0.30, 0.14), R_ELBOW: (0.70, 0.14), L_WRIST: (0.44, 0.04), R_WRIST: (0.56, 0.04), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'fun', 'gentle']
    },
    {
        'name': 'Pose de Mono!', 'color': (0, 200, 255),
        'checks': {'left_arm': check_monkey_left, 'right_arm': check_monkey_right},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.16, 0.35), R_ELBOW: (0.84, 0.35), L_WRIST: (0.36, 0.40), R_WRIST: (0.64, 0.40), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'fun']
    },
    {
        'name': 'Fiebre Disco!', 'color': (255, 90, 255),
        'checks': {'left_arm': check_left_hand_on_hip, 'right_arm': check_right_arm_up},
        'ref': { NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.24, 0.46), R_ELBOW: (0.74, 0.18), L_WRIST: (0.40, 0.58), R_WRIST: (0.86, 0.05), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['cardio', 'dance', 'fun']
    },
    {
        'name': 'Avion Supersonico!', 'color': (100, 255, 200),
        'checks': {'left_arm': check_airplane_left, 'right_arm': check_airplane_right},
        'ref': { NOSE: (0.48, 0.16), L_SHOULDER: (0.34, 0.36), R_SHOULDER: (0.62, 0.28), L_ELBOW: (0.18, 0.42), R_ELBOW: (0.76, 0.22), L_WRIST: (0.06, 0.48), R_WRIST: (0.92, 0.16), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62) },
        'tags': ['junior', 'fun', 'gentle']
    },
]

# =====================================================================
# PERFILES DE EXPERIENCIA
# =====================================================================
PROFILES = {
    'JUNIOR': {
        'id': 'JUNIOR',
        'name': 'AVENTURA JUNIOR',
        'subtitle': 'Ludico, Expresivo y Divertido',
        'time': 7.5,
        'grace_mult': 1.3,
        'tags': {'junior', 'fun', 'basic'}
    },
    'CARDIO': {
        'id': 'CARDIO',
        'name': 'CARDIO GROOVE',
        'subtitle': 'Intenso, Ritmico y Dinamico',
        'time': 5.0,
        'grace_mult': 0.85,
        'tags': {'cardio', 'athletic', 'dance'}
    },
    'ZEN': {
        'id': 'ZEN',
        'name': 'MENTE ACTIVA & ZEN',
        'subtitle': 'Bajo Impacto Articular, Alto Reto Cognitivo',
        'time': 8.5,
        'grace_mult': 1.5,
        'tags': {'cognitive', 'zen', 'gentle'}
    },
    'FIESTA': {
        'id': 'FIESTA',
        'name': 'FIESTA TOTAL',
        'subtitle': 'Todas las Poses y Desafios Combinados',
        'time': 6.0,
        'grace_mult': 1.0,
        'tags': {'all'}
    }
}
PROFILE_KEYS = ['JUNIOR', 'CARDIO', 'ZEN', 'FIESTA']


def get_poses_for_profile(profile_key):
    """Filtra y devuelve las poses elegibles para el perfil activo (excluyendo poses desactivadas)."""
    active_poses = [p for p in POSES if not p.get('disabled', False)]
    if profile_key not in PROFILES or profile_key == 'FIESTA':
        return active_poses
    req_tags = PROFILES[profile_key]['tags']
    matching = [p for p in active_poses if any(t in req_tags for t in p.get('tags', []))]
    return matching if len(matching) >= 4 else active_poses


# =====================================================================
# COREOGRAFÍAS NARRATIVAS
# =====================================================================
COREOGRAFIAS = {
    'macarena.wav': [
        {'name': 'Brazo Der Adelante', 'checks': {'left_arm': check_left_arm_down, 'right_arm': check_right_arm_horizontal}, 'ref': {NOSE: (0.5, 0.14), R_SHOULDER: (0.62, 0.32), R_ELBOW: (0.8, 0.32), R_WRIST: (0.95, 0.32)}, 'color': (255, 200, 0)},
        {'name': 'Brazos Adelante', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_horizontal}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), L_ELBOW: (0.2, 0.32), L_WRIST: (0.05, 0.32), R_SHOULDER: (0.62, 0.32), R_ELBOW: (0.8, 0.32), R_WRIST: (0.95, 0.32)}, 'color': (255, 200, 0)},
        {'name': 'Mano Der Cabeza', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), L_WRIST: (0.05, 0.32), R_SHOULDER: (0.62, 0.32), R_WRIST: (0.55, 0.14)}, 'color': (255, 200, 0)},
        {'name': 'Manos en la Cabeza!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), L_WRIST: (0.45, 0.14), R_SHOULDER: (0.62, 0.32), R_WRIST: (0.55, 0.14)}, 'color': (255, 200, 0)},
        {'name': 'Mano Der Cintura', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_hip}, 'ref': {NOSE: (0.5, 0.14), L_WRIST: (0.45, 0.14), R_SHOULDER: (0.62, 0.32), R_WRIST: (0.58, 0.62), R_HIP: (0.58, 0.62)}, 'color': (255, 200, 0)},
        {'name': 'Manos Cintura!', 'checks': {'left_arm': check_left_hand_on_hip, 'right_arm': check_right_hand_on_hip}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), L_WRIST: (0.42, 0.62), L_HIP: (0.42, 0.62), R_SHOULDER: (0.62, 0.32), R_WRIST: (0.58, 0.62), R_HIP: (0.58, 0.62)}, 'color': (255, 200, 0)},
        {'name': 'Baila! Mueve Caderas', 'dynamic': True, 'checks': check_shake_hips, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.44), R_ELBOW: (0.74, 0.44), L_WRIST: (0.38, 0.60), R_WRIST: (0.62, 0.60), L_HIP: (0.34, 0.62), R_HIP: (0.50, 0.62)}, 'color': (255, 100, 180)},
        {'name': 'Girando!', 'dynamic': True, 'checks': check_spin, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.46, 0.32), R_SHOULDER: (0.54, 0.32), L_ELBOW: (0.36, 0.46), R_ELBOW: (0.64, 0.46), L_WRIST: (0.32, 0.58), R_WRIST: (0.68, 0.58), L_HIP: (0.46, 0.62), R_HIP: (0.54, 0.62)}, 'color': (255, 160, 0)}
    ],
    'asereje.wav': [
        {'name': 'Cruzando Abajo', 'checks': {'left_arm': lambda lm: check_gesture_next(lm), 'right_arm': lambda lm: check_gesture_next(lm)}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.45, 0.45), R_ELBOW: (0.55, 0.45), L_WRIST: (0.62, 0.32), R_WRIST: (0.38, 0.32), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62)}, 'color': (255, 100, 255)}, 
        {'name': 'Manos en la Cabeza!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.25, 0.20), R_ELBOW: (0.75, 0.20), L_WRIST: (0.45, 0.12), R_WRIST: (0.55, 0.12), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62)}, 'color': (100, 50, 255)},
        {'name': 'Baila! Mueve Caderas', 'dynamic': True, 'checks': check_shake_hips, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.44), R_ELBOW: (0.74, 0.44), L_WRIST: (0.38, 0.60), R_WRIST: (0.62, 0.60), L_HIP: (0.34, 0.62), R_HIP: (0.50, 0.62)}, 'color': (255, 100, 180)},
        {'name': 'Mueve los Brazos!', 'dynamic': True, 'checks': check_flail_arms, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.36, 0.32), R_SHOULDER: (0.64, 0.32), L_ELBOW: (0.26, 0.18), R_ELBOW: (0.74, 0.45), L_WRIST: (0.20, 0.05), R_WRIST: (0.80, 0.60), L_HIP: (0.42, 0.62), R_HIP: (0.58, 0.62)}, 'color': (255, 50, 255)},
    ],
    'ymca.wav': [
        {'name': 'Letra Y!', 'checks': {'left_arm': check_left_arm_y, 'right_arm': check_right_arm_y}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.26, 0.18), R_ELBOW: (0.74, 0.18), L_WRIST: (0.16, 0.05), R_WRIST: (0.84, 0.05)}, 'color': (255, 100, 100)},
        {'name': 'Letra M!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.25, 0.20), R_ELBOW: (0.75, 0.20), L_WRIST: (0.45, 0.12), R_WRIST: (0.55, 0.12)}, 'color': (100, 255, 100)},
        {'name': 'Letra C!', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_up}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.30, 0.45), R_ELBOW: (0.70, 0.15), L_WRIST: (0.25, 0.60), R_WRIST: (0.75, 0.05)}, 'color': (100, 100, 255)},
        {'name': 'Letra A!', 'checks': {'left_arm': check_left_hand_on_head, 'right_arm': check_right_hand_on_head}, 'ref': {NOSE: (0.5, 0.14), L_SHOULDER: (0.38, 0.32), R_SHOULDER: (0.62, 0.32), L_ELBOW: (0.38, 0.08), R_ELBOW: (0.62, 0.08), L_WRIST: (0.48, 0.02), R_WRIST: (0.52, 0.02)}, 'color': (255, 255, 100)},
    ],
    'despacito.wav': [
        {'name': 'Namaste Zen!', 'checks': {'left_arm': check_namaste_center, 'right_arm': check_namaste_center}, 'ref': {NOSE: (0.5, 0.14), L_WRIST: (0.47, 0.45), R_WRIST: (0.53, 0.45), L_ELBOW: (0.25, 0.45), R_ELBOW: (0.75, 0.45)}, 'color': (120, 255, 150)},
        {'name': 'Cruzado al Oido!', 'checks': {'left_arm': check_contralateral_left_to_right, 'right_arm': check_right_arm_down}, 'ref': {NOSE: (0.5, 0.14), L_WRIST: (0.56, 0.17), R_WRIST: (0.65, 0.60)}, 'color': (255, 120, 180)},
        {'name': 'Balanceo Suave Flow!', 'dynamic': True, 'checks': check_gentle_sway, 'ref': {NOSE: (0.5, 0.14), L_WRIST: (0.35, 0.45), R_WRIST: (0.65, 0.45)}, 'color': (140, 220, 255)},
        {'name': 'Reloj 9 y 12!', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_up}, 'ref': {NOSE: (0.5, 0.14), L_WRIST: (0.08, 0.32), R_WRIST: (0.68, 0.05)}, 'color': (0, 240, 255)},
        {'name': 'Marco Egipcio!', 'checks': {'left_arm': check_egyptian_left_up_right_down, 'right_arm': check_egyptian_left_up_right_down}, 'ref': {NOSE: (0.5, 0.14), L_WRIST: (0.35, 0.18), L_ELBOW: (0.22, 0.32), R_WRIST: (0.65, 0.55), R_ELBOW: (0.78, 0.42)}, 'color': (255, 200, 50)},
        {'name': 'T-Pose!', 'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_horizontal}, 'ref': {NOSE: (0.5, 0.14), L_WRIST: (0.08, 0.32), R_WRIST: (0.92, 0.32)}, 'color': (255, 210, 0)}
    ]
}
COREOGRAFIAS['macarena_real.wav'] = COREOGRAFIAS['macarena.wav']
COREOGRAFIAS['macarena_vocal.wav'] = COREOGRAFIAS['macarena.wav']
