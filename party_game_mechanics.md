# 🎮 Mecánicas Innovadoras para Party Games con Pose Estimation

Más allá de imitar coreografías clásicas, el uso de Pose Estimation (como MediaPipe o YOLOv8-pose) abre un abanico de mecánicas físicas interactivas ideales para jugar con amigos en una misma habitación. Aquí exploramos varias ideas y conceptos:

## 1. ❄️ "Congelados" (Estilo Luz Roja, Luz Verde)
**Concepto:** Mientras la música suena, los jugadores deben bailar libremente o seguir ciertos pasos. En cualquier momento aleatorio, la música se detiene y la pantalla indica "¡CONGELADOS!".
**Mecánica con Pose:** El sistema guarda las coordenadas de los landmarks clave (nariz, muñecas, tobillos) en el momento exacto en que la música se detiene. Durante los siguientes 3 a 5 segundos, se calcula la distancia euclidiana de esos puntos en tiempo real. Si el movimiento supera un umbral de tolerancia, el jugador es penalizado (pierde puntos, queda eliminado o su avatar explota).

## 2. 🤝 "Figuras Cooperativas" (Co-Op Shapes)
**Concepto:** Aparece en pantalla la silueta de una figura que requiere más de un jugador para completarse (por ejemplo: un corazón gigante, la letra "M", o la fusión de Dragon Ball).
**Mecánica con Pose:** El sistema evalúa a múltiples jugadores de forma concurrente. No solo verifica la postura individual, sino la **distancia relativa entre los jugadores**. Por ejemplo, para hacer un corazón, la muñeca derecha del Jugador 1 debe estar a menos de `X` píxeles de la muñeca izquierda del Jugador 2, y ambas deben estar por encima de sus cabezas.

## 3. 💣 Mecánicas de "Sabotaje" Físico
**Concepto:** Como en Mario Kart, donde lanzas caparazones, pero con tu cuerpo.
**Mecánica con Pose:** Un jugador puede realizar un gesto específico y oculto (ej. poner los brazos en "X" sobre el pecho o hacer el gesto de lanzar una bola de fuego) para activar un sabotaje. Al detectarlo, la pantalla del jugador rival se llena de tinta virtual, su música se acelera o sus controles se invierten. El jugador rival puede anular el sabotaje si detecta la animación entrante y se agacha físicamente a tiempo (evaluando la coordenada 'y' de la nariz).

## 4. 🧱 Esquivar Obstáculos Físicos ("Hole in the Wall")
**Concepto:** Al estilo del programa "El Muro Infernal". Un muro virtual se acerca rápidamente en la pantalla con una silueta recortada.
**Mecánica con Pose:** En los últimos milisegundos antes de que el muro "golpee", el sistema valida si los hombros, codos y rodillas del jugador están dentro de una caja delimitadora (bounding box) generada por la silueta del muro.

---

## 💻 Implementación Base en Python (Lógica)

A continuación, se presenta la lógica base para implementar dos de estas mecánicas utilizando las coordenadas (landmarks) extraídas por MediaPipe o un sistema similar.

### Lógica para "Congelados"

```python
import math
import mediapipe as mp

def check_freeze(previous_landmarks, current_landmarks, threshold=0.05):
    """
    Compara los landmarks actuales con los guardados al inicio del congelamiento.
    Si la distancia de movimiento supera el umbral, el jugador se ha movido.
    """
    if not previous_landmarks or not current_landmarks:
        return False
    
    movement = 0.0
    # Puntos clave a monitorear: Nariz, Muñecas y Tobillos
    key_points = [
        mp.solutions.pose.PoseLandmark.NOSE,
        mp.solutions.pose.PoseLandmark.LEFT_WRIST,
        mp.solutions.pose.PoseLandmark.RIGHT_WRIST
    ]
    
    for kp in key_points:
        prev = previous_landmarks[kp]
        curr = current_landmarks[kp]
        # Distancia euclidiana entre el punto previo y el actual
        dist = math.hypot(curr.x - prev.x, curr.y - prev.y)
        movement += dist
        
    # Si la suma del movimiento de los puntos clave es mayor al umbral, el jugador falló
    return movement > threshold
```

### Lógica para "Figuras Cooperativas" (Ej: Corazón con los brazos)

```python
def check_coop_heart(landmarks_p1, landmarks_p2, threshold=0.08):
    """
    Verifica si el Jugador 1 (izquierda) y el Jugador 2 (derecha)
    están uniendo sus manos en alto para formar un corazón.
    """
    if not landmarks_p1 or not landmarks_p2:
        return False

    # 1. Verificar unión: La muñeca derecha del P1 debe tocar la muñeca izquierda del P2
    p1_wrist = landmarks_p1[mp.solutions.pose.PoseLandmark.RIGHT_WRIST]
    p2_wrist = landmarks_p2[mp.solutions.pose.PoseLandmark.LEFT_WRIST]
    
    hands_touching = math.hypot(p1_wrist.x - p2_wrist.x, p1_wrist.y - p2_wrist.y) < threshold
    
    # 2. Altura: Las muñecas unidas deben estar por encima de los hombros (brazos en alto)
    p1_shoulder = landmarks_p1[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
    p2_shoulder = landmarks_p2[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
    
    # En MediaPipe, el eje Y decrece hacia arriba (Y=0 es el tope de la imagen)
    arms_up = (p1_wrist.y < p1_shoulder.y) and (p2_wrist.y < p2_shoulder.y)
    
    return hands_touching and arms_up
```
