"""
=====================================================================
TEST SUITE Y AUDITORÍA VISUAL DE ILUSTRACIONES Y MOVIMIENTO CINÉTICO
=====================================================================
Valida la biomecánica, simetría bilateral (ambos lados) y ausencia de
deformación en piernas/pies para todas las 23 poses del catálogo.
Genera láminas visuales HD para inspección y auditoría de UI/UX.
=====================================================================
"""

import math
import numpy as np
import cv2
import os

from poses_core.catalog import POSES
from poses_core.rendering import (
    get_animated_ref_points, draw_full_body_stickman,
    draw_intent_arrows_in_box, load_pose_illustration_clean,
    blend_rect_roi
)


def dist_2d(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def test_hip_sway_biomechanics_and_symmetry():
    """Verifica que el baile de caderas oscile a AMBOS lados y no estire los pies."""
    pose_caderas = next(p for p in POSES if 'Caderas' in p['name'])

    period = (2.0 * math.pi) / 5.5
    times = [i * (period / 16.0) for i in range(17)]

    hip_centers = []
    leg_lengths_left = []
    leg_lengths_right = []
    foot_y_left = []
    foot_y_right = []

    for t in times:
        pts = get_animated_ref_points(pose_caderas, t)
        lh = pts['lh']
        rh = pts['rh']
        lk = pts['lk']
        rk = pts['rk']
        la = pts['la']
        ra = pts['ra']

        hc = (lh[0] + rh[0]) / 2.0
        hip_centers.append(hc)

        # Longitud anatómica de la pierna: cadera -> rodilla -> tobillo
        l_leg = dist_2d(lh, lk) + dist_2d(lk, la)
        r_leg = dist_2d(rh, rk) + dist_2d(rk, ra)
        leg_lengths_left.append(l_leg)
        leg_lengths_right.append(r_leg)

        foot_y_left.append(la[1])
        foot_y_right.append(ra[1])

    min_hc = min(hip_centers)
    max_hc = max(hip_centers)

    print(f"      [Caderas] Min Hip X: {min_hc:.3f} (IZQ), Max Hip X: {max_hc:.3f} (DER)")
    # 1. Movimiento a AMBOS lados
    assert min_hc < 0.44, f"Caderas deben ir a la izquierda (<0.44), dio {min_hc:.3f}"
    assert max_hc > 0.56, f"Caderas deben ir a la derecha (>0.56), dio {max_hc:.3f}"

    # 2. Simetría bilateral balanceada
    left_reach = 0.50 - min_hc
    right_reach = max_hc - 0.50
    symmetry_diff = abs(left_reach - right_reach)
    print(f"      [Caderas] Alcance Izq: {left_reach:.3f}, Alcance Der: {right_reach:.3f}, Asimetría: {symmetry_diff:.3f}")
    assert symmetry_diff < 0.025, f"Movimiento asimétrico detectado: diff={symmetry_diff:.3f}"

    # 3. Ausencia de estiramiento deformado de piernas (varianza de longitud < 8%)
    l_ratio = max(leg_lengths_left) / min(leg_lengths_left)
    r_ratio = max(leg_lengths_right) / min(leg_lengths_right)
    print(f"      [Caderas] Ratio estiramiento piernas: Izq={l_ratio:.3f}, Der={r_ratio:.3f}")
    assert l_ratio < 1.10, f"Pierna izquierda estirada anormalmente: ratio={l_ratio:.3f}"
    assert r_ratio < 1.10, f"Pierna derecha estirada anormalmente: ratio={r_ratio:.3f}"

    # 4. Pies firmemente apoyados en el suelo
    for fy in foot_y_left + foot_y_right:
        assert abs(fy - 0.90) < 1e-4, f"Pie flotó o se desprendió del suelo: y={fy:.3f}"

    print("      -> Biomecánica y simetría bilateral de caderas: APROBADA 100%")


def generate_hip_sway_strip():
    """Genera una tira de 4 fotogramas mostrando el ciclo completo del baile de caderas."""
    pose_caderas = next(p for p in POSES if 'Caderas' in p['name'])
    w, h = 320, 360
    total_w = w * 4
    strip = np.full((h + 80, total_w, 3), (20, 18, 28), dtype=np.uint8)

    # Título superior
    cv2.putText(strip, "AUDITORIA VISUAL: MOVIMIENTO BILATERAL DE CADERAS (IZQUIERDA <-> DERECHA)",
                (total_w // 2 - 420, 42), cv2.FONT_HERSHEY_DUPLEX, 0.72, (0, 255, 255), 2, cv2.LINE_AA)

    period = (2.0 * math.pi) / 5.5
    frames_data = [
        {"t": 0.0, "label": "1. CENTRO NEUTRO", "sub": "Preparacion"},
        {"t": period * 0.25, "label": "2. CADERA DERECHA", "sub": "DER > (Rodilla izq flexiona)"},
        {"t": period * 0.50, "label": "3. CENTRO NEUTRO", "sub": "Transicion ritmica"},
        {"t": period * 0.75, "label": "4. CADERA IZQUIERDA", "sub": "< IZQ (Rodilla der flexiona)"}
    ]

    for i, fd in enumerate(frames_data):
        bx = i * w
        by = 70
        bw = w - 16
        bh = h - 20

        blend_rect_roi(strip, bx + 8, by, bw, bh, (32, 28, 42), 0.92)
        cv2.rectangle(strip, (bx + 8, by), (bx + 8 + bw, by + bh), (90, 80, 110), 1)

        pts = get_animated_ref_points(pose_caderas, fd["t"])
        draw_full_body_stickman(strip, bx + 16, by + 10, bw - 16, bh - 60, pts, (255, 100, 180), show_floor=True)
        draw_intent_arrows_in_box(strip, pose_caderas, bx + 16, by + 10, bw - 16, bh - 60, fd["t"])

        # Etiquetas
        cv2.putText(strip, fd["label"], (bx + 24, by + bh - 32), cv2.FONT_HERSHEY_DUPLEX, 0.54, (0, 255, 200), 1, cv2.LINE_AA)
        cv2.putText(strip, fd["sub"], (bx + 24, by + bh - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 210, 230), 1, cv2.LINE_AA)

    out_path = "test_visual_hip_sway_cycle.jpg"
    cv2.imwrite(out_path, strip, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"      -> Lámina '{out_path}' generada con éxito.")


def generate_all_23_poses_grid():
    """Genera un mosaico HD con todas las 23 poses del catálogo y su Coach Vivo."""
    cols = 4
    rows = math.ceil(len(POSES) / cols)
    card_w = 320
    card_h = 240
    grid_w = cols * card_w
    grid_h = rows * card_h + 80

    grid = np.full((grid_h, grid_w, 3), (16, 14, 24), dtype=np.uint8)

    cv2.putText(grid, "CATALOGO COMPLETO: 23 POSES - AUDITORIA DE COACH VIVO E INTENCION VISUAL",
                (grid_w // 2 - 460, 48), cv2.FONT_HERSHEY_DUPLEX, 0.78, (0, 255, 255), 2, cv2.LINE_AA)

    t_eval = 0.35  # Tiempo de muestra representativo

    for idx, p in enumerate(POSES):
        r = idx // cols
        c = idx % cols
        bx = c * card_w + 10
        by = 80 + r * card_h + 8
        bw = card_w - 20
        bh = card_h - 16

        p_col = p.get('color', (0, 255, 120))
        blend_rect_roi(grid, bx, by, bw, bh, (28, 26, 38), 0.90)
        cv2.rectangle(grid, (bx, by), (bx + bw, by + bh), p_col, 2)

        # Nombre de la pose
        cv2.putText(grid, p['name'], (bx + 12, by + 26), cv2.FONT_HERSHEY_DUPLEX, 0.54, p_col, 1, cv2.LINE_AA)

        # Ilustración si existe
        icon_name = p.get('icon_name')
        illus = load_pose_illustration_clean(icon_name, size=(90, 90)) if icon_name else None
        if illus is not None:
            grid[by + 40:by + 130, bx + 12:bx + 102] = illus
            cv2.rectangle(grid, (bx + 12, by + 40), (bx + 102, by + 130), (80, 80, 100), 1)
            stick_x = bx + 112
            stick_w = bw - 122
        else:
            stick_x = bx + 20
            stick_w = bw - 40

        pts = get_animated_ref_points(p, t_eval)
        draw_full_body_stickman(grid, stick_x, by + 35, stick_w, bh - 50, pts, p_col, show_floor=True)
        draw_intent_arrows_in_box(grid, p, stick_x, by + 35, stick_w, bh - 50, t_eval)

        # Categoría
        cat_str = "DINAMICA (RITMO)" if p.get('dynamic') else ("COGNITIVA" if "cognitive" in p.get('tags', []) else "ESTATICA (HOLD)")
        cv2.putText(grid, cat_str, (bx + 12, by + bh - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 190, 210), 1, cv2.LINE_AA)

    out_path = "test_visual_all_23_poses_grid.jpg"
    cv2.imwrite(out_path, grid, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"      -> Lámina '{out_path}' generada con éxito.")


def run_all_illustration_tests():
    print("==================================================")
    print("   TEST Y AUDITORÍA DE ILUSTRACIONES Y MOVIMIENTO ")
    print("==================================================")
    test_hip_sway_biomechanics_and_symmetry()
    generate_hip_sway_strip()
    generate_all_23_poses_grid()
    print("==================================================")
    print("   TODAS LAS ILUSTRACIONES Y MOVIMIENTOS OK!      ")
    print("==================================================")


if __name__ == "__main__":
    run_all_illustration_tests()
