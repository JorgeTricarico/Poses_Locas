# 🎨 BLUEPRINT 01: Rediseño Radical de UI/UX y Comunicación Visual del Movimiento

> **Objetivo para el modelo implementador (Gemini 3.8 Flash):**
> Este documento contiene las especificaciones exactas de diseño, coordenadas, fórmulas y código Python/OpenCV para transformar la interfaz de usuario (`poses_locas.py`) resolviendo los problemas de atención dividida, colisiones visuales y falta de feedback progresivo cuando el jugador está a 2–3 metros de la cámara.

---

## 1. Diagnóstico de Bugs Visuales y Problemas de UX Actuales

Al auditar `poses_locas.py` (líneas 422–512 y 720–906) y las capturas de renderizado (`test_visual_gameplay.jpg` y `test_visual_fever.jpg`), se identifican **6 fallos críticos de UI/UX**:

1. **Colisión de Coordenadas en la Zona Inferior (`y = 640..720`):**
   - El carril inferior se dibuja en `lane_y = display_h - 80` (`y = 640` a `720`).
   - La barra de `"MANTENE!"` (línea 772) se dibuja en `display_h - 80` (`y = 640`), **pisando el borde superior del carril**.
   - El contador `"GOLPES: X/6"` (línea 815) se dibuja en `display_h - 80` (`y = 640`), **pisando el carril**.
   - El texto de ayuda `"Gesto 'Wakanda' o Tecla 'N'..."` (línea 851) se dibuja en `display_h - 20` (`y = 700`), **escribiendo literalmente encima de las tarjetas del carril inferior**.
   - La etiqueta `"AHORA!"` (línea 830) en `lane_y - 5` se corta contra la línea divisoria blanca de `lane_y`.
2. **Bug de Feedback en Poses Dinámicas (`GOLPES: 0/6` congelado):**
   - En las líneas 808–815, cualquier pose con `dynamic=True` y `state.center_x is not None` muestra `f"GOLPES: {state.hip_hits}/6"`.
   - En la pose `'De Lado a Lado!'`, el contador real es `state.move_hits` (meta: 4), por lo que en pantalla dice **`GOLPES: 0/6`** todo el tiempo aunque el jugador lo esté haciendo bien.
   - En `'Mueve los Brazos!'` (`state.arm_hits`), `'Salto Mortal!'`, `'Agacharse!'` y `'Girando!'`, `state.center_x` es `None`, por lo que **no se dibuja ningún indicador visual de progreso**.
3. **Efecto de Atención Dividida (Split-Attention a 2.5 metros):**
   - El jugador debe mirar su cuerpo en el centro, luego mirar arriba a la derecha (`x=1060, y=20`) para ver un esqueleto miniatura de referencia, y luego mirar abajo a la izquierda (`x=20, y=650`) para leer texto pequeño (`scale=0.5`) en una caja morada.
4. **Feedback Binario Todo-o-Nada (Rojo/Verde sin Proximidad):**
   - Los brazos pasan de Rojo (`#FF0000`) a Verde (`#00FF00`) sin estado intermedio. Si al jugador le faltan 2 centímetros para alcanzar la altura de la pose, el brazo se ve igual de rojo que si estuviera quieto.
   - En poses dinámicas combinadas (`'Cabeza y Caderas!'`, `'Salto con Brazos!'`, `'Giro y Cabeza!'`), el código fuerza `left_ok, right_ok = True, True` (línea 729), pintando los brazos de verde incluso cuando el jugador no tiene la mano en la cabeza o los brazos arriba.
5. **Carril Inferior Basado en Texto en vez de Pictogramas:**
   - Leer `"Baila! Mueve Caderas"` en fuente `0.5` a 3 metros de distancia mientras te movés genera alta carga cognitiva. Las tarjetas del carril deben mostrar **mini-pictogramas visuales** + íconos de acción y desplazarse suavemente (`slide lerp`).
6. **Menú Dependiente del Teclado:**
   - Obliga al jugador a caminar hasta la PC para presionar `W/S/Enter` o `M`.

---

## 2. Nuevo Mapa Espacial del HUD (Layout 1280×720 Libre de Colisiones)

Toda la interfaz debe respetar estrictamente estas **5 zonas seguras** para no tapar jamás el cuerpo del jugador ni superponer elementos:

```
+-----------------------------------------------------------------------------------+
| [ZONA 1: TOP-LEFT HUD]                 [ZONA 2: TOP-CENTER]   [ZONA 3: TOP-RIGHT] |
| x:24..320, y:20..155                   x:440..840, y:18..85   x:1036..1256, y:20  |
| - Score + Animación Pop                - Banner de Pose Activa - Card Referencia  |
| - Pill de Multiplicador (x1..x4)         (Nombre grande +       220x230 con       |
| - Barra Fever Neon                       barra Hold/Progreso)   Pictograma grande |
|                                                                                   |
|                                                                                   |
|                              [ZONA CENTRAL AR: JUGADOR]                           |
|                              x:200..1030, y:100..580                              |
|                       - Esqueleto Semáforo (Rojo/Ámbar/Verde)                     |
|                       - Ghost Silhouette (Anclada al torso del jugador)           |
|                       - Anillos Magnéticos en Muñecas + Guías Dinámicas           |
|                                                                                   |
| [ZONA 4: FLOATING FEEDBACK]                                                       |
| x:40..360, y:260..480                                                             |
| - Textos de Juicio ("¡PERFECTO!", "RACHA x5")                                     |
|                                                                                   |
|-----------------------------------------------------------------------------------|
| [ZONA 5: BOTTOM PICTO-HIGHWAY (CARRIL DE PICTOGRAMAS)]        y: 590 .. 720       |
| - Barra de Ayuda sutil integrada en el borde superior (y:572)                     |
| - Receptor Activo "AHORA!" (x:24..234, y:600..710) con borde neón pulsante        |
| - Cola de 4 Próximas Poses (x:250..1250) con mini-esqueleto + slide suave         |
+-----------------------------------------------------------------------------------+
```

---

## 3. Especificación de Mejoras UI/UX Core (Con Código para Implementar)

### MEJORA UX 1: "Body-Anchored Ghost Silhouette" y Anillos Magnéticos de Objetivo

**Concepto:** En lugar de obligar al jugador a traducir mentalmente la cajita de la esquina superior derecha, proyectamos una **silueta guía traslúcida ("Ghost") y anillos magnéticos de destino** directamente sobre el cuerpo real del jugador en pantalla, escalados dinámicamente según la posición y tamaño actual de sus hombros y caderas.

#### Implementación Exacta (Agregar en `poses_locas.py`):

```python
def compute_body_anchored_targets(lm, pose_data, display_w, display_h):
    """
    Transforma las coordenadas normalizadas de 'ref' de la pose para que se anclen
    al centro de hombros y escala corporal real del jugador detectado.
    Retorna un diccionario {lm_id: (px, py)} en coordenadas de pantalla.
    """
    ref = pose_data.get('ref')
    if not ref or L_SHOULDER not in ref or R_SHOULDER not in ref:
        return {}

    # Verificar visibilidad mínima del torso del jugador
    if lm[L_SHOULDER].visibility < 0.35 or lm[R_SHOULDER].visibility < 0.35:
        return {}

    # Centro de hombros del jugador en píxeles
    p_ls = (lm[L_SHOULDER].x * display_w, lm[L_SHOULDER].y * display_h)
    p_rs = (lm[R_SHOULDER].x * display_w, lm[R_SHOULDER].y * display_h)
    player_cx = (p_ls[0] + p_rs[0]) / 2.0
    player_cy = (p_ls[1] + p_rs[1]) / 2.0
    player_shoulder_w = max(40.0, math.hypot(p_rs[0] - p_ls[0], p_rs[1] - p_ls[1]))

    # Centro de hombros en la referencia
    r_ls = ref[L_SHOULDER]
    r_rs = ref[R_SHOULDER]
    ref_cx = (r_ls[0] + r_rs[0]) / 2.0
    ref_cy = (r_ls[1] + r_rs[1]) / 2.0
    ref_shoulder_w = max(0.08, math.hypot(r_rs[0] - r_ls[0], r_rs[1] - r_ls[1]))

    scale = player_shoulder_w / ref_shoulder_w

    anchored_pts = {}
    for lm_id, (rx, ry) in ref.items():
        ax = int(player_cx + (rx - ref_cx) * scale)
        ay = int(player_cy + (ry - ref_cy) * scale * 0.95)
        ax = max(10, min(display_w - 10, ax))
        ay = max(10, min(display_h - 10, ay))
        anchored_pts[lm_id] = (ax, ay)

    return anchored_pts


def draw_ghost_and_target_rings(frame, lm, pose_data, display_w, display_h, left_score, right_score):
    """
    Dibuja la silueta fantasma anclada al jugador y los anillos magnéticos
    donde deben colocarse las manos (L_WRIST, R_WRIST) para poses estáticas.
    """
    if pose_data.get('is_freeze'):
        return

    anchored = compute_body_anchored_targets(lm, pose_data, display_w, display_h)
    if not anchored:
        return

    # 1. Brazos fantasma punteados / traslúcidos anclados a los hombros del jugador
    overlay = frame.copy()
    ghost_color = (255, 220, 100)  # Cian/Celeste brillante (BGR)
    for a, b in LEFT_ARM_CONNECTIONS + RIGHT_ARM_CONNECTIONS:
        if a in anchored and b in anchored:
            cv2.line(overlay, anchored[a], anchored[b], ghost_color, 6, cv2.LINE_AA)

    # Anillos magnéticos en las muñecas objetivo (solo si la pose no es puramente de piernas/caderas)
    pulse = int(math.sin(time.time() * 8) * 4)
    for wrist_id, score in [(L_WRIST, left_score), (R_WRIST, right_score)]:
        if wrist_id in anchored:
            tx, ty = anchored[wrist_id]
            ring_color = (0, 255, 100) if score >= 0.85 else ((0, 215, 255) if score >= 0.45 else ghost_color)
            radius = 24 + pulse if score < 0.85 else 18
            cv2.circle(overlay, (tx, ty), radius, ring_color, 3, cv2.LINE_AA)
            cv2.circle(overlay, (tx, ty), 5, ring_color, -1, cv2.LINE_AA)

            # Línea guía desde la muñeca real del jugador hacia el anillo objetivo si aún no llegó
            player_wrist = get_point(lm, wrist_id, display_w, display_h)
            if player_wrist and score < 0.85:
                cv2.line(overlay, player_wrist, (tx, ty), (0, 215, 255), 2, cv2.LINE_AA)

    cv2.addWeighted(overlay, 0.38, frame, 0.62, 0, frame)
```

---

### MEJORA UX 2: Esqueleto "Traffic Light" Continuo (Rojo → Ámbar → Verde Neón)

**Concepto:** En lugar de pasar booleanos `left_ok, right_ok`, el sistema evalúa un score continuo `left_score, right_score ∈ [0.0, 1.0]`.
- `score < 0.40` → **Rojo Coral** `(60, 60, 255)` (Lejos)
- `0.40 <= score < 0.85` → **Ámbar / Amarillo** `(0, 200, 255)` (¡Cerca! Ajustá un poco más)
- `score >= 0.85` → **Verde Neón** `(80, 255, 0)` (¡Posición correcta!)

```python
def score_to_traffic_color(score):
    """Interpola suavemente en BGR entre Rojo (0.0), Ámbar (0.5) y Verde Neón (1.0)."""
    s = max(0.0, min(1.0, float(score)))
    if s < 0.5:
        t = s / 0.5
        # De Rojo (50, 50, 255) a Ámbar (0, 210, 255)
        return (int(50 * (1 - t)), int(50 + 160 * t), 255)
    else:
        t = (s - 0.5) / 0.5
        # De Ámbar (0, 210, 255) a Verde Neón (80, 255, 0)
        return (int(80 * t), int(210 + 45 * t), int(255 * (1 - t)))
```

> **Corrección crítica para Poses Dinámicas Combinadas:**
> En poses como `'Cabeza y Caderas!'`, `'Salto con Brazos!'` o `'Giro y Cabeza!'`, NO forzar `left_ok = True, right_ok = True` a ciegas. Evaluar la condición de los brazos por separado para colorear los brazos en rojo/ámbar si el jugador olvidó poner la mano en la cabeza o levantar los brazos mientras salta.

---

### MEJORA UX 3: Indicadores Visuales Específicos para TODAS las Poses Dinámicas

**Concepto:** Reemplazar el bloque roto de las líneas 808–815 por una función dedicada `draw_dynamic_pose_hud(frame, current_pose, state, lm, display_w, display_h)` que dibuje en pantalla la guía exacta de cada movimiento dinámico y su progreso real (`0.0` a `1.0`):

| Pose Dinámica | Atributo en `PlayerState` | Meta | Guía Visual AR sobre el Cuerpo |
| :--- | :--- | :---: | :--- |
| `Baila! Mueve Caderas` / `Cabeza y Caderas!` | `state.hip_hits` | `6` | Dos arcos verticales neón a izquierda/derecha de la cadera que se iluminan alternadamente al golpear cada lado. |
| `De Lado a Lado!` | `state.move_hits` | `4` | Dos pilares verticales luminosos a los lados del torso (`center_x ± threshold`) con flecha indicando hacia qué lado moverse ahora. |
| `Mueve los Brazos!` | `state.arm_hits` | `6` | Zona horizontal superior (sobre hombros) e inferior (bajo hombros) que se alternan iluminándose (`ARRIBA` / `ABAJO`). |
| `Salto Mortal!` / `Salto con Brazos!` | `state.jump_phase` | `2` | Línea horizontal cian a la altura objetivo de salto con flechas `^^^ ¡SALTA! ^^^` hacia arriba. |
| `Agacharse!` | `state.jump_phase` | `2` | Línea horizontal naranja más abajo de la cadera con flechas `vvv ¡AGÁCHATE! vvv`. |
| `Girando!` / `Giro y Cabeza!` | `state.spin_phase` | `2` | Elipse orbital alrededor de los hombros con texto `"¡DA UNA VUELTA COMPLETA 360°!"` y progreso `0% -> 50% -> 100%`. |

#### Código Listo para Implementar (`draw_dynamic_pose_hud`):

```python
def get_dynamic_progress(pose_name, state):
    """Retorna (actual, meta, etiqueta) según la pose dinámica activa."""
    if 'Caderas' in pose_name:
        return state.hip_hits, 6, f"CADERAS: {state.hip_hits}/6"
    elif 'Lado a Lado' in pose_name:
        return state.move_hits, 4, f"PASOS LATERALES: {state.move_hits}/4"
    elif 'Mueve los Brazos' in pose_name:
        return state.arm_hits, 6, f"BRAZOS: {state.arm_hits}/6"
    elif 'Salto' in pose_name:
        return state.jump_phase, 2, "¡SALTA AHORA!" if state.jump_phase == 0 else "¡ATERRIZA!"
    elif 'Agacharse' in pose_name:
        return state.jump_phase, 2, "¡BAJA LAS CADERAS!" if state.jump_phase == 0 else "¡SUBE!"
    elif 'Gir' in pose_name:
        return state.spin_phase, 2, "¡GIRA 360°!" if state.spin_phase == 0 else "¡COMPLETA EL GIRO!"
    return 0, 1, ""
```

---

### MEJORA UX 4: Banner Superior Central + Barra "Grace Decay" (Zona 2)

En lugar de dibujar la barra `"MANTENE!"` abajo (donde choca con el carril de cartas), colocar un **Banner Central Superior** en `x = (display_w - 420)//2, y = 18`:
- Muestra el nombre de la pose actual en grande con fondo semitransparente oscuro (usando ROI blending).
- Debajo del título (en `y = 68`), muestra la **Barra Unificada de Progreso de Pose** (tanto para el `hold_progress` de poses estáticas como para el progreso `actual/meta` de poses dinámicas o cuenta regresiva de `CONGELADOS!`).

---

### MEJORA UX 5: Carril Inferior 2.0 con "Picto-Cards" y Deslizamiento Suave (Slide Animation)

**Concepto:**
Cada tarjeta del carril inferior (`y = 595..712`) tiene un ancho de `210px` y alto de `110px`, y está dividida internamente en:
1. **Mini-Pictograma Izquierdo (`70x95px`):** Dibuja en miniatura el esqueleto `p['ref']` con el color propio de la pose `p['color']` (o un copo de nieve / alerta roja si es `CONGELADOS!`).
2. **Etiqueta Derecha (`130x95px`):** Nombre de la pose en 2 líneas limpias + badge del tipo (`HOLD` / `RITMO` / `FREEZE`).
3. **Animación de Transición (`queue_slide_offset`):** Cuando `shift_queue()` avanza a la siguiente pose, inicializar `queue_slide_offset = 225.0` y en cada frame hacer `queue_slide_offset *= 0.80`. Sumar `int(queue_slide_offset)` a la coordenada `X` de las tarjetas en cola para que se deslicen físicamente de derecha a izquierda hacia la caja `"¡AHORA!"`.

#### Código para Dibujar Mini-Pictograma dentro de cada Tarjeta del Carril:

```python
def draw_mini_picto(frame, pose_data, x, y, w, h):
    """Dibuja el pictograma vectorial en miniatura dentro de una tarjeta del carril."""
    color = pose_data.get('color', (0, 255, 255))
    if pose_data.get('is_freeze'):
        cv2.circle(frame, (x + w // 2, y + h // 2), 22, (255, 200, 100), 2, cv2.LINE_AA)
        cv2.putText(frame, "**", (x + w // 2 - 14, y + h // 2 + 8), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 2)
        return

    ref = pose_data.get('ref')
    if not ref:
        return
    pts = {k: (int(x + nx * w), int(y + max(0.05, min(0.95, ny)) * h)) for k, (nx, ny) in ref.items()}
    for a, b in SKELETON_CONNECTIONS:
        if a in pts and b in pts:
            cv2.line(frame, pts[a], pts[b], (180, 180, 180), 2, cv2.LINE_AA)
    for a, b in LEFT_ARM_CONNECTIONS + RIGHT_ARM_CONNECTIONS:
        if a in pts and b in pts:
            cv2.line(frame, pts[a], pts[b], color, 3, cv2.LINE_AA)
    if NOSE in pts:
        cv2.circle(frame, pts[NOSE], 6, color, -1, cv2.LINE_AA)
```

---

### MEJORA UX 6: Menú Kinético Controlado con el Cuerpo a 3 Metros (Sin Teclado)

**Concepto:**
Cuando `show_menu == True`, el jugador sigue siendo detectado por MediaPipe (`has_person`). Permitir controlar el menú sin tocar el teclado mediante **gestos intuitivos en pantalla** (manteniendo además el soporte de teclado actual como fallback):
- **Levantar Mano Izquierda sobre el hombro** (durante 0.4s con cooldown) → Subir opción (`selected_idx - 1`).
- **Levantar Mano Derecha sobre el hombro** (durante 0.4s con cooldown) → Bajar opción (`selected_idx + 1`).
- **Ambas Manos Arriba (`check_left_arm_up and check_right_arm_up`)** durante 1.0 segundo → Barra circular/horizontal `"¡INICIANDO JUEGO!"` se llena y lanza la partida (`show_menu = False`).
- **Durante la partida:** Cruzar brazos al pecho (`check_gesture_next`) durante `0.8s` salta la pose; poner **ambas manos en la cintura + inclinarse o mantener 2.0s con gesto de T-Pose en pausa** o un botón en esquina superior que se activa tocándolo con la mano en AR abre el menú.

---

## 4. Checklist de Verificación Visual para el Modelo Implementador

Al finalizar la implementación de este Blueprint en `poses_locas.py`, ejecutar `python test_game.py` y verificar en `test_visual_gameplay.jpg` y `test_visual_fever.jpg`:
- [ ] Ningún texto se superpone con el carril inferior (`y = 590..720`).
- [ ] El banner central superior muestra el nombre de la pose y su barra de progreso limpia.
- [ ] Las tarjetas del carril inferior muestran el mini-esqueleto vectorial a la izquierda del texto.
- [ ] El esqueleto del jugador muestra los anillos magnéticos de destino en las muñecas y colores graduales (rojo/ámbar/verde).
