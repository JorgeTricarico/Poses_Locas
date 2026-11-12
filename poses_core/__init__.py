"""
Poses Locas Core - Arquitectura Modular y Desacoplada
"""

from .geometry import (
    NOSE, L_EAR, R_EAR, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW,
    L_WRIST, R_WRIST, L_HIP, R_HIP,
    SKELETON_CONNECTIONS, LEFT_ARM_CONNECTIONS, RIGHT_ARM_CONNECTIONS,
    get_body_unit, calc_angle_2d, distance_to_score, score_to_traffic_color,
    score_arm, get_point
)
from .state import PlayerState
from .detectors import (
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
    check_continuous_groove, check_dj_turntable, check_disco_point,
    check_electro_wave, check_windshield_wipers
)
from .catalog import (
    POSES, PROFILES, PROFILE_KEYS, COREOGRAFIAS, SONG_BPM,
    get_poses_for_profile, get_beat_pulse
)
from .rendering import (
    blend_rect_roi, load_pose_illustration_clean, draw_star_icon, draw_bolt_icon,
    draw_progress_bar, draw_full_body_stickman, get_animated_ref_points,
    draw_intent_arrows_in_box, compute_body_anchored_targets,
    draw_ghost_and_target_rings, draw_skeleton_with_feedback,
    HandTrailSystem, ParticleSystem, FloatingText
)
from .capture import MockVideoCapture, VideoCaptureAsync
from .engine import shift_queue, get_dynamic_progress, log_metric
from .calibration import CalibrationStep, CalibrationData, CalibrationManager
from .features import (
    FeatureFlags, FEATURES,
    DuoModeManager, CustomGhostRenderer,
    AudioReactiveEngine, PartyPlatformEngine
)
