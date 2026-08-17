# Mecánicas de Juegos Rítmicos: Gamificación, Feedback y Scoring

Este informe detalla las técnicas de diseño de juegos comerciales (como Just Dance, DDR y osu!) y propone cómo adaptar estas mecánicas para un juego de baile utilizando YOLO y OpenCV en Python.

## 1. Gamificación y "Juice" (Game Feel)

El "Juice" es lo que hace que un juego se sienta vivo y gratificante. Los juegos rítmicos lo logran mediante:
- **Multiplicadores de Racha (Combos):** Mantener una racha de movimientos "Perfectos" o "Buenos" incrementa un multiplicador (ej. x2, x4). Si el jugador falla ("Malo" o "Miss"), el multiplicador se reinicia. Esto crea tensión y recompensa la consistencia.
- **Fever Time / Frenesí:** Una barra que se llena al acertar movimientos. Al activarse (automática o manualmente), la pantalla cambia visualmente (colores vibrantes, luces) y los puntos obtenidos se multiplican masivamente por un tiempo limitado.
- **Gold Moves:** Movimientos específicos en la coreografía que otorgan muchos más puntos (ej. 5x) que un movimiento normal. Fallarlos afecta drásticamente el puntaje final.

## 2. Feedback Visual: "Perfecto" vs "Malo"

El feedback visual debe ser inmediato y claro, comunicando el grado de éxito sin tapar la visión del jugador.

*   **Perfecto (Perfect/Super):**
    *   **Visuales:** Colores vibrantes (dorado, neón), partículas explosivas, destellos en pantalla ("screen-space flashes"), texto emergente dinámico ("Perfect!").
    *   **Audio:** Un sonido agudo, satisfactorio y nítido que complementa la música.
*   **Malo (Bad/Miss o X):**
    *   **Visuales:** Colores desaturados (gris, rojo opaco), ausencia de partículas. La interfaz o el texto pueden temblar (ui-shake) para indicar error.
    *   **Audio:** Un sonido hueco o grave ("thud") que desentona intencionalmente de la música.

## 3. Propuesta de Adaptación con YOLO y OpenCV

Para nuestro juego de baile con YOLO, podemos evaluar la similitud entre los "landmarks" (puntos clave del esqueleto) del jugador y un esqueleto de referencia en un momento dado.

### Propuesta de Mecánicas:
1. **Scoring Continuo:** Usar la Distancia del Coseno o el Error Cuadrático Medio (MSE) entre los ángulos de las articulaciones del jugador y la referencia.
2. **Ventanas de Tiempo:** Evaluar el movimiento en el "beat" exacto.
3. **Feedback en OpenCV:** Dibujar el esqueleto del jugador cambiando de color según la precisión, y superponer texto con efectos.

### Ejemplo de Pseudocódigo (Python/OpenCV):

```python
import cv2
import numpy as np

# Variables de estado del juego
combo = 0
fever_gauge = 0
fever_active = False
multiplier = 1

def calculate_accuracy(player_landmarks, reference_landmarks):
    # Simulación de cálculo de precisión (0.0 a 1.0)
    # Aquí usaríamos similitud del coseno entre los vectores del esqueleto (YOLO)
    accuracy = np.random.uniform(0.5, 1.0) 
    return accuracy

def get_judgment(accuracy):
    if accuracy >= 0.90: return "PERFECT"
    elif accuracy >= 0.75: return "GOOD"
    else: return "BAD"

def apply_juice(frame, judgment, center_pos):
    global combo, fever_gauge, fever_active, multiplier
    
    # Colores en BGR para OpenCV
    colors = {
        "PERFECT": (0, 215, 255), # Dorado/Amarillo
        "GOOD": (0, 255, 0),      # Verde
        "BAD": (0, 0, 255)        # Rojo
    }
    
    color = colors[judgment]
    text = f"{judgment}!"
    
    # Actualizar Lógica de Combo y Fever
    if judgment in ["PERFECT", "GOOD"]:
        combo += 1
        fever_gauge = min(100, fever_gauge + 5)
    else:
        combo = 0
        multiplier = 1
        # Efecto de temblor (Screen Shake) simulado
        M = np.float32([[1, 0, np.random.randint(-10, 10)], [0, 1, np.random.randint(-10, 10)]])
        frame = cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))
        
    if fever_gauge >= 100:
        fever_active = True
        multiplier = 2
        # Aplicar filtro visual de Fever Time (ej. tinte morado/rosado)
        fever_overlay = np.full(frame.shape, (255, 0, 255), np.uint8)
        frame = cv2.addWeighted(frame, 0.8, fever_overlay, 0.2, 0)
        
    # Dibujar texto de Judgment (Feedback Visual)
    font = cv2.FONT_HERSHEY_DUPLEX
    scale = 1.5 if judgment == "PERFECT" else 1.0
    thickness = 3
    
    # Sombra para contraste
    cv2.putText(frame, text, (center_pos[0]+2, center_pos[1]+2), font, scale, (0,0,0), thickness+1)
    cv2.putText(frame, text, center_pos, font, scale, color, thickness)
    
    # Mostrar Combo
    if combo > 5:
        cv2.putText(frame, f"{combo} COMBO", (50, 50), font, 1.2, (255, 255, 255), 2)
        
    return frame
```
