import re

with open('poses_locas.py', 'r') as f:
    content = f.read()

# 1. Add particles to GLOBAL HIP SHAKE
global_hips_old = """            if hip_x > state.global_center_x + threshold and getattr(state, 'global_last_side', None) != 'right':
                state.global_last_side = 'right'
                px, py = 50, 100
                floating_texts.add("+10", px, py, (255, 100, 255), 1.5)
                score += 10
            elif hip_x < state.global_center_x - threshold and getattr(state, 'global_last_side', None) != 'left':
                state.global_last_side = 'left'
                px, py = 50, 100
                floating_texts.add("+10", px, py, (255, 100, 255), 1.5)
                score += 10"""

global_hips_new = """            if hip_x > state.global_center_x + threshold and getattr(state, 'global_last_side', None) != 'right':
                state.global_last_side = 'right'
                floating_texts.add("CADERAS! +10", 50, 100, (255, 100, 255), 1.5)
                particles.emit(int(hip_x * display_w), int(hip_y * display_h), (255, 100, 255), 15)
                score += 10
            elif hip_x < state.global_center_x - threshold and getattr(state, 'global_last_side', None) != 'left':
                state.global_last_side = 'left'
                floating_texts.add("CADERAS! +10", 50, 100, (255, 100, 255), 1.5)
                particles.emit(int(hip_x * display_w), int(hip_y * display_h), (255, 100, 255), 15)
                score += 10"""
content = content.replace(global_hips_old, global_hips_new)

# 2. Add GLOBAL HEAD SHAKE
global_head_new = """
            # --- GLOBAL HEAD SHAKE ---
            nose_x = lm[NOSE].x
            nose_y = lm[NOSE].y
            if not hasattr(state, 'global_head_center_x') or state.global_head_center_x is None:
                state.global_head_center_x = nose_x
                state.global_head_last_side = None
            
            state.global_head_center_x = state.global_head_center_x * 0.95 + nose_x * 0.05
            
            if nose_x > state.global_head_center_x + threshold and getattr(state, 'global_head_last_side', None) != 'right':
                state.global_head_last_side = 'right'
                floating_texts.add("CABEZA! +10", 50, 150, (150, 255, 100), 1.5)
                particles.emit(int(nose_x * display_w), int(nose_y * display_h), (150, 255, 100), 15)
                score += 10
            elif nose_x < state.global_head_center_x - threshold and getattr(state, 'global_head_last_side', None) != 'left':
                state.global_head_last_side = 'left'
                floating_texts.add("CABEZA! +10", 50, 150, (150, 255, 100), 1.5)
                particles.emit(int(nose_x * display_w), int(nose_y * display_h), (150, 255, 100), 15)
                score += 10
            # ------------------------"""

idx = content.find("            if True:\n                pause_start = None")
content = content[:idx] + global_head_new + "\n" + content[idx:]

# 3. Move static success texts to side
dyn_success_old = """                        particles.emit_confetti(display_w)
                        particles.emit(display_w // 2, display_h // 2, current_pose['color'], 40)
                        floating_texts.add(f"BAILASTE GENIAL! +{points}", display_w // 2 - 250, display_h // 2 - 80, (0, 255, 100), 2.0)"""
dyn_success_new = """                        particles.emit_confetti(display_w)
                        particles.emit(display_w // 2, display_h // 2, current_pose['color'], 40)
                        floating_texts.add(f"BAILASTE GENIAL! +{points}", 50, 250, (0, 255, 100), 2.0)"""
content = content.replace(dyn_success_old, dyn_success_new)

stat_success_old = """                            particles.emit_confetti(display_w)
                            particles.emit(display_w // 2, display_h // 2, current_pose['color'], 30)
                            floating_texts.add(f"GENIAL! +{points}", display_w // 2 - 130, display_h // 2 - 80, (0, 255, 100), 2.0)
                            if streak >= 3: floating_texts.add(f"RACHA x{streak}!", display_w // 2 - 100, display_h // 2 - 20, (0, 255, 255), 1.5)"""
stat_success_new = """                            particles.emit_confetti(display_w)
                            particles.emit(display_w // 2, display_h // 2, current_pose['color'], 30)
                            floating_texts.add(f"GENIAL! +{points}", 50, 250, (0, 255, 100), 2.0)
                            if streak >= 3: floating_texts.add(f"RACHA x{streak}!", 50, 300, (0, 255, 255), 1.5)"""
content = content.replace(stat_success_old, stat_success_new)


with open('poses_locas.py', 'w') as f:
    f.write(content)
print("Patch 5 applied")
