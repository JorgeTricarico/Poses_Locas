"""
Módulo de Detección de Poses (Estáticas, Cognitivas y Dinámicas)
"""

import math
import time
from .geometry import (
    NOSE, L_EAR, R_EAR, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW,
    L_WRIST, R_WRIST, L_HIP, R_HIP, get_body_unit
)


# =====================================================================
# CHECKS ESTÁTICOS
# =====================================================================
def check_left_arm_up(lm):
    return lm[L_WRIST].y < lm[NOSE].y - 0.05


def check_right_arm_up(lm):
    return lm[R_WRIST].y < lm[NOSE].y - 0.05


def check_left_arm_down(lm):
    return lm[L_WRIST].y > lm[L_SHOULDER].y + 0.05


def check_right_arm_down(lm):
    return lm[R_WRIST].y > lm[R_SHOULDER].y + 0.05


def check_left_arm_horizontal(lm):
    return abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.12 and lm[L_WRIST].x < lm[L_SHOULDER].x - 0.08


def check_right_arm_horizontal(lm):
    return abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.12 and lm[R_WRIST].x > lm[R_SHOULDER].x + 0.08


def check_left_hand_on_hip(lm):
    return abs(lm[L_WRIST].x - lm[L_HIP].x) < 0.15 and abs(lm[L_WRIST].y - lm[L_HIP].y) < 0.15


def check_right_hand_on_hip(lm):
    return abs(lm[R_WRIST].x - lm[R_HIP].x) < 0.15 and abs(lm[R_WRIST].y - lm[R_HIP].y) < 0.15


def check_left_hand_on_head(lm):
    return (abs(lm[L_WRIST].x - lm[NOSE].x) < 0.12 or abs(lm[L_WRIST].x - lm[L_EAR].x) < 0.12) and (
        abs(lm[L_WRIST].y - lm[NOSE].y) < 0.12 or abs(lm[L_WRIST].y - lm[L_EAR].y) < 0.12
    )


def check_right_hand_on_head(lm):
    return (abs(lm[R_WRIST].x - lm[NOSE].x) < 0.12 or abs(lm[R_WRIST].x - lm[R_EAR].x) < 0.12) and (
        abs(lm[R_WRIST].y - lm[NOSE].y) < 0.12 or abs(lm[R_WRIST].y - lm[R_EAR].y) < 0.12
    )


def check_left_bicep(lm):
    return abs(lm[L_WRIST].x - lm[L_SHOULDER].x) < 0.10 and abs(
        lm[L_WRIST].y - lm[L_SHOULDER].y
    ) < 0.15 and lm[L_ELBOW].x < lm[L_SHOULDER].x - 0.05


def check_right_bicep(lm):
    return abs(lm[R_WRIST].x - lm[R_SHOULDER].x) < 0.10 and abs(
        lm[R_WRIST].y - lm[R_SHOULDER].y
    ) < 0.15 and lm[R_ELBOW].x > lm[R_SHOULDER].x + 0.05


def check_right_salute(lm):
    return abs(lm[R_WRIST].x - lm[R_EAR].x) < 0.12 and abs(lm[R_WRIST].y - lm[R_EAR].y) < 0.12


def check_left_arm_y(lm):
    return lm[L_WRIST].y < lm[NOSE].y and lm[L_WRIST].x < lm[L_SHOULDER].x - 0.10


def check_right_arm_y(lm):
    return lm[R_WRIST].y < lm[NOSE].y and lm[R_WRIST].x > lm[R_SHOULDER].x + 0.10


def check_left_arm_o(lm):
    return lm[L_WRIST].y < lm[NOSE].y - 0.05 and abs(lm[L_WRIST].x - lm[NOSE].x) < 0.12


def check_right_arm_o(lm):
    return lm[R_WRIST].y < lm[NOSE].y - 0.05 and abs(lm[R_WRIST].x - lm[NOSE].x) < 0.12


def check_monkey_left(lm):
    bu = get_body_unit(lm)
    near_shoulder = math.hypot(lm[L_WRIST].x - lm[L_SHOULDER].x, lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.45 * bu
    elbow_out = lm[L_ELBOW].x < lm[L_SHOULDER].x - 0.25 * bu
    return near_shoulder and elbow_out


def check_monkey_right(lm):
    bu = get_body_unit(lm)
    near_shoulder = math.hypot(lm[R_WRIST].x - lm[R_SHOULDER].x, lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.45 * bu
    elbow_out = lm[R_ELBOW].x > lm[R_SHOULDER].x + 0.25 * bu
    return near_shoulder and elbow_out


def check_airplane_left(lm):
    return check_left_arm_horizontal(lm) and (lm[L_SHOULDER].y - lm[R_SHOULDER].y > 0.04)


def check_airplane_right(lm):
    return check_right_arm_horizontal(lm) and (lm[L_SHOULDER].y - lm[R_SHOULDER].y > 0.04)


# =====================================================================
# CHECKS COGNITIVOS Y DE COORDINACIÓN CONTRALATERAL (BAJO IMPACTO)
# =====================================================================
def check_contralateral_left_to_right(lm):
    """Mano izquierda toca oreja derecha (cruce de la línea media)."""
    return abs(lm[L_WRIST].x - lm[R_EAR].x) < 0.14 and abs(lm[L_WRIST].y - lm[R_EAR].y) < 0.14


def check_contralateral_right_to_left(lm):
    """Mano derecha toca oreja izquierda (cruce de la línea media)."""
    return abs(lm[R_WRIST].x - lm[L_EAR].x) < 0.14 and abs(lm[R_WRIST].y - lm[L_EAR].y) < 0.14


def check_namaste_center(lm):
    """Manos juntas en el centro del pecho (altura esternón / propiocepción)."""
    bu = get_body_unit(lm)
    d_hands = math.hypot(lm[L_WRIST].x - lm[R_WRIST].x, lm[L_WRIST].y - lm[R_WRIST].y)
    mid_chest_y = (lm[L_SHOULDER].y + lm[L_HIP].y) * 0.50
    avg_wrist_y = (lm[L_WRIST].y + lm[R_WRIST].y) * 0.50
    return d_hands < 0.38 * bu and abs(avg_wrist_y - mid_chest_y) < 0.22 * bu


def check_clock_arms_9_12(lm):
    """Brazo izquierdo horizontal (las 9) y derecho vertical arriba (las 12)."""
    return check_left_arm_horizontal(lm) and check_right_arm_up(lm)


def check_clock_arms_12_3(lm):
    """Brazo izquierdo vertical arriba (las 12) y derecho horizontal (las 3)."""
    return check_left_arm_up(lm) and check_right_arm_horizontal(lm)


def check_egyptian_left_up_right_down(lm):
    """Brazo izquierdo flexionado 90° arriba y derecho flexionado 90° abajo."""
    bu = get_body_unit(lm)
    l_up = lm[L_WRIST].y < lm[L_SHOULDER].y and abs(lm[L_ELBOW].x - lm[L_SHOULDER].x) > 0.15 * bu
    r_down = lm[R_WRIST].y > lm[R_SHOULDER].y and abs(lm[R_ELBOW].x - lm[R_SHOULDER].x) > 0.15 * bu
    return l_up and r_down


def check_gentle_sway(state, lm):
    """Balanceo pendular rítmico suave de brazos/cuerpo sin impacto articular."""
    events = []
    hands_avg_x = (lm[L_WRIST].x + lm[R_WRIST].x) / 2.0
    if state.center_x is None:
        state.center_x = hands_avg_x
    else:
        state.center_x = state.center_x * 0.96 + hands_avg_x * 0.04
    threshold = 0.07
    if hands_avg_x > state.center_x + threshold and state.last_hit_side != 'right':
        state.last_hit_side = 'right'
        state.arm_hits += 1
        events.append({'type': 'hit', 'side': 'right', 'x': hands_avg_x, 'y': lm[R_WRIST].y})
    elif hands_avg_x < state.center_x - threshold and state.last_hit_side != 'left':
        state.last_hit_side = 'left'
        state.arm_hits += 1
        events.append({'type': 'hit', 'side': 'left', 'x': hands_avg_x, 'y': lm[L_WRIST].y})
    completed = state.arm_hits >= 6
    return completed, events


# =====================================================================
# CHECKS DINÁMICOS
# =====================================================================
def check_shake_hips(state, lm):
    events = []
    hip_x = (lm[L_HIP].x + lm[R_HIP].x) / 2.0
    hip_y = (lm[L_HIP].y + lm[R_HIP].y) / 2.0
    if state.center_x is None:
        state.center_x = hip_x
    else:
        state.center_x = state.center_x * 0.98 + hip_x * 0.02
    threshold = 0.025
    if hip_x > state.center_x + threshold and state.last_hit_side != 'right':
        state.last_hit_side = 'right'
        state.hip_hits += 1
        events.append({'type': 'hit', 'side': 'right', 'x': hip_x, 'y': hip_y})
    elif hip_x < state.center_x - threshold and state.last_hit_side != 'left':
        state.last_hit_side = 'left'
        state.hip_hits += 1
        events.append({'type': 'hit', 'side': 'left', 'x': hip_x, 'y': hip_y})
    completed = state.hip_hits >= 6
    return completed, events


def check_shake_head(state, lm):
    events = []
    nose_x = lm[NOSE].x
    nose_y = lm[NOSE].y
    if state.center_x is None:
        state.center_x = nose_x
    else:
        state.center_x = state.center_x * 0.96 + nose_x * 0.04
    threshold = 0.020
    if nose_x > state.center_x + threshold and state.last_hit_side != 'right':
        state.last_hit_side = 'right'
        state.hip_hits += 1
        events.append({'type': 'hit', 'side': 'right', 'x': nose_x, 'y': nose_y})
    elif nose_x < state.center_x - threshold and state.last_hit_side != 'left':
        state.last_hit_side = 'left'
        state.hip_hits += 1
        events.append({'type': 'hit', 'side': 'left', 'x': nose_x, 'y': nose_y})
    completed = state.hip_hits >= 6
    return completed, events


def check_jump(state, lm):
    events = []
    hip_y = (lm[L_HIP].y + lm[R_HIP].y) / 2.0
    if state.center_y is None:
        state.center_y = hip_y
    else:
        if state.jump_phase == 0:
            state.center_y = state.center_y * 0.95 + hip_y * 0.05
    threshold = 0.08
    if state.jump_phase == 0:
        if hip_y < state.center_y - threshold:
            state.jump_phase = 1
            events.append({'type': 'hit', 'side': 'center', 'x': 0.5, 'y': hip_y})
    elif state.jump_phase == 1:
        if hip_y > state.center_y - 0.02:
            state.jump_phase = 2
    completed = state.jump_phase >= 2
    return completed, events


def check_squat(state, lm):
    events = []
    hip_y = (lm[L_HIP].y + lm[R_HIP].y) / 2.0
    if state.center_y is None:
        state.center_y = hip_y
    else:
        if state.jump_phase == 0:
            state.center_y = state.center_y * 0.995 + hip_y * 0.005
    threshold = 0.12
    if state.jump_phase == 0:
        if hip_y > state.center_y + threshold:
            state.jump_phase = 1
            events.append({'type': 'hit', 'side': 'center', 'x': 0.5, 'y': hip_y})
    elif state.jump_phase == 1:
        if hip_y < state.center_y + 0.02:
            state.jump_phase = 2
    completed = state.jump_phase >= 2
    return completed, events


def check_spin(state, lm):
    events = []
    left_is_right_of_right = lm[L_SHOULDER].x > lm[R_SHOULDER].x
    if getattr(state, 'initial_shoulder_order', None) is None:
        state.initial_shoulder_order = left_is_right_of_right
        state.spin_start_time = time.time()
    if state.spin_phase == 0:
        if left_is_right_of_right != state.initial_shoulder_order:
            state.spin_phase = 1
        elif lm[L_SHOULDER].visibility < 0.2 and lm[R_SHOULDER].visibility < 0.2:
            state.spin_phase = 1
    elif state.spin_phase == 1:
        if time.time() - state.spin_start_time > 0.35:
            if left_is_right_of_right == state.initial_shoulder_order and lm[L_SHOULDER].visibility > 0.4 and lm[R_SHOULDER].visibility > 0.4:
                state.spin_phase = 2
                events.append({'type': 'hit', 'side': 'center', 'x': lm[NOSE].x, 'y': lm[NOSE].y})
    completed = state.spin_phase >= 2
    return completed, events


def check_flail_arms(state, lm):
    events = []
    l_arm_up = lm[L_WRIST].y < lm[L_SHOULDER].y
    r_arm_up = lm[R_WRIST].y < lm[R_SHOULDER].y
    current_pos = 'up' if (l_arm_up and r_arm_up) else ('down' if not l_arm_up and not r_arm_up else 'mid')
    if state.last_arm_pos is None:
        state.last_arm_pos = current_pos
    if current_pos == 'up' and state.last_arm_pos != 'up':
        state.last_arm_pos = 'up'
        state.arm_hits += 1
        events.append({'type': 'hit', 'side': 'up', 'x': 0.5, 'y': 0.2})
    elif current_pos == 'down' and state.last_arm_pos != 'down':
        state.last_arm_pos = 'down'
        state.arm_hits += 1
        events.append({'type': 'hit', 'side': 'down', 'x': 0.5, 'y': 0.8})
    completed = state.arm_hits >= 6
    return completed, events


def check_move_side_to_side(state, lm):
    events = []
    nose_x = lm[NOSE].x
    if state.center_x is None:
        state.center_x = nose_x
    else:
        state.center_x = state.center_x * 0.99 + nose_x * 0.01
    threshold = 0.12
    if nose_x > state.center_x + threshold and state.last_hit_side != 'right':
        state.last_hit_side = 'right'
        state.move_hits += 1
        events.append({'type': 'hit', 'side': 'right', 'x': nose_x, 'y': lm[NOSE].y})
    elif nose_x < state.center_x - threshold and state.last_hit_side != 'left':
        state.last_hit_side = 'left'
        state.move_hits += 1
        events.append({'type': 'hit', 'side': 'left', 'x': nose_x, 'y': lm[NOSE].y})
    completed = state.move_hits >= 4
    return completed, events


def check_boxer_jabs(state, lm):
    events = []
    bu = get_body_unit(lm)
    diff_y = lm[L_WRIST].y - lm[R_WRIST].y
    if abs(diff_y) > 0.18 * bu:
        curr = 'left_jab' if diff_y < 0 else 'right_jab'
        if state.last_arm_pos != curr:
            state.last_arm_pos = curr
            state.arm_hits += 1
            pt = lm[L_WRIST] if curr == 'left_jab' else lm[R_WRIST]
            events.append({'type': 'hit', 'side': curr, 'x': pt.x, 'y': pt.y})
    completed = state.arm_hits >= 6
    return completed, events


def check_air_guitar(state, lm):
    events = []
    bu = get_body_unit(lm)
    hand_y = lm[R_WRIST].y
    if state.last_arm_pos is None:
        state.last_arm_pos = hand_y
    if abs(hand_y - state.last_arm_pos) > 0.15 * bu:
        state.last_arm_pos = hand_y
        state.arm_hits += 1
        events.append({'type': 'hit', 'side': 'strum', 'x': lm[R_WRIST].x, 'y': hand_y})
    completed = state.arm_hits >= 6
    return completed, events


def check_hand_head_shake_hips(state, lm):
    hand_on_head = check_left_hand_on_head(lm) or check_right_hand_on_head(lm)
    if not hand_on_head:
        return False, []
    return check_shake_hips(state, lm)


def check_jump_arms_up(state, lm):
    arms_up = check_left_arm_up(lm) and check_right_arm_up(lm)
    if not arms_up:
        return False, []
    return check_jump(state, lm)


def check_spin_hand_head(state, lm):
    hand_on_head = check_left_hand_on_head(lm) or check_right_hand_on_head(lm)
    if not hand_on_head:
        return False, []
    return check_spin(state, lm)


def check_gesture_next(lm):
    l_cross = abs(lm[L_WRIST].x - lm[R_SHOULDER].x) < 0.15 and abs(lm[L_WRIST].y - lm[R_SHOULDER].y) < 0.15
    r_cross = abs(lm[R_WRIST].x - lm[L_SHOULDER].x) < 0.15 and abs(lm[R_WRIST].y - lm[L_SHOULDER].y) < 0.15
    return l_cross and r_cross
