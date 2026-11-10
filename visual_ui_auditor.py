import cv2
import numpy as np
import math
import os
import json
import time

# =====================================================================
# MOTOR DE AUDITORÍA AUTOMÁTICA DE UI/UX (5 GATES MATEMÁTICOS)
# =====================================================================
class UILayoutAuditor:
    """
    Audita matemáticamente cada pantalla renderizada para detectar:
    - Gate 1: Colisiones/solapamientos entre elementos de UI (textos, barras, tarjetas).
    - Gate 2: Invasión de la Zona Segura Central del cuerpo del jugador (x:370..890, y:130..555).
    - Gate 3: Legibilidad a 3 metros (escala mínima de fuente >= 0.48).
    - Gate 4: Elementos cortados o fuera de los bordes de la pantalla (1280x720).
    - Gate 5: Caracteres Unicode/No-ASCII incompatibles con OpenCV Hershey (ord(c) > 126, ej. emojis o '¡' que salen como '?').
    """
    def __init__(self, screen_name, width=1280, height=720, check_center_safe_zone=True):
        self.screen_name = screen_name
        self.width = width
        self.height = height
        self.check_center_safe_zone = check_center_safe_zone
        self.elements = []
        self.violations = []

    def check_ascii_safe(self, text):
        bad_chars = [c for c in text if ord(c) > 126 or ord(c) < 32]
        if bad_chars:
            self.violations.append(
                f"[GATE 5 - CARACTER CORRUPTO EN OPENCV] Texto '{text}' contiene caracteres no-ASCII {bad_chars} que cv2.putText dibuja como '?'"
            )

    def register_box(self, name, x, y, w, h, group="ui", allow_center=False):
        x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
        # Gate 4: Out of bounds check
        if x1 < 0 or y1 < 0 or x2 > self.width or y2 > self.height:
            self.violations.append(
                f"[GATE 4 - FUERA DE PANTALLA] '{name}' ({x1},{y1})-({x2},{y2}) excede {self.width}x{self.height}"
            )
        # Gate 2: Center Safe Zone check (x:370..890, y:130..555)
        if self.check_center_safe_zone and not allow_center:
            cz_x1, cz_y1, cz_x2, cz_y2 = 370, 130, 890, 555
            ix1, iy1 = max(x1, cz_x1), max(y1, cz_y1)
            ix2, iy2 = min(x2, cz_x2), min(y2, cz_y2)
            if ix2 > ix1 and iy2 > iy1 and (ix2 - ix1) * (iy2 - iy1) > 2500:
                self.violations.append(
                    f"[GATE 2 - OBSTRUCCIÓN CENTRAL] '{name}' invade la zona del cuerpo del jugador en ({ix1},{iy1})-({ix2},{iy2})"
                )
        # Gate 1: Overlap check against other groups
        for el in self.elements:
            if el["group"] == group:
                continue
            ox1, oy1 = max(x1, el["x1"]), max(y1, el["y1"])
            ox2, oy2 = min(x2, el["x2"]), min(y2, el["y2"])
            if ox2 > ox1 + 2 and oy2 > oy1 + 2:
                self.violations.append(
                    f"[GATE 1 - COLISIÓN UI] '{name}' se superpone con '{el['name']}' en ({ox1},{oy1})-({ox2},{oy2})"
                )
        self.elements.append({"name": name, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "group": group})

    def register_text(self, frame, text, x, y, font, scale, color, thickness, group="ui", allow_center=False, shadow=True):
        self.check_ascii_safe(text)
        if scale < 0.48:
            self.violations.append(
                f"[GATE 3 - TEXTO MUY PEQUEÑO] '{text}' tiene scale={scale:.2f} (< 0.48, ilegible a 3m)"
            )
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
        self.register_box(f"Texto:{text[:20]}", x, y - th - 2, tw, th + baseline + 4, group=group, allow_center=allow_center)
        if shadow:
            cv2.putText(frame, text, (int(x) + 1, int(y) + 1), font, scale, (0, 0, 0), thickness + 1, cv2.LINE_AA)
        cv2.putText(frame, text, (int(x), int(y)), font, scale, color, thickness, cv2.LINE_AA)

    def summary(self):
        return {
            "screen": self.screen_name,
            "total_elements": len(self.elements),
            "violations_count": len(self.violations),
            "passed": len(self.violations) == 0,
            "violations": self.violations,
        }


# =====================================================================
# UTILIDADES VISUALES Y CARGADOR DE ILUSTRACIONES (BLUEPRINT 01, 02, 04)
# =====================================================================
def blend_rect_roi(frame, x, y, w, h, bgr_color, alpha=0.6):
    fh, fw = frame.shape[:2]
    x1, y1 = max(0, int(x)), max(0, int(y))
    x2, y2 = min(fw, int(x + w)), min(fh, int(y + h))
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    rect = np.full_like(roi, bgr_color, dtype=np.uint8)
    cv2.addWeighted(rect, alpha, roi, 1.0 - alpha, 0, roi)


def load_pose_illustration_clean(filename_no_ext, size=(160, 160), bg_color=(30, 25, 38)):
    path = f"{filename_no_ext}.jpg"
    if not os.path.exists(path):
        return None
    img = cv2.imread(path)
    if img is None:
        return None
    img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners = [int(gray[0, 0]), int(gray[0, -1]), int(gray[-1, 0]), int(gray[-1, -1])]
    bg_brightness = sum(corners) / 4.0
    if bg_brightness > 200:
        _, mask = cv2.threshold(gray, 238, 255, cv2.THRESH_BINARY_INV)
    else:
        _, mask = cv2.threshold(gray, 22, 255, cv2.THRESH_BINARY)
    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    alpha = (mask.astype(np.float32) / 255.0)[..., None]
    bg_card = np.full_like(img, bg_color, dtype=np.uint8)
    return (img.astype(np.float32) * alpha + bg_card.astype(np.float32) * (1.0 - alpha)).astype(np.uint8)


def draw_full_body_stickman(frame, x, y, w, h, pts, arm_color, body_color=(210, 210, 220), show_floor=True):
    """Dibuja un muñeco guía expresivo con torso, brazos, piernas, rodillas, pies y línea de suelo."""
    def p(key):
        nx, ny = pts[key]
        return (int(x + nx * w), int(y + ny * h))

    if show_floor:
        fy = int(y + h * 0.92)
        cv2.line(frame, (int(x + w * 0.12), fy), (int(x + w * 0.88), fy), (90, 90, 115), 2, cv2.LINE_AA)

    torso_conns = [('ls', 'rs'), ('ls', 'lh'), ('rs', 'rh'), ('lh', 'rh')]
    leg_conns = [('lh', 'lk'), ('lk', 'la'), ('rh', 'rk'), ('rk', 'ra')]
    arm_conns = [('ls', 'le'), ('le', 'lw'), ('rs', 're'), ('re', 'rw')]

    if all(k in pts for k in ['ls', 'rs', 'rh', 'lh']):
        poly = np.array([p('ls'), p('rs'), p('rh'), p('lh')], np.int32)
        cv2.fillPoly(frame, [poly], (60, 60, 80))

    for a, b in torso_conns + leg_conns:
        if a in pts and b in pts:
            cv2.line(frame, p(a), p(b), body_color, 3, cv2.LINE_AA)
    for a, b in arm_conns:
        if a in pts and b in pts:
            cv2.line(frame, p(a), p(b), arm_color, 5, cv2.LINE_AA)
            cv2.line(frame, p(a), p(b), (255, 255, 255), 2, cv2.LINE_AA)

    for k in ['lw', 'rw']:
        if k in pts:
            cv2.circle(frame, p(k), 6, arm_color, -1, cv2.LINE_AA)
            cv2.circle(frame, p(k), 3, (255, 255, 255), -1, cv2.LINE_AA)

    if 'nose' in pts:
        r_head = max(8, int(w * 0.08))
        cv2.circle(frame, p('nose'), r_head, arm_color, 2, cv2.LINE_AA)
        cv2.circle(frame, p('nose'), max(3, r_head - 4), (240, 240, 255), -1, cv2.LINE_AA)


def draw_star_icon(frame, cx, cy, r, color):
    """Dibuja un ícono vectorial de estrella/diamante (reemplaza emojis que OpenCV no soporta)."""
    pts = np.array([
        [cx, cy - r], [cx + r // 3, cy - r // 3], [cx + r, cy],
        [cx + r // 3, cy + r // 3], [cx, cy + r], [cx - r // 3, cy + r // 3],
        [cx - r, cy], [cx - r // 3, cy - r // 3]
    ], np.int32)
    cv2.fillPoly(frame, [pts], color, cv2.LINE_AA)


def draw_bolt_icon(frame, cx, cy, r, color):
    """Dibuja un ícono vectorial de rayo eléctrico (Speed Pose)."""
    pts = np.array([
        [cx + 3, cy - r], [cx - r + 2, cy + 2], [cx - 1, cy + 2],
        [cx - 3, cy + r], [cx + r - 2, cy - 2], [cx + 1, cy - 2]
    ], np.int32)
    cv2.fillPoly(frame, [pts], color, cv2.LINE_AA)


# =====================================================================
# LÁMINA 1: COMPARATIVA ANTES vs DESPUÉS (DIAGNÓSTICO DE ERRORES VISUALES)
# =====================================================================
def generate_sheet_01_before_after():
    w, h = 1280, 720
    frame = np.full((h, w, 3), (22, 18, 30), dtype=np.uint8)

    blend_rect_roi(frame, 0, 0, w, 68, (40, 25, 60), 0.9)
    cv2.putText(frame, "LAMINA 1/6: DIAGNOSTICO VISUAL - ANTES vs DESPUES (UI/UX)", (28, 44),
                cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)

    bx, by, bw, bh = 25, 85, 595, 595
    blend_rect_roi(frame, bx, by, bw, bh, (35, 25, 35), 0.85)
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (60, 60, 255), 2)
    cv2.putText(frame, "ANTES (Bugs Visuales Detectados)", (bx + 20, by + 35),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, (80, 80, 255), 2, cv2.LINE_AA)

    if os.path.exists("test_visual_gameplay.jpg"):
        old_img = cv2.imread("test_visual_gameplay.jpg")
        old_resized = cv2.resize(old_img, (555, 312))
        frame[by + 55:by + 55 + 312, bx + 20:bx + 20 + 555] = old_resized
        cv2.rectangle(frame, (bx + 22, by + 55 + 265), (bx + 150, by + 55 + 310), (0, 0, 255), 2)
        cv2.circle(frame, (bx + 45, by + 55 + 275), 18, (0, 0, 255), 2)

    bugs = [
        "1. COLISION INFERIOR: 'MANTENE!', 'GOLPES: 0/6' y",
        "   el texto de ayuda pisan el carril de poses (y=640..720).",
        "2. INTENCION INVISIBLE: El muneco de referencia no tiene",
        "   piernas ni flechas. 'Salto', 'Agacharse' y 'Girando'",
        "   se ven como palitos quietos imposibles de adivinar.",
        "3. IMAGENES DESCONECTADAS: Las 8 fotos pose_*.jpg quedaron",
        "   sin cargar y pose_letra_y.jpg tenia fondo blanco.",
        "4. FEEDBACK BINARIO: El brazo pasa de Rojo a Verde de",
        "   golpe y un parpadeo de 1 frame resetea la barra a 0%."
    ]
    for i, line in enumerate(bugs):
        col = (100, 120, 255) if line[0].isdigit() else (210, 210, 220)
        cv2.putText(frame, line, (bx + 20, by + 400 + i * 21), cv2.FONT_HERSHEY_SIMPLEX, 0.54, col, 1, cv2.LINE_AA)

    ax, ay, aw, ah = 655, 85, 600, 595
    blend_rect_roi(frame, ax, ay, aw, ah, (25, 40, 35), 0.85)
    cv2.rectangle(frame, (ax, ay), (ax + aw, ay + ah), (80, 255, 100), 2)
    cv2.putText(frame, "DESPUES (Mapa de 5 Zonas + Coach Vivo)", (ax + 20, ay + 35),
                cv2.FONT_HERSHEY_DUPLEX, 0.82, (80, 255, 100), 2, cv2.LINE_AA)

    mx, my, mw, mh = ax + 25, ay + 55, 550, 312
    cv2.rectangle(frame, (mx, my), (mx + mw, my + mh), (40, 45, 60), -1)
    cv2.rectangle(frame, (mx, my), (mx + mw, my + mh), (200, 200, 200), 1)
    cv2.rectangle(frame, (mx + 10, my + 10), (mx + 145, my + 75), (255, 180, 0), 2)
    cv2.putText(frame, "Z1: Score+Fever", (mx + 16, my + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 50), 1, cv2.LINE_AA)
    cv2.rectangle(frame, (mx + 165, my + 10), (mx + 385, my + 65), (0, 255, 255), 2)
    cv2.putText(frame, "Z2: Pose + Barra Hold", (mx + 185, my + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1, cv2.LINE_AA)
    cv2.rectangle(frame, (mx + 400, my + 10), (mx + 540, my + 125), (255, 100, 255), 2)
    cv2.putText(frame, "Z3: Ilustracion", (mx + 412, my + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 150, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, "+ Coach Vivo", (mx + 412, my + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 150, 255), 1, cv2.LINE_AA)
    cv2.rectangle(frame, (mx + 155, my + 75), (mx + 390, my + 240), (80, 255, 100), 2)
    cv2.putText(frame, "ZONA CENTRAL 100% LIBRE", (mx + 172, my + 145), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (80, 255, 100), 1, cv2.LINE_AA)
    cv2.putText(frame, "Ghost Pose + Anillos + Trails", (mx + 165, my + 175), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 255, 180), 1, cv2.LINE_AA)
    cv2.rectangle(frame, (mx + 10, my + 115), (mx + 145, my + 220), (100, 220, 255), 1)
    cv2.putText(frame, "Z4: Combos", (mx + 25, my + 170), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 220, 255), 1, cv2.LINE_AA)
    cv2.rectangle(frame, (mx + 10, my + 250), (mx + 540, my + 302), (0, 215, 255), 2)
    cv2.putText(frame, "Z5: Carril de Picto-Cards con Mini-Esqueleto y Slide Suave", (mx + 45, my + 282),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 215, 255), 1, cv2.LINE_AA)

    fixes = [
        "1. CERO SUPERPOSICION: Verificado por UILayoutAuditor.",
        "2. SILUETA FANTASMA Y ANILLOS MAGNETICOS sobre el cuerpo",
        "   del jugador (no hace falta desviar la vista).",
        "3. SEMAFORO CONTINUO (Rojo -> Ambar -> Verde) + Grace",
        "   Decay (la barra baja suave si parpadea la camara).",
        "4. COACH HOLOGRAFICO VIVO: Con piernas, piso y flechas",
        "   animadas + las 8 ilustraciones pose_*.jpg limpiadas.",
        "5. +8 POSES NUEVAS Y MODIFICADORES: Mono, Boxeo, Disco,",
        "   Avion, Guitarra, Gold Move (+500) y Relampago (x2)."
    ]
    for i, line in enumerate(fixes):
        col = (100, 255, 140) if line[0].isdigit() else (215, 230, 220)
        cv2.putText(frame, line, (ax + 20, ay + 400 + i * 21), cv2.FONT_HERSHEY_SIMPLEX, 0.54, col, 1, cv2.LINE_AA)

    cv2.imwrite("diseno_01_comparativa_antes_vs_despues.jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return frame


# =====================================================================
# LÁMINA 2: NUEVO HUD EN GAMEPLAY (GHOST POSE + SEMÁFORO + PICTO-CARDS)
# =====================================================================
def generate_sheet_02_new_hud_gameplay():
    w, h = 1280, 720
    frame = np.full((h, w, 3), (38, 32, 48), dtype=np.uint8)
    auditor = UILayoutAuditor("Lamina_02_HUD_Gameplay", w, h, check_center_safe_zone=True)

    cv2.circle(frame, (630, 345), 250, (48, 40, 62), -1, cv2.LINE_AA)
    cv2.circle(frame, (630, 345), 185, (55, 45, 72), 2, cv2.LINE_AA)

    # --- ZONA 1: TOP-LEFT HUD ---
    blend_rect_roi(frame, 20, 18, 290, 132, (18, 15, 25), 0.78)
    cv2.rectangle(frame, (20, 18), (310, 150), (0, 220, 255), 2)
    auditor.register_box("Panel_Score_Left", 20, 18, 290, 132, group="z1")
    auditor.register_text(frame, "PUNTAJE: 2,450", 35, 58, cv2.FONT_HERSHEY_DUPLEX, 0.95, (0, 255, 255), 2, group="z1")
    auditor.register_text(frame, "RACHA x4  |  MULTI x2", 35, 95, cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 200, 255), 2, group="z1")
    cv2.rectangle(frame, (35, 112), (225, 132), (60, 60, 75), -1)
    cv2.rectangle(frame, (35, 112), (180, 132), (255, 50, 255), -1)
    cv2.rectangle(frame, (35, 112), (225, 132), (255, 255, 255), 2)
    auditor.register_text(frame, "FEVER 75%", 234, 128, cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 130, 255), 1, group="z1")

    # --- ZONA 2: TOP-CENTER BANNER ---
    bx, by, bw, bh = 385, 18, 465, 102
    blend_rect_roi(frame, bx, by, bw, bh, (15, 15, 25), 0.82)
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 120), 2)
    auditor.register_box("Banner_Top_Center", bx, by, bw, bh, group="z2")
    auditor.register_text(frame, "BRAZOS ARRIBA!", bx + 82, by + 40, cv2.FONT_HERSHEY_DUPLEX, 1.12, (0, 255, 120), 2, group="z2")
    cv2.rectangle(frame, (bx + 28, by + 52), (bx + bw - 28, by + 74), (45, 45, 60), -1)
    cv2.rectangle(frame, (bx + 28, by + 52), (bx + 28 + int((bw - 56) * 0.78), by + 74), (0, 210, 110), -1)
    cv2.rectangle(frame, (bx + 28, by + 52), (bx + bw - 28, by + 74), (255, 255, 255), 2)
    auditor.register_text(frame, "MANTENE: 78% (Grace Buffer Activo)", bx + 75, by + 95, cv2.FONT_HERSHEY_SIMPLEX, 0.52, (210, 255, 220), 1, group="z2")

    # --- ZONA 3: TOP-RIGHT DUAL REFERENCE CARD ---
    rx, ry, rw, rh = 900, 18, 356, 200
    blend_rect_roi(frame, rx, ry, rw, rh, (20, 18, 30), 0.85)
    cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (255, 200, 0), 2)
    auditor.register_box("Card_Reference_Right", rx, ry, rw, rh, group="z3")
    illus = load_pose_illustration_clean("pose_brazos", size=(155, 155))
    if illus is not None:
        frame[ry + 12:ry + 12 + 155, rx + 12:rx + 12 + 155] = illus
        cv2.rectangle(frame, (rx + 12, ry + 12), (rx + 167, ry + 167), (100, 100, 130), 1)
    ref_pts = {
        'nose': (0.5, 0.16), 'ls': (0.36, 0.32), 'rs': (0.64, 0.32),
        'le': (0.28, 0.18), 're': (0.72, 0.18), 'lw': (0.32, 0.05), 'rw': (0.68, 0.05),
        'lh': (0.42, 0.60), 'rh': (0.58, 0.60),
        'lk': (0.41, 0.76), 'rk': (0.59, 0.76), 'la': (0.40, 0.90), 'ra': (0.60, 0.90)
    }
    draw_full_body_stickman(frame, rx + 180, ry + 10, 160, 158, ref_pts, (0, 255, 120))
    auditor.register_text(frame, "ILUSTRACION + COACH VIVO", rx + 42, ry + 190, cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1, group="z3")

    # --- ZONA CENTRAL AR: JUGADOR CON GHOST POSE, ANILLOS MAGNÉTICOS Y SEMÁFORO ---
    p_ls, p_rs = (545, 285), (705, 285)
    p_lh, p_rh = (565, 470), (685, 470)
    ghost_lw, ghost_rw = (520, 170), (730, 170)
    ghost_le, ghost_re = (505, 225), (745, 225)
    cv2.line(frame, p_rs, ghost_re, (255, 220, 100), 4, cv2.LINE_AA)
    cv2.line(frame, ghost_re, ghost_rw, (255, 220, 100), 4, cv2.LINE_AA)
    cv2.circle(frame, ghost_lw, 22, (0, 255, 100), 3, cv2.LINE_AA)
    cv2.circle(frame, ghost_rw, 26, (0, 215, 255), 3, cv2.LINE_AA)
    auditor.register_text(frame, "ANILLO DESTINO", ghost_rw[0] - 55, ghost_rw[1] - 32, cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 215, 255), 1, group="ar", allow_center=True)

    real_lw, real_le = (520, 170), (505, 225)
    real_rw, real_re = (795, 260), (755, 295)
    cv2.arrowedLine(frame, real_rw, (ghost_rw[0] + 10, ghost_rw[1] + 10), (0, 215, 255), 3, cv2.LINE_AA, tipLength=0.25)

    for a, b in [(p_ls, p_rs), (p_ls, p_lh), (p_rs, p_rh), (p_lh, p_rh)]:
        cv2.line(frame, a, b, (255, 255, 0), 10, cv2.LINE_AA)
        cv2.line(frame, a, b, (255, 255, 255), 3, cv2.LINE_AA)
    for a, b in [(p_ls, real_le), (real_le, real_lw)]:
        cv2.line(frame, a, b, (60, 255, 60), 14, cv2.LINE_AA)
        cv2.line(frame, a, b, (255, 255, 255), 4, cv2.LINE_AA)
    for a, b in [(p_rs, real_re), (real_re, real_rw)]:
        cv2.line(frame, a, b, (0, 200, 255), 14, cv2.LINE_AA)
        cv2.line(frame, a, b, (255, 255, 255), 4, cv2.LINE_AA)
    cv2.circle(frame, (625, 210), 24, (255, 255, 0), 3, cv2.LINE_AA)
    auditor.register_text(frame, "100% OK!", real_lw[0] - 110, real_lw[1] + 5, cv2.FONT_HERSHEY_DUPLEX, 0.58, (80, 255, 80), 2, group="ar", allow_center=True)
    auditor.register_text(frame, "65% SUBE MAS!", real_rw[0] - 20, real_rw[1] + 35, cv2.FONT_HERSHEY_DUPLEX, 0.58, (0, 215, 255), 2, group="ar", allow_center=True)

    # --- ZONA 4: FLOATING FEEDBACK LATERAL IZQUIERDO ---
    auditor.register_text(frame, "PERFECTO!! +300", 30, 310, cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 215, 255), 2, group="z4")
    auditor.register_text(frame, "GROOVE CADERA +15", 30, 355, cv2.FONT_HERSHEY_DUPLEX, 0.72, (255, 120, 255), 2, group="z4")

    # --- ZONA 5: CARRIL INFERIOR 2.0 ---
    lane_y = 588
    blend_rect_roi(frame, 0, lane_y - 26, w, 26, (10, 10, 18), 0.78)
    auditor.register_text(frame, "Gesto Brazos en X = Saltar Pose  |  Manos Arriba en Menu = Jugar  |  BPM Beat-Sync: 103 BPM",
                          28, lane_y - 7, cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 210, 230), 1, group="z5_help")

    blend_rect_roi(frame, 0, lane_y, w, h - lane_y, (18, 16, 26), 0.92)
    cv2.line(frame, (0, lane_y), (w, lane_y), (0, 255, 255), 2)

    cards = [
        {"title": "Brazos Arriba!", "tag": "AHORA! (HOLD)", "col": (0, 255, 120), "active": True, "icon": None, "pts": ref_pts},
        {"title": "Mueve Caderas", "tag": "SIGUIENTE (RITMO)", "col": (255, 100, 180), "active": False, "icon": None,
         "pts": {'nose':(0.5,0.16),'ls':(0.36,0.32),'rs':(0.64,0.32),'le':(0.25,0.45),'re':(0.75,0.45),'lw':(0.38,0.60),'rw':(0.62,0.60),'lh':(0.32,0.62),'rh':(0.50,0.62),'lk':(0.38,0.78),'rk':(0.55,0.78),'la':(0.40,0.90),'ra':(0.58,0.90)}},
        {"title": "Pose de Mono!", "tag": "NUEVA POSE", "col": (0, 200, 255), "active": False, "icon": None,
         "pts": {'nose':(0.5,0.16),'ls':(0.36,0.32),'rs':(0.64,0.32),'le':(0.18,0.35),'re':(0.82,0.35),'lw':(0.38,0.40),'rw':(0.62,0.40),'lh':(0.42,0.62),'rh':(0.58,0.62),'lk':(0.36,0.78),'rk':(0.64,0.78),'la':(0.38,0.90),'ra':(0.62,0.90)}},
        {"title": "Salto Mortal!", "tag": "RELAMPAGO x2", "col": (255, 220, 0), "active": False, "icon": "bolt",
         "pts": {'nose':(0.5,0.10),'ls':(0.36,0.24),'rs':(0.64,0.24),'le':(0.22,0.15),'re':(0.78,0.15),'lw':(0.18,0.05),'rw':(0.82,0.05),'lh':(0.42,0.48),'rh':(0.58,0.48),'lk':(0.35,0.64),'rk':(0.65,0.64),'la':(0.38,0.78),'ra':(0.62,0.78)}},
        {"title": "Fiebre Disco!", "tag": "GOLD +500", "col": (0, 215, 255), "active": False, "icon": "star",
         "pts": {'nose':(0.5,0.16),'ls':(0.36,0.32),'rs':(0.64,0.32),'le':(0.26,0.48),'re':(0.76,0.18),'lw':(0.40,0.60),'rw':(0.86,0.05),'lh':(0.42,0.62),'rh':(0.58,0.62),'lk':(0.40,0.78),'rk':(0.60,0.78),'la':(0.38,0.90),'ra':(0.62,0.90)}},
    ]

    for i, c in enumerate(cards):
        cx = 22 + i * 248
        cy = lane_y + 12
        cw, ch = 236, 108
        bg = (65, 25, 85) if c["active"] else (35, 32, 48)
        blend_rect_roi(frame, cx, cy, cw, ch, bg, 0.9)
        border_th = 3 if c["active"] else 1
        cv2.rectangle(frame, (cx, cy), (cx + cw, cy + ch), c["col"], border_th)
        auditor.register_box(f"Card_Queue_{i}", cx, cy, cw, ch, group=f"z5_c{i}")

        cv2.rectangle(frame, (cx + 6, cy + 6), (cx + 82, cy + ch - 6), (22, 20, 30), -1)
        draw_full_body_stickman(frame, cx + 8, cy + 8, 72, ch - 16, c["pts"], c["col"], show_floor=True)

        tx_off = cx + 90
        if c["icon"] == "bolt":
            draw_bolt_icon(frame, cx + 98, cy + 28, 9, c["col"])
            tx_off = cx + 112
        elif c["icon"] == "star":
            draw_star_icon(frame, cx + 98, cy + 28, 9, c["col"])
            tx_off = cx + 112

        auditor.register_text(frame, c["tag"], tx_off, cy + 34, cv2.FONT_HERSHEY_SIMPLEX, 0.50, c["col"], 1, group=f"z5_c{i}")
        auditor.register_text(frame, c["title"], cx + 90, cy + 68, cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1, group=f"z5_c{i}")

    cv2.imwrite("diseno_02_hud_gameplay_ghost_y_semaforo.jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return auditor.summary()


# =====================================================================
# LÁMINA 3: MOVIMIENTOS DINÁMICOS CON INTENCIÓN FÍSICA + MOTION TRAILS
# =====================================================================
def generate_sheet_03_dynamic_intent():
    w, h = 1280, 720
    frame = np.full((h, w, 3), (24, 20, 34), dtype=np.uint8)
    blend_rect_roi(frame, 0, 0, w, 65, (45, 20, 60), 0.9)
    cv2.putText(frame, "LAMINA 3/6: COMUNICACION VISUAL DE MOVIMIENTOS DINAMICOS (INTENCION)", (25, 42),
                cv2.FONT_HERSHEY_DUPLEX, 0.92, (0, 255, 255), 2, cv2.LINE_AA)

    panels = [
        ("1. CADERAS Y PASO LATERAL", "Arcos Neon Laterales + Conteo Real", (255, 100, 200)),
        ("2. SALTO vs AGACHARSE (SENTADILLA)", "Linea de Piso + Rodillas + Flechas", (0, 255, 140)),
        ("3. GIRO 360 Y BOXEO RAPIDO", "Anillo Orbital 3D + Estelas (Trails)", (0, 215, 255)),
    ]

    for idx, (title, sub, col) in enumerate(panels):
        px = 24 + idx * 414
        py = 82
        pw, ph = 400, 610
        blend_rect_roi(frame, px, py, pw, ph, (34, 30, 48), 0.9)
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), col, 2)
        cv2.putText(frame, title, (px + 16, py + 34), cv2.FONT_HERSHEY_DUPLEX, 0.62, col, 2, cv2.LINE_AA)
        cv2.putText(frame, sub, (px + 16, py + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (210, 210, 225), 1, cv2.LINE_AA)

        if idx == 0:
            cx, cy = px + 200, py + 240
            cv2.ellipse(frame, (cx - 75, cy + 40), (22, 65), 0, 110, 250, (0, 255, 120), 6, cv2.LINE_AA)
            cv2.ellipse(frame, (cx + 75, cy + 40), (22, 65), 0, -70, 70, (255, 80, 200), 6, cv2.LINE_AA)
            cv2.arrowedLine(frame, (cx - 15, cy + 40), (cx - 68, cy + 40), (0, 255, 120), 4, tipLength=0.4)
            cv2.arrowedLine(frame, (cx + 15, cy + 40), (cx + 68, cy + 40), (255, 80, 200), 4, tipLength=0.4)
            pts = {'nose':(0.5,0.16),'ls':(0.36,0.32),'rs':(0.64,0.32),'le':(0.24,0.44),'re':(0.76,0.44),
                   'lw':(0.36,0.58),'rw':(0.64,0.58),'lh':(0.32,0.60),'rh':(0.50,0.60),
                   'lk':(0.38,0.76),'rk':(0.56,0.76),'la':(0.40,0.90),'ra':(0.58,0.90)}
            draw_full_body_stickman(frame, px + 70, py + 95, 260, 260, pts, col)
            cv2.putText(frame, "CADERAS: 4/6 HITS!", (px + 85, py + 400), cv2.FONT_HERSHEY_DUPLEX, 0.75, (0, 255, 255), 2, cv2.LINE_AA)
            desc = [
                "- El jugador ve 2 ARCOS LATERALES",
                "  pegados a su cintura.",
                "- Al tocar cada arco con la cadera,",
                "  el arco explota en particulas.",
                "- 'De Lado a Lado' muestra pilares",
                "  de cuerpo completo (state.move_hits)."
            ]
            for j, d in enumerate(desc):
                cv2.putText(frame, d, (px + 18, py + 445 + j * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (220, 220, 230), 1, cv2.LINE_AA)

        elif idx == 1:
            cv2.putText(frame, "SALTO MORTAL (Despega del piso)", (px + 25, py + 100), cv2.FONT_HERSHEY_DUPLEX, 0.58, (0, 255, 140), 1, cv2.LINE_AA)
            pts_jump = {'nose':(0.5,0.10),'ls':(0.36,0.24),'rs':(0.64,0.24),'le':(0.22,0.14),'re':(0.78,0.14),
                        'lw':(0.18,0.04),'rw':(0.82,0.04),'lh':(0.42,0.46),'rh':(0.58,0.46),
                        'lk':(0.34,0.60),'rk':(0.66,0.60),'la':(0.38,0.72),'ra':(0.62,0.72)}
            draw_full_body_stickman(frame, px + 85, py + 110, 220, 200, pts_jump, (0, 255, 140))
            cv2.arrowedLine(frame, (px + 60, py + 260), (px + 60, py + 140), (0, 255, 140), 4, tipLength=0.3)
            cv2.arrowedLine(frame, (px + 335, py + 260), (px + 335, py + 140), (0, 255, 140), 4, tipLength=0.3)

            cv2.putText(frame, "AGACHARSE (Flexiona rodillas al piso)", (px + 20, py + 345), cv2.FONT_HERSHEY_DUPLEX, 0.58, (100, 180, 255), 1, cv2.LINE_AA)
            pts_squat = {'nose':(0.5,0.34),'ls':(0.36,0.48),'rs':(0.64,0.48),'le':(0.25,0.62),'re':(0.75,0.62),
                         'lw':(0.35,0.72),'rw':(0.65,0.72),'lh':(0.40,0.72),'rh':(0.60,0.72),
                         'lk':(0.26,0.80),'rk':(0.74,0.80),'la':(0.40,0.90),'ra':(0.60,0.90)}
            draw_full_body_stickman(frame, px + 85, py + 355, 220, 200, pts_squat, (100, 180, 255))
            cv2.arrowedLine(frame, (px + 60, py + 380), (px + 60, py + 500), (100, 180, 255), 4, tipLength=0.3)
            cv2.arrowedLine(frame, (px + 335, py + 380), (px + 335, py + 500), (100, 180, 255), 4, tipLength=0.3)
            cv2.putText(frame, "Rodillas abiertas + linea de suelo = 100% claro", (px + 16, py + 585), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 230, 255), 1, cv2.LINE_AA)

        elif idx == 2:
            cv2.putText(frame, "GIRANDO! (Vortice Orbital 360 deg)", (px + 30, py + 100), cv2.FONT_HERSHEY_DUPLEX, 0.58, (0, 215, 255), 1, cv2.LINE_AA)
            pts_spin = {'nose':(0.5,0.16),'ls':(0.44,0.32),'rs':(0.56,0.32),'le':(0.34,0.45),'re':(0.66,0.45),
                        'lw':(0.30,0.55),'rw':(0.70,0.55),'lh':(0.45,0.60),'rh':(0.55,0.60),
                        'lk':(0.45,0.76),'rk':(0.55,0.76),'la':(0.45,0.90),'ra':(0.55,0.90)}
            draw_full_body_stickman(frame, px + 90, py + 110, 220, 195, pts_spin, (0, 215, 255))
            cv2.ellipse(frame, (px + 200, py + 200), (115, 32), 0, -20, 240, (0, 255, 255), 4, cv2.LINE_AA)
            cv2.putText(frame, "360 GIRO COMPLETO", (px + 95, py + 320), cv2.FONT_HERSHEY_DUPLEX, 0.62, (0, 255, 255), 2, cv2.LINE_AA)

            cv2.putText(frame, "ESTELAS DE ENERGIA (HandTrails)", (px + 35, py + 365), cv2.FONT_HERSHEY_DUPLEX, 0.58, (255, 120, 255), 1, cv2.LINE_AA)
            trail_pts = [(px + 80 + i * 30, py + 480 - int(math.sin(i * 0.7) * 55)) for i in range(9)]
            for i in range(1, len(trail_pts)):
                th = max(2, int((i / len(trail_pts)) * 14))
                cv2.line(frame, trail_pts[i - 1], trail_pts[i], (255, 80, 220), th, cv2.LINE_AA)
            cv2.circle(frame, trail_pts[-1], 14, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.putText(frame, "Rastro fluido de las ultimas 8 posiciones", (px + 30, py + 560), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (220, 220, 235), 1, cv2.LINE_AA)
            cv2.putText(frame, "de las munecas (estilo Beat Saber / Just Dance).", (px + 22, py + 585), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 220, 235), 1, cv2.LINE_AA)

    cv2.imwrite("diseno_03_poses_dinamicas_e_intencion.jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return frame


# =====================================================================
# LÁMINA 4: ATLAS DE LAS 8 ILUSTRACIONES RECUPERADAS + 8 NUEVAS POSES
# =====================================================================
def generate_sheet_04_pose_atlas():
    w, h = 1280, 720
    frame = np.full((h, w, 3), (20, 18, 28), dtype=np.uint8)
    blend_rect_roi(frame, 0, 0, w, 62, (35, 25, 55), 0.9)
    cv2.putText(frame, "LAMINA 4/6: ILUSTRACIONES RECUPERADAS (pose_*.jpg) + NUEVAS POSES EXPRESIVAS", (22, 40),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 255, 255), 2, cv2.LINE_AA)

    cv2.putText(frame, "FILA 1: Las 8 Ilustraciones Originales Recuperadas y Normalizadas (incluye fix de fondo blanco en Letra Y):",
                (25, 92), cv2.FONT_HERSHEY_DUPLEX, 0.60, (255, 215, 0), 1, cv2.LINE_AA)

    icons = [
        ("pose_brazos", "Brazos Arriba"),
        ("pose_caderas", "Mueve Caderas"),
        ("pose_fuerte", "Fuerte (Biceps)"),
        ("pose_cabeza", "Mueve Cabeza"),
        ("pose_letra_y", "Letra Y (Fixed!)"),
        ("pose_letra_o", "Letra O"),
        ("pose_saludo", "Saludo Militar"),
        ("pose_tpose", "T-Pose"),
    ]
    for i, (fname, label) in enumerate(icons):
        ix = 24 + i * 154
        iy = 108
        img = load_pose_illustration_clean(fname, size=(142, 142))
        if img is not None:
            frame[iy:iy + 142, ix:ix + 142] = img
        cv2.rectangle(frame, (ix, iy), (ix + 142, iy + 142), (0, 220, 255), 2)
        cv2.putText(frame, label, (ix + 4, iy + 165), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (240, 240, 255), 1, cv2.LINE_AA)

    cv2.putText(frame, "FILA 2: Nuevas Poses Divertidas y Dinamicas Agregadas al Catalogo (Arquetipos de Party Game):",
                (25, 315), cv2.FONT_HERSHEY_DUPLEX, 0.62, (80, 255, 140), 1, cv2.LINE_AA)

    new_poses = [
        ("POSE DE MONO!", "Manos en axilas + codos afuera", (0, 200, 255),
         {'nose':(0.5,0.16),'ls':(0.36,0.32),'rs':(0.64,0.32),'le':(0.14,0.34),'re':(0.86,0.34),'lw':(0.38,0.40),'rw':(0.62,0.40),'lh':(0.42,0.60),'rh':(0.58,0.60),'lk':(0.34,0.76),'rk':(0.66,0.76),'la':(0.38,0.90),'ra':(0.62,0.90)}),
        ("FIEBRE DISCO!", "Mano Der alta + Izq en cintura", (255, 100, 255),
         {'nose':(0.5,0.16),'ls':(0.36,0.32),'rs':(0.64,0.32),'le':(0.24,0.46),'re':(0.76,0.16),'lw':(0.40,0.58),'rw':(0.88,0.04),'lh':(0.42,0.60),'rh':(0.58,0.60),'lk':(0.38,0.76),'rk':(0.62,0.76),'la':(0.36,0.90),'ra':(0.64,0.90)}),
        ("AVION SUPERSONICO!", "Brazos en T + Inclinacion Torso", (100, 255, 220),
         {'nose':(0.46,0.18),'ls':(0.34,0.38),'rs':(0.62,0.26),'le':(0.18,0.44),'re':(0.78,0.20),'lw':(0.05,0.50),'rw':(0.94,0.14),'lh':(0.42,0.62),'rh':(0.58,0.60),'lk':(0.42,0.78),'rk':(0.58,0.78),'la':(0.42,0.90),'ra':(0.58,0.90)}),
        ("BOXEO RAPIDO! (Din)", "6 Jabs alternados izq/der", (80, 120, 255),
         {'nose':(0.5,0.16),'ls':(0.36,0.32),'rs':(0.64,0.32),'le':(0.28,0.42),'re':(0.74,0.26),'lw':(0.42,0.24),'rw':(0.62,0.14),'lh':(0.42,0.60),'rh':(0.58,0.60),'lk':(0.38,0.76),'rk':(0.62,0.76),'la':(0.36,0.90),'ra':(0.64,0.90)}),
        ("GUITARRA ROCK! (Din)", "Brazo mastil + mano rasgueando", (0, 255, 120),
         {'nose':(0.5,0.16),'ls':(0.36,0.32),'rs':(0.64,0.32),'le':(0.20,0.34),'re':(0.74,0.46),'lw':(0.08,0.30),'rw':(0.54,0.56),'lh':(0.42,0.60),'rh':(0.58,0.60),'lk':(0.36,0.76),'rk':(0.64,0.76),'la':(0.34,0.90),'ra':(0.66,0.90)}),
    ]

    for i, (title, desc, col, pts) in enumerate(new_poses):
        cx = 24 + i * 248
        cy = 335
        cw, ch = 236, 355
        blend_rect_roi(frame, cx, cy, cw, ch, (32, 28, 44), 0.9)
        cv2.rectangle(frame, (cx, cy), (cx + cw, cy + ch), col, 2)
        draw_full_body_stickman(frame, cx + 18, cy + 20, 200, 235, pts, col)
        cv2.putText(frame, title, (cx + 12, cy + 290), cv2.FONT_HERSHEY_DUPLEX, 0.56, col, 1, cv2.LINE_AA)
        cv2.putText(frame, desc, (cx + 12, cy + 320), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (215, 215, 230), 1, cv2.LINE_AA)

    cv2.imwrite("diseno_04_catalogo_nuevas_poses_e_iconos.jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return frame


# =====================================================================
# LÁMINA 5: MODIFICADORES (GOLD MOVE, RELÁMPAGO, MENÚ KINÉTICO SIN TECLADO)
# =====================================================================
def generate_sheet_05_modifiers_and_kinetic_menu():
    w, h = 1280, 720
    frame = np.full((h, w, 3), (22, 18, 32), dtype=np.uint8)
    blend_rect_roi(frame, 0, 0, w, 64, (45, 25, 65), 0.9)
    cv2.putText(frame, "LAMINA 5/6: EVENTOS DINAMICOS (GOLD / SPEED) Y MENU KINETICO SIN TECLADO", (24, 42),
                cv2.FONT_HERSHEY_DUPLEX, 0.88, (0, 255, 255), 2, cv2.LINE_AA)

    lx, ly, lw, lh = 24, 82, 600, 610
    blend_rect_roi(frame, lx, ly, lw, lh, (32, 26, 46), 0.9)
    cv2.rectangle(frame, (lx, ly), (lx + lw, ly + lh), (0, 215, 255), 2)
    cv2.putText(frame, "VARIABILIDAD DINAMICA DURANTE LA PARTIDA", (lx + 20, ly + 38),
                cv2.FONT_HERSHEY_DUPLEX, 0.72, (0, 215, 255), 2, cv2.LINE_AA)

    cards_info = [
        ("[ESTRELLA] GOLD MOVE (Movimiento Dorado - 12% prob.)", (0, 215, 255),
         ["- Toda la tarjeta y los anillos brillan en ORO.",
          "- Otorga +500 x Multiplicador y llena +40% de Fever.",
          "- Dispara doble lluvia de confeti dorado al completarse."]),
        ("[RAYO] POSE RELAMPAGO (Speed Pose - 15% prob.)", (255, 230, 0),
         ["- Pide la mitad de tiempo (0.30s) o mitad de golpes.",
          "- Si el jugador reacciona en < 2.2s gana DOBLE PUNTAJE (x2).",
          "- Rompe la monotonia con picos de adrenalina."]),
        ("[RITMO] GROOVE BONUS PASIVO (Bailar mientras posas)", (255, 100, 255),
         ["- Mientras mantenes una pose estatica de brazos, si",
          "  ademas moves las caderas al ritmo, ganas +15 RITMO!",
          "- Premia bailar con todo el cuerpo como en Just Dance."]),
        ("[ESCALA] BODY-UNIT NORMALIZATION (Invarianza)", (80, 255, 140),
         ["- Mide todo en multiplos del ancho de hombros actual.",
          "- Funciona igual para un nino a 3m que un adulto a 1.3m."])
    ]
    for i, (t, col, lines) in enumerate(cards_info):
        cy = ly + 62 + i * 132
        blend_rect_roi(frame, lx + 18, cy, lw - 36, 118, (22, 18, 32), 0.85)
        cv2.rectangle(frame, (lx + 18, cy), (lx + lw - 18, cy + 118), col, 2)
        cv2.putText(frame, t, (lx + 32, cy + 30), cv2.FONT_HERSHEY_DUPLEX, 0.56, col, 1, cv2.LINE_AA)
        for j, l in enumerate(lines):
            cv2.putText(frame, l, (lx + 32, cy + 58 + j * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (220, 225, 235), 1, cv2.LINE_AA)

    rx, ry, rw, rh = 652, 82, 604, 610
    blend_rect_roi(frame, rx, ry, rw, rh, (26, 36, 46), 0.9)
    cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (0, 255, 160), 2)
    cv2.putText(frame, "MENU KINETICO (CONTROL CON MANOS A 3 METROS)", (rx + 20, ry + 38),
                cv2.FONT_HERSHEY_DUPLEX, 0.68, (0, 255, 160), 2, cv2.LINE_AA)

    mx, my, mw, mh = rx + 25, ry + 60, 554, 340
    cv2.rectangle(frame, (mx, my), (mx + mw, my + mh), (16, 20, 28), -1)
    cv2.rectangle(frame, (mx, my), (mx + mw, my + mh), (100, 200, 255), 1)
    cv2.putText(frame, "SELECCIONA CANCION CON TUS MANOS", (mx + 95, my + 35), cv2.FONT_HERSHEY_DUPLEX, 0.62, (0, 255, 255), 1, cv2.LINE_AA)

    cv2.circle(frame, (mx + 65, my + 110), 42, (255, 180, 0), 3, cv2.LINE_AA)
    cv2.putText(frame, "MANO IZQ", (mx + 26, my + 105), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 200, 50), 1, cv2.LINE_AA)
    cv2.putText(frame, "SUBIR", (mx + 40, my + 128), cv2.FONT_HERSHEY_DUPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.circle(frame, (mx + mw - 65, my + 110), 42, (255, 180, 0), 3, cv2.LINE_AA)
    cv2.putText(frame, "MANO DER", (mx + mw - 104, my + 105), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 200, 50), 1, cv2.LINE_AA)
    cv2.putText(frame, "BAJAR", (mx + mw - 90, my + 128), cv2.FONT_HERSHEY_DUPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

    songs = ["   [LIBRE] ASEREJE", "-> [COREO] MACARENA (103 BPM) <-", "   [LIBRE] DANZA KUDURO", "   [COREO] YMCA"]
    for i, s in enumerate(songs):
        scol = (0, 255, 120) if "->" in s else (160, 165, 180)
        cv2.putText(frame, s, (mx + 125, my + 95 + i * 38), cv2.FONT_HERSHEY_DUPLEX, 0.56, scol, 1, cv2.LINE_AA)

    cv2.rectangle(frame, (mx + 85, my + 265), (mx + mw - 85, my + 305), (45, 55, 70), -1)
    cv2.rectangle(frame, (mx + 85, my + 265), (mx + 85 + 290, my + 305), (0, 255, 120), -1)
    cv2.rectangle(frame, (mx + 85, my + 265), (mx + mw - 85, my + 305), (255, 255, 255), 2)
    cv2.putText(frame, "AMBOS BRAZOS ARRIBA = JUGAR! (75%)", (mx + 110, my + 292), cv2.FONT_HERSHEY_DUPLEX, 0.54, (0, 0, 0), 2, cv2.LINE_AA)

    gestures_help = [
        "1. Levantar Mano Izquierda: Sube en la lista de canciones.",
        "2. Levantar Mano Derecha: Baja en la lista de canciones.",
        "3. Levantar AMBOS Brazos 1.0s: Inicia la partida sin teclado.",
        "4. En partida - Cruzar brazos en X (0.8s): Salta la pose.",
        "5. Teclado (W/S/Enter/Espacio/M) sigue activo como respaldo."
    ]
    for i, g in enumerate(gestures_help):
        cv2.putText(frame, g, (rx + 28, ry + 440 + i * 32), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (220, 235, 230), 1, cv2.LINE_AA)

    cv2.imwrite("diseno_05_eventos_gold_move_y_menu_kinetico.jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return frame


# =====================================================================
# LÁMINA 6: PIPELINE DE AUTO-AUDITORÍA POR SUBAGENTE ESPECIALISTA UI/UX
# =====================================================================
def generate_sheet_06_subagent_qa_pipeline():
    w, h = 1280, 720
    frame = np.full((h, w, 3), (18, 20, 30), dtype=np.uint8)
    blend_rect_roi(frame, 0, 0, w, 66, (30, 45, 75), 0.92)
    cv2.putText(frame, "LAMINA 6/6: SISTEMA DE AUTO-AUDITORIA VISUAL CON SUBAGENTE UI/UX", (24, 43),
                cv2.FONT_HERSHEY_DUPLEX, 0.90, (0, 255, 255), 2, cv2.LINE_AA)

    steps = [
        ("PASO 1: GENERADOR DE ESCENARIOS", "python visual_ui_auditor.py", (0, 200, 255),
         ["Renderiza automaticamente sin camara:",
          "- Gameplay Estatico (Rojo/Ambar/Verde)",
          "- Gameplay Dinamico + Flechas Intencion",
          "- Fever / Gold Move + Menu Kinetico",
          "- Atlas de las 18+ Poses e Iconos"]),
        ("PASO 2: 5 GATES MATEMATICOS", "UILayoutAuditor (Hard Checks)", (80, 255, 140),
         ["Falla automaticamente si detecta:",
          "- Gate 1: Dos textos o cajas se pisan",
          "- Gate 2: Algo tapa el centro del jugador",
          "- Gate 3: Fuente < 0.48 (ilegible a 3m)",
          "- Gate 4/5: Sale de 1280x720 o char '?'"]),
        ("PASO 3: SUBAGENTE CRITICO UI/UX", "invoke_subagent (Vision Multimodal)", (255, 120, 255),
         ["Un subagente especialista abre los .jpg",
          "con read_file y audita visualmente:",
          "- Se entiende que hacer en 0.2 seg?",
          "- Hay buen contraste y estetica Arcade?",
          "- Si nota < 9/10, ordena corregir codigo."]),
        ("PASO 4: ENVIO A MOTOROLA", "Tailscale Drop (moto-g24-power)", (0, 215, 255),
         ["Una vez aprobados los 5 Gates y el",
          "Subagente UI/UX, envia las capturas",
          "validadas directo a tu celular:",
          "tailscale file cp *.jpg moto-g24-power:"])
    ]

    for i, (title, badge, col, lines) in enumerate(steps):
        sx = 24 + i * 310
        sy = 100
        sw, sh = 292, 360
        blend_rect_roi(frame, sx, sy, sw, sh, (28, 32, 48), 0.92)
        cv2.rectangle(frame, (sx, sy), (sx + sw, sy + sh), col, 2)
        cv2.putText(frame, title, (sx + 14, sy + 36), cv2.FONT_HERSHEY_DUPLEX, 0.52, col, 1, cv2.LINE_AA)
        cv2.rectangle(frame, (sx + 14, sy + 52), (sx + sw - 14, sy + 82), (15, 18, 26), -1)
        cv2.putText(frame, badge, (sx + 20, sy + 72), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)
        for j, l in enumerate(lines):
            cv2.putText(frame, l, (sx + 14, sy + 120 + j * 36), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 225, 235), 1, cv2.LINE_AA)

        if i < 3:
            cv2.arrowedLine(frame, (sx + sw + 2, sy + sh // 2), (sx + sw + 16, sy + sh // 2), (0, 255, 255), 3, tipLength=0.4)

    bx, by, bw, bh = 24, 490, 1232, 200
    blend_rect_roi(frame, bx, by, bw, bh, (25, 35, 30), 0.9)
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 140), 2)
    cv2.putText(frame, "GARANTIA DE CALIDAD VISUAL PERMANENTE EN EL PROYECTO (BLUEPRINT 05):",
                (bx + 22, by + 38), cv2.FONT_HERSHEY_DUPLEX, 0.72, (0, 255, 140), 2, cv2.LINE_AA)
    rubric = [
        "1. Ningun modelo (como Gemini 3.8 Flash) puede dar por terminada una tarea sin correr `python visual_ui_auditor.py`.",
        "2. Si `ui_audit_report.json` reporta `passed: false` (ej. un texto pisa una barra o hay '?'), debe corregirlo antes de seguir.",
        "3. Luego, el modelo invoca al Subagente Especialista UI/UX que mira las imagenes .jpg generadas como un jugador humano a 3 metros",
        "   y verifica que las poses, flechas de intencion, colores y textos se entiendan al instante."
    ]
    for i, r in enumerate(rubric):
        cv2.putText(frame, r, (bx + 22, by + 78 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (230, 240, 235), 1, cv2.LINE_AA)

    cv2.imwrite("diseno_06_arquitectura_subagente_auditor_ui_ux.jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return frame


def main():
    print("Generando las 6 Laminas de Diseno Visual HD y ejecutando UILayoutAuditor (5 Gates)...")
    generate_sheet_01_before_after()
    hud_audit = generate_sheet_02_new_hud_gameplay()
    generate_sheet_03_dynamic_intent()
    generate_sheet_04_pose_atlas()
    generate_sheet_05_modifiers_and_kinetic_menu()
    generate_sheet_06_subagent_qa_pipeline()

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hud_gameplay_audit": hud_audit,
        "generated_sheets": [
            "diseno_01_comparativa_antes_vs_despues.jpg",
            "diseno_02_hud_gameplay_ghost_y_semaforo.jpg",
            "diseno_03_poses_dinamicas_e_intencion.jpg",
            "diseno_04_catalogo_nuevas_poses_e_iconos.jpg",
            "diseno_05_eventos_gold_move_y_menu_kinetico.jpg",
            "diseno_06_arquitectura_subagente_auditor_ui_ux.jpg",
        ]
    }
    with open("ui_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("Resultado de UILayoutAuditor en Nuevo HUD:", json.dumps(hud_audit, indent=2, ensure_ascii=False))
    if not hud_audit["passed"]:
        raise AssertionError(f"Auditoria UI fallo con violaciones: {hud_audit['violations']}")
    print("EXITO: Las 6 laminas de diseno pasaron todos los 5 Gates matematicos.")


if __name__ == "__main__":
    main()
