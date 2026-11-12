"""
Módulo de Estado del Jugador (PlayerState)
"""


class PlayerState:
    """
    Gestiona el estado cinético del jugador:
    - Acumuladores de golpes para caderas, cabeza, saltos, giros, etc.
    - Centros de referencia filtrados por suavizado exponencial.
    - Fases de movimiento dinámico.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.hip_hits = 0
        self.last_hit_side = None
        self.center_x = None
        self.center_y = None
        self.jump_phase = 0
        self.spin_phase = 0
        self.arm_hits = 0
        self.last_arm_pos = None
        self.last_alt_arm_pos = None
        self.last_sym_arm_pos = None
        self.last_arm_hit_time = 0
        self.move_hits = 0
        self.last_move_pos = None
        self.freeze_reference = None
        self.initial_shoulder_order = None
        self.spin_start_time = 0
        self.global_center_x = None
        self.global_last_side = None
        self.last_groove_time = 0
