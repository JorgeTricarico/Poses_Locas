import re

with open('poses_locas.py', 'r') as f:
    content = f.read()

# 1. Update check_shake_hips to require 4 hits
content = content.replace("completed = state.hip_hits >= 6 # 6 golpes para ganar", "completed = state.hip_hits >= 4")

# 2. Add check_shake_head and new pose
head_shake_code = """
def check_shake_head(state, lm):
    events = []
    nose_x = lm[NOSE].x
    
    if state.center_x is None:
        state.center_x = nose_x
        
    threshold = 0.015
    
    if nose_x > state.center_x + threshold and state.last_hit_side != 'right':
        state.last_hit_side = 'right'
        state.hip_hits += 1
    elif nose_x < state.center_x - threshold and state.last_hit_side != 'left':
        state.last_hit_side = 'left'
        state.hip_hits += 1
        
    completed = state.hip_hits >= 4
    return completed, events
"""
# Insert after check_shake_hips
idx = content.find("def check_shake_hips")
# find the end of the function
end_idx = content.find("def check_left_arm_up", idx)
content = content[:end_idx] + head_shake_code + "\n" + content[end_idx:]

# 3. Add to POSES
pose_cabeza = """    {
        'name': 'Mueve la Cabeza!', 'color': (150, 255, 100),
        'dynamic': True, 'checks': check_shake_head,
        'icon': load_icon('pose_cabeza'),
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.32, 0.45), R_ELBOW: (0.68, 0.45), L_WRIST: (0.35, 0.60), R_WRIST: (0.65, 0.60), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
"""
# Insert into POSES list
idx_poses = content.find("POSES = [")
idx_first_pose = content.find("{", idx_poses)
content = content[:idx_first_pose] + pose_cabeza + content[idx_first_pose:]

# 4. Update draw_reference to draw icon separately
draw_ref_old = """def draw_reference(frame, pose_data, box_x, box_y, box_w, box_h):
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

draw_ref_new = """def draw_reference(frame, pose_data, box_x, box_y, box_w, box_h):
    ref = pose_data.get('ref')
    icon = pose_data.get('icon')
    if not ref: return
    
    if icon is not None:
        icon_resized = cv2.resize(icon, (box_w, box_h))
        icon_x = box_x - box_w - 10
        if icon_x >= 0:
            roi = frame[box_y:box_y+box_h, icon_x:icon_x+box_w]
            if roi.shape == icon_resized.shape:
                frame[box_y:box_y+box_h, icon_x:icon_x+box_w] = cv2.add(roi, icon_resized)
                cv2.rectangle(frame, (icon_x, box_y), (icon_x + box_w, box_y + box_h), (255, 255, 255), 2)
                cv2.putText(frame, "FIGURA", (icon_x + 10, box_y + box_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, "POSTURA", (box_x + 10, box_y + box_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    overlay = frame.copy()
    cv2.rectangle(overlay, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (255, 255, 255), 2)"""
content = content.replace(draw_ref_old, draw_ref_new)

# 5. Update Dynamic feedback UI
dynamic_old = """            if current_pose.get('dynamic'):
                # Dibujar centro y limites
                cx = int(state.center_x * display_w) if state.center_x else display_w//2
                cy = int(display_h * 0.6) # Aproximado
                threshold_px = int(0.015 * display_w)
                
                # Barra central
                cv2.circle(frame, (cx, cy), 5, (255,255,255), -1)
                # Limites
                cv2.line(frame, (cx - threshold_px, cy - 50), (cx - threshold_px, cy + 50), (0,255,255), 2)
                cv2.line(frame, (cx + threshold_px, cy - 50), (cx + threshold_px, cy + 50), (0,255,255), 2)
                
                # Feedback de golpes logrados
                cv2.putText(frame, f"GOLPES: {state.hip_hits}/6", ((display_w-200)//2, display_h-80), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 0, 255), 3)"""

dynamic_new = """            if current_pose.get('dynamic'):
                # Draw a massive progress bar at the bottom center
                progress = min(1.0, state.hip_hits / 4.0)
                bar_w, bar_h = 400, 40
                bar_x, bar_y = (display_w - bar_w) // 2, display_h - 120
                
                # Draw background
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)
                # Draw fill
                if progress > 0:
                    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * progress), bar_y + bar_h), current_pose['color'], -1)
                # Draw border
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (255, 255, 255), 3)
                
                # Draw Text
                msg = "¡MUEVETE!"
                text_sz = cv2.getTextSize(msg, cv2.FONT_HERSHEY_DUPLEX, 1.5, 4)[0]
                cv2.putText(frame, msg, (bar_x + (bar_w - text_sz[0])//2, bar_y - 20), cv2.FONT_HERSHEY_DUPLEX, 1.5, current_pose['color'], 4)
                
                cv2.putText(frame, f"{state.hip_hits}/4", (bar_x + (bar_w - 30)//2, bar_y + 30), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2)"""
content = content.replace(dynamic_old, dynamic_new)

# 6. Update pose name UI background
name_ui_old = """        pose_text = current_pose['name']
        text_x = (display_w - cv2.getTextSize(pose_text, cv2.FONT_HERSHEY_DUPLEX, 2, 4)[0][0]) // 2
        cv2.putText(frame, pose_text, (text_x + 3, 73), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 0, 0), 6)
        cv2.putText(frame, pose_text, (text_x, 70), cv2.FONT_HERSHEY_DUPLEX, 2, current_pose['color'], 4)"""

name_ui_new = """        pose_text = current_pose['name']
        text_sz = cv2.getTextSize(pose_text, cv2.FONT_HERSHEY_DUPLEX, 2, 4)[0]
        text_x = (display_w - text_sz[0]) // 2
        
        # Background rectangle for the text
        overlay = frame.copy()
        cv2.rectangle(overlay, (text_x - 30, 20), (text_x + text_sz[0] + 30, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        cv2.putText(frame, pose_text, (text_x + 4, 74), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 0, 0), 8)
        cv2.putText(frame, pose_text, (text_x, 70), cv2.FONT_HERSHEY_DUPLEX, 2, current_pose['color'], 4)"""
content = content.replace(name_ui_old, name_ui_new)


with open('poses_locas.py', 'w') as f:
    f.write(content)
print("Patch2 applied")
