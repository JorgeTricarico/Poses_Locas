"""
=====================================================================
POSES LOCAS - SISTEMA DE FEATURES DESACOPLADAS Y TOGGLES
=====================================================================
Módulo con las extensiones avanzadas del juego:
  1. FeatureFlags: Toggles globales (por defecto TODOS desactivados).
  2. DuoModeManager: Modo multijugador local / cooperativo 2 jugadores.
  3. CustomGhostRenderer: Silueta Ghost AR personalizada (auras y temas neón).
  4. AudioReactiveEngine: Visuales reactivos al audio y ritmo (BPM spectrum).
  5. PartyPlatformEngine: Minijuego "Gran Salto Party / Plataforma de Movimiento".
=====================================================================
"""

import os
import math
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from .geometry import (
    NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST,
    L_HIP, R_HIP, get_body_unit, score_to_traffic_color, score_arm
)
from .state import PlayerState
from .rendering import blend_rect_roi, draw_full_body_stickman, get_animated_ref_points


class FeatureFlags:
    """
    Gestor centralizado de Feature Flags.
    Por directiva del diseño y especificación, todas las features
    están estrictamente DESACTIVADAS (False) por defecto.
    """

    def __init__(self):
        # Todos los flags inician en False por defecto.
        # Permiten override por variables de entorno si se configuran explícitamente.
        self.enable_duo_mode: bool = os.environ.get("POSES_ENABLE_DUO", "0").strip() == "1"
        self.enable_custom_ghost: bool = os.environ.get("POSES_ENABLE_CUSTOM_GHOST", "0").strip() == "1"
        self.enable_reactive_audio: bool = os.environ.get("POSES_ENABLE_REACTIVE_AUDIO", "0").strip() == "1"
        self.enable_party_platform: bool = os.environ.get("POSES_ENABLE_PARTY_PLATFORM", "0").strip() == "1"

    def toggle_duo_mode(self) -> bool:
        self.enable_duo_mode = not self.enable_duo_mode
        return self.enable_duo_mode

    def toggle_custom_ghost(self) -> bool:
        self.enable_custom_ghost = not self.enable_custom_ghost
        return self.enable_custom_ghost

    def toggle_reactive_audio(self) -> bool:
        self.enable_reactive_audio = not self.enable_reactive_audio
        return self.enable_reactive_audio

    def toggle_party_platform(self) -> bool:
        self.enable_party_platform = not self.enable_party_platform
        return self.enable_party_platform

    def reset_all(self):
        """Desactiva todas las features restaurando el estado por defecto."""
        self.enable_duo_mode = False
        self.enable_custom_ghost = False
        self.enable_reactive_audio = False
        self.enable_party_platform = False

    def as_dict(self) -> Dict[str, bool]:
        return {
            "duo_mode": self.enable_duo_mode,
            "custom_ghost": self.enable_custom_ghost,
            "reactive_audio": self.enable_reactive_audio,
            "party_platform": self.enable_party_platform
        }


# Instancia singleton global
FEATURES = FeatureFlags()


# =====================================================================
# 1. MODO DÚO (2 JUGADORES / MULTIJUGADOR LOCAL)
# =====================================================================

class DuoModeManager:
    """
    Gestiona el seguimiento, evaluación concurrente y scoring de dos jugadores.
    Permite modos cooperativo y versus con bonificación por sincronización perfecta.
    """

    def __init__(self):
        self.state_p1 = PlayerState()
        self.state_p2 = PlayerState()
        self.score_p1 = 0
        self.score_p2 = 0
        self.streak_p1 = 0
        self.streak_p2 = 0
        self.hold_progress_p1 = 0.0
        self.hold_progress_p2 = 0.0
        self.sync_streak = 0
        self.total_synced_poses = 0
        self.last_sync_time = 0.0

    def reset(self):
        self.state_p1.reset()
        self.state_p2.reset()
        self.score_p1 = 0
        self.score_p2 = 0
        self.streak_p1 = 0
        self.streak_p2 = 0
        self.hold_progress_p1 = 0.0
        self.hold_progress_p2 = 0.0
        self.sync_streak = 0

    def evaluate_players(
        self,
        current_pose: Dict[str, Any],
        lm_p1: Optional[List[Any]],
        lm_p2: Optional[List[Any]],
        dt: float,
        current_time: float
    ) -> Tuple[bool, float, bool, float, bool, List[Dict[str, Any]]]:
        """
        Evalúa a P1 y P2 sobre la pose actual.
        Retorna:
          (p1_ok, p1_score, p2_ok, p2_score, is_synced, events)
        """
        events = []
        p1_ok, p2_ok = False, False
        p1_score, p2_score = 0.0, 0.0

        if not current_pose or current_pose.get('is_freeze') or current_pose.get('dynamic'):
            # En poses dinámicas o congelados se evalúa por estado
            return False, 0.0, False, 0.0, False, []

        checks = current_pose.get('checks', {})
        left_check = checks.get('left_arm')
        right_check = checks.get('right_arm')

        # Evaluar Jugador 1
        if lm_p1 and left_check and right_check:
            l_ok = left_check(lm_p1)
            r_ok = right_check(lm_p1)
            p1_ok = l_ok and r_ok
            p1_score = (score_arm(left_check, lm_p1) + score_arm(right_check, lm_p1)) / 2.0
            if p1_ok:
                self.hold_progress_p1 = min(1.0, self.hold_progress_p1 + dt / 0.55)
            else:
                self.hold_progress_p1 = max(0.0, self.hold_progress_p1 - 0.9 * dt)
        else:
            self.hold_progress_p1 = max(0.0, self.hold_progress_p1 - 0.9 * dt)

        # Evaluar Jugador 2
        if lm_p2 and left_check and right_check:
            l_ok2 = left_check(lm_p2)
            r_ok2 = right_check(lm_p2)
            p2_ok = l_ok2 and r_ok2
            p2_score = (score_arm(left_check, lm_p2) + score_arm(right_check, lm_p2)) / 2.0
            if p2_ok:
                self.hold_progress_p2 = min(1.0, self.hold_progress_p2 + dt / 0.55)
            else:
                self.hold_progress_p2 = max(0.0, self.hold_progress_p2 - 0.9 * dt)
        else:
            self.hold_progress_p2 = max(0.0, self.hold_progress_p2 - 0.9 * dt)

        # Chequeo de sincronización cooperativa
        is_synced = False
        if p1_ok and p2_ok:
            is_synced = True
            if current_time - self.last_sync_time > 1.0 and (self.hold_progress_p1 > 0.8 and self.hold_progress_p2 > 0.8):
                self.sync_streak += 1
                self.total_synced_poses += 1
                self.last_sync_time = current_time
                bonus = 300 * self.sync_streak
                self.score_p1 += bonus
                self.score_p2 += bonus
                events.append({
                    "type": "sync_bonus",
                    "text": f"SINCRONIA COOP! +{bonus}",
                    "sync_streak": self.sync_streak
                })

        return p1_ok, p1_score, p2_ok, p2_score, is_synced, events

    def draw_duo_hud(self, frame: np.ndarray, w: int, h: int):
        """Dibuja el HUD dual en pantalla (P1 Azul Neón a la izquierda, P2 Magenta a la derecha)."""
        # P1 HUD (Izquierda)
        blend_rect_roi(frame, 20, 156, 260, 58, (25, 18, 12), 0.82)
        cv2.rectangle(frame, (20, 156), (280, 214), (255, 200, 0), 2)
        cv2.putText(frame, "JUGADOR 1 (AZUL)", (32, 178), cv2.FONT_HERSHEY_DUPLEX, 0.52, (255, 220, 50), 1, cv2.LINE_AA)
        cv2.putText(frame, f"PTS: {self.score_p1:,} | HOLD: {int(self.hold_progress_p1*100)}%", (32, 202), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

        # P2 HUD (Derecha)
        blend_rect_roi(frame, w - 280, 156, 260, 58, (25, 12, 24), 0.82)
        cv2.rectangle(frame, (w - 280, 156), (w - 20, 214), (255, 60, 240), 2)
        cv2.putText(frame, "JUGADOR 2 (MAGENTA)", (w - 268, 178), cv2.FONT_HERSHEY_DUPLEX, 0.52, (255, 120, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"PTS: {self.score_p2:,} | HOLD: {int(self.hold_progress_p2*100)}%", (w - 268, 202), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

        # Badge Central de Cooperativo / Sincronización
        if self.sync_streak > 0:
            blend_rect_roi(frame, w // 2 - 120, 124, 240, 32, (15, 10, 30), 0.85)
            cv2.rectangle(frame, (w // 2 - 120, 124), (w // 2 + 120, 156), (0, 255, 255), 1)
            cv2.putText(frame, f"SYNC COOP x{self.sync_streak}!", (w // 2 - 80, 146), cv2.FONT_HERSHEY_DUPLEX, 0.54, (0, 255, 255), 1, cv2.LINE_AA)


# =====================================================================
# 2. SILUETA GHOST PERSONALIZADA (CUSTOM GHOST SILHOUETTE)
# =====================================================================

class CustomGhostRenderer:
    """
    Renderizador de siluetas Ghost AR con temas visuales personalizables,
    adaptación antropométrica dinámica y auras de neón pulsantes.
    """

    THEMES = {
        "CYBERPUNK": {
            "name": "Cyberpunk Neon",
            "outline": (255, 0, 255),      # Magenta neón
            "accent": (0, 255, 255),       # Cian neón
            "glow_alpha": 0.35
        },
        "GOLDEN": {
            "name": "Sunset Gold",
            "outline": (0, 215, 255),      # Dorado
            "accent": (255, 255, 255),     # Blanco brillante
            "glow_alpha": 0.40
        },
        "MATRIX": {
            "name": "Matrix Bio-Green",
            "outline": (0, 255, 60),       # Verde neón
            "accent": (80, 255, 140),      # Verde claro
            "glow_alpha": 0.30
        },
        "HOLO_BLUE": {
            "name": "Hologram Blue",
            "outline": (255, 200, 0),      # Azul cobalto
            "accent": (255, 255, 200),     # Azul glacial
            "glow_alpha": 0.35
        }
    }

    def __init__(self, theme_key: str = "CYBERPUNK"):
        self.theme_key = theme_key if theme_key in self.THEMES else "CYBERPUNK"

    def set_theme(self, theme_key: str):
        if theme_key in self.THEMES:
            self.theme_key = theme_key

    def get_theme(self) -> Dict[str, Any]:
        return self.THEMES[self.theme_key]

    def render_custom_ghost(
        self,
        frame: np.ndarray,
        lm: List[Any],
        pose: Dict[str, Any],
        w: int,
        h: int,
        left_score: float,
        right_score: float,
        current_time: float,
        pulse_bpm: float = 120.0
    ):
        """
        Dibuja una silueta Ghost personalizada adaptada al body_unit y altura del jugador,
        con aura exterior de neón y estilo temático.
        """
        if not lm or len(lm) < 25:
            return

        theme = self.get_theme()
        body_unit = get_body_unit(lm)
        l_sh = lm[L_SHOULDER]
        r_sh = lm[R_SHOULDER]
        hip_mid_x = (lm[L_HIP].x + lm[R_HIP].x) / 2.0
        sh_mid_x = (l_sh.x + r_sh.x) / 2.0
        sh_mid_y = (l_sh.y + r_sh.y) / 2.0

        # Pulso rítmico suave de respiración
        beat_interval = 60.0 / max(60.0, pulse_bpm)
        phase = (current_time % beat_interval) / beat_interval
        pulse = 1.0 + 0.06 * math.sin(phase * 2 * math.pi)

        # Proyección adaptativa
        cx = int(sh_mid_x * w)
        cy = int(sh_mid_y * h)
        radius = max(8, int(body_unit * w * 0.16 * pulse))

        # Aura neón concéntrica difusa
        glow_col = theme["outline"]
        cv2.circle(frame, (cx, cy), radius + 10, glow_col, 1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), radius + 6, theme["accent"], 2, cv2.LINE_AA)

        # Anillos magnéticos en objetivos de muñecas con color de semáforo
        ref_pts = get_animated_ref_points(pose, current_time)
        lw_ref = ref_pts.get("L_WRIST", (0.35, 0.45))
        rw_ref = ref_pts.get("R_WRIST", (0.65, 0.45))

        # Re-centrar objetivos sobre el centroide del jugador
        lw_tx = int((hip_mid_x + (lw_ref[0] - 0.5) * (body_unit / 0.24)) * w)
        lw_ty = int((sh_mid_y + (lw_ref[1] - 0.35) * (body_unit / 0.24)) * h)
        rw_tx = int((hip_mid_x + (rw_ref[0] - 0.5) * (body_unit / 0.24)) * w)
        rw_ty = int((sh_mid_y + (rw_ref[1] - 0.35) * (body_unit / 0.24)) * h)

        col_l = score_to_traffic_color(left_score)
        col_r = score_to_traffic_color(right_score)

        # Trazos holográficos punteados hacia el objetivo
        p_lw = (int(lm[L_WRIST].x * w), int(lm[L_WRIST].y * h))
        p_rw = (int(lm[R_WRIST].x * w), int(lm[R_WRIST].y * h))
        cv2.line(frame, p_lw, (lw_tx, lw_ty), col_l, 1, cv2.LINE_AA)
        cv2.line(frame, p_rw, (rw_tx, rw_ty), col_r, 1, cv2.LINE_AA)

        # Anillos concéntricos neón
        for r_step in [14, 22]:
            cv2.circle(frame, (lw_tx, lw_ty), int(r_step * pulse), col_l, 2, cv2.LINE_AA)
            cv2.circle(frame, (rw_tx, rw_ty), int(r_step * pulse), col_r, 2, cv2.LINE_AA)


# =====================================================================
# 3. AUDIO REACTIVO (AUDIO REACTIVE ENGINE)
# =====================================================================

class AudioReactiveEngine:
    """
    Sincroniza y modula elementos visuales en base al pulso de ritmo (BPM),
    simulación espectral de frecuencias y picos de bombo/bajos.
    """

    def __init__(self, bpm: float = 120.0):
        self.bpm = bpm
        self.beat_energy = 0.0
        self.frequency_bands = [0.0] * 8
        self.last_update_time = 0.0

    def update(self, current_time: float, bpm: Optional[float] = None, is_playing: bool = True):
        if bpm:
            self.bpm = max(60.0, bpm)

        dt = current_time - self.last_update_time if self.last_update_time > 0 else 0.033
        self.last_update_time = current_time

        if not is_playing:
            self.beat_energy = max(0.0, self.beat_energy - 3.0 * dt)
            self.frequency_bands = [max(0.0, b - 2.5 * dt) for b in self.frequency_bands]
            return

        # Pulso rítmico derivado de BPM (ataque instantáneo y caída exponencial)
        beat_interval = 60.0 / self.bpm
        beat_phase = (current_time % beat_interval) / beat_interval
        # Sharp transient on beat
        if beat_phase < 0.12:
            target_energy = 1.0 - (beat_phase / 0.12) * 0.4
        else:
            target_energy = max(0.0, 0.6 * math.exp(-(beat_phase - 0.12) * 4.5))

        self.beat_energy = self.beat_energy * 0.3 + target_energy * 0.7

        # Modulación de 8 bandas de frecuencias
        for i in range(8):
            harmonic = math.sin(current_time * (self.bpm / 60.0) * (i + 1) * 1.5)
            band_val = self.beat_energy * (0.5 + 0.5 * harmonic)
            self.frequency_bands[i] = max(0.05, min(1.0, band_val))

    def draw_reactive_visuals(self, frame: np.ndarray, w: int, h: int):
        """Dibuja barras espectrales en las esquinas inferiores sin obstruir el gameplay."""
        # Esquina inferior izquierda (Bandas de bajos)
        bar_w = 10
        gap = 4
        base_x = 24
        base_y = h - 140

        for i, val in enumerate(self.frequency_bands[:4]):
            bx = base_x + i * (bar_w + gap)
            bh = int(36 * val)
            by = base_y - bh
            color = (0, int(200 + 55 * val), int(255 * val))
            cv2.rectangle(frame, (bx, by), (bx + bar_w, base_y), color, -1)

        # Esquina inferior derecha (Bandas de agudos)
        base_xr = w - 24 - 4 * (bar_w + gap)
        for i, val in enumerate(self.frequency_bands[4:]):
            bx = base_xr + i * (bar_w + gap)
            bh = int(36 * val)
            by = base_y - bh
            color = (int(255 * val), 50, int(220 + 35 * val))
            cv2.rectangle(frame, (bx, by), (bx + bar_w, base_y), color, -1)


# =====================================================================
# 4. GRAN SALTO PARTY / PLATAFORMA DE MOVIMIENTO PARTY
# =====================================================================

class PartyPlatformEngine:
    """
    Minijuego de fiesta interactivo:
    Una plataforma móvil o barrera láser se desplaza por el escenario.
    Los jugadores deben realizar un salto físico sincronizado cuando
    la plataforma alcanza la 'ZONA DE IMPACTO'.
    """

    def __init__(self, speed: float = 380.0):
        self.speed = speed
        self.platform_x = 0.0
        self.direction = 1  # 1: derecha, -1: izquierda
        self.consecutive_jumps = 0
        self.total_jumps = 0
        self.last_jump_time = 0.0
        self.cleared_this_pass = False
        self.state_label = "ESPERANDO"

    def reset(self):
        self.platform_x = 0.0
        self.consecutive_jumps = 0
        self.total_jumps = 0
        self.cleared_this_pass = False
        self.state_label = "ESPERANDO"

    def update(
        self,
        dt: float,
        player_state: PlayerState,
        w: int,
        current_time: float
    ) -> List[Dict[str, Any]]:
        """
        Avanza la plataforma móvil y valida saltos físicos en la zona de timing.
        Retorna lista de eventos con puntajes y tiers.
        """
        events = []
        self.platform_x += self.direction * self.speed * dt

        # Rebote de plataforma en los bordes
        margin = 100
        if self.platform_x > w - margin:
            self.platform_x = w - margin
            self.direction = -1
            self.cleared_this_pass = False
        elif self.platform_x < margin:
            self.platform_x = margin
            self.direction = 1
            self.cleared_this_pass = False

        # Zona central de impacto (jugador en el centro de pantalla)
        target_center_x = w // 2
        hit_zone_radius = 160
        dist_to_center = abs(self.platform_x - target_center_x)

        in_hit_zone = dist_to_center <= hit_zone_radius

        if in_hit_zone and not self.cleared_this_pass:
            # Evaluar si el jugador saltó en este instante
            is_jumping = player_state.jump_active or (current_time - player_state.last_jump_time < 0.35)

            if is_jumping:
                self.cleared_this_pass = True
                self.consecutive_jumps += 1
                self.total_jumps += 1
                self.last_jump_time = current_time

                # Precisión según cercanía al centro
                if dist_to_center <= 55:
                    tier = "PERFECT JUMP!"
                    points = 300
                    color = (0, 215, 255)
                else:
                    tier = "GOOD JUMP!"
                    points = 150
                    color = (0, 255, 120)

                self.state_label = tier
                events.append({
                    "type": "jump_success",
                    "tier": tier,
                    "points": points,
                    "color": color,
                    "consecutive": self.consecutive_jumps,
                    "x": int(self.platform_x)
                })

        # Si cruzó toda la zona central sin saltar
        if not in_hit_zone and self.cleared_this_pass is False and dist_to_center > hit_zone_radius:
            # Solo penalizar si acaba de pasar de largo el centro
            if (self.direction == 1 and self.platform_x > target_center_x + hit_zone_radius) or \
               (self.direction == -1 and self.platform_x < target_center_x - hit_zone_radius):
                if self.consecutive_jumps > 0:
                    self.consecutive_jumps = 0
                    self.state_label = "FALLASTE!"
                    events.append({
                        "type": "jump_miss",
                        "tier": "MISS!",
                        "points": 0,
                        "color": (60, 60, 255)
                    })
                self.cleared_this_pass = True  # Para no disparar múltiples misses por pasada

        return events

    def draw_platform(self, frame: np.ndarray, w: int, h: int):
        """Renderiza la plataforma móvil arcade y el área de salto en la base de la pantalla."""
        floor_y = h - 170

        # Zona de impacto marcada en el suelo
        target_center_x = w // 2
        hz_radius = 160
        cv2.rectangle(frame, (target_center_x - hz_radius, floor_y - 6), (target_center_x + hz_radius, floor_y + 12), (50, 40, 70), -1)
        cv2.rectangle(frame, (target_center_x - hz_radius, floor_y - 6), (target_center_x + hz_radius, floor_y + 12), (0, 255, 255), 1)
        cv2.putText(frame, "ZONA DE SALTO", (target_center_x - 62, floor_y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 255), 1, cv2.LINE_AA)

        # Plataforma móvil (Barra de energía Neón)
        px = int(self.platform_x)
        pw = 90
        ph = 14
        blend_rect_roi(frame, px - pw // 2, floor_y - ph, pw, ph, (255, 100, 0), 0.9)
        cv2.rectangle(frame, (px - pw // 2, floor_y - ph), (px + pw // 2, floor_y), (0, 255, 255), 2)
        cv2.circle(frame, (px, floor_y - ph // 2), 6, (255, 255, 255), -1)

        # Contador de saltos consecutivos
        if self.consecutive_jumps > 0:
            blend_rect_roi(frame, w // 2 - 110, floor_y - 48, 220, 32, (15, 12, 28), 0.85)
            cv2.rectangle(frame, (w // 2 - 110, floor_y - 48), (w // 2 + 110, floor_y - 16), (0, 255, 120), 1)
            cv2.putText(frame, f"SALTOS: x{self.consecutive_jumps}", (w // 2 - 58, floor_y - 26), cv2.FONT_HERSHEY_DUPLEX, 0.52, (0, 255, 120), 1, cv2.LINE_AA)
