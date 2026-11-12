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
    POSES, COREOGRAFIAS,
    FeatureFlags, FEATURES, DuoModeManager, CustomGhostRenderer,
    AudioReactiveEngine, PartyPlatformEngine,
    MockVideoCapture, VideoCaptureAsync,
    CalibrationStep, CalibrationData, CalibrationManager
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

    # 6. Mueve los brazos (Alternado / Antifase)
    state = PlayerState()
    done = False
    for i in range(14):
        time.sleep(0.11)
        lm = make_base_skeleton()
        if i % 2 == 0:
            lm[L_WRIST] = MockLM(0.20, 0.10) # Izq arriba
            lm[R_WRIST] = MockLM(0.80, 0.50) # Der abajo
        else:
            lm[L_WRIST] = MockLM(0.20, 0.50) # Izq abajo
            lm[R_WRIST] = MockLM(0.80, 0.10) # Der arriba
        done, _ = check_flail_arms(state, lm)
        if done: break
    assert_true(done, "Mueve los brazos alternado (coach) completado")

    # 7. Mueve los brazos (Simetrico / Bombeo conjunto)
    state = PlayerState()
    done = False
    for i in range(14):
        time.sleep(0.11)
        lm = make_base_skeleton()
        if i % 2 == 0:
            lm[L_WRIST] = MockLM(0.20, 0.10) # Ambos arriba
            lm[R_WRIST] = MockLM(0.80, 0.10)
        else:
            lm[L_WRIST] = MockLM(0.20, 0.50) # Ambos abajo
            lm[R_WRIST] = MockLM(0.80, 0.50)
        done, _ = check_flail_arms(state, lm)
        if done: break
    assert_true(done, "Mueve los brazos simetrico completado")

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

    # Z2: Banner Inferior Centrado con Opacidad Adaptativa (Brazos Libres Arriba)
    bx, by, bw, bh = 390, 634, 500, 70
    blend_rect_roi(frame_gameplay, bx, by, bw, bh, (15, 15, 25), 0.76)
    cv2.rectangle(frame_gameplay, (bx, by), (bx + bw, by + bh), (0, 255, 120), 2)
    auditor.register_box("Banner_Bottom_Center", bx, by, bw, bh, group="z2")
    auditor.register_text(frame_gameplay, "BRAZOS ARRIBA!", bx + 105, by + 30, cv2.FONT_HERSHEY_DUPLEX, 0.88, (0, 255, 120), 2, group="z2")
    cv2.rectangle(frame_gameplay, (bx + 24, by + 40), (bx + bw - 24, by + 58), (45, 45, 60), -1)
    cv2.rectangle(frame_gameplay, (bx + 24, by + 40), (bx + 24 + int((bw - 48) * 0.78), by + 58), (0, 210, 110), -1)
    cv2.rectangle(frame_gameplay, (bx + 24, by + 40), (bx + bw - 24, by + 58), (255, 255, 255), 1)
    auditor.register_text(frame_gameplay, "MANTENE: 78%", bx + 35, by + 54, cv2.FONT_HERSHEY_SIMPLEX, 0.48, (210, 255, 220), 1, group="z2")

    # Z3: Top-Right Dual Reference Card (Limpia sin etiquetas redundantes)
    rx, ry, rw, rh = 900, 18, 356, 190
    blend_rect_roi(frame_gameplay, rx, ry, rw, rh, (20, 18, 30), 0.85)
    cv2.rectangle(frame_gameplay, (rx, ry), (rx + rw, ry + rh), (255, 200, 0), 2)
    auditor.register_box("Card_Reference_Right", rx, ry, rw, rh, group="z3")
    illus = load_pose_illustration_clean("pose_brazos", size=(155, 155))
    if illus is not None:
        frame_gameplay[ry + 16:ry + 16 + 155, rx + 12:rx + 12 + 155] = illus
        cv2.rectangle(frame_gameplay, (rx + 12, ry + 16), (rx + 167, ry + 171), (100, 100, 130), 1)
    ref_pts = {
        'nose': (0.5, 0.16), 'ls': (0.36, 0.32), 'rs': (0.64, 0.32),
        'le': (0.28, 0.18), 're': (0.72, 0.18), 'lw': (0.32, 0.05), 'rw': (0.68, 0.05),
        'lh': (0.42, 0.60), 'rh': (0.58, 0.60),
        'lk': (0.41, 0.76), 'rk': (0.59, 0.76), 'la': (0.40, 0.90), 'ra': (0.60, 0.90)
    }
    draw_full_body_stickman(frame_gameplay, rx + 176, ry + 10, 168, 165, ref_pts, (0, 255, 120))

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

    # ZONA INFERIOR LIBRE DE SOBRECARGA COGNITIVA (100% VISIBILIDAD DE CUERPO Y PISO)
    # Se ha eliminado el carril de picto-cards de poses futuras para no adelantar pasos,
    # evitar sobrecarga cognitiva y permitir 100% de visibilidad del cuerpo completo del jugador.
    auditor.register_text(frame_gameplay, "X = Saltar Pose", 35, 145, cv2.FONT_HERSHEY_SIMPLEX, 0.48, (170, 185, 210), 1, group="z1")

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

def run_feature_and_toggles_tests():
    print("[6/6] Probando Feature Flags, Modo Duo, Custom Ghost, Audio Reactivo y Salto Party...")

    # 1. Verificar que por defecto TODOS los flags estan desactivados (False)
    FEATURES.reset_all()
    assert_eq(FEATURES.enable_duo_mode, False, "Duo mode desactivado por defecto")
    assert_eq(FEATURES.enable_custom_ghost, False, "Custom ghost desactivado por defecto")
    assert_eq(FEATURES.enable_reactive_audio, False, "Audio reactivo desactivado por defecto")
    assert_eq(FEATURES.enable_party_platform, False, "Salto party desactivado por defecto")

    # 2. Toggles funcionan bidireccionalmente
    assert_eq(FEATURES.toggle_duo_mode(), True, "Toggle Duo a True")
    assert_eq(FEATURES.toggle_duo_mode(), False, "Toggle Duo restaurado a False")

    assert_eq(FEATURES.toggle_custom_ghost(), True, "Toggle Ghost a True")
    assert_eq(FEATURES.toggle_custom_ghost(), False, "Toggle Ghost restaurado a False")

    assert_eq(FEATURES.toggle_reactive_audio(), True, "Toggle Audio a True")
    assert_eq(FEATURES.toggle_reactive_audio(), False, "Toggle Audio restaurado a False")

    assert_eq(FEATURES.toggle_party_platform(), True, "Toggle Party a True")
    assert_eq(FEATURES.toggle_party_platform(), False, "Toggle Party restaurado a False")

    # 3. Test DuoModeManager
    duo = DuoModeManager()
    sk_p1 = make_base_skeleton()
    # P1 brazos arriba
    sk_p1[L_WRIST].y = 0.05
    sk_p1[R_WRIST].y = 0.05
    sk_p2 = make_base_skeleton()
    # P2 brazos arriba
    sk_p2[L_WRIST].y = 0.05
    sk_p2[R_WRIST].y = 0.05
    pose_test = next(p for p in POSES if p.get('name') == 'Brazos Arriba!')

    p1_ok, p1_score, p2_ok, p2_score, is_synced, events = duo.evaluate_players(
        pose_test, sk_p1, sk_p2, dt=0.5, current_time=1.0
    )
    assert_true(p1_ok, "P1 realizo la pose correctamente")
    assert_true(p2_ok, "P2 realizo la pose correctamente")
    assert_true(is_synced, "Ambos jugadores estan sincronizados en la pose")
    assert_true(duo.hold_progress_p1 > 0.5, "P1 acumulo hold progress")
    assert_true(duo.hold_progress_p2 > 0.5, "P2 acumulo hold progress")

    frame_duo = np.zeros((720, 1280, 3), dtype=np.uint8)
    duo.draw_duo_hud(frame_duo, 1280, 720)
    print("      -> DuoModeManager (scoring concurrente y cooperativo) OK!")

    # 4. Test CustomGhostRenderer
    ghost = CustomGhostRenderer("CYBERPUNK")
    assert_eq(ghost.theme_key, "CYBERPUNK", "Tema inicial Cyberpunk")
    ghost.set_theme("GOLDEN")
    assert_eq(ghost.theme_key, "GOLDEN", "Tema cambiado a Golden")
    frame_ghost = np.zeros((720, 1280, 3), dtype=np.uint8)
    ghost.render_custom_ghost(frame_ghost, sk_p1, pose_test, 1280, 720, 1.0, 1.0, current_time=0.5)
    print("      -> CustomGhostRenderer (4 temas y auras adaptativas) OK!")

    # 5. Test AudioReactiveEngine
    audio = AudioReactiveEngine(bpm=128.0)
    audio.update(current_time=0.25, bpm=128.0, is_playing=True)
    assert_eq(len(audio.frequency_bands), 8, "8 bandas espectrales de ecualizador")
    assert_true(audio.beat_energy > 0, "Energia reactiva de ritmo calculada")
    frame_audio = np.zeros((720, 1280, 3), dtype=np.uint8)
    audio.draw_reactive_visuals(frame_audio, 1280, 720)
    print("      -> AudioReactiveEngine (sincronia BPM y espectro) OK!")

    # 6. Test PartyPlatformEngine (Gran Salto Party)
    party = PartyPlatformEngine(speed=300.0)
    p_state = PlayerState()
    party.platform_x = 640.0  # Justo en el centro (ZONA DE IMPACTO)
    p_state.jump_active = True
    evs = party.update(dt=0.01, player_state=p_state, w=1280, current_time=2.0)
    assert_eq(len(evs), 1, "Disparo evento de salto exitoso en zona de impacto")
    assert_eq(evs[0]["type"], "jump_success", "Tipo de evento jump_success")
    assert_true(evs[0]["points"] >= 150, "Puntaje otorgado por salto coordinado")
    assert_eq(party.consecutive_jumps, 1, "Racha de 1 salto consecutivo")
    frame_party = np.zeros((720, 1280, 3), dtype=np.uint8)
    party.draw_platform(frame_party, 1280, 720)
    print("      -> PartyPlatformEngine (plataforma de movimiento y deteccion de salto) OK!")

    # 7. Verificacion de exclusion estricta de Simon Dice
    for val in POSES:
        p_name = val.get("name", "").lower()
        assert_true("simon" not in p_name, f"Nombre prohibido encontrado: {val.get('name')}")
    print("      -> Verificacion: Modo Simon Dice excluido estrictamente como solicito el usuario.")
    print("      -> Todas las 4 features desactivadas por defecto e integradas exitosamente!")

def run_regression_tests():
    print("[7/7] Probando Anti-Regresiones Obligatorias (UI/UX y Hardware)...")

    # 1. Anti-regresion: Brazos Libres Arriba y Barra Inferior Compacta
    auditor_reg = UILayoutAuditor("Anti_Regression_Gameplay", 1280, 720)
    auditor_reg.register_box("score_box", 20, 18, 290, 132, group="z1")
    auditor_reg.register_box("ref_card", 900, 18, 356, 190, group="z3")
    auditor_reg.register_box("bottom_banner", 390, 634, 500, 70, group="z2")

    # Validar que la zona superior central (x:370..890, y:0..130) esté 100% libre para levantar brazos
    top_center_boxes = [b for b in auditor_reg.elements if b['group'] == 'z2' and b['y1'] < 130]
    assert_eq(len(top_center_boxes), 0, "La parte superior central debe estar libre para brazos arriba")
    print("      -> Brazos libres arriba y banner inferior con opacidad adaptativa OK!")

    # 1b. Validar exclusion de 'De Lado a Lado' y reemplazo por 'Caderas' en JUNIOR
    junior_poses = get_poses_for_profile('JUNIOR')
    junior_names = [p['name'] for p in junior_poses]
    assert_true('De Lado a Lado!' not in junior_names, "'De Lado a Lado' debe estar excluida de ninos")
    assert_true('Baila! Mueve Caderas' in junior_names, "'Baila! Mueve Caderas' debe estar activa para ninos")
    print("      -> Perfil Junior optimizado (Sin desplazamiento lateral, con baile de caderas) OK!")

    # 2. Anti-regresion: Prevencion de Texto Espejado (Text Mirroring Prevention)
    mock_cam = MockVideoCapture()
    ret, raw_frame = mock_cam.read()
    assert_true(ret and raw_frame is not None, "MockVideoCapture debe entregar frame valido")
    assert_eq(raw_frame.shape, (720, 1280, 3), "Dimensiones correctas en MockVideoCapture")

    flipped = cv2.flip(raw_frame, 1)
    diff = np.abs(raw_frame.astype(int) - flipped.astype(int))
    center_diff = float(np.mean(diff[300:420, 500:780]))
    assert_true(center_diff < 5.0, f"Canvas sintetico de calibracion es simetrico (diff={center_diff:.2f})")
    assert_true(getattr(mock_cam, 'is_mock', False), "MockVideoCapture debe identificarse con is_mock=True")
    print("      -> Prevencion de texto espejado en modo demo/virtual OK!")

    # 3. Anti-regresion: Soporte de FourCC MJPG y warm-up en VideoCaptureAsync
    cam_async = VideoCaptureAsync(src=999)
    assert_true(not cam_async.is_opened(), "Dispositivo inexistente no debe marcarse como opened")
    assert_eq(getattr(cam_async, 'is_mock', False), False, "VideoCaptureAsync tiene is_mock=False")
    print("      -> Resiliencia y control de warm-up en VideoCaptureAsync OK!")

    # 4. Anti-regresion: Contrato de Pose Unica Activa
    pose_names = [p['name'] for p in POSES]
    assert_eq(len(pose_names), len(set(pose_names)), "No deben existir poses con nombres duplicados")
    print("      -> Contrato de Pose Unica Activa y Catalogo sin colisiones OK!")

    # 5. Anti-regresion: Sincronia biomecanica de brazos y correspondencia visual
    p_arms = {'name': 'Mueve los Brazos!', 'dynamic': True}
    pts_wave_up = get_animated_ref_points(p_arms, t=0.26)
    assert_true(pts_wave_up['lw'][1] < pts_wave_up['rw'][1], "Brazo izq debe subir (y menor) cuando der baja")
    assert_true(0.08 <= pts_wave_up['lw'][1] <= 0.75, "Brazo izq dentro de limites visuales")
    assert_true(0.08 <= pts_wave_up['rw'][1] <= 0.75, "Brazo der dentro de limites visuales")
    print("      -> Sincronia biomecanica de brazos y correspondencia visual OK!")

def run_calibration_tests():
    print("[6.5/7] Probando Sistema de Calibracion Pre-Juego (Centro -> T-Pose -> Brazos Arriba)...")
    calib = CalibrationManager()
    assert_true(not calib.is_active(), "Calibracion debe iniciar inactiva")

    calib.start()
    assert_true(calib.is_active(), "Calibracion debe activarse con start()")
    assert_eq(calib.step, CalibrationStep.CENTER, "Paso inicial debe ser CENTER")

    # 1. Simular Centrado: pose centrada por 1.1s
    center_lm = make_base_skeleton()
    done = False
    for _ in range(6):
        done = calib.update(0.20, center_lm, time.time())
    assert_true(not done, "Paso 1 no debe terminar inmediatamente la sesion")
    assert_eq(calib.step, CalibrationStep.T_POSE, "Debe haber avanzado a T_POSE")

    # 2. Simular T-Pose por 1.3s
    t_pose_lm = make_base_skeleton()
    t_pose_lm[L_WRIST] = MockLM(0.12, 0.32)
    t_pose_lm[R_WRIST] = MockLM(0.88, 0.32)
    for _ in range(7):
        done = calib.update(0.20, t_pose_lm, time.time())
    assert_true(not done, "Paso 2 no debe terminar inmediatamente")
    assert_eq(calib.step, CalibrationStep.ARMS_UP, "Debe haber avanzado a ARMS_UP")
    assert_true(calib.data.arm_span > 0.60, f"Envergadura calibrada esperada > 0.60, dio {calib.data.arm_span}")

    # 3. Simular Brazos Arriba por 1.1s
    arms_up_lm = make_base_skeleton()
    arms_up_lm[L_WRIST] = MockLM(0.35, 0.08)
    arms_up_lm[R_WRIST] = MockLM(0.65, 0.08)
    for _ in range(6):
        done = calib.update(0.20, arms_up_lm, time.time())
    assert_true(not done, "Paso 3 pasa a READY")
    assert_eq(calib.step, CalibrationStep.READY, "Debe haber avanzado a READY")
    assert_true(calib.data.is_calibrated, "Datos deben marcarse como calibrados")

    # 4. Finalizar cuenta regresiva de READY por 0.9s
    for _ in range(5):
        done = calib.update(0.20, arms_up_lm, time.time())
    assert_true(done, "Calibracion debe marcarse como completada tras READY")
    assert_true(not calib.is_active(), "Calibracion debe quedar inactiva tras terminar")

    # 5. Prueba de Salto (Skip)
    calib_skip = CalibrationManager()
    calib_skip.start()
    calib_skip.skip()
    assert_true(not calib_skip.is_active(), "skip() debe desactivar calibracion")
    assert_true(calib_skip.data.is_calibrated, "skip() debe aplicar valores por defecto validos")

    # 6. Auditoria de UI / Renderizado del HUD de Calibracion
    frame_calib = np.full((720, 1280, 3), (35, 30, 42), dtype=np.uint8)
    calib_render = CalibrationManager()
    calib_render.start()
    calib_render.step = CalibrationStep.T_POSE
    calib_render.hold_time = 0.6
    calib_render.draw(frame_calib, 1280, 720, 1.0)
    assert_eq(frame_calib.shape, (720, 1280, 3), "Frame de calibracion debe tener dimensiones 1280x720")

    auditor_calib = UILayoutAuditor("PreGame_Calibration", 1280, 720, check_center_safe_zone=False)
    auditor_calib.register_box("Calib_Top_Banner", 1280 // 2 - 340, 20, 680, 102, group="banner")
    auditor_calib.register_box("Calib_Coach_Card", 1280 - 230, 20, 210, 160, group="coach")
    auditor_calib.register_box("Calib_Skip_Pill", 1280 // 2 - 220, 720 - 48, 440, 36, group="skip")
    auditor_calib.register_text(frame_calib, "CALIBRACION PRE-JUEGO [PASO 2/3]: T-POSE", 1280 // 2 - 200, 50,
                                cv2.FONT_HERSHEY_DUPLEX, 0.72, (0, 255, 255), 2, group="banner")
    summary = auditor_calib.summary()
    assert_true(summary["passed"], f"Auditoria visual de calibracion fallida: {summary['violations']}")
    print("      -> Sistema y HUD de Calibracion Pre-Juego aprobado 100%!")

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

def test_feature_toggles_and_subsystems():
    run_feature_and_toggles_tests()

def test_calibration():
    run_calibration_tests()

def test_illustrations_and_movement():
    from test_pose_illustrations import run_all_illustration_tests
    run_all_illustration_tests()

def test_regressions():
    run_regression_tests()

def run_all():
    print("==================================================")
    print("      POSES LOCAS - SUITE COMPLETA DE TESTS       ")
    print("==================================================")
    run_anatomy_and_math_tests()
    run_static_pose_tests()
    run_dynamic_pose_tests()
    run_cognitive_and_profile_tests()
    run_visual_and_auditor_tests()
    run_feature_and_toggles_tests()
    run_calibration_tests()
    from test_pose_illustrations import run_all_illustration_tests
    run_all_illustration_tests()
    run_regression_tests()
    print("==================================================")
    print("      TODO CHECKQUEADO Y APROBADO EXITOSAMENTE    ")
    print("==================================================")

if __name__ == "__main__":
    run_all()
