import sys
import types

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

import cv2
import time
import numpy as np
import os
from poses_locas import (
    draw_skeleton_with_feedback, FloatingText, ParticleSystem,
    draw_progress_bar, SKELETON_CONNECTIONS, LEFT_ARM_CONNECTIONS, RIGHT_ARM_CONNECTIONS,
    NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP,
    L_EAR, R_EAR,
    PlayerState, check_left_arm_up, check_squat, check_left_hand_on_head,
    POSES, COREOGRAFIAS
)

def assert_eq(a, b, msg):
    if a != b: raise AssertionError(f"{msg}: expected {b}, got {a}")

class MockLM:
    def __init__(self, x, y, v=1.0):
        self.x, self.y, self.visibility = x, y, v

def create_mock_landmarks(pose_type="T_POSE"):
    lm = [MockLM(0,0,0) for _ in range(33)]
    # Base T-pose
    lm[NOSE] = MockLM(0.5, 0.2)
    lm[L_SHOULDER] = MockLM(0.4, 0.4)
    lm[R_SHOULDER] = MockLM(0.6, 0.4)
    lm[L_ELBOW] = MockLM(0.3, 0.4)
    lm[R_ELBOW] = MockLM(0.7, 0.4)
    lm[L_WRIST] = MockLM(0.2, 0.4)
    lm[R_WRIST] = MockLM(0.8, 0.4)
    lm[L_HIP] = MockLM(0.45, 0.7)
    lm[R_HIP] = MockLM(0.55, 0.7)
    
    if pose_type == "ARMS_UP":
        lm[L_WRIST] = MockLM(0.4, 0.1) # Above nose (0.2)
        lm[R_WRIST] = MockLM(0.6, 0.1)
    elif pose_type == "SQUAT":
        lm[L_HIP] = MockLM(0.45, 0.85) # Lower
        lm[R_HIP] = MockLM(0.55, 0.85)
    elif pose_type == "HAND_ON_HEAD":
        lm[L_WRIST] = MockLM(0.48, 0.18) # Near nose
        
    return lm

def run_functional_tests():
    print("Running functional tests...")
    
    # 1. Test check_left_arm_up
    lm_tpose = create_mock_landmarks("T_POSE")
    assert_eq(check_left_arm_up(lm_tpose), False, "T-Pose left arm up")
    
    lm_arms_up = create_mock_landmarks("ARMS_UP")
    assert_eq(check_left_arm_up(lm_arms_up), True, "Arms up left arm up")
    
    # 2. Test check_squat
    state = PlayerState()
    lm_squat = create_mock_landmarks("SQUAT")
    # Initialize center_y
    check_squat(state, lm_tpose)
    # Perform squat
    completed, events = check_squat(state, lm_squat)
    assert_eq(state.jump_phase, 1, "Squat phase 1")
    # Return up
    completed, events = check_squat(state, lm_tpose)
    assert_eq(completed, True, "Squat completed")
    
    # 3. Test Hand on head
    lm_head = create_mock_landmarks("HAND_ON_HEAD")
    assert_eq(check_left_hand_on_head(lm_head), True, "Hand on head")
    assert_eq(check_left_hand_on_head(lm_tpose), False, "Hand not on head")
    
    print("All functional tests passed!")

def run_visual_tests():
    print("Generating visual tests...")
    display_w, display_h = 1280, 720
    
    # Simulate UI Lane rendering (isolated from main loop)
    def draw_lane(frame, pose_queue):
        lane_y = display_h - 80
        cv2.rectangle(frame, (0, lane_y), (display_w, display_h), (20, 20, 20), -1)
        cv2.rectangle(frame, (0, lane_y), (display_w, lane_y+3), (255, 255, 255), -1)
        receptor_x, receptor_w = 20, 180
        cv2.rectangle(frame, (receptor_x, lane_y + 10), (receptor_x + receptor_w, display_h - 10), (0, 255, 255), 3)
        cv2.putText(frame, "AHORA!", (receptor_x + 5, lane_y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        for i, p in enumerate(pose_queue):
            card_x = receptor_x + i * 190
            if card_x > display_w: break
            bg_color = (150, 0, 150) if i == 0 else (60, 60, 60)
            text_color = (0, 255, 255) if i == 0 else (200, 200, 200)
            cv2.rectangle(frame, (card_x, lane_y + 10), (card_x + 180, display_h - 10), bg_color, -1)
            cv2.rectangle(frame, (card_x, lane_y + 10), (card_x + 180, display_h - 10), text_color, 1)
            words = p['name'].split()
            if len(words) >= 2:
                cv2.putText(frame, " ".join(words[:2]), (card_x + 10, lane_y + 35), cv2.FONT_HERSHEY_DUPLEX, 0.5, text_color, 1)
                cv2.putText(frame, " ".join(words[2:]), (card_x + 10, lane_y + 60), cv2.FONT_HERSHEY_DUPLEX, 0.5, text_color, 1)
            else:
                cv2.putText(frame, p['name'], (card_x + 10, lane_y + 45), cv2.FONT_HERSHEY_DUPLEX, 0.6, text_color, 1)

    pose_queue = POSES[:5]
    
    # Frame 1: Standard Gameplay
    frame = np.full((display_h, display_w, 3), (40, 40, 60), dtype=np.uint8)
    draw_skeleton_with_feedback(frame, create_mock_landmarks(), display_w, display_h, True, False)
    draw_lane(frame, pose_queue)
    cv2.putText(frame, "PUNTAJE: 500", (30, 60), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 255, 255), 3)
    cv2.imwrite("test_visual_gameplay.jpg", frame)

    # Frame 2: Fever Mode
    frame = np.full((display_h, display_w, 3), (40, 40, 60), dtype=np.uint8)
    fever_overlay = np.full((display_h, display_w, 3), (255, 0, 255), dtype=np.uint8)
    cv2.addWeighted(fever_overlay, 0.2, frame, 0.8, 0, frame)
    draw_skeleton_with_feedback(frame, create_mock_landmarks("ARMS_UP"), display_w, display_h, True, True)
    draw_lane(frame, pose_queue)
    cv2.putText(frame, "MULTI: x3", (30, 110), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 150, 255), 3)
    draw_progress_bar(frame, 30, 130, 200, 15, 1.0, (255, 0, 255))
    cv2.putText(frame, "FEVER!", (240, 145), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 0, 255), 2)
    cv2.imwrite("test_visual_fever.jpg", frame)

if __name__ == "__main__":
    run_functional_tests()
    run_visual_tests()
