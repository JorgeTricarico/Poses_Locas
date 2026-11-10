# 🎭 BLUEPRINT 04: Claridad de Intención Visual, Recuperación de Ilustraciones (`pose_*.jpg`), Coach Animado y Variedad de Movimientos

> **Objetivo para el modelo implementador (Gemini 3.8 Flash):**
> Este documento resuelve el problema central de **comunicación visual de las poses y dinamismo del juego**:
> 1. Recupera y corrige las ilustraciones artísticas `pose_*.jpg` que quedaron huérfanas en el repositorio.
> 2. Reemplaza el dibujo de referencia estático (que hoy no tiene piernas ni movimiento y hace que *Girando*, *Salto* y *Agacharse* no se entiendan) por un **Coach Vectorial Animado de Cuerpo Completo + Vectores de Intención (Flechas de Acción)**.
> 3. Agrega **Estelas de Movimiento (Motion Trails)** en las manos del jugador, **Bonus Pasivo de Groove**, **Eventos Especiales (Gold Move 🌟, Pose Relámpago ⚡, Combos 1➔2)** y **8 Nuevas Poses Expresivas y Dinámicas** (*Mono*, *Boxeador*, *Fiebre Disco*, *Air Guitar*, *Avión*, *Letra Y*, *Letra O*, *Mueve la Cabeza*).

---

## 1. Diagnóstico: ¿Por qué hoy NO se entiende la intención de muchas poses?

1. **Las 8 ilustraciones `pose_*.jpg` fueron desconectadas del código:**
   - En la raíz del proyecto existen 8 ilustraciones excelentes (`pose_brazos.jpg`, `pose_cabeza.jpg`, `pose_caderas.jpg`, `pose_fuerte.jpg`, `pose_letra_o.jpg`, `pose_letra_y.jpg`, `pose_saludo.jpg`, `pose_tpose.jpg`), pero `poses_locas.py` actualmente no carga ninguna.
   - **Detalle técnico crítico:** 7 de esas imágenes tienen fondo negro (`~RGB(11,11,16)`), pero **`pose_letra_y.jpg` tiene fondo BLANCO puro (`RGB(255,255,255)`)**. Si se superponen sin normalizar el fondo, `pose_letra_y.jpg` genera un parche blanco molesto.
2. **El muñeco de referencia actual (`draw_reference`) es estático y NO tiene piernas ni flechas de intención:**
   - En **`Girando!`**: los puntos `ref` tienen los hombros en `x=0.48` y `0.52` (pegados). En pantalla se ve como un palo vertical quieto; el jugador no tiene forma de adivinar que significa "dar una vuelta de 360°".
   - En **`Salto Mortal!`** y **`Agacharse!`**: como `SKELETON_CONNECTIONS` solo dibuja hasta la cadera (`L_HIP`, `R_HIP`) sin rodillas, pies ni línea de suelo, ambas poses se ven casi iguales.
   - En **`Baila! Mueve Caderas`**, **`De Lado a Lado!`** y **`Mueve los Brazos!`**: son poses de **movimiento continuo**, pero la referencia muestra un dibujo inmóvil.

---

## 2. Solución 1: Cargador Inteligente de Ilustraciones `pose_*.jpg` con Auto-Limpieza de Fondo

Agregar en `poses_locas.py` este cargador que detecta automáticamente si el fondo de un `.jpg` es blanco (como `pose_letra_y.jpg`) o negro (como el resto), extrae una máscara limpia del personaje ilustrado y la pre-escala para renderizarla sin costo de CPU en cada frame:

```python
ICON_CACHE = {}

def load_pose_illustration(filename_no_ext, size=(180, 180)):
    """
    Carga una ilustración pose_*.jpg, elimina automáticamente su fondo (sea negro o blanco)
    y la devuelve en caché con su máscara alpha para superposición limpia.
    """
    cache_key = (filename_no_ext, size)
    if cache_key in ICON_CACHE:
        return ICON_CACHE[cache_key]

    path = f"{filename_no_ext}.jpg"
    if not os.path.exists(path):
        ICON_CACHE[cache_key] = None
        return None

    img = cv2.imread(path)
    if img is None:
        ICON_CACHE[cache_key] = None
        return None

    img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detectar color de fondo muestreando las 4 esquinas
    corners = [int(gray[0, 0]), int(gray[0, -1]), int(gray[-1, 0]), int(gray[-1, -1])]
    bg_brightness = sum(corners) / 4.0

    if bg_brightness > 200:
        # Fondo blanco (ej. pose_letra_y.jpg): quedarnos con los píxeles más oscuros que 240
        _, mask = cv2.threshold(gray, 238, 255, cv2.THRESH_BINARY_INV)
    else:
        # Fondo negro (ej. pose_brazos.jpg, pose_caderas.jpg, etc.): píxeles más claros que 22
        _, mask = cv2.threshold(gray, 22, 255, cv2.THRESH_BINARY)

    # Suavizar bordes de la máscara
    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    alpha = (mask.astype(np.float32) / 255.0)[..., None]

    # Pre-componer sobre un fondo oscuro elegante (30, 25, 35) para la tarjeta de referencia
    bg_card = np.full_like(img, (30, 25, 35), dtype=np.uint8)
    composited = (img.astype(np.float32) * alpha + bg_card.astype(np.float32) * (1.0 - alpha)).astype(np.uint8)

    ICON_CACHE[cache_key] = composited
    return composited
```

---

## 3. Solución 2: "Living Animated Coach" + Vectores de Intención Física

Reemplazar el `draw_reference` estático por un **Coach Animado en Tiempo Real (`draw_animated_coach_and_intent`)** que:
1. Muestra la **Ilustración Artística (`pose_*.jpg`)** en el panel izquierdo de la tarjeta de referencia (cuando existe) y el **Holograma Animado** al lado (o en pantalla principal).
2. **Dibuja Piernas, Rodillas, Pies y Línea de Suelo** para que *Salto*, *Agacharse* y *Paso Lateral* sean 100% inequívocos.
3. **Anima el esqueleto de referencia con `t = time.time()`** según la acción:
   - Si es **Cadera (`shake_hips`)**: la cadera del holograma oscila de izquierda a derecha en vivo + dibuja **flechas dobles laterales (`◄───►`)**.
   - Si es **Salto (`jump`)**: el holograma despega del suelo con piernas impulsadas + **flechas triples hacia arriba (`▲ ▲ ▲`)** y ondas en el piso.
   - Si es **Agacharse (`squat`)**: el holograma flexiona las rodillas bajando la cadera + **flechas dobles hacia abajo (`▼ ▼`)**.
   - Si es **Giro (`spin`)**: los hombros y brazos rotan con `math.cos(t * 5)` simulando un giro 3D + **anillo elíptico con flecha de rotación `"360° ↻"`**.
   - Si es **Mueve Brazos (`flail_arms`)** o **Boxeo (`boxer`)**: los brazos del holograma suben y bajan rítmicamente en vivo con flechas en las manos.

### Código Completo del Coach Animado con Intención (`draw_reference` mejorado):

```python
def get_animated_ref_points(pose_data, t):
    """
    Devuelve una copia de pose_data['ref'] animada en función del tiempo `t`
    y agrega rodillas/tobillos sintéticos coherentes para que se entienda todo el cuerpo.
    """
    base_ref = pose_data.get('ref', {})
    pts = {k: (float(v[0]), float(v[1])) for k, v in base_ref.items()}
    name = pose_data.get('name', '')

    # Calcular caderas base para generar rodillas y pies
    lh = pts.get(L_HIP, (0.42, 0.65))
    rh = pts.get(R_HIP, (0.58, 0.65))

    # Animaciones matemáticas según la intención de la pose
    if 'Caderas' in name:
        sway = math.sin(t * 7.0) * 0.10
        pts[L_HIP] = (lh[0] + sway, lh[1])
        pts[R_HIP] = (rh[0] + sway, rh[1])
    elif 'Lado a Lado' in name:
        step = math.sin(t * 4.5) * 0.16
        for k in list(pts.keys()):
            pts[k] = (pts[k][0] + step, pts[k][1])
    elif 'Salto' in name:
        bounce = -abs(math.sin(t * 5.5)) * 0.16
        for k in list(pts.keys()):
            pts[k] = (pts[k][0], pts[k][1] + bounce)
    elif 'Agacharse' in name:
        squat_down = abs(math.sin(t * 4.0)) * 0.18
        for k in list(pts.keys()):
            pts[k] = (pts[k][0], pts[k][1] + squat_down)
    elif 'Mueve los Brazos' in name:
        wave = math.sin(t * 8.0) * 0.22
        if L_WRIST in pts: pts[L_WRIST] = (pts[L_WRIST][0], 0.30 + wave)
        if R_WRIST in pts: pts[R_WRIST] = (pts[R_WRIST][0], 0.30 - wave)
        if L_ELBOW in pts: pts[L_ELBOW] = (pts[L_ELBOW][0], 0.30 + wave * 0.5)
        if R_ELBOW in pts: pts[R_ELBOW] = (pts[R_ELBOW][0], 0.30 - wave * 0.5)
    elif 'Cabeza!' in name and pose_data.get('dynamic'):
        nod = math.sin(t * 8.0) * 0.08
        if NOSE in pts: pts[NOSE] = (0.5 + nod, pts[NOSE][1])
    elif 'Boxeo' in name or 'Puños' in name:
        jab = math.sin(t * 10.0) * 0.12
        if L_WRIST in pts: pts[L_WRIST] = (0.38 - jab, 0.22 - abs(jab)*0.3)
        if R_WRIST in pts: pts[R_WRIST] = (0.62 + jab, 0.22 - abs(jab)*0.3)
    elif 'Gir' in name:
        spin_cos = math.cos(t * 4.5)
        for k in list(pts.keys()):
            dx = pts[k][0] - 0.5
            pts[k] = (0.5 + dx * spin_cos, pts[k][1])

    # Generar rodillas y tobillos virtuales para que el jugador vea las piernas
    lh_now = pts.get(L_HIP, (0.42, 0.65))
    rh_now = pts.get(R_HIP, (0.58, 0.65))
    is_squat = 'Agacharse' in name
    knee_spread = 0.07 if is_squat else 0.0
    foot_y = 0.92 if not ('Salto' in name) else min(0.92, lh_now[1] + 0.26)
    knee_y = (lh_now[1] + foot_y) * 0.5

    pts['L_KNEE_V'] = (lh_now[0] - knee_spread, knee_y)
    pts['R_KNEE_V'] = (rh_now[0] + knee_spread, knee_y)
    pts['L_ANKLE_V'] = (0.40, foot_y)
    pts['R_ANKLE_V'] = (0.60, foot_y)
    return pts


def draw_intent_arrows_in_box(frame, pose_data, box_x, box_y, box_w, box_h, t):
    """Dibuja flechas e iconos de intención de movimiento dentro del cuadro de referencia."""
    name = pose_data.get('name', '')
    color = pose_data.get('color', (0, 255, 255))
    cx, cy = box_x + box_w // 2, box_y + box_h // 2

    # Línea de suelo de referencia
    floor_y = box_y + int(box_h * 0.93)
    cv2.line(frame, (box_x + 20, floor_y), (box_x + box_w - 20, floor_y), (100, 100, 120), 2)

    if 'Caderas' in name or 'Lado a Lado' in name:
        y_arr = box_y + int(box_h * 0.63)
        off = int(math.sin(t * 7.0) * 8)
        cv2.arrowedLine(frame, (cx - 15 + off, y_arr), (box_x + 15, y_arr), color, 3, tipLength=0.4)
        cv2.arrowedLine(frame, (cx + 15 + off, y_arr), (box_x + box_w - 15, y_arr), color, 3, tipLength=0.4)
    elif 'Salto' in name:
        off = int(abs(math.sin(t * 6.0)) * 12)
        cv2.arrowedLine(frame, (box_x + 25, cy + 20 - off), (box_x + 25, box_y + 25 - off), (0, 255, 100), 3, tipLength=0.35)
        cv2.arrowedLine(frame, (box_x + box_w - 25, cy + 20 - off), (box_x + box_w - 25, box_y + 25 - off), (0, 255, 100), 3, tipLength=0.35)
    elif 'Agacharse' in name:
        off = int(abs(math.sin(t * 4.0)) * 12)
        cv2.arrowedLine(frame, (box_x + 25, box_y + 40 + off), (box_x + 25, cy + 35 + off), (100, 180, 255), 3, tipLength=0.35)
        cv2.arrowedLine(frame, (box_x + box_w - 25, box_y + 40 + off), (box_x + box_w - 25, cy + 35 + off), (100, 180, 255), 3, tipLength=0.35)
    elif 'Gir' in name:
        cv2.ellipse(frame, (cx, cy), (box_w // 3, 18), 0, 20, 320, (0, 215, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, "360", (cx - 24, box_y + box_h - 18), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 215, 255), 2)
    elif 'Mueve los Brazos' in name:
        cv2.arrowedLine(frame, (box_x + 22, cy), (box_x + 22, box_y + 25), color, 3, tipLength=0.4)
        cv2.arrowedLine(frame, (box_x + box_w - 22, box_y + 25), (box_x + box_w - 22, cy), color, 3, tipLength=0.4)
```

---

## 4. Solución 3: Nuevas Poses Expresivas, Dinámicas y Variadas (Catálogo Ampliado)

Para que el juego sea mucho más divertido, intuitivo y variable, agregar las siguientes poses al catálogo `POSES` (junto con sus ilustraciones `pose_*.jpg` donde correspondan):

### 4.1. Poses Recuperadas y Mejoradas (con `pose_*.jpg`):
1. **`Letra Y!`** (`icon: 'pose_letra_y'`): Brazos arriba abiertos en diagonal formando una V/Y amplia.
2. **`Letra O!`** (`icon: 'pose_letra_o'`): Brazos arqueados sobre la cabeza juntando las manos arriba de la nariz.
3. **`Mueve la Cabeza!`** (`icon: 'pose_cabeza'`, `dynamic=True`): Mover la cabeza al ritmo de lado a lado (4 hits).

### 4.2. Nuevas Poses con Alta Personalidad ("Party Archetypes"):
4. **🦍 `Pose de Mono!`** *(Estática / Expresiva)*:
   - **Intención física:** Manos cerca de las axilas/pecho (`abs(L_WRIST.x - L_SHOULDER.x) < 0.45 * bu` y `abs(L_WRIST.y - L_SHOULDER.y) < 0.55 * bu`) con los codos bien abiertos hacia afuera (`L_ELBOW.x < L_SHOULDER.x - 0.35 * bu`).
5. **🕺 `Fiebre Disco!`** *(Estática Asimétrica — Estilo John Travolta)*:
   - **Intención física:** Mano derecha apuntando alto en diagonal arriba (`check_right_arm_up`) + mano izquierda apoyada en la cadera (`check_left_hand_on_hip`).
6. **✈️ `Avión Supersónico!`** *(Estática de Cuerpo/Torso)*:
   - **Intención física:** Brazos abiertos en cruz (`T-Pose`) pero **inclinando los hombros** (`abs(lm[L_SHOULDER].y - lm[R_SHOULDER].y) > 0.18 * get_body_unit(lm)`). ¡Obliga a inclinar el torso como un avión!
7. **🥊 `Boxeo Rápido!` (`check_boxer_jabs`)** *(Dinámica de Velocidad de Manos)*:
   - **Intención física:** Las manos a la altura del pecho/mentón lanzando 6 puñetazos rápidos alternados.
   - **Lógica exacta:**
     ```python
     def check_boxer_jabs(state, lm):
         events = []
         bu = get_body_unit(lm)
         # Medir cuál mano está más arriba/adelante cerca de la altura de los hombros/nariz
         l_high = lm[L_WRIST].y < lm[L_SHOULDER].y + 0.15 * bu
         r_high = lm[R_WRIST].y < lm[R_SHOULDER].y + 0.15 * bu
         diff_y = lm[L_WRIST].y - lm[R_WRIST].y
         if l_high and r_high:
             if diff_y < -0.20 * bu and state.last_arm_pos != 'left_jab':
                 state.last_arm_pos = 'left_jab'
                 state.arm_hits += 1
                 events.append({'type': 'hit', 'side': 'left', 'x': lm[L_WRIST].x, 'y': lm[L_WRIST].y})
             elif diff_y > 0.20 * bu and state.last_arm_pos != 'right_jab':
                 state.last_arm_pos = 'right_jab'
                 state.arm_hits += 1
                 events.append({'type': 'hit', 'side': 'right', 'x': lm[R_WRIST].x, 'y': lm[R_WRIST].y})
         return state.arm_hits >= 6, events
     ```
8. **🎸 `Guitarra Rockera!` (`check_air_guitar`)** *(Dinámica Asimétrica Divertida)*:
   - **Intención física:** Un brazo extendido al costado sosteniendo el mástil de la guitarra (`check_left_arm_horizontal` o `check_right_arm_horizontal`) mientras la otra mano rasguea rápido arriba y abajo cerca de la cadera/abdomen (4 rasgueos).

---

## 5. Solución 4: Mecánicas de Variabilidad para que Nunca Sea Repetitivo

Para que el ritmo de la partida sea **dinámico, impredecible y emocionante**, agregar en `shift_queue()` y en el bucle principal estas **3 mecánicas de variabilidad**:

### 5.1. Modificadores de Pose en Cola (`variant`: `'NORMAL' | 'SPEED' | 'GOLD' | 'COMBO_2'`)
Cuando `shift_queue()` encola una nueva pose en modo `LIBRE`:
- **15% de probabilidad → `⚡ POSE RELÁMPAGO (variant='SPEED')`**:
  - El tiempo requerido de retención baja a la mitad (`match_required = 0.30s` o mitad de hits dinámicos).
  - La tarjeta en el carril brilla en **Azul Eléctrico**, muestra `"⚡ RÁPIDO x2"` y otorga **doble puntaje** si se logra en menos de `2.2s`.
- **12% de probabilidad → `🌟 GOLD MOVE (variant='GOLD')`**:
  - La tarjeta y los anillos de las manos brillan en **Oro Puro `(0, 215, 255)`**.
  - Al completarla, dispara lluvia doble de confeti dorado, otorga **`+500 * multiplier` puntos** y suma **`+40` de Fever Gauge**.
- **Bonus Pasivo de "Groove" (`GLOBAL HIP GROOVE`)**:
  - Mientras el jugador está resolviendo cualquier pose **estática**, monitorear suavemente el balanceo de sus caderas (`hip_x`). Si baila con la cadera mientras sostiene la pose con los brazos, otorgar **`+15 RITMO!`** extra con chispas magenta en las caderas (cooldown `0.45s`). ¡Premia bailar de verdad en lugar de quedarse rígido!

---

## 6. Solución 5: Estelas de Energía en las Manos (`HandTrailSystem`)

Para que el jugador **sienta físicamente la fluidez de sus propios movimientos** en la pantalla, agregar un buffer circular de las últimas 8 posiciones `(x, y)` de `L_WRIST` y `R_WRIST` y dibujarlo con grosor decreciente:

```python
from collections import deque

class HandTrailSystem:
    def __init__(self, maxlen=8):
        self.left_trail = deque(maxlen=maxlen)
        self.right_trail = deque(maxlen=maxlen)

    def update_and_draw(self, frame, lm, display_w, display_h, left_color, right_color):
        l_pt = get_point(lm, L_WRIST, display_w, display_h)
        r_pt = get_point(lm, R_WRIST, display_w, display_h)

        if l_pt: self.left_trail.append(l_pt)
        elif self.left_trail: self.left_trail.popleft()

        if r_pt: self.right_trail.append(r_pt)
        elif self.right_trail: self.right_trail.popleft()

        for trail, col in [(self.left_trail, left_color), (self.right_trail, right_color)]:
            pts = list(trail)
            for i in range(1, len(pts)):
                thickness = max(2, int((i / len(pts)) * 10))
                cv2.line(frame, pts[i - 1], pts[i], col, thickness, cv2.LINE_AA)
```
