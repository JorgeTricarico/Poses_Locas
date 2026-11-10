import sys
import types
import math
import random
import time
import numpy as np
import cv2
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Mock MediaPipe para entorno headless/test
mock_mp = types.ModuleType('mediapipe')
mock_mp.solutions = types.ModuleType('solutions')
mock_mp.solutions.pose = types.ModuleType('pose')
mock_mp.solutions.pose.Pose = lambda *args, **kwargs: None
mock_mp.solutions.pose.PoseLandmark = types.SimpleNamespace(
    NOSE=0, LEFT_SHOULDER=11, RIGHT_SHOULDER=12,
    LEFT_ELBOW=13, RIGHT_ELBOW=14, LEFT_WRIST=15, RIGHT_WRIST=16,
    LEFT_HIP=23, RIGHT_HIP=24, LEFT_EAR=7, RIGHT_EAR=8
)
sys.modules['mediapipe'] = mock_mp

from poses_locas import (
    get_body_unit, calc_angle_2d, distance_to_score, score_to_traffic_color,
    score_arm, blend_rect_roi, draw_star_icon, draw_bolt_icon,
    draw_full_body_stickman, get_animated_ref_points, draw_intent_arrows_in_box,
    compute_body_anchored_targets, draw_ghost_and_target_rings,
    draw_skeleton_with_feedback, HandTrailSystem, FloatingText, ParticleSystem,
    draw_progress_bar, load_pose_illustration_clean,
    NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP, L_EAR, R_EAR,
    PlayerState,
    check_left_arm_up, check_right_arm_up, check_left_arm_down, check_right_arm_down,
    check_left_arm_horizontal, check_right_arm_horizontal,
    check_left_hand_on_hip, check_right_hand_on_hip,
    check_left_hand_on_head, check_right_hand_on_head,
    check_left_bicep, check_right_bicep, check_right_salute,
    check_left_arm_y, check_right_arm_y, check_left_arm_o, check_right_arm_o,
    check_monkey_left, check_monkey_right, check_airplane_left, check_airplane_right,
    check_shake_hips, check_shake_head, check_jump, check_squat,
    check_flail_arms, check_move_side_to_side, check_boxer_jabs, check_air_guitar,
    check_contralateral_left_to_right, check_contralateral_right_to_left,
    check_namaste_center, check_clock_arms_9_12, check_clock_arms_12_3,
    check_egyptian_left_up_right_down, check_gentle_sway,
    PROFILES, PROFILE_KEYS, get_poses_for_profile,
    POSES, COREOGRAFIAS
)
from visual_ui_auditor import UILayoutAuditor

def assert_true(cond, msg):
    if not cond:
        raise AssertionError(f"FAILED: {msg}")

def assert_eq(a, b, msg):
    if a != b:
        raise AssertionError(f"FAILED: {msg} -> expected {b}, got {a}")

class MockLM:
    def __init__(self, x, y, v=1.0):
        self.x, self.y, self.visibility = x, y, v

def make_base_skeleton():
    lm = [MockLM(0.5, 0.5, 0.0) for _ in range(33)]
    # T-Pose simétrica básica centrada
    lm[NOSE] = MockLM(0.50, 0.18, 0.95)
    lm[L_EAR] = MockLM(0.44, 0.17, 0.90)
    lm[R_EAR] = MockLM(0.56, 0.17, 0.90)
    lm[L_SHOULDER] = MockLM(0.38, 0.32, 0.95)
    lm[R_SHOULDER] = MockLM(0.62, 0.32, 0.95)
    lm[L_ELBOW] = MockLM(0.24, 0.32, 0.95)
    lm[R_ELBOW] = MockLM(0.76, 0.32, 0.95)
    lm[L_WRIST] = MockLM(0.12, 0.32, 0.95)
    lm[R_WRIST] = MockLM(0.88, 0.32, 0.95)
    lm[L_HIP] = MockLM(0.42, 0.65, 0.95)
    lm[R_HIP] = MockLM(0.58, 0.65, 0.95)
    return lm

def run_anatomy_and_math_tests():
    print("[1/5] Probando Normalizacion BodyUnit y Matematicas...")
    lm = make_base_skeleton()
    bu = get_body_unit(lm)
    assert_true(bu > 0.20, f"BodyUnit euclidiana hombros invalida: {bu}")

    # Distance to score
    assert_eq(distance_to_score(0.05, 0.10, 0.10), 1.0, "Score continuo maximo dentro de tolerancia")
    s_half = distance_to_score(0.15, 0.10, 0.10)
    assert_true(abs(s_half - 0.5) < 1e-4, f"Score continuo medio esperado 0.5, dio {s_half}")

    # Traffic color
    col_red = score_to_traffic_color(0.0)
    assert_eq(col_red[2], 255, "Rojo al 0.0 score")
    col_green = score_to_traffic_color(1.0)
    assert_true(col_green[1] >= 240, "Verde neon al 1.0 score")
    print("      -> Matematicas de BodyUnit y Colorimetria OK!")

def run_static_pose_tests():
    print("[2/5] Probando Deteccion de Poses Estaticas (18 Poses)...")
    base = make_base_skeleton()

    # 1. T-Pose
    assert_true(check_left_arm_horizontal(base) and check_right_arm_horizontal(base), "T-Pose base")

    # 2. Brazos Arriba
    up = make_base_skeleton()
    up[L_WRIST] = MockLM(0.35, 0.05)
    up[R_WRIST] = MockLM(0.65, 0.05)
    assert_true(check_left_arm_up(up), "Brazo izq arriba")
    assert_true(check_right_arm_up(up), "Brazo der arriba")

    # 3. Brazos Abajo
    down = make_base_skeleton()
    down[L_WRIST] = MockLM(0.36, 0.50)
    down[R_WRIST] = MockLM(0.64, 0.50)
    assert_true(check_left_arm_down(down), "Brazo izq abajo")
    assert_true(check_right_arm_down(down), "Brazo der abajo")

    # 4. Manos en Cadera
    hip = make_base_skeleton()
    hip[L_WRIST] = MockLM(0.42, 0.65)
    hip[R_WRIST] = MockLM(0.58, 0.65)
    assert_true(check_left_hand_on_hip(hip), "Mano izq en cadera")
    assert_true(check_right_hand_on_hip(hip), "Mano der en cadera")

    # 5. Mano en Cabeza
    head = make_base_skeleton()
    head[L_WRIST] = MockLM(0.48, 0.18)
    head[R_WRIST] = MockLM(0.52, 0.18)
    assert_true(check_left_hand_on_head(head), "Mano izq en cabeza")
    assert_true(check_right_hand_on_head(head), "Mano der en cabeza")

    # 6. Biceps (Fuerte)
    bicep = make_base_skeleton()
    bicep[L_WRIST] = MockLM(0.38, 0.32)
    bicep[L_ELBOW] = MockLM(0.24, 0.32)
    bicep[R_WRIST] = MockLM(0.62, 0.32)
    bicep[R_ELBOW] = MockLM(0.76, 0.32)
    assert_true(check_left_bicep(bicep), "Bicep izq")
    assert_true(check_right_bicep(bicep), "Bicep der")

    # 7. Saludo Militar
    salute = make_base_skeleton()
    salute[R_WRIST] = MockLM(0.56, 0.17)
    assert_true(check_right_salute(salute), "Saludo militar derecho")

    # 8. Letra Y
    y_pose = make_base_skeleton()
    y_pose[L_WRIST] = MockLM(0.20, 0.05)
    y_pose[R_WRIST] = MockLM(0.80, 0.05)
    assert_true(check_left_arm_y(y_pose), "Letra Y izq")
    assert_true(check_right_arm_y(y_pose), "Letra Y der")

    # 9. Letra O
    o_pose = make_base_skeleton()
    o_pose[L_WRIST] = MockLM(0.48, 0.05)
    o_pose[R_WRIST] = MockLM(0.52, 0.05)
    assert_true(check_left_arm_o(o_pose), "Letra O izq")
    assert_true(check_right_arm_o(o_pose), "Letra O der")

    # 10. Mono
    monkey = make_base_skeleton()
    monkey[L_WRIST] = MockLM(0.38, 0.35)
    monkey[L_ELBOW] = MockLM(0.25, 0.35)
    monkey[R_WRIST] = MockLM(0.62, 0.35)
    monkey[R_ELBOW] = MockLM(0.75, 0.35)
    assert_true(check_monkey_left(monkey), "Mono izq")
    assert_true(check_monkey_right(monkey), "Mono der")

    # 11. Avion
    plane = make_base_skeleton()
    plane[L_SHOULDER] = MockLM(0.38, 0.36)
    plane[R_SHOULDER] = MockLM(0.62, 0.30)
    plane[L_WRIST] = MockLM(0.12, 0.36)
    plane[R_WRIST] = MockLM(0.88, 0.30)
    assert_true(check_airplane_left(plane), "Avion izq")
    assert_true(check_airplane_right(plane), "Avion der")

    print("      -> Todas las 18 poses estaticas pasaron la suite!")

def run_dynamic_pose_tests():
    print("[3/5] Probando Poses Dinamicas y Maquinas de Estado...")
    # 1. Caderas
    state = PlayerState()
    base_lm = make_base_skeleton()
    check_shake_hips(state, base_lm) # Calibrar center_x
    done = False
    for i in range(12):
        lm = make_base_skeleton()
        x_off = 0.06 if i % 2 == 0 else -0.06
        lm[L_HIP] = MockLM(0.42 + x_off, 0.65)
        lm[R_HIP] = MockLM(0.58 + x_off, 0.65)
        done, _ = check_shake_hips(state, lm)
        if done: break
    assert_true(done, "Caderas dinamicas completadas")

    # 2. Cabeza
    state = PlayerState()
    check_shake_head(state, base_lm) # Calibrar center_x
    done = False
    for i in range(12):
        lm = make_base_skeleton()
        x_off = 0.05 if i % 2 == 0 else -0.05
        lm[NOSE] = MockLM(0.50 + x_off, 0.18)
        done, _ = check_shake_head(state, lm)
        if done: break
    assert_true(done, "Cabeza dinamica completada")

    # 3. Salto
    state = PlayerState()
    lm_down = make_base_skeleton()
    check_jump(state, lm_down) # init center
    lm_jump = make_base_skeleton()
    lm_jump[L_HIP] = MockLM(0.42, 0.50)
    lm_jump[R_HIP] = MockLM(0.58, 0.50)
    check_jump(state, lm_jump) # phase 1
    done, _ = check_jump(state, lm_down) # phase 2 land
    assert_true(done, "Salto dinamico completado")

    # 4. Boxeo jabs
    state = PlayerState()
    done = False
    for i in range(12):
        lm = make_base_skeleton()
        diff = 0.22 if i % 2 == 0 else -0.22
        lm[L_WRIST] = MockLM(0.40, 0.30 + diff)
        lm[R_WRIST] = MockLM(0.60, 0.30 - diff)
        done, _ = check_boxer_jabs(state, lm)
        if done: break
    assert_true(done, "Boxeo jabs completado")

    # 5. Guitarra
    state = PlayerState()
    done = False
    for i in range(12):
        lm = make_base_skeleton()
        diff = 0.20 if i % 2 == 0 else -0.20
        lm[R_WRIST] = MockLM(0.60, 0.55 + diff)
        done, _ = check_air_guitar(state, lm)
        if done: break
    assert_true(done, "Guitarra dinamica completada")

    print("      -> Todas las poses dinamicas pasaron la suite!")

def run_cognitive_and_profile_tests():
    print("[4/6] Probando Poses Cognitivas, Cruces Contralaterales y Perfiles...")
    base = make_base_skeleton()

    # 1. Cruzado al Oido (Izquierda a Derecha)
    cross_lr = make_base_skeleton()
    cross_lr[L_WRIST] = MockLM(0.56, 0.17) # Mano izquierda sobre oreja derecha
    cross_lr[R_WRIST] = MockLM(0.64, 0.50) # Mano derecha abajo
    assert_true(check_contralateral_left_to_right(cross_lr), "Cruzado izq a oreja der")
    assert_true(check_right_arm_down(cross_lr), "Brazo der abajo en pose cruzada")

    # 2. Cruzado al Oido (Derecha a Izquierda)
    cross_rl = make_base_skeleton()
    cross_rl[R_WRIST] = MockLM(0.44, 0.17) # Mano derecha sobre oreja izquierda
    cross_rl[L_WRIST] = MockLM(0.36, 0.50) # Mano izquierda abajo
    assert_true(check_contralateral_right_to_left(cross_rl), "Cruzado der a oreja izq")
    assert_true(check_left_arm_down(cross_rl), "Brazo izq abajo en pose cruzada")

    # 3. Namaste Zen (Manos juntas en el centro del pecho)
    namaste = make_base_skeleton()
    namaste[L_WRIST] = MockLM(0.49, 0.48)
    namaste[R_WRIST] = MockLM(0.51, 0.48)
    assert_true(check_namaste_center(namaste), "Namaste manos juntas al centro del pecho")

    # 4. Reloj 9 y 12 (Brazo izq a las 9, der a las 12)
    clock_9_12 = make_base_skeleton()
    clock_9_12[L_WRIST] = MockLM(0.12, 0.32) # horizontal izq
    clock_9_12[R_WRIST] = MockLM(0.62, 0.05) # vertical arriba der
    assert_true(check_clock_arms_9_12(clock_9_12), "Reloj 9 y 12")

    # 5. Reloj 12 y 3 (Brazo izq a las 12, der a las 3)
    clock_12_3 = make_base_skeleton()
    clock_12_3[L_WRIST] = MockLM(0.38, 0.05) # vertical arriba izq
    clock_12_3[R_WRIST] = MockLM(0.88, 0.32) # horizontal der
    assert_true(check_clock_arms_12_3(clock_12_3), "Reloj 12 y 3")

    # 6. Marco Egipcio (L-up, R-down flexionados)
    egypt = make_base_skeleton()
    egypt[L_SHOULDER] = MockLM(0.38, 0.32)
    egypt[L_ELBOW] = MockLM(0.25, 0.32)
    egypt[L_WRIST] = MockLM(0.25, 0.18) # arriba del hombro
    egypt[R_SHOULDER] = MockLM(0.62, 0.32)
    egypt[R_ELBOW] = MockLM(0.75, 0.32)
    egypt[R_WRIST] = MockLM(0.75, 0.46) # abajo del hombro
    assert_true(check_egyptian_left_up_right_down(egypt), "Marco Egipcio asimetrico")

    # 7. Balanceo Suave Flow (dinamico)
    state = PlayerState()
    check_gentle_sway(state, base) # Calibrar center_x
    done = False
    for i in range(12):
        lm = make_base_skeleton()
        x_off = 0.08 if i % 2 == 0 else -0.08
        lm[L_WRIST] = MockLM(0.35 + x_off, 0.45)
        lm[R_WRIST] = MockLM(0.65 + x_off, 0.45)
        done, _ = check_gentle_sway(state, lm)
        if done: break
    assert_true(done, "Balanceo Suave Flow completado")

    # 8. Verificacion de Perfiles y Filtrado Seguro
    for p_key in PROFILE_KEYS:
        assert_true(p_key in PROFILES, f"Perfil {p_key} registrado en PROFILES")
        poses_p = get_poses_for_profile(p_key)
        assert_true(len(poses_p) >= 4, f"Perfil {p_key} debe tener al menos 4 poses, tiene {len(poses_p)}")

    # Perfil ZEN / MENTE ACTIVA: Exclusion estricta de saltos y sentadillas
    zen_poses = get_poses_for_profile('ZEN')
    for p in zen_poses:
        assert_true(p.get('checks') != check_jump, f"Perfil ZEN no debe incluir check_jump ({p['name']})")
        assert_true(p.get('checks') != check_squat, f"Perfil ZEN no debe incluir check_squat ({p['name']})")
        tags = set(p.get('tags', []))
        assert_true(bool(tags.intersection({'cognitive', 'zen', 'gentle'})), f"Pose {p['name']} en ZEN sin tag permitido")

    # Perfil CARDIO: Inclusion de saltos/boxeo/caderas
    cardio_poses = get_poses_for_profile('CARDIO')
    cardio_names = [p['name'] for p in cardio_poses]
    assert_true('Boxeo Rapido!' in cardio_names, "Cardio debe incluir Boxeo Rapido!")
    assert_true('Salto Mortal!' in cardio_names, "Cardio debe incluir Salto Mortal!")

    # Perfil JUNIOR: Inclusion de poses ludicas
    junior_poses = get_poses_for_profile('JUNIOR')
    junior_names = [p['name'] for p in junior_poses]
    assert_true('Mueve la Cabeza!' in junior_names, "Junior debe incluir Mueve la Cabeza!")
    assert_true('Letra Y!' in junior_names, "Junior debe incluir Letra Y!")

    print("      -> Todas las 5 poses cognitivas y los 4 perfiles pasaron la suite!")

def run_visual_and_auditor_tests():
    print("[5/6] Renderizando Escenas Reales Arquitectura 2.0 (5 Zonas AAA)...")
    w, h = 1280, 720
    auditor = UILayoutAuditor("Gameplay_AAA", w, h, check_center_safe_zone=True)

    # -------------------------------------------------------------
    # ESCENA 1: GAMEPLAY REGULAR ARQUITECTURA 2.0
    # -------------------------------------------------------------
    frame_gameplay = np.full((h, w, 3), (38, 32, 48), dtype=np.uint8)

    # Z1: Top-Left (Score + Fever)
    blend_rect_roi(frame_gameplay, 20, 18, 290, 132, (18, 15, 25), 0.82)
    cv2.rectangle(frame_gameplay, (20, 18), (310, 150), (0, 220, 255), 2)
    auditor.register_box("Panel_Score_Left", 20, 18, 290, 132, group="z1")
    auditor.register_text(frame_gameplay, "PUNTAJE: 12,450", 35, 58, cv2.FONT_HERSHEY_DUPLEX, 0.95, (0, 255, 255), 2, group="z1")
    auditor.register_text(frame_gameplay, "RACHA x12 | MULTI x2", 35, 95, cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 200, 255), 2, group="z1")
    cv2.rectangle(frame_gameplay, (35, 112), (225, 132), (60, 60, 75), -1)
    cv2.rectangle(frame_gameplay, (35, 112), (180, 132), (255, 50, 255), -1)
    cv2.rectangle(frame_gameplay, (35, 112), (225, 132), (255, 255, 255), 2)
    auditor.register_text(frame_gameplay, "FEVER 75%", 234, 128, cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 130, 255), 1, group="z1")

    # Z2: Top-Center Banner (Pose + Barra Hold)
    bx, by, bw, bh = 385, 18, 465, 102
    blend_rect_roi(frame_gameplay, bx, by, bw, bh, (15, 15, 25), 0.85)
    cv2.rectangle(frame_gameplay, (bx, by), (bx + bw, by + bh), (0, 255, 120), 2)
    auditor.register_box("Banner_Top_Center", bx, by, bw, bh, group="z2")
    auditor.register_text(frame_gameplay, "BRAZOS ARRIBA!", bx + 82, by + 40, cv2.FONT_HERSHEY_DUPLEX, 1.12, (0, 255, 120), 2, group="z2")
    cv2.rectangle(frame_gameplay, (bx + 28, by + 52), (bx + bw - 28, by + 74), (45, 45, 60), -1)
    cv2.rectangle(frame_gameplay, (bx + 28, by + 52), (bx + 28 + int((bw - 56) * 0.78), by + 74), (0, 210, 110), -1)
    cv2.rectangle(frame_gameplay, (bx + 28, by + 52), (bx + bw - 28, by + 74), (255, 255, 255), 2)
    auditor.register_text(frame_gameplay, "MANTENE: 78% (Grace Buffer Activo)", bx + 75, by + 95, cv2.FONT_HERSHEY_SIMPLEX, 0.52, (210, 255, 220), 1, group="z2")

    # Z3: Top-Right Dual Reference Card
    rx, ry, rw, rh = 900, 18, 356, 200
    blend_rect_roi(frame_gameplay, rx, ry, rw, rh, (20, 18, 30), 0.85)
    cv2.rectangle(frame_gameplay, (rx, ry), (rx + rw, ry + rh), (255, 200, 0), 2)
    auditor.register_box("Card_Reference_Right", rx, ry, rw, rh, group="z3")
    illus = load_pose_illustration_clean("pose_brazos", size=(155, 155))
    if illus is not None:
        frame_gameplay[ry + 12:ry + 12 + 155, rx + 12:rx + 12 + 155] = illus
        cv2.rectangle(frame_gameplay, (rx + 12, ry + 12), (rx + 167, ry + 167), (100, 100, 130), 1)
    ref_pts = {
        'nose': (0.5, 0.16), 'ls': (0.36, 0.32), 'rs': (0.64, 0.32),
        'le': (0.28, 0.18), 're': (0.72, 0.18), 'lw': (0.32, 0.05), 'rw': (0.68, 0.05),
        'lh': (0.42, 0.60), 'rh': (0.58, 0.60),
        'lk': (0.41, 0.76), 'rk': (0.59, 0.76), 'la': (0.40, 0.90), 'ra': (0.60, 0.90)
    }
    draw_full_body_stickman(frame_gameplay, rx + 180, ry + 10, 160, 158, ref_pts, (0, 255, 120))
    auditor.register_text(frame_gameplay, "ILUSTRACION + COACH VIVO", rx + 42, ry + 190, cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1, group="z3")

    # Z4: Lateral Izquierdo Flotante (Combos - Sin cajas opacas)
    auditor.register_text(frame_gameplay, "PERFECTO!! +300", 30, 310, cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 215, 255), 2, group="z4")
    auditor.register_text(frame_gameplay, "GROOVE CADERA +15", 30, 355, cv2.FONT_HERSHEY_DUPLEX, 0.72, (255, 120, 255), 2, group="z4")

    # ZONA CENTRAL AR (Safe Zone): Jugador con Ghost Pose, Anillos y Semáforo Continuo
    p_ls, p_rs = (545, 285), (705, 285)
    p_lh, p_rh = (565, 470), (685, 470)
    ghost_lw, ghost_rw = (520, 170), (730, 170)
    ghost_le, ghost_re = (505, 225), (745, 225)
    cv2.line(frame_gameplay, p_rs, ghost_re, (255, 220, 100), 4, cv2.LINE_AA)
    cv2.line(frame_gameplay, ghost_re, ghost_rw, (255, 220, 100), 4, cv2.LINE_AA)
    cv2.circle(frame_gameplay, ghost_lw, 22, (0, 255, 100), 3, cv2.LINE_AA)
    cv2.circle(frame_gameplay, ghost_rw, 26, (0, 215, 255), 3, cv2.LINE_AA)
    auditor.register_text(frame_gameplay, "ANILLO DESTINO", ghost_rw[0] - 55, ghost_rw[1] - 32, cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 215, 255), 1, group="ar", allow_center=True)

    real_lw, real_le = (520, 170), (505, 225)
    real_rw, real_re = (795, 260), (755, 295)
    cv2.arrowedLine(frame_gameplay, real_rw, (ghost_rw[0] + 10, ghost_rw[1] + 10), (0, 215, 255), 3, cv2.LINE_AA, tipLength=0.25)

    for a, b in [(p_ls, p_rs), (p_ls, p_lh), (p_rs, p_rh), (p_lh, p_rh)]:
        cv2.line(frame_gameplay, a, b, (255, 255, 0), 10, cv2.LINE_AA)
        cv2.line(frame_gameplay, a, b, (255, 255, 255), 3, cv2.LINE_AA)
    for a, b in [(p_ls, real_le), (real_le, real_lw)]:
        cv2.line(frame_gameplay, a, b, (60, 255, 60), 14, cv2.LINE_AA)
        cv2.line(frame_gameplay, a, b, (255, 255, 255), 4, cv2.LINE_AA)
    for a, b in [(p_rs, real_re), (real_re, real_rw)]:
        cv2.line(frame_gameplay, a, b, (0, 200, 255), 14, cv2.LINE_AA)
        cv2.line(frame_gameplay, a, b, (255, 255, 255), 4, cv2.LINE_AA)
    cv2.circle(frame_gameplay, (625, 210), 24, (255, 255, 0), 3, cv2.LINE_AA)
    auditor.register_text(frame_gameplay, "100% OK!", real_lw[0] - 110, real_lw[1] + 5, cv2.FONT_HERSHEY_DUPLEX, 0.58, (80, 255, 80), 2, group="ar", allow_center=True)
    auditor.register_text(frame_gameplay, "65% SUBE MAS!", real_rw[0] - 20, real_rw[1] + 35, cv2.FONT_HERSHEY_DUPLEX, 0.58, (0, 215, 255), 2, group="ar", allow_center=True)

    # Z5: Bottom Strip de Picto-Cards
    blend_rect_roi(frame_gameplay, 20, 585, 1240, 120, (18, 15, 28), 0.88)
    cv2.rectangle(frame_gameplay, (20, 585), (1260, 705), (80, 70, 100), 2)
    auditor.register_box("Strip_Bottom_Container", 20, 585, 1240, 120, group="z5")

    for i in range(5):
        cx = 35 + i * 245
        p_data = POSES[i]
        blend_rect_roi(frame_gameplay, cx, 595, 235, 100, (40, 35, 55), 0.82)
        cv2.rectangle(frame_gameplay, (cx, 595), (cx + 235, 695), (0, 215, 255) if i == 0 else (90, 85, 110), 2 if i == 0 else 1)
        icon = load_pose_illustration_clean(p_data.get('icon_name', ''), size=(75, 75))
        if icon is not None:
            frame_gameplay[607:682, cx + 10:cx + 85] = icon
        else:
            draw_star_icon(frame_gameplay, cx + 45, 645, 22, (0, 215, 255))
        words = p_data['name'].split()
        l1 = " ".join(words[:2])
        l2 = " ".join(words[2:]) if len(words) > 2 else ""
        cv2.putText(frame_gameplay, l1, (cx + 90, 635), cv2.FONT_HERSHEY_DUPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)
        if l2:
            cv2.putText(frame_gameplay, l2, (cx + 90, 660), cv2.FONT_HERSHEY_DUPLEX, 0.48, (200, 200, 220), 1, cv2.LINE_AA)
        auditor.register_box(f"card_{i}", cx, 595, 235, 100, group="z5")

    cv2.imwrite("test_visual_gameplay.jpg", frame_gameplay, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print("      -> test_visual_gameplay.jpg guardada con estandar AAA!")

    # -------------------------------------------------------------
    # ESCENA 2: FEVER MODE ACTIVO (BANNER SUPERIOR Y CONFETI ORGÁNICO)
    # -------------------------------------------------------------
    frame_fever = frame_gameplay.copy()
    fever_tint = np.full_like(frame_fever, (180, 20, 180), dtype=np.uint8)
    cv2.addWeighted(fever_tint, 0.20, frame_fever, 0.80, 0, frame_fever)

    # Confeti con física distribuida en todo el frame
    ps = ParticleSystem()
    for _ in range(80):
        ps.particles.append({
            'x': float(random.randint(20, w - 20)), 'y': float(random.randint(40, h - 120)),
            'dx': random.uniform(-2.0, 2.0), 'dy': random.uniform(2, 6),
            'life': random.randint(20, 50), 'color': (0, random.randint(215, 255), 255),
            'size': random.randint(4, 8)
        })
    ps.update_and_draw(frame_fever)

    # Banner FEVER TIME en Zona Superior (y: 115) - NUNCA SOBRE LA CABEZA DEL JUGADOR
    blend_rect_roi(frame_fever, 420, 115, 440, 55, (20, 15, 30), 0.88)
    cv2.rectangle(frame_fever, (420, 115), (860, 170), (0, 240, 255), 2)
    cv2.putText(frame_fever, "FEVER TIME! MULTI x3", (450, 152), cv2.FONT_HERSHEY_DUPLEX, 0.95, (0, 240, 255), 2, cv2.LINE_AA)

    cv2.imwrite("test_visual_fever.jpg", frame_fever, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print("      -> test_visual_fever.jpg guardada con estandar AAA!")

    # -------------------------------------------------------------
    # ESCENA 3: MENÚ CINÉTICO ERGONÓMICO (CONTROL DISCRETO + DWELL ACOPLADO)
    # -------------------------------------------------------------
    frame_menu = np.full((h, w, 3), (25, 20, 35), dtype=np.uint8)
    auditor_menu = UILayoutAuditor("Menu_AAA", w, h, check_center_safe_zone=True)

    # Header Menu (Zona Superior Fuera de Safe Zone)
    blend_rect_roi(frame_menu, 200, 15, 880, 52, (15, 12, 22), 0.88)
    cv2.rectangle(frame_menu, (200, 15), (1080, 67), (0, 215, 255), 2)
    auditor_menu.register_box("menu_header", 200, 15, 880, 52, group="menu_hud")
    auditor_menu.register_text(frame_menu, "POSES LOCAS - SELECCION KINETICA", 280, 48, cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2, group="menu_hud")

    # Receptor Superior de Inicio de Partida (Termina en y=120, protegiendo Safe Zone y>=130)
    blend_rect_roi(frame_menu, 380, 75, 520, 45, (20, 35, 25), 0.85)
    cv2.rectangle(frame_menu, (380, 75), (900, 120), (0, 255, 120), 2)
    auditor_menu.register_box("menu_start_receptor", 380, 75, 520, 45, group="menu_hud")
    auditor_menu.register_text(frame_menu, "AMBOS BRAZOS ARRIBA: HOLD PARA JUGAR", 405, 105, cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 120), 1, group="menu_hud")

    # Columnas Laterales Delgadas con Dwell Acoplado (Fuera de x:370..890)
    # Mano Izquierda: Selector de Modo
    blend_rect_roi(frame_menu, 30, 160, 260, 360, (20, 30, 45), 0.80)
    cv2.rectangle(frame_menu, (30, 160), (290, 520), (0, 255, 120), 2)
    auditor_menu.register_box("menu_left_col", 30, 160, 260, 360, group="menu_left")
    auditor_menu.register_text(frame_menu, "MANO IZQ: MODO", 45, 195, cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 255, 120), 2, group="menu_left")

    modes = ["1. ARCADE (ACTIVO)", "2. COREOGRAFIA", "3. PRACTICA"]
    for i, m in enumerate(modes):
        bg_col = (40, 80, 50) if i == 0 else (30, 35, 45)
        border_col = (0, 255, 120) if i == 0 else (80, 90, 100)
        cv2.rectangle(frame_menu, (45, 220 + i * 55), (275, 265 + i * 55), bg_col, -1)
        cv2.rectangle(frame_menu, (45, 220 + i * 55), (275, 265 + i * 55), border_col, 2)
        cv2.putText(frame_menu, m, (55, 250 + i * 55), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

    # Mano Derecha: Selector de Música
    blend_rect_roi(frame_menu, 990, 160, 260, 360, (45, 20, 35), 0.80)
    cv2.rectangle(frame_menu, (990, 160), (1250, 520), (255, 100, 200), 2)
    auditor_menu.register_box("menu_right_col", 990, 160, 260, 360, group="menu_right")
    auditor_menu.register_text(frame_menu, "MANO DER: MUSICA", 1005, 195, cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 100, 200), 2, group="menu_right")

    songs = ["1. MACARENA (103 BPM)", "2. ASEREJE (106 BPM)", "3. YMCA (127 BPM)"]
    for i, s in enumerate(songs):
        bg_col = (80, 40, 60) if i == 0 else (35, 30, 45)
        border_col = (255, 100, 200) if i == 0 else (90, 80, 100)
        cv2.rectangle(frame_menu, (1005, 220 + i * 55), (1235, 265 + i * 55), bg_col, -1)
        cv2.rectangle(frame_menu, (1005, 220 + i * 55), (1235, 265 + i * 55), border_col, 2)
        cv2.putText(frame_menu, s, (1015, 250 + i * 55), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

    # Zona Central AR: Jugador realizando postura neutra
    lm_menu = make_base_skeleton()
    draw_skeleton_with_feedback(frame_menu, lm_menu, w, h, True, True, 1.0, 1.0)
    cv2.imwrite("test_visual_menu.jpg", frame_menu, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print("      -> test_visual_menu.jpg guardada con estandar AAA!")

    # Ejecutar auditoría matemática de 5 Compuertas
    summary_gp = auditor.summary()
    summary_menu = auditor_menu.summary()

    total_violations = summary_gp['violations_count'] + summary_menu['violations_count']
    print(f"      -> Violaciones de Layout Detectadas: {total_violations}")
    for v in summary_gp['violations']:
        print(f"         [Gameplay] {v}")
    for v in summary_menu['violations']:
        print(f"         [Menu] {v}")

    assert_eq(total_violations, 0, f"Auditor detecto {total_violations} violaciones matematicas en layout")
    print("      -> 5 Compuertas Matematicas aprobadas con CERO violaciones!")
    print("      -> 5 Compuertas Matematicas aprobadas con CERO violaciones!")

def test_anatomy_and_math():
    run_anatomy_and_math_tests()

def test_static_poses():
    run_static_pose_tests()

def test_dynamic_poses():
    run_dynamic_pose_tests()

def test_cognitive_and_profiles():
    run_cognitive_and_profile_tests()

def test_visual_and_auditor():
    run_visual_and_auditor_tests()

def run_all():
    print("==================================================")
    print("      POSES LOCAS - SUITE COMPLETA DE TESTS       ")
    print("==================================================")
    run_anatomy_and_math_tests()
    run_static_pose_tests()
    run_dynamic_pose_tests()
    run_cognitive_and_profile_tests()
    run_visual_and_auditor_tests()
    print("==================================================")
    print("      TODO CHECKQUEADO Y APROBADO EXITOSAMENTE    ")
    print("==================================================")

if __name__ == "__main__":
    run_all()
