import re

with open('poses_locas.py', 'r') as f:
    content = f.read()

# 1. Decrease Floating Text size globally
text_scale_old = """    def add(self, text, x, y, color, scale=1.5):
        self.texts.append({'text': text, 'x': x, 'y': float(y), 'color': color, 'life': 40, 'scale': scale})"""
text_scale_new = """    def add(self, text, x, y, color, scale=1.5):
        scale = scale * 0.6  # Reduce scale so it doesn't block view
        self.texts.append({'text': text, 'x': x, 'y': float(y), 'color': color, 'life': 40, 'scale': scale})"""
content = content.replace(text_scale_old, text_scale_new)


# 2. Add Mouse Controls and pause state
mouse_cb_code = """
    WINDOW_NAME = "Poses Locas AR"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    game_control = {'paused': False, 'music': True}
    def mouse_cb(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if display_w - 60 <= x <= display_w - 10 and display_h - 60 <= y <= display_h - 10:
                game_control['paused'] = not game_control['paused']
            elif display_w - 120 <= x <= display_w - 70 and display_h - 60 <= y <= display_h - 10:
                game_control['music'] = not game_control['music']
                if pygame and pygame.mixer.get_init():
                    if game_control['music']: pygame.mixer.music.unpause()
                    else: pygame.mixer.music.pause()
    cv2.setMouseCallback(WINDOW_NAME, mouse_cb)
"""
content = content.replace("""    WINDOW_NAME = "Poses Locas AR"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)""", mouse_cb_code)

pause_logic = """        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
        
        frame = cv2.resize(frame, (display_w, display_h))
        frame = cv2.flip(frame, 1)
        
        if game_control['paused']:
            cv2.putText(frame, "PAUSA", (display_w//2 - 100, display_h//2), cv2.FONT_HERSHEY_DUPLEX, 2.0, (0,0,255), 4)
            
            # Draw buttons
            color_p = (0, 255, 0) if not game_control['paused'] else (0, 0, 255)
            cv2.rectangle(frame, (display_w - 60, display_h - 60), (display_w - 10, display_h - 10), color_p, -1)
            cv2.putText(frame, "P", (display_w - 45, display_h - 25), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0,0,0), 2)
            color_m = (255, 150, 0) if game_control['music'] else (100, 100, 100)
            cv2.rectangle(frame, (display_w - 120, display_h - 60), (display_w - 70, display_h - 10), color_m, -1)
            cv2.putText(frame, "M", (display_w - 105, display_h - 25), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0,0,0), 2)
            
            cv2.imshow(WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break
            continue
"""
content = content.replace("""        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
        
        frame = cv2.resize(frame, (display_w, display_h))
        frame = cv2.flip(frame, 1)""", pause_logic)

# 3. Draw buttons at the end of loop
draw_buttons = """        
        # Draw buttons
        color_p = (0, 255, 0) if not game_control['paused'] else (0, 0, 255)
        cv2.rectangle(frame, (display_w - 60, display_h - 60), (display_w - 10, display_h - 10), color_p, -1)
        cv2.putText(frame, "P", (display_w - 45, display_h - 25), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0,0,0), 2)
        
        color_m = (255, 150, 0) if game_control['music'] else (100, 100, 100)
        cv2.rectangle(frame, (display_w - 120, display_h - 60), (display_w - 70, display_h - 10), color_m, -1)
        cv2.putText(frame, "M", (display_w - 105, display_h - 25), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0,0,0), 2)
        
        cv2.imshow(WINDOW_NAME, frame)"""
content = content.replace("        cv2.imshow(WINDOW_NAME, frame)", draw_buttons)

# 4. Move static progress bar out of center
static_prog_old = """                        draw_progress_bar(frame, (display_w-300)//2, display_h-80, 300, 25, hold_progress, (0, 255, 0))
                        cv2.putText(frame, "MANTENE!", ((display_w-300)//2, display_h-90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)"""
static_prog_new = """                        draw_progress_bar(frame, 20, 100, 300, 25, hold_progress, (0, 255, 0))
                        cv2.putText(frame, "MANTENE!", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)"""
content = content.replace(static_prog_old, static_prog_new)

# 5. Move dynamic GOLPES out of center
dyn_prog_old = """                # Feedback de golpes logrados
                cv2.putText(frame, f"GOLPES: {state.hip_hits}/6", ((display_w-200)//2, display_h-80), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 0, 255), 3)"""
dyn_prog_new = """                # Feedback de golpes logrados
                cv2.putText(frame, f"GOLPES: {state.hip_hits}/4", (20, 150), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 0, 255), 3)"""
content = content.replace(dyn_prog_old, dyn_prog_new)


with open('poses_locas.py', 'w') as f:
    f.write(content)
print("Patch 6 applied")
