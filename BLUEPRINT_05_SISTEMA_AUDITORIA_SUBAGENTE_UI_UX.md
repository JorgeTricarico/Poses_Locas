# 🔍 BLUEPRINT 05: Sistema de Auto-Testeo de Pantallas y Auditoría por Subagente Especialista UI/UX

> **Objetivo para el modelo implementador (Gemini 3.8 Flash):**
> Este documento establece el **Protocolo Permanente de Garantía de Calidad Visual (Visual QA Loop)** del proyecto `poses_locas`. Ningún cambio en pantallas, HUD, poses o menús se considera terminado hasta aprobar tanto los **5 Gates Matemáticos (`visual_ui_auditor.py`)** como la **Inspección Visual Multimodal de un Subagente Especialista en UI/UX**.

---

## 1. ¿Por qué existe este Protocolo en el Proyecto?

Cuando un modelo genera código gráfico en OpenCV (`cv2.putText`, `cv2.rectangle`, `cv2.line`) o en HTML/Canvas sin "mirar" el resultado renderizado, ocurren errores visuales clásicos:
- **Colisiones de coordenadas:** Textos que pisan barras o bordes (como ocurría en `y = 640..720` en `test_visual_gameplay.jpg`).
- **Caracteres corruptos (`?`):** Las fuentes Hershey de OpenCV solo soportan ASCII (`32..126`). Si el modelo escribe `¡`, `¿`, `°`, tildes o emojis (`⚡`, `🌟`), OpenCV dibuja signos de interrogación `?`.
- **Poses incomprensibles:** Dibujos de palitos sin piernas, sin suelo o sin flechas donde el usuario no entiende si debe saltar, agacharse o girar.
- **Obstrucción del jugador:** Elementos colocados en el centro de la pantalla que tapan el cuerpo del jugador.

Para erradicar esto de raíz, el proyecto incorpora una **arquitectura de doble barrera**:
1. **Barrera 1 (Determinista / Matemática):** El script [`visual_ui_auditor.py`](file:///C:/Users/admin/Juegos/poses_locas/visual_ui_auditor.py) y la clase `UILayoutAuditor` con **5 Gates Automáticos**.
2. **Barrera 2 (Cognitiva / Visual):** Un **Subagente Especialista en UI/UX (`ui-ux-auditor`)** invocado mediante `define_subagent` + `invoke_subagent` que inspecciona con visión multimodal (`read_file`) todas las imágenes `.jpg` generadas y exige correcciones si la nota es menor a **9/10**.

---

## 2. Los 5 Gates Matemáticos de `UILayoutAuditor` (`visual_ui_auditor.py`)

Cualquier pantalla renderizada en los tests visuales debe registrar sus elementos en `UILayoutAuditor`:

| Gate | Nombre | Qué verifica automáticamente |
| :---: | :--- | :--- |
| **Gate 1** | **Zero UI Overlap** | Calcula la intersección de *bounding boxes* `(x1, y1, x2, y2)` entre todos los textos, barras y paneles registrados. Falla si dos elementos de distintos grupos se pisan en más de `2px`. |
| **Gate 2** | **Center Safe-Zone** | Verifica que ningún panel ni texto fijo invada el rectángulo central donde se mueve el cuerpo del jugador (`x: 370..890, y: 130..555`). |
| **Gate 3** | **3-Meter Legibility** | Verifica que ningún texto tenga `scale < 0.48` (ilegible a 2.5–3 metros de distancia de la TV/monitor). |
| **Gate 4** | **Viewport Bounds** | Verifica que ningún texto ni caja se corte ni salga fuera de los límites `0..1280` × `0..720`. |
| **Gate 5** | **OpenCV ASCII Hygiene** | Escanea cada string pasado a `cv2.putText` y falla si contiene cualquier carácter con `ord(c) > 126` (como `¡`, `¿`, `°`, tildes o emojis que OpenCV renderiza como `?`). |

### Cómo ejecutar la Barrera 1:
```powershell
python visual_ui_auditor.py
python test_game.py
```
Esto genera el archivo `ui_audit_report.json` y las capturas `.jpg` de todos los estados del juego.

---

## 3. Protocolo de Invocación del Subagente Especialista UI/UX (Barrera 2)

Siempre que **Gemini 3.8 Flash** (o cualquier agente) modifique el código visual de `poses_locas.py`, `test_game.py` o `android_app/`, **DEBE** ejecutar estos pasos antes de finalizar su respuesta:

### Paso A: Definir el Subagente Especialista (una vez por sesión)
Usar la herramienta `define_subagent` con esta configuración exacta:

- **`Name`**: `ui-ux-visual-critic`
- **`Description`**: `Especialista senior en UI/UX de videojuegos rítmicos y AR (estilo Just Dance / WarioWare). Audita capturas de pantalla renderizadas buscando defectos visuales, problemas de legibilidad a 3 metros y claridad de intención de poses.`
- **`EnableWriteTools`**: `false` (Solo lectura e inspección visual imparcial)
- **`SystemPrompt`**:
  ```text
  Eres un Director de Arte y Auditor implacable de UI/UX especializado en juegos de cámara y movimiento corporal (Just Dance, Ring Fit, Kinect).
  Tu única misión es inspeccionar con `read_file` las imágenes .jpg renderizadas del juego y auditarlas con ojo clínico.
  Evalúa cada imagen en 5 categorías (0 a 2 puntos cada una, total 10 puntos):
  1. CERO SOLAPAMIENTOS Y BORDES LIMPIOS: ¿Algún texto pisa una línea, borde de caja, barra o ícono? ¿Algún texto se sale de su recuadro?
  2. CERO CARACTERES ROTOS: ¿Aparece algún signo '?' espurio por emojis o caracteres no-ASCII en OpenCV?
  3. LEGIBILIDAD A 3 METROS Y CONTRASTE: ¿Puede un jugador parado a 3 metros leyendo en 0.3 segundos distinguir el nombre de la pose, el puntaje y las tarjetas del carril?
  4. INTENCIÓN FÍSICA DE LA POSE (0.2s Rule): Mirando el Coach/Esqueleto y las flechas, ¿se entiende instantáneamente qué deben hacer los brazos, piernas y torso (ej. diferencia entre Salto, Agacharse, Giro 360, Caderas)?
  5. ZONA CENTRAL DESPEJADA: ¿El centro de la pantalla permite ver el cuerpo del jugador, la Ghost Pose y los anillos magnéticos sin textos molestos encima?

  Devuelve SIEMPRE un dictamen estructurado:
  - PUNTAJE TOTAL: X/10
  - ESTADO: APROBADO (>= 9/10) o RECHAZADO (< 9/10)
  - LISTA EXACTA DE DEFECTOS VISUALES (indicando archivo .jpg, zona de la pantalla y coordenada aproximada a corregir).
  ```

### Paso B: Invocar al Subagente (`invoke_subagent`) sobre las Capturas Generadas
Llamar a `invoke_subagent`:
- **`TypeName`**: `ui-ux-visual-critic`
- **`Role`**: `Auditor Visual UI/UX de Pantallas`
- **`Prompt`**:
  ```text
  Lee con `read_file` las siguientes imágenes recién generadas en C:\Users\admin\Juegos\poses_locas:
  - test_visual_gameplay.jpg
  - test_visual_fever.jpg
  - diseno_01_comparativa_antes_vs_despues.jpg
  - diseno_02_hud_gameplay_ghost_y_semaforo.jpg
  - diseno_03_poses_dinamicas_e_intencion.jpg
  - diseno_04_catalogo_nuevas_poses_e_iconos.jpg
  - diseno_05_eventos_gold_move_y_menu_kinetico.jpg
  - diseno_06_arquitectura_subagente_auditor_ui_ux.jpg
  Además lee `ui_audit_report.json`.
  Audita cada imagen siguiendo tu rúbrica de 10 puntos y dime si están APROBADAS o qué coordenadas/textos deben corregirse.
  ```

### Paso C: Bucle de Corrección y Envío a Celular Motorola por Tailscale
1. Si el subagente devuelve `RECHAZADO (< 9/10)` o reporta cualquier defecto visual, el agente principal **corrige las coordenadas/colores/textos**, vuelve a correr `python visual_ui_auditor.py` y `python test_game.py`, y verifica la corrección.
2. Una vez **APROBADO (>= 9/10)**, envía las capturas finales al celular Motorola del usuario mediante Tailscale Drop:
   ```powershell
   tailscale file cp test_visual_gameplay.jpg test_visual_fever.jpg moto-g24-power:
   ```
