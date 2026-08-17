import re

with open('poses_locas.py', 'r') as f:
    content = f.read()

# 1. Add load_icon and update POSES
poses_replacement = """
def load_icon(name):
    img = cv2.imread(f"{name}.jpg")
    return img

def check_gesture_pause(lm):
    return check_left_hand_on_head(lm) and check_right_hand_on_head(lm)

POSES = [
    {
        'name': 'Baila! Mueve Caderas', 'color': (255, 100, 150),
        'dynamic': True, 'checks': check_shake_hips,
        'icon': load_icon('pose_caderas'),
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.28, 0.42), R_ELBOW: (0.72, 0.42), L_WRIST: (0.40, 0.60), R_WRIST: (0.60, 0.60), L_HIP: (0.35, 0.65), R_HIP: (0.50, 0.65) },
    },
    {
        'name': 'Brazos Arriba!', 'color': (0, 255, 100),
        'checks': {'left_arm': check_left_arm_up, 'right_arm': check_right_arm_up},
        'icon': load_icon('pose_brazos'),
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.32, 0.18), R_ELBOW: (0.68, 0.18), L_WRIST: (0.35, 0.05), R_WRIST: (0.65, 0.05), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'T-Pose!', 'color': (255, 200, 0),
        'checks': {'left_arm': check_left_arm_horizontal, 'right_arm': check_right_arm_horizontal},
        'icon': load_icon('pose_tpose'),
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.22, 0.30), R_ELBOW: (0.78, 0.30), L_WRIST: (0.08, 0.30), R_WRIST: (0.92, 0.30), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'Fuerte!', 'color': (255, 100, 50),
        'checks': {'left_arm': check_left_bicep, 'right_arm': check_right_bicep},
        'icon': load_icon('pose_fuerte'),
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.22, 0.30), R_ELBOW: (0.78, 0.30), L_WRIST: (0.32, 0.20), R_WRIST: (0.68, 0.20), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'Saludo Militar!', 'color': (50, 100, 255),
        'checks': {'left_arm': check_left_arm_down, 'right_arm': check_right_salute},
        'icon': load_icon('pose_saludo'),
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.32, 0.45), R_ELBOW: (0.75, 0.30), L_WRIST: (0.35, 0.58), R_WRIST: (0.58, 0.12), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
]
"""
content = re.sub(r'POSES = \[.*?\]\n', poses_replacement, content, flags=re.DOTALL)

# 2. Update draw_reference
draw_ref_old = """def draw_reference(frame, pose_data, box_x, box_y, box_w, box_h):
    ref = pose_data.get('ref')
    if not ref: return
    overlay = frame.copy()
    cv2.rectangle(overlay, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (255, 255, 255), 2)"""

draw_ref_new = """def draw_reference(frame, pose_data, box_x, box_y, box_w, box_h):
    ref = pose_data.get('ref')
    icon = pose_data.get('icon')
    if not ref: return
    
    if icon is not None:
        icon_resized = cv2.resize(icon, (box_w, box_h))
        roi = frame[box_y:box_y+box_h, box_x:box_x+box_w]
        if roi.shape == icon_resized.shape:
            blended = cv2.addWeighted(roi, 0.5, icon_resized, 0.5, 0)
            frame[box_y:box_y+box_h, box_x:box_x+box_w] = blended
    else:
        overlay = frame.copy()
        cv2.rectangle(overlay, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    
    cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (255, 255, 255), 2)"""
content = content.replace(draw_ref_old, draw_ref_new)

# 3. Add FloatingGraphic
floating_graphic = """
class FloatingGraphic:
    def __init__(self): self.graphics = []
    def add(self, img, x, y):
        if img is not None:
            self.graphics.append({'img': cv2.resize(img, (80, 80)), 'x': x, 'y': y, 'life': 30})
    def update_and_draw(self, frame):
        for g in self.graphics[:]:
            g['y'] -= 4
            g['life'] -= 1
            if g['life'] <= 0:
                self.graphics.remove(g)
            else:
                img = g['img']
                h, w = img.shape[:2]
                x, y = int(g['x']), int(g['y'])
                if 0 <= y < frame.shape[0]-h and 0 <= x < frame.shape[1]-w:
                    roi = frame[y:y+h, x:x+w]
                    # Add image (black background acts as transparent when added to non-white)
                    # To prevent overflow:
                    frame[y:y+h, x:x+w] = cv2.add(roi, img)
"""
content = content.replace("class FloatingText:", floating_graphic + "\nclass FloatingText:")

# 4. Update Main Loop Initialization
content = content.replace("floating_texts = FloatingText()", "floating_texts = FloatingText()\n    floating_graphics = FloatingGraphic()\n    icon_caderas = load_icon('pose_caderas')\n    is_paused = False\n    pause_start = None")

# 5. Update global hip shake
hip_shake_old = """            threshold = 0.015
            if hip_x > state.global_center_x + threshold and getattr(state, 'global_last_side', None) != 'right':
                state.global_last_side = 'right'
                px, py = int(hip_x * display_w), int(hip_y * display_h)
                particles.emit(px, py, (255, 100, 255), 50)
                floating_texts.add("RITMO! +10", px - 100, py - 60, (255, 100, 255), 2.5)
                score += 10
            elif hip_x < state.global_center_x - threshold and getattr(state, 'global_last_side', None) != 'left':
                state.global_last_side = 'left'
                px, py = int(hip_x * display_w), int(hip_y * display_h)
                particles.emit(px, py, (255, 100, 255), 50)
                floating_texts.add("RITMO! +10", px - 100, py - 60, (255, 100, 255), 2.5)
                score += 10"""

hip_shake_new = """            threshold = 0.015
            if hip_x > state.global_center_x + threshold and getattr(state, 'global_last_side', None) != 'right':
                state.global_last_side = 'right'
                px, py = int(hip_x * display_w), int(hip_y * display_h)
                floating_graphics.add(icon_caderas, px - 40, py - 40)
                floating_texts.add("+10", px, py - 60, (255, 100, 255), 1.5)
                score += 10
            elif hip_x < state.global_center_x - threshold and getattr(state, 'global_last_side', None) != 'left':
                state.global_last_side = 'left'
                px, py = int(hip_x * display_w), int(hip_y * display_h)
                floating_graphics.add(icon_caderas, px - 40, py - 40)
                floating_texts.add("+10", px, py - 60, (255, 100, 255), 1.5)
                score += 10"""
content = content.replace(hip_shake_old, hip_shake_new)

# 6. Add command gesture for PAUSE
pause_code = """
            if check_gesture_pause(lm):
                if pause_start is None: pause_start = current_time
                hold = min(1.0, (current_time - pause_start) / 1.0)
                draw_progress_bar(frame, (display_w-300)//2, 100, 300, 20, hold, (255, 0, 0))
                cv2.putText(frame, "PAUSANDO...", ((display_w-300)//2, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                if current_time - pause_start >= 1.0:
                    is_paused = not is_paused
                    pause_start = None
                    play_sound(snd_success)
                    time.sleep(1) # debounce
            else:
                pause_start = None

            if is_paused:
                cv2.putText(frame, "PAUSA", (display_w//2 - 100, display_h//2), cv2.FONT_HERSHEY_DUPLEX, 2.0, (0, 0, 255), 5)
                cv2.putText(frame, "PAUSA", (display_w//2 - 100, display_h//2), cv2.FONT_HERSHEY_DUPLEX, 2.0, (255, 255, 255), 2)
                # Skip the rest of game logic this frame
            else:
                if check_gesture_next(lm):
"""
content = content.replace("            if check_gesture_next(lm):", pause_code)
# Then fix indentation of the rest of the else block.
# Wait, replacing just "if check_gesture_next" is dangerous because of the else block indent.
# Instead of indenting the rest of the logic, I can just do:
pause_code_alt = """
            if check_gesture_pause(lm):
                if pause_start is None: pause_start = current_time
                hold = min(1.0, (current_time - pause_start) / 1.0)
                draw_progress_bar(frame, (display_w-300)//2, 100, 300, 20, hold, (255, 0, 0))
                cv2.putText(frame, "PAUSANDO...", ((display_w-300)//2, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                if current_time - pause_start >= 1.0:
                    is_paused = not is_paused
                    pause_start = None
                    play_sound(snd_success)
                    time.sleep(0.5) # debounce
            else:
                pause_start = None

            if is_paused:
                cv2.putText(frame, "PAUSA", (display_w//2 - 100, display_h//2), cv2.FONT_HERSHEY_DUPLEX, 2.0, (0, 0, 255), 5)
                cv2.putText(frame, "PAUSA", (display_w//2 - 100, display_h//2), cv2.FONT_HERSHEY_DUPLEX, 2.0, (255, 255, 255), 2)
            elif check_gesture_next(lm):
"""
content = content.replace("            if check_gesture_next(lm):", pause_code_alt.strip() + "\n")

# 7. Update Score UI
content = content.replace('cv2.putText(frame, f"PUNTAJE: {score}", (30, 60), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 0), 8)', 'cv2.putText(frame, f"PUNTAJE: {score}", (20, 40), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 0, 0), 4)')
content = content.replace('cv2.putText(frame, f"PUNTAJE: {score}", (30, 60), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 255, 255), 3)', 'cv2.putText(frame, f"PUNTAJE: {score}", (20, 40), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 255), 2)')

# 8. Add update_and_draw for floating_graphics
content = content.replace("floating_texts.update_and_draw(frame)", "floating_texts.update_and_draw(frame)\n        floating_graphics.update_and_draw(frame)")

with open('poses_locas.py', 'w') as f:
    f.write(content)
print("Patch applied")
