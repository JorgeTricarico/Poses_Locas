# ⚙️ BLUEPRINT 02: Motor Matemático de Poses, "Grace Decay" y Arquitectura Core

> **Objetivo para el modelo implementador (Gemini 3.8 Flash):**
> Este documento especifica las mejoras conceptuales fundamentales en el motor de evaluación de poses, tolerancia al ruido de sensores (MediaPipe), rendimiento de memoria en OpenCV y limpieza arquitectónica del repositorio.

---

## 1. Problema Conceptual Fundamental #1: Dependencia de Escala y Distancia a la Cámara

### Diagnóstico del Código Actual (`poses_locas.py` líneas 131–144)
Actualmente, todas las funciones `check_*` usan diferencias en coordenadas normalizadas de pantalla (`0.0` a `1.0`):
```python
# ACTUAL (Frágil a la distancia y altura del jugador):
def check_left_hand_on_head(lm):
    return abs(lm[L_WRIST].x - lm[NOSE].x) < 0.10 and abs(lm[L_WRIST].y - lm[NOSE].y) < 0.10
```
- **Por qué falla:**
  1. Si el jugador se acerca a 1.2 metros de la cámara, su cabeza mide `0.18` unidades de pantalla: poner la mano en la sien o arriba de la cabeza da `abs(x - nose.x) = 0.13` → **Falla aunque la pose sea perfecta**.
  2. Si juega un niño pequeño a 3 metros de la cámara, el ancho de sus hombros es apenas `0.10` unidades de pantalla: en `check_left_arm_horizontal`, exigir `lm[L_WRIST].x < lm[L_SHOULDER].x - 0.08` o en `check_move_side_to_side` exigir `threshold = 0.15` equivale a pedirle que salte medio metro.
  3. En `check_left_hand_on_head`, comparar contra `NOSE` obliga a taparse la cara con las manos (lo que a su vez hace que MediaPipe pierda el tracking de la cara y las muñecas por oclusión).

### Solución Matemática Core: Normalización por Unidad Anatómica (`BodyUnit`) + Score Continuo `[0.0, 1.0]`

Definimos **`1.0 BodyUnit (BU)` = Ancho Biacromial (distancia 2D entre hombro izquierdo y hombro derecho del jugador en el frame actual)**, con piso de seguridad `0.12`. Todas las tolerancias espaciales se expresan como múltiplos de `BU` y se combinan con **ángulos articulares 2D**.

#### Código Exacto a Implementar en `poses_locas.py`:

```python
def get_body_unit(lm):
    """
    Retorna la distancia euclidiana entre ambos hombros como unidad anatómica base (BodyUnit).
    Garantiza invarianza ante la distancia a la cámara y la estatura del jugador (niños vs adultos).
    """
    dx = lm[L_SHOULDER].x - lm[R_SHOULDER].x
    dy = lm[L_SHOULDER].y - lm[R_SHOULDER].y
    return max(0.10, math.hypot(dx, dy))

def calc_angle_2d(lm, a_id, b_id, c_id):
    """Calcula el ángulo articular en grados (0..180) en el vértice b_id."""
    ax, ay = lm[a_id].x, lm[a_id].y
    bx, by = lm[b_id].x, lm[b_id].y
    cx, cy = lm[c_id].x, lm[c_id].y
    rad = math.atan2(cy - by, cx - bx) - math.atan2(ay - by, ax - bx)
    ang = abs(math.degrees(rad))
    return 360.0 - ang if ang > 180.0 else ang

def distance_to_score(dist_val, target_dist, tolerance):
    """
    Convierte un error de distancia en un score continuo [0.0, 1.0].
    Si dist_val <= target_dist -> 1.0 (Verde).
    Entre target_dist y target_dist + tolerance -> decae linealmente de 1.0 a 0.0 (Ámbar -> Rojo).
    """
    if dist_val <= target_dist:
        return 1.0
    over = dist_val - target_dist
    return max(0.0, 1.0 - (over / max(1e-5, tolerance)))
```

#### Nuevos Evaluadores Duales (Compatibles con `bool` y con `score` continuo):

Cada función `check_*` se mantiene devolviendo `bool` para **no romper `test_game.py`**, y se agrega `eval_arm_score(check_fn, lm) -> float` (o funciones `score_*`) que retornan un `float ∈ [0.0, 1.0]`:

```python
def score_left_arm_up(lm):
    bu = get_body_unit(lm)
    # Qué tan arriba está la muñeca respecto a la nariz/hombro normalizado por BU
    target_y = lm[NOSE].y - 0.15 * bu
    if lm[L_WRIST].y <= target_y:
        return 1.0
    return distance_to_score(lm[L_WRIST].y, target_y, 0.8 * bu)

def score_right_arm_up(lm):
    bu = get_body_unit(lm)
    target_y = lm[NOSE].y - 0.15 * bu
    if lm[R_WRIST].y <= target_y:
        return 1.0
    return distance_to_score(lm[R_WRIST].y, target_y, 0.8 * bu)

def score_left_arm_horizontal(lm):
    bu = get_body_unit(lm)
    dy = abs(lm[L_WRIST].y - lm[L_SHOULDER].y)
    extended = (lm[L_SHOULDER].x - lm[L_WRIST].x) > 0.35 * bu
    if not extended:
        return 0.2
    return distance_to_score(dy, 0.50 * bu, 0.60 * bu)

def score_right_arm_horizontal(lm):
    bu = get_body_unit(lm)
    dy = abs(lm[R_WRIST].y - lm[R_SHOULDER].y)
    extended = (lm[R_WRIST].x - lm[R_SHOULDER].x) > 0.35 * bu
    if not extended:
        return 0.2
    return distance_to_score(dy, 0.50 * bu, 0.60 * bu)

def score_left_hand_on_hip(lm):
    bu = get_body_unit(lm)
    d = math.hypot(lm[L_WRIST].x - lm[L_HIP].x, lm[L_WRIST].y - lm[L_HIP].y)
    return distance_to_score(d, 0.65 * bu, 0.60 * bu)

def score_right_hand_on_hip(lm):
    bu = get_body_unit(lm)
    d = math.hypot(lm[R_WRIST].x - lm[R_HIP].x, lm[R_WRIST].y - lm[R_HIP].y)
    return distance_to_score(d, 0.65 * bu, 0.60 * bu)

def score_left_hand_on_head(lm):
    bu = get_body_unit(lm)
    # Acepta cerca de la nariz O de la oreja izquierda (evita ocluir la cara)
    d_nose = math.hypot(lm[L_WRIST].x - lm[NOSE].x, lm[L_WRIST].y - lm[NOSE].y)
    d_ear = math.hypot(lm[L_WRIST].x - lm[L_EAR].x, lm[L_WRIST].y - lm[L_EAR].y)
    return distance_to_score(min(d_nose, d_ear), 0.55 * bu, 0.55 * bu)

def score_right_hand_on_head(lm):
    bu = get_body_unit(lm)
    d_nose = math.hypot(lm[R_WRIST].x - lm[NOSE].x, lm[R_WRIST].y - lm[NOSE].y)
    d_ear = math.hypot(lm[R_WRIST].x - lm[R_EAR].x, lm[R_WRIST].y - lm[R_EAR].y)
    return distance_to_score(min(d_nose, d_ear), 0.55 * bu, 0.55 * bu)
```

---

## 2. Problema Conceptual Fundamental #2: Reset Instantáneo de Dwell-Time (`match_start = None`)

### Diagnóstico del Código Actual (`poses_locas.py` líneas 769–803)
En el código actual:
```python
if left_ok and right_ok:
    if match_start is None: match_start = current_time
    hold_progress = min(1.0, (current_time - match_start) / match_required)
    ...
else:
    match_start = None
```
Si el jugador mantiene la pose durante `0.58s` (97% de la barra) y en el frame siguiente MediaPipe tiene un micro-parpadeo de 33ms por motion blur, `match_start` se vuelve `None` y **la barra cae de 97% a 0% en un instante**.

### Solución Core: Acumulador Bidireccional con "Grace Decay" y Tiers de Juicio (`PERFECTO` / `GENIAL` / `BUENO`)

En lugar de medir `current_time - match_start`, mantener una variable de estado `hold_progress: float = 0.0` y `last_frame_time: float`:

```python
dt = min(0.1, current_time - last_frame_time)
last_frame_time = current_time

if left_ok and right_ok:
    # Sube de 0.0 a 1.0 en match_required segundos (0.55s)
    hold_progress = min(1.0, hold_progress + (dt / match_required))
else:
    # GRACE DECAY: Si un solo brazo está bien, decae muy lento (0.6/s).
    # Si ambos fallan, decae a 1.2/s (nunca cae a 0 de golpe por 1 frame perdido).
    decay_rate = 0.6 if (left_ok or right_ok) else 1.2
    hold_progress = max(0.0, hold_progress - decay_rate * dt)
```

#### Sistema de Juicio Graduado (Tiers tipo Just Dance / Arcade):
Cuando una pose se completa (`hold_progress >= 1.0` o `dynamic completed`), evaluar `time_taken = current_time - pose_start_time`:
- **`time_taken <= 1.8s` → `"¡¡PERFECTO!!"`** (Color Dorado `(0, 215, 255)`, `+150 * multiplier` pts, `+20` Fever).
- **`1.8s < time_taken <= 3.5s` → `"¡GENIAL!"`** (Color Verde Neón `(0, 255, 100)`, `+100 * multiplier` pts, `+15` Fever).
- **`time_taken > 3.5s` → `"¡BIEN!"`** (Color Cian `(255, 255, 0)`, `+70 * multiplier` pts, `+10` Fever).

---

## 3. Problema Conceptual Fundamental #3: Cuello de Botella de Memoria en Renderizado OpenCV (`frame.copy()`)

### Diagnóstico del Código Actual
En cada frame de `1280×720×3` (2.76 MB):
1. `draw_skeleton_with_feedback` hace `overlay = frame.copy()` y `cv2.addWeighted` sobre `1280×720`.
2. `draw_reference` (línea 425) hace **otro** `overlay = frame.copy()` de `1280×720` y `cv2.addWeighted` sobre toda la pantalla solo para pintar un rectángulo semitransparente de `200×220` píxeles (que es apenas el 4.7% de la imagen).
3. En Fever Mode y Flash de éxito se hacen dos `cv2.addWeighted` adicionales a pantalla completa.

### Solución Core: Helper de Alpha-Blending por Sub-Región (ROI Slicing)

Agregar esta función utilitaria de **costo cero de copia de frame completo**:

```python
def blend_rect_roi(frame, x, y, w, h, bgr_color, alpha=0.55):
    """
    Aplica un rectángulo semitransparente operando ÚNICAMENTE sobre el slice (ROI)
    de NumPy en lugar de clonar todo el frame de 1280x720. Hasta 25x más rápido.
    """
    fh, fw = frame.shape[:2]
    x1, y1 = max(0, int(x)), max(0, int(y))
    x2, y2 = min(fw, int(x + w)), min(fh, int(y + h))
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    rect = np.full_like(roi, bgr_color, dtype=np.uint8)
    cv2.addWeighted(rect, alpha, roi, 1.0 - alpha, 0, roi)
```
Reemplazar en `draw_reference`, en el banner superior, en el carril inferior y en el menú el uso de `frame.copy()` por `blend_rect_roi(...)`.

---

## 4. Problema Conceptual Fundamental #4: Sincronización Rítmica Visual (Beat-Pulse Engine)

Las canciones incluidas en el proyecto tienen tempos (BPM) bien definidos. Agregar un diccionario `SONG_BPM` para que el borde del receptor `"¡AHORA!"`, el título y el tamaño de las articulaciones latan exactamente al ritmo de la canción activa:

```python
SONG_BPM = {
    'macarena.wav': 103,
    'macarena_real.wav': 103,
    'macarena_vocal.wav': 103,
    'asereje.wav': 106,
    'ymca.wav': 127,
    'danza_kuduro.wav': 130,
    'waka_waka.wav': 127,
    'despacito.wav': 89,
}

def get_beat_pulse(current_time, song_name):
    """Retorna un valor [0.0, 1.0] que hace pico en cada negra (beat) de la canción."""
    bpm = SONG_BPM.get(song_name, 110)
    beats_per_sec = bpm / 60.0
    phase = (current_time * beats_per_sec) % 1.0
    # Decaimiento exponencial rápido tras el golpe del beat
    return math.exp(-phase * 5.0)
```

---

## 5. Problema Conceptual Fundamental #5: Seguridad y Limpieza de Credenciales RTSP

En `poses_locas.py` (línea 39), `monsters_ar.py` (línea 9), `balloon_pop.py` (línea 10), `balloon_pop_native.py` (línea 9) y `practice_mode.py` (línea 8), la URL de la cámara IP está hardcodeada en texto plano.
- **Acción para el modelo implementador:**
  Reemplazar la constante literal por lectura desde variable de entorno con fallback opcional:
  ```python
  RTSP_URL = os.environ.get("POSES_RTSP_URL", "")
  ```
  Y en el bucle de detección de cámara (`for cam_id in [0, 1, 2, RTSP_URL]:`), ignorar `RTSP_URL` si es un string vacío `""`.
