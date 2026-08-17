# Análisis de Arquitectura: Juegos de Baile Open Source (Pose Estimation)

Tras analizar diversos repositorios en GitHub (como *JustMove*, *Mimeflow*, *Smart-Dance* y *Dance-with*), aquí se detalla cómo implementan sus mecánicas en la práctica.

## 1. Pipeline de Evaluación y Estructura del Código

Los proyectos más robustos **no** utilizan colisiones de cajas (tipo Beat Saber) para evaluar el cuerpo completo, ya que este enfoque sufre de problemas de escalabilidad respecto a la altura del jugador y su distancia a la cámara. En su lugar, utilizan:

*   **Vectores Normalizados y Ángulos (Joint Angles):** En lugar de medir si una mano tocó la coordenada `(X, Y)`, el motor calcula el ángulo formado por articulaciones clave (por ejemplo: hombro-codo-muñeca). Esto hace que la evaluación sea **invariante a la escala y traslación**.
*   **Dynamic Time Warping (DTW) de Ventana Deslizante:** Es casi imposible que el jugador se mueva en el frame exacto que el video de referencia. Para perdonar ligeros desfases de ritmo (adelantos o retrasos), no se evalúa estrictamente frame a frame. En su lugar, se mantiene un *buffer* (por ejemplo, los últimos 15 frames) y se usa DTW para encontrar la mejor alineación temporal entre el movimiento reciente del jugador y la ventana de la coreografía esperada.
*   **Ponderación (Weighting):** Se asignan distintos multiplicadores a las extremidades (manos, pies) sobre el torso central, pues capturan mejor la expresión del baile.

## 2. Formato de Coreografías

No se procesa el video del bailarín original en tiempo real, ya que sería costoso y redundante. Las coreografías se pre-procesan y se guardan como series temporales, habitualmente en formato **JSON** o **CSV**. 

Un archivo de coreografía típico almacena la pose frame a frame:

```json
{
  "metadata": {
    "fps": 30,
    "song": "cancion_ejemplo",
    "difficulty": "hard"
  },
  "frames": [
    {
      "frame": 1,
      "timestamp_ms": 33.3,
      "keypoints": {
        "left_shoulder": {"x": 0.5, "y": 0.2, "z": -0.1},
        "right_shoulder": {"x": 0.6, "y": 0.2, "z": -0.1}
      },
      "angles": {
        "left_elbow_angle": 145.2,
        "right_elbow_angle": 160.0,
        "left_knee_angle": 175.5
      }
    }
  ]
}
```

## 3. Patrones de Diseño y Código Real

**Patrón Productor-Consumidor (Multithreading):**
Para no bloquear el renderizado, se separan los procesos:
1.  **Hilo de Captura:** Lee la cámara y corre MediaPipe para extraer las coordenadas de los *Landmarks*.
2.  **Hilo Lógico:** Recibe los datos, calcula los ángulos, aplica la ventana DTW contra los datos en memoria de la canción y despacha eventos de "Puntuación" (Perfect, Great, Miss).

**Ejemplo Real: Cálculo de Ángulos invariantes a la cámara (Python)**

```python
import numpy as np

def calculate_angle(a, b, c):
    """
    Calcula el ángulo en la articulación 'b' dados los puntos a, b y c.
    Ejemplo: a=Hombro, b=Codo, c=Muñeca.
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    # Cálculo en radianes a partir de las coordenadas X e Y
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    # Normalización del ángulo
    if angle > 180.0:
        angle = 360 - angle
        
    return angle
```

**Ejemplo Real: Evaluación con DTW-Lite / FastDTW**

```python
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw

def get_similarity_score(user_pose_buffer, reference_pose_buffer):
    """
    Compara las últimas N posturas del usuario con las N esperadas.
    Retorna un score que perdona pequeños errores rítmicos.
    """
    # distance será menor cuanto más similares sean los movimientos en el tiempo
    distance, path = fastdtw(user_pose_buffer, reference_pose_buffer, dist=euclidean)
    
    # Mapear distancia a un score de 0 a 100
    score = max(0, 100 - (distance * weight_factor))
    return score
```
