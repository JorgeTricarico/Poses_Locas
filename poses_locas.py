"""
=====================================================================
POSES LOCAS AR — ORQUESTADOR PRINCIPAL (ARQUITECTURA MODULAR 2.0)
=====================================================================
Punto de entrada liviano y desacoplado, compatible con PC, Smart TV y PWA.
Los subsistemas están aislados en el paquete `poses_core`:
  - `poses_core.geometry`: Álgebra vectorial y normalización anatómica BodyUnit.
  - `poses_core.state`: Máquina de estados cinéticos del jugador.
  - `poses_core.detectors`: Detectores de poses estáticas, dinámicas y cognitivas.
  - `poses_core.catalog`: 23 Poses, 4 Perfiles inclusivos y Coreografías.
  - `poses_core.rendering`: Primitivas, Coach vivo, Ghost AR y partículas.
  - `poses_core.capture`: Captura asíncrona de cámara USB y RTSP.
  - `poses_core.engine`: Colas de poses, scoring continuo y telemetría.
=====================================================================
"""

import os
import cv2
import time
import math
import random
import numpy as np

# Importaciones retrocompatibles y modulares desde poses_core
from poses_core import (
    NOSE, L_EAR, R_EAR, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW,
    L_WRIST, R_WRIST, L_HIP, R_HIP,
    SKELETON_CONNECTIONS, LEFT_ARM_CONNECTIONS, RIGHT_ARM_CONNECTIONS,
    get_body_unit, calc_angle_2d, distance_to_score, score_to_traffic_color,
    score_arm, get_point,
    PlayerState,
    check_left_arm_up, check_right_arm_up, check_left_arm_down, check_right_arm_down,
    check_left_arm_horizontal, check_right_arm_horizontal,
    check_left_hand_on_hip, check_right_hand_on_hip,
    check_left_hand_on_head, check_right_hand_on_head,
    check_left_bicep, check_right_bicep, check_right_salute,
    check_left_arm_y, check_right_arm_y, check_left_arm_o, check_right_arm_o,
    check_monkey_left, check_monkey_right, check_airplane_left, check_airplane_right,
    check_contralateral_left_to_right, check_contralateral_right_to_left,
    check_namaste_center, check_clock_arms_9_12, check_clock_arms_12_3,
    check_egyptian_left_up_right_down, check_gentle_sway,
    check_shake_hips, check_shake_head, check_jump, check_squat,
    check_spin, check_flail_arms, check_move_side_to_side,
    check_boxer_jabs, check_air_guitar, check_hand_head_shake_hips,
    check_jump_arms_up, check_spin_hand_head, check_gesture_next,
    POSES, PROFILES, PROFILE_KEYS, COREOGRAFIAS, SONG_BPM,
    get_poses_for_profile, get_beat_pulse,
    blend_rect_roi, load_pose_illustration_clean, draw_star_icon, draw_bolt_icon,
    draw_progress_bar, draw_full_body_stickman, get_animated_ref_points,
    draw_intent_arrows_in_box, compute_body_anchored_targets,
    draw_ghost_and_target_rings, draw_skeleton_with_feedback,
    HandTrailSystem, ParticleSystem, FloatingText,
    MockVideoCapture, VideoCaptureAsync,
    shift_queue, get_dynamic_progress, log_metric,
    FeatureFlags, FEATURES, DuoModeManager, CustomGhostRenderer,
    AudioReactiveEngine, PartyPlatformEngine,
    CalibrationStep, CalibrationData, CalibrationManager
)

# Configuración de entorno y audio
ENABLE_SFX = False
RTSP_URL = os.environ.get("POSES_RTSP_URL", "")

try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()
    snd_success = pygame.mixer.Sound('success_new.wav') if os.path.exists('success_new.wav') else None
    snd_fail = pygame.mixer.Sound('fail.wav') if os.path.exists('fail.wav') else None
    snd_punch = pygame.mixer.Sound('punch_new.wav') if os.path.exists('punch_new.wav') else None
    HAS_AUDIO = True
except Exception as e:
    HAS_AUDIO = False
    snd_success = None
    snd_fail = None
    snd_punch = None


def play_sound(snd):
    """Reproduce sonido si SFX está habilitado y el dispositivo está activo."""
    if HAS_AUDIO and snd and ENABLE_SFX:
        try:
            snd.play()
        except Exception:
            pass


# Carga diferida de mediapipe para entornos headless y pruebas
try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
except Exception:
    mp = None
    mp_pose = None


def main():
    """Bucle orquestador principal del juego de escritorio."""
    cap = None
    target_cams = [0, 1, 2]
    if RTSP_URL:
        target_cams.append(RTSP_URL)

    for cam_id in target_cams:
        test_cap = VideoCaptureAsync(cam_id)
        if test_cap.is_opened():
            cap = test_cap
            print(f"Camara abierta correctamente en origen: {cam_id}")
            break
        test_cap.release()

    if cap is None or not cap.is_opened():
        print("No se detecto camara fisica/RTSP. Iniciando modo Demo / Camara Virtual...")
        cap = MockVideoCapture()

    cap.start()

    if mp_pose:
        pose_detector = mp_pose.Pose(
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            enable_segmentation=False
        )
    else:
        pose_detector = None

    display_w, display_h = 1280, 720
    WINDOW_NAME = "Poses Locas AR"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    fever_overlay = np.full((display_h, display_w, 3), (255, 0, 255), dtype=np.uint8)
    green_overlay = np.full((display_h, display_w, 3), (0, 255, 0), dtype=np.uint8)
    gold_overlay = np.full((display_h, display_w, 3), (0, 215, 255), dtype=np.uint8)

    menu_options = []
    sfx_files = {'success.wav', 'success_new.wav', 'fail.wav', 'punch.wav', 'punch_new.wav', 'music.wav'}
    wav_files = [f for f in os.listdir('.') if f.endswith('.wav') and f not in sfx_files]
    wav_files.sort()
    for f in wav_files:
        name_display = f.replace('.wav', '').replace('_', ' ').upper()
        menu_options.append({'file': f, 'type': 'LIBRE', 'display': f"[LIBRE] {name_display}"})
        if f in COREOGRAFIAS:
            menu_options.append({'file': f, 'type': 'COREO', 'display': f"[COREO] {name_display}"})

    if not menu_options:
        menu_options = [{'file': 'Sin Musica', 'type': 'LIBRE', 'display': 'Sin Musica'}]

    selected_idx = 0
    show_menu = True

    score, streak, poses_completed = 0, 0, 0
    fever_gauge = 0
    fever_active = False
    fever_start_time = 0
    fever_duration = 10.0
    shake_time = 0
    multiplier = 1
    current_mode = 'LIBRE'
    current_song = menu_options[selected_idx]['file']
    coreo_idx = -1

    current_profile_idx = 0
    current_profile = PROFILE_KEYS[current_profile_idx]

    pose_queue = []
    for _ in range(5):
        if current_mode == 'COREO' and current_song in COREOGRAFIAS:
            coreo_idx = (coreo_idx + 1) % len(COREOGRAFIAS[current_song])
            p = dict(COREOGRAFIAS[current_song][coreo_idx])
            p['variant'] = 'NORMAL'
        else:
            candidates = get_poses_for_profile(current_profile)
            p = dict(random.choice(candidates))
            p['variant'] = 'NORMAL'
        pose_queue.append(p)
    current_pose = pose_queue[0]

    hold_progress = 0.0
    last_frame_time = time.time()
    pose_start_time = time.time()
    control_gesture_start = None
    control_gesture_required = 0.8
    queue_slide_offset = 0.0

    menu_left_start = None
    menu_right_start = None
    menu_both_start = None
    menu_confirm_required = 0.9

    particles = ParticleSystem()
    floating_texts = FloatingText()
    hand_trails = HandTrailSystem(maxlen=8)
    show_success_flash = False
    success_flash_time = 0
    state = PlayerState()

    # Motores de features desacopladas (desactivadas por defecto)
    duo_mgr = DuoModeManager()
    custom_ghost = CustomGhostRenderer()
    audio_reactive = AudioReactiveEngine()
    party_platform = PartyPlatformEngine()
    calib_mgr = CalibrationManager()
    in_calibration = False

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue

        frame = cv2.resize(frame, (display_w, display_h))
        frame = cv2.flip(frame, 1)

        results = None
        if pose_detector:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose_detector.process(rgb_frame)

        current_time = time.time()
        dt = min(0.1, current_time - last_frame_time)
        last_frame_time = current_time

        queue_slide_offset *= 0.82

        has_person = results is not None and results.pose_landmarks is not None
        left_score, right_score = 0.0, 0.0
        left_ok, right_ok = False, False

        # =========================================================
        # MODO JUEGO ACTIVO (show_menu == False)
        # =========================================================
        if not show_menu:
            if in_calibration:
                lm = results.pose_landmarks.landmark if has_person else None
                done = calib_mgr.update(dt, lm, current_time)
                calib_mgr.draw(frame, display_w, display_h, current_time)
                if done:
                    in_calibration = False
                    pose_start_time = current_time
                    state.reset()
                    if HAS_AUDIO and current_song and current_song != "Sin Musica":
                        try:
                            pygame.mixer.music.load(current_song)
                            pygame.mixer.music.play(-1)
                            pygame.mixer.music.set_volume(0.4)
                        except Exception:
                            pass
            else:
                # Reproducción infinita en Modo Libre: reinicia loop si termina la pista
                if HAS_AUDIO and current_mode == 'LIBRE' and current_song != 'Sin Musica':
                    if not pygame.mixer.music.get_busy():
                        try:
                            pygame.mixer.music.load(current_song)
                            pygame.mixer.music.play(-1)
                        except Exception:
                            pass
                if has_person:
                    lm = results.pose_landmarks.landmark
    
                    # Gesto Saltar Pose (Wakanda X en pecho)
                    if check_gesture_next(lm):
                        if control_gesture_start is None:
                            control_gesture_start = current_time
                        skip_prog = min(1.0, (current_time - control_gesture_start) / control_gesture_required)
                        blend_rect_roi(frame, (display_w - 320) // 2, 80, 320, 40, (20, 20, 30), 0.85)
                        draw_progress_bar(frame, (display_w - 300) // 2, 88, 300, 22, skip_prog, (0, 100, 255))
                        cv2.putText(frame, "SALTANDO POSE...", ((display_w - 280) // 2, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 150, 255), 2, cv2.LINE_AA)
    
                        if current_time - control_gesture_start >= control_gesture_required:
                            floating_texts.add("POSE SALTEADA!", 40, 310, (0, 100, 255), 1.3)
                            play_sound(snd_fail)
                            fever_gauge = max(0, fever_gauge - 20)
                            shake_time = current_time
                            log_metric(current_mode, current_pose['name'], current_time - pose_start_time, 'SKIPPED')
                            current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx, current_profile)
                            pose_start_time = current_time
                            control_gesture_start, hold_progress, streak = None, 0.0, 0
                            queue_slide_offset = 240.0
                            state.reset()
                    else:
                        control_gesture_start = None
    
                        # --- POSE: CONGELADOS! ---
                        if current_pose.get('is_freeze'):
                            left_score, right_score = 1.0, 1.0
                            left_ok, right_ok = True, True
                            if hold_progress == 0.0 and state.freeze_reference is None:
                                state.freeze_reference = [{"x": lm[kp].x, "y": lm[kp].y} for kp in [NOSE, L_WRIST, R_WRIST, L_HIP, R_HIP]]
    
                            movement = 0.0
                            if state.freeze_reference:
                                for i, kp in enumerate([NOSE, L_WRIST, R_WRIST, L_HIP, R_HIP]):
                                    dx = lm[kp].x - state.freeze_reference[i]["x"]
                                    dy = lm[kp].y - state.freeze_reference[i]["y"]
                                    movement += math.hypot(dx, dy)
    
                            time_left = max(0.0, 3.0 - (current_time - pose_start_time))
                            blend_rect_roi(frame, 400, 18, 480, 85, (15, 15, 30), 0.85)
                            cv2.rectangle(frame, (400, 18), (880, 103), (0, 215, 255), 2)
                            cv2.putText(frame, f"CONGELADOS! {time_left:.1f}s", (435, 58), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 255), 2, cv2.LINE_AA)
                            draw_progress_bar(frame, 425, 70, 430, 20, time_left / 3.0, (0, 215, 255))
    
                            if movement > 0.22:
                                floating_texts.add("TE MOVISTE!", 40, 310, (60, 60, 255), 1.8)
                                play_sound(snd_fail)
                                fever_gauge = max(0, fever_gauge - 40)
                                shake_time = current_time
                                streak = 0
                                log_metric(current_mode, 'CONGELADOS!', current_time - pose_start_time, 'FAILED')
                                current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx, current_profile)
                                pose_start_time = current_time
                                hold_progress = 0.0
                                queue_slide_offset = 240.0
                                state.reset()
                            elif time_left <= 0:
                                multiplier = 3 if fever_active else (1 + int(streak // 3))
                                points = int(1000 * multiplier)
                                score += points
                                poses_completed += 1
                                streak += 1
                                if not fever_active:
                                    fever_gauge = min(100, fever_gauge + 20)
                                    if fever_gauge >= 100:
                                        fever_active = True
                                        fever_start_time = current_time
                                        floating_texts.add("FEVER TIME!", display_w//2 - 160, 220, (0, 255, 255), 2.4)
                                particles.emit(display_w // 2, 340, (255, 255, 255), 45)
                                floating_texts.add(f"SOBREVIVISTE! +{points}", 40, 310, (0, 255, 120), 1.8)
                                play_sound(snd_success)
                                log_metric(current_mode, 'CONGELADOS!', current_time - pose_start_time, 'COMPLETED')
                                current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx, current_profile)
                                pose_start_time = current_time
                                hold_progress = 0.0
                                queue_slide_offset = 240.0
                                state.reset()
    
                        # --- POSES DINÁMICAS ---
                        elif current_pose.get('dynamic'):
                            completed, events = current_pose['checks'](state, lm)
                            left_score, right_score = 1.0, 1.0
                            left_ok, right_ok = True, True
    
                            for e in events:
                                if e['type'] == 'hit':
                                    play_sound(snd_punch)
                                    px = int(e['x'] * display_w)
                                    py = int(e['y'] * display_h)
                                    particles.emit(px, py, current_pose['color'], 24)
                                    floating_texts.add("HIT! +20", px - 40, py - 30, (0, 255, 255), 1.2)
                                    score += 20
    
                            if completed:
                                time_taken = current_time - pose_start_time
                                streak += 1
                                poses_completed += 1
                                multiplier = 3 if fever_active else (1 + int(streak // 3))
    
                                is_gold = current_pose.get('variant') == 'GOLD'
                                is_speed = current_pose.get('variant') == 'SPEED'
                                if time_taken <= 2.2 or is_speed:
                                    tier_text = "PERFECTO!!"
                                    tier_col = (0, 215, 255)
                                    base_pts = 150 * (2 if is_speed else 1)
                                    fever_add = 25
                                elif time_taken <= 3.8:
                                    tier_text = "GENIAL!"
                                    tier_col = (0, 255, 120)
                                    base_pts = 100
                                    fever_add = 15
                                else:
                                    tier_text = "BIEN!"
                                    tier_col = (255, 230, 0)
                                    base_pts = 70
                                    fever_add = 10
    
                                if is_gold:
                                    base_pts += 500
                                    fever_add += 30
    
                                points = int(base_pts * multiplier)
                                score += points
                                if not fever_active:
                                    fever_gauge = min(100, fever_gauge + fever_add)
                                    if fever_gauge >= 100:
                                        fever_active = True
                                        fever_start_time = current_time
                                        floating_texts.add("FEVER TIME!", display_w//2 - 160, 220, (0, 255, 255), 2.4)
    
                                play_sound(snd_success)
                                particles.emit_confetti(display_w, gold_only=is_gold)
                                particles.emit(display_w // 2, 340, current_pose['color'], 35)
                                floating_texts.add(f"{tier_text} +{points}", 40, 310, tier_col, 1.8)
                                show_success_flash = True
                                success_flash_time = current_time
                                log_metric(current_mode, current_pose['name'], time_taken, 'COMPLETED')
                                current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx, current_profile)
                                pose_start_time = current_time
                                queue_slide_offset = 240.0
                                state.reset()
    
                        # --- POSES ESTÁTICAS CON ACUMULADOR GRACE DECAY ---
                        else:
                            left_check = current_pose['checks']['left_arm']
                            right_check = current_pose['checks']['right_arm']
                            left_ok = left_check(lm)
                            right_ok = right_check(lm)
                            left_score = score_arm(left_check, lm)
                            right_score = score_arm(right_check, lm)
    
                            # Bonus Pasivo de Groove
                            hip_x = (lm[L_HIP].x + lm[R_HIP].x) / 2.0
                            if state.global_center_x is None:
                                state.global_center_x = hip_x
                            else:
                                state.global_center_x = state.global_center_x * 0.98 + hip_x * 0.02
                            if abs(hip_x - state.global_center_x) > 0.025 and current_time - state.last_groove_time > 0.45:
                                state.last_groove_time = current_time
                                score += 15
                                floating_texts.add("GROOVE CADERA +15", 40, 355, (255, 120, 255), 0.72)
                                particles.emit(int(hip_x * display_w), int(lm[L_HIP].y * display_h), (255, 100, 255), 10)
    
                            is_speed = current_pose.get('variant') == 'SPEED'
                            req_time = (0.35 if is_speed else 0.55) * PROFILES[current_profile]['grace_mult']
                            if left_ok and right_ok:
                                hold_progress = min(1.0, hold_progress + (dt / req_time))
                            else:
                                decay = 0.6 if (left_ok or right_ok) else 1.2
                                hold_progress = max(0.0, hold_progress - decay * dt)
    
                            if hold_progress >= 1.0:
                                time_taken = current_time - pose_start_time
                                streak += 1
                                poses_completed += 1
                                multiplier = 3 if fever_active else (1 + int(streak // 3))
    
                                is_gold = current_pose.get('variant') == 'GOLD'
                                if time_taken <= 1.9 or is_speed:
                                    tier_text = "PERFECTO!!"
                                    tier_col = (0, 215, 255)
                                    base_pts = 150 * (2 if is_speed else 1)
                                    fever_add = 25
                                elif time_taken <= 3.6:
                                    tier_text = "GENIAL!"
                                    tier_col = (0, 255, 120)
                                    base_pts = 100
                                    fever_add = 15
                                else:
                                    tier_text = "BIEN!"
                                    tier_col = (255, 230, 0)
                                    base_pts = 70
                                    fever_add = 10
    
                                if is_gold:
                                    base_pts += 500
                                    fever_add += 30
    
                                points = int(base_pts * multiplier)
                                score += points
                                if not fever_active:
                                    fever_gauge = min(100, fever_gauge + fever_add)
                                    if fever_gauge >= 100:
                                        fever_active = True
                                        fever_start_time = current_time
                                        floating_texts.add("FEVER TIME!", display_w//2 - 160, 220, (0, 255, 255), 2.4)
    
                                play_sound(snd_success)
                                particles.emit_confetti(display_w, gold_only=is_gold)
                                particles.emit(display_w // 2, 340, current_pose['color'], 30)
                                floating_texts.add(f"{tier_text} +{points}", 40, 310, tier_col, 1.8)
                                if streak >= 3 and not fever_active:
                                    floating_texts.add(f"RACHA x{streak}!", 40, 360, (0, 255, 255), 1.2)
    
                                show_success_flash = True
                                success_flash_time = current_time
                                log_metric(current_mode, current_pose['name'], time_taken, 'COMPLETED')
                                current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx, current_profile)
                                pose_start_time = current_time
                                hold_progress = 0.0
                                queue_slide_offset = 240.0
                                state.reset()
    
                    # Dibujo AR Central (Ghost Silhouette + Anillos + Esqueleto Semáforo + Estelas)
                    if FEATURES.enable_custom_ghost:
                        custom_ghost.render_custom_ghost(frame, lm, current_pose, display_w, display_h, left_score, right_score, current_time)
                    else:
                        draw_ghost_and_target_rings(frame, lm, current_pose, display_w, display_h, left_score, right_score)
    
                    draw_skeleton_with_feedback(frame, lm, display_w, display_h, left_ok, right_ok, left_score, right_score)
                    hand_trails.update_and_draw(frame, lm, display_w, display_h, score_to_traffic_color(left_score), score_to_traffic_color(right_score))
    
                    # Feature: Modo Dúo (desactivado por defecto)
                    if FEATURES.enable_duo_mode:
                        duo_mgr.evaluate_players(current_pose, lm, None, dt, current_time)
                        duo_mgr.draw_duo_hud(frame, display_w, display_h)
    
                else:
                    control_gesture_start = None
                    hold_progress = max(0.0, hold_progress - 1.0 * dt)
    
                # =========================================================
                # RENDERIZADO DEL HUD (MAPA DE 5 ZONAS LIBRE DE COLISIONES)
                # =========================================================
    
                # --- ZONA 1: TOP-LEFT HUD ---
                blend_rect_roi(frame, 20, 18, 290, 132, (18, 15, 25), 0.78)
                cv2.rectangle(frame, (20, 18), (310, 150), (0, 220, 255), 2)
                cv2.putText(frame, f"PUNTAJE: {score:,}", (35, 58), cv2.FONT_HERSHEY_DUPLEX, 0.95, (0, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"RACHA x{streak}  |  MULTI x{multiplier}", (35, 95), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 200, 255), 2, cv2.LINE_AA)
                cv2.rectangle(frame, (35, 112), (225, 132), (55, 55, 70), -1)
                fever_w = int(190 * (fever_gauge / 100.0))
                if fever_w > 0:
                    cv2.rectangle(frame, (35, 112), (35 + fever_w, 132), (255, 50, 255), -1)
                cv2.rectangle(frame, (35, 112), (225, 132), (255, 255, 255), 2)
                cv2.putText(frame, f"FEVER {fever_gauge}%", (234, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 130, 255), 1, cv2.LINE_AA)
    
                # --- ZONA 2: BANNER INFERIOR CENTRADO CON OPACIDAD ADAPTATIVA ---
                # Reposicionado abajo para evitar oclusión cuando el jugador levanta los brazos al cielo.
                # Cuenta con auto-ghosting (desvanecimiento automático) si las manos entran en la zona.
                bx, by, bw, bh = 390, 634, 500, 70
                banner_col = (0, 215, 255) if current_pose.get('variant') == 'GOLD' else (
                    (255, 230, 0) if current_pose.get('variant') == 'SPEED' else current_pose.get('color', (0, 255, 120))
                )
                # Opacidad adaptativa contra extremidades
                hand_near_banner = False
                if has_person:
                    for kp in (L_WRIST, R_WRIST):
                        if 0.28 <= lm[kp].x <= 0.72 and lm[kp].y >= 0.80:
                            hand_near_banner = True
                            break
                banner_alpha = 0.25 if hand_near_banner else 0.76
    
                blend_rect_roi(frame, bx, by, bw, bh, (15, 15, 25), banner_alpha)
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), banner_col, 2)
    
                pname = current_pose.get('name', '')
                (tw, _), _ = cv2.getTextSize(pname, cv2.FONT_HERSHEY_DUPLEX, 0.88, 2)
                cv2.putText(frame, pname, (bx + (bw - tw) // 2, by + 30), cv2.FONT_HERSHEY_DUPLEX, 0.88, banner_col, 2, cv2.LINE_AA)
    
                if current_pose.get('dynamic'):
                    cur_act, cur_target, lbl = get_dynamic_progress(pname, state)
                    prog_val = min(1.0, cur_act / max(1, cur_target))
                    cv2.rectangle(frame, (bx + 24, by + 40), (bx + bw - 24, by + 58), (45, 45, 60), -1)
                    cv2.rectangle(frame, (bx + 24, by + 40), (bx + 24 + int((bw - 48) * prog_val), by + 58), banner_col, -1)
                    cv2.rectangle(frame, (bx + 24, by + 40), (bx + bw - 24, by + 58), (255, 255, 255), 1)
                    cv2.putText(frame, lbl, (bx + 35, by + 54), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
                elif not current_pose.get('is_freeze'):
                    cv2.rectangle(frame, (bx + 24, by + 40), (bx + bw - 24, by + 58), (45, 45, 60), -1)
                    cv2.rectangle(frame, (bx + 24, by + 40), (bx + 24 + int((bw - 48) * hold_progress), by + 58), (0, 210, 110), -1)
                    cv2.rectangle(frame, (bx + 24, by + 40), (bx + bw - 24, by + 58), (255, 255, 255), 1)
                    cv2.putText(frame, f"MANTENE: {int(hold_progress * 100)}%", (bx + 35, by + 54), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (210, 255, 220), 1, cv2.LINE_AA)
    
                # --- ZONA 3: TOP-RIGHT DUAL REFERENCE CARD (LIMPIA Y SIN TEXTOS REDUNDANTES) ---
                rx, ry, rw, rh = 900, 18, 356, 190
                blend_rect_roi(frame, rx, ry, rw, rh, (20, 18, 30), 0.85)
                cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (255, 200, 0), 2)
    
                icon_name = current_pose.get('icon_name')
                illus = load_pose_illustration_clean(icon_name, size=(155, 155)) if icon_name else None
                use_illus = (illus is not None) and (not FEATURES.enable_stickman_only)
    
                if use_illus:
                    frame[ry + 16:ry + 16 + 155, rx + 12:rx + 12 + 155] = illus
                    cv2.rectangle(frame, (rx + 12, ry + 16), (rx + 167, ry + 171), (90, 90, 115), 1)
                    stick_x, stick_w = rx + 176, 168
                else:
                    # Proporción anatómica centrada cuando no hay imagen o en modo solo silueta
                    stick_x, stick_w = rx + (rw - 190) // 2, 190
    
                ref_pts = get_animated_ref_points(current_pose, current_time)
                draw_full_body_stickman(frame, stick_x, ry + 10, stick_w, 165, ref_pts, banner_col)
                draw_intent_arrows_in_box(frame, current_pose, stick_x, ry + 10, stick_w, 165, current_time)
    
                # --- RECORDATORIO DISCRETO EN ZONA 1 (FUERA DE SAFE ZONE) ---
                cv2.putText(frame, "Gesto X en pecho = Saltar", (35, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (170, 185, 210), 1, cv2.LINE_AA)
    
                particles.update_and_draw(frame)
                floating_texts.update_and_draw(frame)
    
                # Feature: Gran Salto Party / Plataforma de Movimiento (desactivada por defecto)
                if FEATURES.enable_party_platform:
                    party_events = party_platform.update(dt, state, display_w, current_time)
                    party_platform.draw_platform(frame, display_w, display_h)
                    for pe in party_events:
                        if pe["type"] == "jump_success":
                            score += pe["points"]
                            particles.emit(pe["x"], display_h - 170, pe["color"], 25)
                            floating_texts.add(f"{pe['tier']} +{pe['points']}", pe["x"] - 50, display_h - 220, pe["color"], 1.3)
                            play_sound(snd_success)
                        elif pe["type"] == "jump_miss":
                            floating_texts.add("MISS!", display_w // 2 - 40, display_h - 220, pe["color"], 1.3)
                            play_sound(snd_fail)
    
                # Feature: Audio Reactivo (desactivado por defecto)
                if FEATURES.enable_reactive_audio:
                    bpm_val = SONG_BPM.get(current_song, 115.0)
                    audio_reactive.update(current_time, bpm_val, is_playing=True)
                    audio_reactive.draw_reactive_visuals(frame, display_w, display_h)
    
                if show_success_flash and current_time - success_flash_time < 0.25:
                    overlay_flash = gold_overlay if current_pose.get('variant') == 'GOLD' else green_overlay
                    cv2.addWeighted(overlay_flash, 0.15, frame, 0.85, 0, frame)
                elif show_success_flash:
                    show_success_flash = False

        # =========================================================
        # FEVER & SCREEN SHAKE
        # =========================================================
        if fever_active:
            if current_time - fever_start_time > fever_duration:
                fever_active = False
                fever_gauge = 0
                multiplier = 1
            else:
                cv2.addWeighted(fever_overlay, 0.18, frame, 0.82, 0, frame)

        if current_time - shake_time < 0.28:
            dx = random.randint(-16, 16)
            dy = random.randint(-16, 16)
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            frame = cv2.warpAffine(frame, M, (display_w, display_h))

        # =========================================================
        # MENÚ KINÉTICO (CONTROL CON MANOS A DISTANCIA + TECLADO)
        # =========================================================
        if show_menu:
            blend_rect_roi(frame, 0, 0, display_w, display_h, (12, 10, 18), 0.82)
            cv2.putText(frame, "MENU DE CANCIONES Y COREOGRAFIAS", (display_w//2 - 380, 85), cv2.FONT_HERSHEY_DUPLEX, 1.3, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "Controla con tus manos a distancia o con flechas del teclado", (display_w//2 - 350, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 220, 240), 1, cv2.LINE_AA)

            # Selector de Perfil de Experiencia
            prof = PROFILES[current_profile]
            p_color = (0, 255, 120) if current_profile == 'ZEN' else (
                (0, 215, 255) if current_profile == 'JUNIOR' else (
                    (255, 100, 200) if current_profile == 'CARDIO' else (255, 215, 0)
                )
            )
            blend_rect_roi(frame, display_w//2 - 360, 138, 720, 52, (20, 22, 38), 0.90)
            cv2.rectangle(frame, (display_w//2 - 360, 138), (display_w//2 + 360, 190), p_color, 2)
            cv2.putText(frame, f"PERFIL [TECLA P]: {prof['name']} - {prof['subtitle']}", (display_w//2 - 340, 172), cv2.FONT_HERSHEY_SIMPLEX, 0.54, p_color, 2, cv2.LINE_AA)

            # Botones kinéticos en pantalla
            cv2.circle(frame, (120, 340), 55, (255, 180, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, "MANO IZQ", (72, 332), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 200, 50), 1, cv2.LINE_AA)
            cv2.putText(frame, "SUBIR", (86, 358), cv2.FONT_HERSHEY_DUPLEX, 0.54, (255, 255, 255), 1, cv2.LINE_AA)

            cv2.circle(frame, (display_w - 120, 340), 55, (255, 180, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, "MANO DER", (display_w - 168, 332), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 200, 50), 1, cv2.LINE_AA)
            cv2.putText(frame, "BAJAR", (display_w - 152, 358), cv2.FONT_HERSHEY_DUPLEX, 0.54, (255, 255, 255), 1, cv2.LINE_AA)

            max_visible = 5
            start_idx = max(0, selected_idx - max_visible // 2)
            end_idx = min(len(menu_options), start_idx + max_visible)
            if end_idx - start_idx < max_visible:
                start_idx = max(0, end_idx - max_visible)

            for i in range(start_idx, end_idx):
                opt = menu_options[i]
                is_sel = (i == selected_idx)
                color = (0, 255, 120) if is_sel else (150, 150, 165)
                prefix = "->  " if is_sel else "    "
                draw_i = i - start_idx
                oy = 230 + draw_i * 68
                if is_sel:
                    blend_rect_roi(frame, display_w//2 - 320, oy - 42, 640, 56, (30, 40, 60), 0.85)
                    cv2.rectangle(frame, (display_w//2 - 320, oy - 42), (display_w//2 + 320, oy + 14), (0, 255, 120), 2)
                cv2.putText(frame, prefix + opt['display'], (display_w//2 - 290, oy), cv2.FONT_HERSHEY_DUPLEX, 1.0, color, 2, cv2.LINE_AA)

            confirm_prog = 0.0
            if has_person:
                lm = results.pose_landmarks.landmark
                l_up = check_left_arm_up(lm) and not check_right_arm_up(lm)
                r_up = check_right_arm_up(lm) and not check_left_arm_up(lm)
                both_up = check_left_arm_up(lm) and check_right_arm_up(lm)

                if both_up:
                    if menu_both_start is None: menu_both_start = current_time
                    confirm_prog = min(1.0, (current_time - menu_both_start) / menu_confirm_required)
                    if confirm_prog >= 1.0:
                        show_menu = False
                        current_song = menu_options[selected_idx]['file']
                        current_mode = menu_options[selected_idx]['type']
                        menu_both_start = None
                        pose_start_time = current_time
                        coreo_idx = -1
                        pose_queue = []
                        for _ in range(5):
                            if current_mode == 'COREO' and current_song in COREOGRAFIAS:
                                coreo_idx = (coreo_idx + 1) % len(COREOGRAFIAS[current_song])
                                p = dict(COREOGRAFIAS[current_song][coreo_idx])
                                p['variant'] = 'NORMAL'
                            else:
                                candidates = get_poses_for_profile(current_profile)
                                p = dict(random.choice(candidates))
                                p['variant'] = 'NORMAL'
                            pose_queue.append(p)
                        current_pose = pose_queue[0]
                        in_calibration = True
                        calib_mgr.start()
                else:
                    menu_both_start = None

                if l_up:
                    if menu_left_start is None:
                        menu_left_start = current_time
                        selected_idx = max(0, selected_idx - 1)
                else:
                    menu_left_start = None

                if r_up:
                    if menu_right_start is None:
                        menu_right_start = current_time
                        selected_idx = min(len(menu_options) - 1, selected_idx + 1)
                else:
                    menu_right_start = None

            blend_rect_roi(frame, display_w//2 - 300, display_h - 110, 600, 48, (20, 20, 30), 0.85)
            cv2.rectangle(frame, (display_w//2 - 300, display_h - 110), (display_w//2 + 300, display_h - 62), (255, 255, 255), 2)
            if confirm_prog > 0:
                cv2.rectangle(frame, (display_w//2 - 296, display_h - 106), (display_w//2 - 296 + int(592 * confirm_prog), display_h - 66), (0, 255, 120), -1)
            cv2.putText(frame, "AMBOS BRAZOS ARRIBA O ENTER = ¡JUGAR!", (display_w//2 - 250, display_h - 78), cv2.FONT_HERSHEY_DUPLEX, 0.68, (0, 0, 0) if confirm_prog > 0.5 else (255, 255, 255), 2, cv2.LINE_AA)

            # Barra informativa de Features avanzadas (todas desactivadas por defecto)
            feat_text = (
                f"[D] DUO: {'ON' if FEATURES.enable_duo_mode else 'OFF'}  |  "
                f"[G] GHOST: {'CUSTOM' if FEATURES.enable_custom_ghost else 'CLASICA'}  |  "
                f"[I] MODO: {'SILUETA' if FEATURES.enable_stickman_only else 'ILUS+COACH'}  |  "
                f"[A] AUDIO: {'ON' if FEATURES.enable_reactive_audio else 'OFF'}  |  "
                f"[J] SALTO PARTY: {'ON' if FEATURES.enable_party_platform else 'OFF'}"
            )
            cv2.putText(frame, feat_text, (display_w//2 - 420, display_h - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (180, 200, 220), 1, cv2.LINE_AA)

        # Diagnóstico de Modo Demo si no hay hardware USB disponible
        # Renderizado SIEMPRE después del flip para garantizar que el texto NUNCA sufra inversión especular
        if getattr(cap, 'is_mock', False):
            blend_rect_roi(frame, display_w // 2 - 250, 10, 500, 32, (20, 15, 30), 0.88)
            cv2.rectangle(frame, (display_w // 2 - 250, 10), (display_w // 2 + 250, 42), (0, 200, 255), 1)
            cv2.putText(frame, "MODO DEMO: Camara USB no detectada", (display_w // 2 - 200, 31),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 220, 255), 1, cv2.LINE_AA)

        cv2.imshow(WINDOW_NAME, frame)

        # Teclado de respaldo
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('m'):
            show_menu = not show_menu
            if show_menu and HAS_AUDIO:
                pygame.mixer.music.pause()
        elif in_calibration and (key == 13 or key == 32 or key == ord('c')):
            calib_mgr.skip()
            in_calibration = False
            pose_start_time = current_time
            state.reset()
            if HAS_AUDIO and current_song and current_song != "Sin Musica":
                try:
                    pygame.mixer.music.load(current_song)
                    pygame.mixer.music.play(-1)
                    pygame.mixer.music.set_volume(0.4)
                except Exception:
                    pass
        elif not show_menu and not in_calibration and key == ord('c'):
            in_calibration = True
            calib_mgr.start()
            if HAS_AUDIO:
                pygame.mixer.music.pause()
        elif key == ord('p') or key == 9:
            current_profile_idx = (current_profile_idx + 1) % len(PROFILE_KEYS)
            current_profile = PROFILE_KEYS[current_profile_idx]
            floating_texts.add(f"PERFIL: {PROFILES[current_profile]['name']}", 40, 250, (0, 255, 255), 1.2)
        elif key == ord('d'):
            act = FEATURES.toggle_duo_mode()
            floating_texts.add(f"MODO DUO: {'ACTIVADO' if act else 'DESACTIVADO'}", 40, 250, (0, 255, 255), 1.2)
        elif key == ord('g'):
            act = FEATURES.toggle_custom_ghost()
            floating_texts.add(f"SILUETA GHOST: {'CUSTOM NEON' if act else 'CLASICA'}", 40, 250, (0, 255, 255), 1.2)
        elif key == ord('a'):
            act = FEATURES.toggle_reactive_audio()
            floating_texts.add(f"AUDIO REACTIVO: {'ACTIVADO' if act else 'DESACTIVADO'}", 40, 250, (0, 255, 255), 1.2)
        elif key == ord('j'):
            act = FEATURES.toggle_party_platform()
            floating_texts.add(f"SALTO PARTY: {'ACTIVADO' if act else 'DESACTIVADO'}", 40, 250, (0, 255, 255), 1.2)
        elif key == ord('i'):
            act = FEATURES.toggle_stickman_only()
            floating_texts.add(f"MODO VISUAL: {'SOLO SILUETA' if act else 'ILUS + COACH'}", 40, 250, (0, 255, 255), 1.2)
        elif key == ord('n') or key == 32:
            if not show_menu and not in_calibration:
                floating_texts.add("POSE SALTEADA!", 40, 310, (0, 100, 255), 1.3)
                play_sound(snd_fail)
                fever_gauge = max(0, fever_gauge - 20)
                shake_time = current_time
                log_metric(current_mode, current_pose['name'], current_time - pose_start_time, 'SKIPPED')
                current_pose, coreo_idx = shift_queue(pose_queue, current_mode, current_song, coreo_idx, current_profile)
                pose_start_time = current_time
                control_gesture_start, hold_progress, streak = None, 0.0, 0
                queue_slide_offset = 240.0
                state.reset()

        if show_menu:
            if key == 82 or key == ord('w'):
                selected_idx = max(0, selected_idx - 1)
            elif key == 84 or key == ord('s'):
                selected_idx = min(len(menu_options) - 1, selected_idx + 1)
            elif key == 13 or key == 32:
                show_menu = False
                current_song = menu_options[selected_idx]['file']
                current_mode = menu_options[selected_idx]['type']
                coreo_idx = -1
                pose_queue = []
                for _ in range(5):
                    if current_mode == 'COREO' and current_song in COREOGRAFIAS:
                        coreo_idx = (coreo_idx + 1) % len(COREOGRAFIAS[current_song])
                        p = dict(COREOGRAFIAS[current_song][coreo_idx])
                        p['variant'] = 'NORMAL'
                    else:
                        candidates = get_poses_for_profile(current_profile)
                        p = dict(random.choice(candidates))
                        p['variant'] = 'NORMAL'
                    pose_queue.append(p)
                current_pose = pose_queue[0]
                hold_progress = 0.0
                pose_start_time = current_time
                queue_slide_offset = 240.0
                in_calibration = True
                calib_mgr.start()

        if HAS_AUDIO and current_song and current_song != "Sin Musica" and not show_menu:
            if not pygame.mixer.music.get_busy():
                try:
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass

        try:
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
        except Exception:
            break

    cap.stop()
    if pose_detector:
        pose_detector.close()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
