"""
Módulo del Motor de Reglas, Colas de Poses, Métricas y Gestión de Audio
"""

import time
import random
import os
from .catalog import get_poses_for_profile, COREOGRAFIAS


def shift_queue(pose_queue, mode, song, coreo_idx, profile='FIESTA'):
    """Avanza la cola de poses asegurando variabilidad, coreografía o perfil."""
    if pose_queue:
        pose_queue.pop(0)
    if mode == 'COREO' and song in COREOGRAFIAS:
        coreo_idx = (coreo_idx + 1) % len(COREOGRAFIAS[song])
        p = dict(COREOGRAFIAS[song][coreo_idx])
        p['variant'] = 'NORMAL'
    else:
        profile_poses = get_poses_for_profile(profile)
        candidates = [x for x in profile_poses if not pose_queue or x['name'] != pose_queue[-1]['name']]
        if not candidates:
            candidates = profile_poses
        p = dict(random.choice(candidates))
        # Modificadores de Variabilidad
        var_roll = random.random()
        if var_roll < 0.15 and not p.get('dynamic') and profile == 'CARDIO':
            p['variant'] = 'SPEED'  # Pose Relámpago
        elif var_roll < 0.27:
            p['variant'] = 'GOLD'   # Gold Move
        else:
            p['variant'] = 'NORMAL'

    pose_queue.append(p)
    return pose_queue[0], coreo_idx


def get_dynamic_progress(pose_name, state):
    """Retorna (actual, meta, etiqueta) según la pose dinámica activa."""
    if 'Caderas' in pose_name:
        return state.hip_hits, 6, f"CADERAS: {state.hip_hits}/6"
    elif 'Cabeza' in pose_name:
        return state.hip_hits, 6, f"CABEZA: {state.hip_hits}/6"
    elif 'Lado a Lado' in pose_name:
        return state.move_hits, 4, f"PASOS: {state.move_hits}/4"
    elif 'Brazos' in pose_name:
        return state.arm_hits, 6, f"BRAZOS: {state.arm_hits}/6"
    elif 'Boxeo' in pose_name:
        return state.arm_hits, 6, f"JABS: {state.arm_hits}/6"
    elif 'Guitarra' in pose_name:
        return state.arm_hits, 6, f"ROCK: {state.arm_hits}/6"
    elif 'Salto' in pose_name:
        return state.jump_phase, 2, "SALTA!" if state.jump_phase == 0 else "ATERRIZA!"
    elif 'Agacharse' in pose_name:
        return state.jump_phase, 2, "BAJA!" if state.jump_phase == 0 else "SUBE!"
    elif 'Gir' in pose_name:
        return state.spin_phase, 2, "GIRA 360!" if state.spin_phase == 0 else "COMPLETA EL GIRO!"
    elif 'Balanceo' in pose_name:
        return state.arm_hits, 6, f"FLOW: {state.arm_hits}/6"
    elif 'Remolino' in pose_name or 'DJ' in pose_name:
        return state.dj_steps // 4, 4, f"GIROS DJ: {state.dj_steps // 4}/4"
    elif 'Disco' in pose_name:
        return state.disco_hits, 6, f"DISCO: {state.disco_hits}/6"
    elif 'Onda' in pose_name or 'Electro' in pose_name:
        return state.wave_hits, 6, f"ONDAS: {state.wave_hits}/6"
    elif 'Limpiaparabrisas' in pose_name:
        return state.wiper_hits, 6, f"BARRIDOS: {state.wiper_hits}/6"
    return 0, 1, ""


def log_metric(mode, pose_name, time_taken, status, filename='metrics.csv'):
    """Registra telemetría de rendimiento y dwell times."""
    try:
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(f"{time.time()},{mode},{pose_name},{time_taken:.3f},{status}\n")
    except Exception as e:
        print(f"Error logging metric: {e}")


class AudioController:
    """Controlador defensivo de audio y efectos de sonido."""
    def __init__(self, enable_sfx=False):
        self.enable_sfx = enable_sfx
        self.has_audio = False
        self.snd_success = None
        self.snd_fail = None
        self.snd_punch = None

        try:
            import pygame
            pygame.mixer.pre_init(44100, -16, 1, 512)
            pygame.init()
            self.snd_success = pygame.mixer.Sound('success_new.wav') if os.path.exists('success_new.wav') else None
            self.snd_fail = pygame.mixer.Sound('fail.wav') if os.path.exists('fail.wav') else None
            self.snd_punch = pygame.mixer.Sound('punch_new.wav') if os.path.exists('punch_new.wav') else None
            self.has_audio = True
        except Exception as e:
            print(f"Audio desactivado o no disponible: {e}")
            self.has_audio = False

    def play(self, snd):
        if self.has_audio and snd and self.enable_sfx:
            try:
                snd.play()
            except Exception:
                pass
