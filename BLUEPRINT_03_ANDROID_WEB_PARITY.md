# 📱 BLUEPRINT 03: Paridad Total, Corrección de Bugs y Rediseño UI/UX en `android_app/` (PWA / Smart TV)

> **Objetivo para el modelo implementador (Gemini 3.8 Flash):**
> La versión Web/Android (`android_app/game.js`, `index.html`, `style.css`) quedó muy atrasada respecto a `poses_locas.py` y presenta bugs críticos de tiempo y detección. Este documento especifica cómo corregir los bugs y llevar la versión móvil/TV al mismo estándar de UI/UX de última generación.

---

## 1. Bugs Críticos Detectados en `android_app/game.js` (Prioridad Alta)

### Bug Crítico 1: Función `updateGameLoop()` Duplicada y Timer Roto tras Pausa
- En `android_app/game.js`, `function updateGameLoop()` está declarada **dos veces**:
  - Primera definición en **líneas 178–202** (actualiza `timeRemaining = Math.max(0, difficultyTime - elapsed)`).
  - Segunda definición en **líneas 406–429** (sobrescribe la primera en JS y calcula `let left = timeRemaining - elapsed` **sin actualizar `timeRemaining`**).
- **Consecuencia:** Cuando el usuario pausa y despausa el juego (línea 85: `poseStartTime = performance.now() - ((difficultyTime - timeRemaining) * 1000)`), como `timeRemaining` quedó clavado en `difficultyTime`, **el reloj se reinicia siempre al máximo al salir de pausa**.
- **Solución:** Eliminar la primera declaración duplicada (líneas 178–202) y unificar una única `updateGameLoop()` que actualice `timeRemaining` correctamente y gestione también la barra de retención (`holdProgress`).

### Bug Crítico 2: Ausencia Total de Dwell-Time en Poses Estáticas (Falsos Positivos Instantáneos)
- En `android_app/game.js` (líneas 380–389):
  ```javascript
  l_ok = currentPose.checks.l(lm);
  r_ok = currentPose.checks.r(lm);
  success = l_ok && r_ok;
  if (success) {
      currentPose = null;
      handleSuccess();
  }
  ```
- **Consecuencia:** A diferencia de Python (que exige mantener la pose `0.6s`), en Android **basta con que la pose coincida durante 1 solo frame (16ms)** mientras el jugador mueve los brazos al azar para que la dé por completada.
- **Solución:** Implementar el acumulador `holdProgress` con **Grace Decay** (`+dt / 0.55` cuando `l_ok && r_ok`, y `-dt * 0.8` cuando falla) y mostrar el llenado progresivo en `#progress-bar`.

### Bug Crítico 3: Espejado de Canvas CSS (`transform: scaleX(-1)`) Invierte Cualquier Texto en Canvas
- Como `#output-canvas` tiene `transform: scaleX(-1)` en `style.css` (línea 183), si se dibujan textos flotantes (`"¡BOOM!"`, `"¡PERFECTO!"`) dentro del canvas, **salen escritos al revés (en espejo)**.
- **Solución:** Para dibujar texto en `canvasCtx` cuando el elemento tiene `scaleX(-1)`, usar este helper:
  ```javascript
  function drawMirroredText(ctx, text, x, y, font, fillStyle, strokeStyle = '#000') {
      ctx.save();
      ctx.translate(x, y);
      ctx.scale(-1, 1); // Contrarresta el scaleX(-1) del CSS para que el texto se lea al derecho
      ctx.font = font;
      ctx.textAlign = 'center';
      ctx.lineWidth = 4;
      ctx.strokeStyle = strokeStyle;
      ctx.strokeText(text, 0, 0);
      ctx.fillStyle = fillStyle;
      ctx.fillText(text, 0, 0);
      ctx.restore();
  }
  ```

---

## 2. Paridad de Contenido y Mecánicas (De 5 Poses a 18 Poses + Coreografías + Fever + Congelados)

Actualmente `android_app/game.js` solo tiene **5 poses** (frente a las **18 poses** de `poses_locas.py`), no tiene modo Coreografía (`COREOGRAFIAS`), no tiene `"¡CONGELADOS!"`, no tiene racha (`streak`), ni Fever Mode, ni cola de próximas poses.

### 2.1. Portar el Set Completo de Poses y Coreografías a `android_app/game.js`
Implementar en `game.js`:
1. **Unidad Anatómica `getBodyUnit(lm)`** en JS:
   ```javascript
   function getBodyUnit(lm) {
       const dx = lm[L_SHOULDER].x - lm[R_SHOULDER].x;
       const dy = lm[L_SHOULDER].y - lm[R_SHOULDER].y;
       return Math.max(0.10, Math.hypot(dx, dy));
   }
   ```
2. **Checks adicionales en JS** (recordando que en `game.js` los landmarks vienen crudos sin flip previo de imagen, por lo que la izquierda de la imagen es la derecha del usuario espejado):
   - `check_left_hand_on_hip`, `check_right_hand_on_hip`
   - `check_left_hand_on_head`, `check_right_hand_on_head`
   - `check_jump`, `check_squat`, `check_spin`, `check_flail_arms`, `check_move_side_to_side`
   - `check_gesture_next` (Gesto Wakanda / Brazos cruzados durante 0.8s para saltar pose en móvil sin tocar la pantalla).
3. **Diccionario `COREOGRAFIAS`** para `macarena.wav`, `asereje.wav` y `ymca.wav`, agregando el botón `"Coreografía"` en `#mode-group` de `index.html`:
   ```html
   <div class="btn-group" id="mode-group">
       <button class="opt-btn active" data-val="arcade">Arcade</button>
       <button class="opt-btn" data-val="coreo">Coreografía</button>
       <button class="opt-btn" data-val="practice">Práctica</button>
   </div>
   ```

---

## 3. Rediseño UI/UX de `android_app/` (Mobile Portrait + Smart TV Landscape)

### 3.1. Problema Actual del Banner Central en `style.css`
En `style.css` (líneas 216–228):
```css
.instruction {
    font-size: 3rem;
    background: rgba(0,0,0,0.4);
    padding: 20px;
    margin: auto 0; /* <-- ¡ESTO LO PONE EN EL MEDIO EXACTO DE LA PANTALLA TAPANDO LA CARA Y TORSO DEL JUGADOR! */
}
```
- **Solución en `style.css`:**
  Mover `#pose-instruction` a la parte superior (debajo del header) con un diseño compacto tipo **Glassmorphism Pill**, dejando el **100% del centro de la pantalla despejado** para ver el cuerpo, el Ghost Silhouette y las partículas:
  ```css
  .instruction {
      font-size: clamp(1.5rem, 4vw, 2.6rem);
      font-weight: 900;
      text-align: center;
      text-shadow: 0 3px 8px rgba(0,0,0,0.9);
      background: rgba(10, 10, 28, 0.65);
      padding: 10px 24px;
      border-radius: 999px;
      border: 2px solid rgba(255, 255, 255, 0.25);
      backdrop-filter: blur(8px);
      align-self: center;
      margin-top: 8px;
      margin-bottom: auto; /* Empuja el resto hacia abajo sin ocupar el centro */
  }
  ```

### 3.2. Carril Inferior de Próximas Poses (HTML/CSS Overlay) + Barra Fever
En `android_app/index.html`, dentro de `#ui-layer`, agregar:
1. **Indicador de Racha y Fever** debajo del puntaje en `.header`:
   ```html
   <div class="combo-pill" id="combo-pill">🔥 Racha x1</div>
   <div class="fever-bar-wrap"><div id="fever-bar"></div></div>
   ```
2. **Cola Visual de Próximas Poses (`#queue-strip`)** encima de `#progress-container`:
   ```html
   <div id="queue-strip" class="queue-strip">
       <!-- Renderizado dinámicamente por game.js con la pose actual y las próximas 3 -->
   </div>
   ```

### 3.3. Sistema de Partículas y Ghost Silhouette en Canvas 2D (`game.js`)
Agregar en `game.js` la clase `CanvasParticles` y `drawGhostTarget(ctx, lm, currentPose, drawX, drawY, drawW, drawH)` para que al completar una pose o lograr un hit de cadera estallen partículas de colores en 60 FPS sobre el canvas, igual que en la versión Desktop.
