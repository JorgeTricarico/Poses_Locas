import re

with open('poses_locas.py', 'r') as f:
    content = f.read()

# 1. Update draw_reference to overlay faintly
draw_ref_old = """def draw_reference(frame, pose_data, box_x, box_y, box_w, box_h):
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

draw_ref_new = """def draw_reference(frame, pose_data, box_x, box_y, box_w, box_h):
    ref = pose_data.get('ref')
    icon = pose_data.get('icon')
    if not ref: return
    
    roi = frame[box_y:box_y+box_h, box_x:box_x+box_w]
    if icon is not None and roi.shape[:2] == (box_h, box_w):
        icon_resized = cv2.resize(icon, (box_w, box_h))
        frame[box_y:box_y+box_h, box_x:box_x+box_w] = cv2.addWeighted(roi, 0.2, icon_resized, 0.8, 0)
    else:
        overlay = frame.copy()
        cv2.rectangle(overlay, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        
    cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (255, 255, 255), 2)
    points = {lm_id: (int(box_x + nx * box_w), int(box_y + ny * box_h)) for lm_id, (nx, ny) in ref.items()}
    # Draw sticks very faintly
    overlay_lines = frame.copy()
    for a, b in SKELETON_CONNECTIONS:
        if a in points and b in points: cv2.line(overlay_lines, points[a], points[b], (200, 200, 200), 2)
    for a, b in LEFT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(overlay_lines, points[a], points[b], (255, 255, 0), 2)
    for a, b in RIGHT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(overlay_lines, points[a], points[b], (255, 255, 0), 2)
    for pt in points.values(): cv2.circle(overlay_lines, pt, 3, (0, 255, 255), -1)
    if NOSE in points: cv2.circle(overlay_lines, points[NOSE], 6, (0, 255, 255), 2)
    # Blend the lines faintly over the image
    cv2.addWeighted(overlay_lines, 0.4, frame, 0.6, 0, frame)
"""
content = content.replace(draw_ref_old, draw_ref_new)
# Since the original draw_reference drew the skeleton AFTER, we need to remove the old skeleton drawing code from draw_reference
# wait, the old skeleton drawing was right after the replaced block!
old_skeleton_draw = """    points = {lm_id: (int(box_x + nx * box_w), int(box_y + ny * box_h)) for lm_id, (nx, ny) in ref.items()}
    for a, b in SKELETON_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (200, 200, 200), 2)
    for a, b in LEFT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (255, 255, 0), 3)
    for a, b in RIGHT_ARM_CONNECTIONS:
        if a in points and b in points: cv2.line(frame, points[a], points[b], (255, 255, 0), 3)
    for pt in points.values(): cv2.circle(frame, pt, 4, (0, 255, 255), -1)
    if NOSE in points: cv2.circle(frame, points[NOSE], 10, (0, 255, 255), 2)"""
content = content.replace(old_skeleton_draw, "")


# 2. Fix dynamic state center updates
hips_old = """    if state.center_x is None:
        state.center_x = hip_x
        
    threshold = 0.015"""
hips_new = """    if state.center_x is None:
        state.center_x = hip_x
    
    state.center_x = state.center_x * 0.98 + hip_x * 0.02
        
    threshold = 0.015"""
content = content.replace(hips_old, hips_new)

head_old = """    if state.center_x is None:
        state.center_x = nose_x
        
    threshold = 0.015"""
head_new = """    if state.center_x is None:
        state.center_x = nose_x
    
    state.center_x = state.center_x * 0.98 + nose_x * 0.02
        
    threshold = 0.015"""
content = content.replace(head_old, head_new)


# 3. Add huge arrows to dynamic poses UI
dynamic_old = """                # Barra central
                cv2.circle(frame, (cx, cy), 5, (255,255,255), -1)
                # Limites
                cv2.line(frame, (cx - threshold_px, cy - 50), (cx - threshold_px, cy + 50), (0,255,255), 2)
                cv2.line(frame, (cx + threshold_px, cy - 50), (cx + threshold_px, cy + 50), (0,255,255), 2)"""
dynamic_new = """                # Barra central
                cv2.circle(frame, (cx, cy), 5, (255,255,255), -1)
                # Limites
                cv2.line(frame, (cx - threshold_px, cy - 50), (cx - threshold_px, cy + 50), (0,255,255), 2)
                cv2.line(frame, (cx + threshold_px, cy - 50), (cx + threshold_px, cy + 50), (0,255,255), 2)
                
                import math
                arrow_col = current_pose['color']
                offset = int(math.sin(current_time * 8) * 15)
                cv2.arrowedLine(frame, (cx - 30 + offset, cy), (cx - 100 + offset, cy), arrow_col, 8, tipLength=0.4)
                cv2.arrowedLine(frame, (cx + 30 - offset, cy), (cx + 100 - offset, cy), arrow_col, 8, tipLength=0.4)"""
content = content.replace(dynamic_old, dynamic_new)

# 4. Remove Wakanda and Pause logic completely
content = re.sub(r'            if check_gesture_pause\(lm\):.*?            else:', '            if True:', content, flags=re.DOTALL)
content = re.sub(r'            if is_paused:.*?            else:', '            if True:', content, flags=re.DOTALL)
content = content.replace('cv2.putText(frame, "Gesto \'Wakanda\' (X en pecho) = Saltar", (30, display_h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)', '')

with open('poses_locas.py', 'w') as f:
    f.write(content)
print("Patch 3 applied")
