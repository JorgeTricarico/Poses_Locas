import cv2
import time
import numpy as np
from poses_locas import (
    draw_skeleton_with_feedback, FloatingText, ParticleSystem,
    draw_progress_bar, SKELETON_CONNECTIONS, LEFT_ARM_CONNECTIONS, RIGHT_ARM_CONNECTIONS,
    NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP,
    PlayerState
)

def create_mock_landmarks():
    class MockLM:
        def __init__(self, x, y, v=1.0):
            self.x = x; self.y = y; self.visibility = v
            
    lm = [MockLM(0,0,0) for _ in range(33)]
    # T-pose
    lm[NOSE] = MockLM(0.5, 0.2)
    lm[L_SHOULDER] = MockLM(0.4, 0.4)
    lm[R_SHOULDER] = MockLM(0.6, 0.4)
    lm[L_ELBOW] = MockLM(0.3, 0.4)
    lm[R_ELBOW] = MockLM(0.7, 0.4)
    lm[L_WRIST] = MockLM(0.2, 0.4)
    lm[R_WRIST] = MockLM(0.8, 0.4)
    lm[L_HIP] = MockLM(0.45, 0.7)
    lm[R_HIP] = MockLM(0.55, 0.7)
    return lm

def generate_screenshots():
    display_w, display_h = 1280, 720
    
    # 1. Gameplay Screenshot
    frame = np.full((display_h, display_w, 3), (40, 40, 60), dtype=np.uint8)
    lm = create_mock_landmarks()
    
    # Simulate UI
    floating_texts = FloatingText()
    floating_texts.add("FEVER TIME!", display_w//2 - 150, display_h//2, (0, 255, 255), 3.0)
    floating_texts.add("BAILASTE GENIAL! +300", 50, 400, (0, 255, 100), 2.0)
    
    # Fever overlay
    fever_overlay = np.full((display_h, display_w, 3), (255, 0, 255), dtype=np.uint8)
    cv2.addWeighted(fever_overlay, 0.2, frame, 0.8, 0, frame)
    
    draw_skeleton_with_feedback(frame, lm, display_w, display_h, left_ok=True, right_ok=False)
    
    # Progress bar
    draw_progress_bar(frame, (display_w-300)//2, display_h-80, 300, 25, 0.6, (0, 255, 0))
    cv2.putText(frame, "MANTENE!", ((display_w-300)//2, display_h-90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Floating texts
    floating_texts.update_and_draw(frame)
    
    # Top score
    cv2.putText(frame, "PUNTOS: 1200", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
    
    cv2.imwrite("screenshot_gameplay.jpg", frame)
    print("Saved screenshot_gameplay.jpg")
    
    # 2. Menu Screenshot
    frame_menu = np.full((display_h, display_w, 3), (30, 30, 30), dtype=np.uint8)
    black_overlay = np.full((display_h, display_w, 3), (0, 0, 0), dtype=np.uint8)
    cv2.addWeighted(black_overlay, 0.8, frame_menu, 0.2, 0, frame_menu)
    cv2.putText(frame_menu, "MENU DE CONFIGURACION", (display_w//2 - 350, 150), cv2.FONT_HERSHEY_DUPLEX, 1.8, (0, 255, 255), 3)
    cv2.putText(frame_menu, "-> [COREO] MACARENA", (display_w//2 - 250, 250), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0,255,0), 3)
    cv2.putText(frame_menu, "   [LIBRE] DANCE", (display_w//2 - 250, 320), cv2.FONT_HERSHEY_DUPLEX, 1.2, (150,150,150), 3)
    cv2.imwrite("screenshot_menu.jpg", frame_menu)
    print("Saved screenshot_menu.jpg")

if __name__ == '__main__':
    generate_screenshots()
