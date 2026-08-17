import re

with open('poses_locas.py', 'r') as f:
    content = f.read()

# 1. Update global hip shake floating texts to appear on the side
global_hips_old = """            if hip_x > state.global_center_x + threshold and getattr(state, 'global_last_side', None) != 'right':
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

global_hips_new = """            if hip_x > state.global_center_x + threshold and getattr(state, 'global_last_side', None) != 'right':
                state.global_last_side = 'right'
                px, py = 50, 100
                floating_texts.add("+10", px, py, (255, 100, 255), 1.5)
                score += 10
            elif hip_x < state.global_center_x - threshold and getattr(state, 'global_last_side', None) != 'left':
                state.global_last_side = 'left'
                px, py = 50, 100
                floating_texts.add("+10", px, py, (255, 100, 255), 1.5)
                score += 10"""
content = content.replace(global_hips_old, global_hips_new)

# 2. Update dynamic events floating text to appear on the side
dynamic_events_old = """                    for e in events:
                        if e['type'] == 'hit':
                            play_sound(snd_punch)
                            px = int(e['x'] * display_w)
                            py = int(e['y'] * display_h)
                            particles.emit(px, py, (255, 50, 255), 25)
                            floating_texts.add("BOOM!", px - 50, py - 50, (255, 255, 0), 1.5)"""

dynamic_events_new = """                    for e in events:
                        if e['type'] == 'hit':
                            play_sound(snd_punch)
                            px = int(e['x'] * display_w)
                            py = int(e['y'] * display_h)
                            particles.emit(px, py, (255, 50, 255), 25)
                            floating_texts.add("BOOM!", 50, 150, (255, 255, 0), 1.5)"""
content = content.replace(dynamic_events_old, dynamic_events_new)

# 3. Update dynamic arrows to adapt cy based on head vs hips
arrows_old = """                cx = int(state.center_x * display_w) if state.center_x else display_w//2
                cy = int(display_h * 0.4)
                # Barra central"""

arrows_new = """                cx = int(state.center_x * display_w) if state.center_x else display_w//2
                if 'Cabeza' in current_pose['name']:
                    cy = int(display_h * 0.25)
                else:
                    cy = int(display_h * 0.6)
                # Barra central"""
content = content.replace(arrows_old, arrows_new)

with open('poses_locas.py', 'w') as f:
    f.write(content)
print("Patch 4 applied")
