# 🚀 PLAN MAESTRO DE MEJORAS (UI/UX + IMÁGENES CON INTENCIÓN + CORE + AUTO-AUDITORÍA) — GUÍA PARA GEMINI 3.8 FLASH

Este repositorio cuenta con **5 Blueprints de Ingeniería y Diseño** + el motor ejecutable **[`visual_ui_auditor.py`](file:///C:/Users/admin/Juegos/poses_locas/visual_ui_auditor.py)** y las **6 Láminas Visuales de Referencia (`diseno_01_*.jpg` a `diseno_06_*.jpg`)** para que un modelo rápido y económico (**Gemini 3.8 Flash**) pueda implementar todo de principio a fin y **autotestear / auditar visualmente cada pantalla con un Subagente Especialista en UI/UX**.

---

## 📂 Índice de Documentos y Herramientas del Proyecto

1. **[BLUEPRINT_01_UI_UX_RADICAL.md](file:///C:/Users/admin/Juegos/poses_locas/BLUEPRINT_01_UI_UX_RADICAL.md)**
   - Mapa Espacial HUD 1280×720 de **5 Zonas Libres de Colisiones**.
   - **Body-Anchored Ghost Silhouette & Anillos Magnéticos** proyectados sobre el cuerpo del jugador.
   - **Esqueleto "Traffic Light" Continuo (Rojo → Ámbar → Verde Neón)** y **Carril Inferior 2.0 con Mini-Pictogramas (`draw_mini_picto`)** + **Menú Kinético sin Teclado**.
2. **[BLUEPRINT_02_CORE_POSE_ENGINE_Y_ARQUITECTURA.md](file:///C:/Users/admin/Juegos/poses_locas/BLUEPRINT_02_CORE_POSE_ENGINE_Y_ARQUITECTURA.md)**
   - **Normalización Anatómica (`get_body_unit`):** invarianza total a la distancia y estatura (niños vs adultos).
   - **Acumulador "Grace Decay" para Dwell-Time** y **3 Tiers de Juicio (`PERFECTO!!`, `GENIAL!`, `BIEN!`)**.
   - **ROI Alpha-Blending (`blend_rect_roi`)** y **Beat-Pulse Engine (`SONG_BPM`)**.
3. **[BLUEPRINT_04_INTENCION_VISUAL_IMAGENES_Y_VARIEDAD_MOVIMIENTOS.md](file:///C:/Users/admin/Juegos/poses_locas/BLUEPRINT_04_INTENCION_VISUAL_IMAGENES_Y_VARIEDAD_MOVIMIENTOS.md)**
   - **Recuperación y Auto-Limpieza de las 8 Ilustraciones `pose_*.jpg`** (incluyendo fix automático del fondo blanco en `pose_letra_y.jpg`).
   - **Coach Holográfico Animado con Piernas, Suelo y Flechas de Intención (`get_animated_ref_points` + `draw_intent_arrows_in_box`)**.
   - **8 Poses Nuevas y Recuperadas:** *Pose de Mono*, *Fiebre Disco*, *Avión Supersónico*, *Boxeo Rápido*, *Guitarra Rockera*, *Letra Y*, *Letra O* y *Mueve la Cabeza*.
   - **Variabilidad Dinámica:** *Pose Relámpago (x2)*, *Gold Move (+500)*, *Groove Bonus Pasivo (+15)* y *Estelas de Manos (`HandTrailSystem`)*.
4. **[BLUEPRINT_05_SISTEMA_AUDITORIA_SUBAGENTE_UI_UX.md](file:///C:/Users/admin/Juegos/poses_locas/BLUEPRINT_05_SISTEMA_AUDITORIA_SUBAGENTE_UI_UX.md)** + **[visual_ui_auditor.py](file:///C:/Users/admin/Juegos/poses_locas/visual_ui_auditor.py)**
   - **Barrera 1 (`UILayoutAuditor` - 5 Gates Matemáticos):** detecta colisiones de bounding boxes, invasión de zona central, fuentes chicas (`< 0.48`), elementos fuera de `1280×720` y caracteres no-ASCII (`?` en OpenCV).
   - **Barrera 2 (`ui-ux-visual-critic` Subagente Especialista):** inspecciona con visión multimodal (`read_file`) todas las imágenes `.jpg` generadas, califica del 1 al 10 y obliga a corregir defectos antes de enviar las pantallas al celular Motorola (`moto-g24-power`) por Tailscale.
5. **[BLUEPRINT_03_ANDROID_WEB_PARITY.md](file:///C:/Users/admin/Juegos/poses_locas/BLUEPRINT_03_ANDROID_WEB_PARITY.md)**
   - Corrección de bugs críticos (`updateGameLoop` duplicada y falta de Dwell-Time) y paridad completa en `android_app/`.

---

## 🖼️ Láminas Visuales de Diseño (Ya generadas y enviadas a `moto-g24-power`)

- [`diseno_01_comparativa_antes_vs_despues.jpg`](file:///C:/Users/admin/Juegos/poses_locas/diseno_01_comparativa_antes_vs_despues.jpg) — Diagnóstico de errores actuales vs Mapa de 5 Zonas.
- [`diseno_02_hud_gameplay_ghost_y_semaforo.jpg`](file:///C:/Users/admin/Juegos/poses_locas/diseno_02_hud_gameplay_ghost_y_semaforo.jpg) — Nuevo HUD en Gameplay con Ghost Pose, Anillos Magnéticos, Semáforo y Picto-Cards.
- [`diseno_03_poses_dinamicas_e_intencion.jpg`](file:///C:/Users/admin/Juegos/poses_locas/diseno_03_poses_dinamicas_e_intencion.jpg) — Comunicación de Intención en Movimientos Dinámicos (Caderas, Salto vs Agacharse, Giro 360 y Estelas).
- [`diseno_04_catalogo_nuevas_poses_e_iconos.jpg`](file:///C:/Users/admin/Juegos/poses_locas/diseno_04_catalogo_nuevas_poses_e_iconos.jpg) — Las 8 ilustraciones `pose_*.jpg` limpiadas + las Nuevas Poses Expresivas.
- [`diseno_05_eventos_gold_move_y_menu_kinetico.jpg`](file:///C:/Users/admin/Juegos/poses_locas/diseno_05_eventos_gold_move_y_menu_kinetico.jpg) — Modificadores Gold/Speed, Groove Bonus y Menú Kinético sin Teclado.
- [`diseno_06_arquitectura_subagente_auditor_ui_ux.jpg`](file:///C:/Users/admin/Juegos/poses_locas/diseno_06_arquitectura_subagente_auditor_ui_ux.jpg) — Pipeline de Auto-Testeo (5 Gates + Subagente Crítico UI/UX + Tailscale Drop).

---

## 🤖 Prompts Listos para Copiar y Pegar en Gemini 3.8 Flash

### 🔹 FASE 1: Motor Core, Normalización Anatómica y Grace Decay (`poses_locas.py`)
> **Prompt para Gemini 3.8 Flash:**
> ```text
> Lee detalladamente `BLUEPRINT_02_CORE_POSE_ENGINE_Y_ARQUITECTURA.md` y `poses_locas.py`.
> Implementa en `poses_locas.py` todos los cambios del Blueprint 02:
> 1. Agrega `get_body_unit(lm)`, `calc_angle_2d`, `distance_to_score` y las funciones `score_*` continuas (0.0 a 1.0) manteniendo intactas las firmas booleanas `check_*` para compatibilidad con `test_game.py`.
> 2. Reemplaza el sistema binario `match_start = None` por el acumulador `hold_progress` con "Grace Decay" y agrega los 3 tiers de juicio ("PERFECTO!!", "GENIAL!", "BIEN!") según el tiempo de resolución (usando solo caracteres ASCII limpios para OpenCV).
> 3. Agrega `blend_rect_roi` para optimizar el renderizado de cajas semitransparentes sin copiar el frame entero, y agrega `SONG_BPM` + `get_beat_pulse`.
> 4. Reemplaza `RTSP_URL` hardcodeada por `os.environ.get("POSES_RTSP_URL", "")` en los scripts Python.
> Ejecuta `python test_game.py` al terminar para verificar que todos los tests pasen.
> ```

### 🔹 FASE 2: Imágenes `pose_*.jpg`, Coach Animado con Intención y Nuevas Poses Variadas (`poses_locas.py`)
> **Prompt para Gemini 3.8 Flash:**
> ```text
> Lee detalladamente `BLUEPRINT_04_INTENCION_VISUAL_IMAGENES_Y_VARIEDAD_MOVIMIENTOS.md` y `poses_locas.py`.
> Implementa todas las mejoras del Blueprint 04 en `poses_locas.py`:
> 1. Agrega `load_pose_illustration` con detección automática de fondo blanco/negro y vincula los 8 archivos `pose_*.jpg` a sus respectivas poses en `POSES`.
> 2. Implementa `get_animated_ref_points` (con rodillas, tobillos y animación en vivo según el movimiento) y `draw_intent_arrows_in_box` para que en la referencia se entienda inmediatamente la intención física (Salto, Agacharse, Giro 360, Caderas, Brazos) junto con la ilustración `pose_*.jpg`.
> 3. Agrega las nuevas poses expresivas y dinámicas (`Letra Y!`, `Letra O!`, `Mueve la Cabeza!`, `Pose de Mono!`, `Fiebre Disco!`, `Avion Supersonico!`, `Boxeo Rapido!`, `Guitarra Rockera!`).
> 4. Agrega los modificadores dinámicos en `shift_queue` (`SPEED` Relámpago y `GOLD` Move), el Bonus Pasivo de Groove de caderas y la clase `HandTrailSystem` para estelas de energía en las manos.
> Ejecuta `python test_game.py` para validar que todo funcione sin errores.
> ```

### 🔹 FASE 3: Rediseño UI/UX Radical + Auditoría Automática con Subagente Especialista y Envío a Motorola
> **Prompt para Gemini 3.8 Flash:**
> ```text
> Lee detalladamente `BLUEPRINT_01_UI_UX_RADICAL.md`, `BLUEPRINT_05_SISTEMA_AUDITORIA_SUBAGENTE_UI_UX.md`, `visual_ui_auditor.py`, `poses_locas.py` y `test_game.py`.
> 1. Implementa el rediseño completo de UI/UX en `poses_locas.py` siguiendo exactamente el diseño de `diseno_02_hud_gameplay_ghost_y_semaforo.jpg` y `BLUEPRINT_01_UI_UX_RADICAL.md` (Mapa de 5 Zonas, Ghost Silhouette y Anillos Magnéticos, Esqueleto Semáforo, Progreso Dinámico Universal, Carril 2.0 con Mini-Pictogramas y Menú Kinético).
> 2. Actualiza `run_visual_tests()` en `test_game.py` para que utilice `UILayoutAuditor` de `visual_ui_auditor.py` y genere capturas de todos los estados (`test_visual_gameplay.jpg`, `test_visual_fever.jpg`, `test_visual_dynamic.jpg`, `test_visual_menu.jpg`).
> 3. Ejecuta `python test_game.py` y `python visual_ui_auditor.py` y asegúrate de que los 5 Gates Matemáticos pasen con 0 violaciones.
> 4. OBLIGATORIO (Protocolo Blueprint 05): Define e invoca al subagente `ui-ux-visual-critic` (`define_subagent` + `invoke_subagent`) para que lea con `read_file` todas las imágenes `.jpg` generadas y audite visualmente las pantallas. Si reporta cualquier defecto o puntaje < 9/10, corrige el código, regenera las capturas y vuelve a auditar.
> 5. Cuando esté aprobado (>= 9/10), envía las capturas al celular Motorola con:
>    `tailscale file cp test_visual_gameplay.jpg test_visual_fever.jpg moto-g24-power:`
> ```

### 🔹 FASE 4: Paridad Total y Corrección de Bugs en App Móvil/TV (`android_app/`)
> **Prompt para Gemini 3.8 Flash:**
> ```text
> Lee detalladamente `BLUEPRINT_03_ANDROID_WEB_PARITY.md` y los archivos `android_app/index.html`, `android_app/style.css` y `android_app/game.js`.
> Implementa todas las correcciones y mejoras del Blueprint 03 y porta las poses y el Coach Animado del Blueprint 04 a `android_app/game.js`.
> ```
