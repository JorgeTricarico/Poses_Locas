# Investigación: Multijugador Local y Scoring tipo "Just Dance" con YOLOv8 Pose

## 1. Multijugador Local: Tracking de múltiples personas
Para manejar y rastrear a 2 o más jugadores sin confundir sus IDs (identity switches) cuando se cruzan o interactúan de cerca, YOLOv8 provee integración nativa con algoritmos de tracking avanzados: **BoT-SORT** y **ByteTrack**.

### Diferencias Clave
- **ByteTrack:** Asocia objetos utilizando solo el movimiento y cruza cajas de alta y baja confianza. Es muy rápido (ideal para Edge y Real-Time), pero pierde el ID con oclusiones severas o cuando los jugadores se tapan totalmente.
- **BoT-SORT (Recomendado para juegos de baile):** Combina predicción de movimiento, compensación de movimiento de cámara y *Appearance Embeddings* (ReID). Al usar características visuales, si dos jugadores se cruzan, el modelo utiliza el aspecto visual (color de ropa, forma) para re-asignar los IDs correctamente. Es más pesado pero mucho más robusto.

### Ejemplo de Código en Python
YOLOv8 facilita esto al incorporar el argumento `persist=True` y `tracker`.

```python
import cv2
from ultralytics import YOLO

# 1. Cargar el modelo YOLOv8 de Pose (se recomienda 'm' o 'l' para mayor precisión)
model = YOLO('yolov8m-pose.pt')

cap = cv2.VideoCapture(0) # o un video.mp4

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # 2. Ejecutar tracking con BoT-SORT para mantener IDs estables
    results = model.track(frame, tracker="botsort.yaml", persist=True)

    # 3. Dibujar resultados en pantalla
    annotated_frame = results[0].plot()
    
    # 4. Obtener Keypoints y Track IDs para lógica de juego
    if results[0].boxes.id is not None:
        track_ids = results[0].boxes.id.int().cpu().tolist()
        keypoints = results[0].keypoints.xyn.cpu().numpy() # Keypoints normalizados
        
        for track_id, kp in zip(track_ids, keypoints):
            # Guardar el historial de `kp` por `track_id` para evaluar el baile
            pass

    cv2.imshow("Just Dance - Tracking", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
```

## 2. Evaluación de Precisión (Scoring tipo Just Dance)
Para comparar la secuencia de movimientos del jugador contra una "coreografía perfecta" y dar puntaje, la combinación ideal es usar **Similitud del Coseno (Cosine Similarity)** en conjunto con **Dynamic Time Warping (DTW)**.

### ¿Por qué esta combinación?
- **Cosine Similarity:** En vez de medir la posición en la pantalla (Distancia Euclidiana), mide los **ángulos** entre las articulaciones. Esto hace que el puntaje sea invariante a la altura del jugador o a su distancia de la cámara.
- **Dynamic Time Warping (DTW):** Alinea secuencias en el tiempo. Si el jugador se adelanta o se atrasa ligeramente respecto a la coreografía, DTW "estira" o "comprime" el tiempo para encontrar el mejor emparejamiento, dando un puntaje justo.

### Ejemplo de Código en Python
Utilizaremos `dtaidistance` para DTW y `scipy` para calcular la matriz de distancias.

```python
import numpy as np
from scipy.spatial.distance import cdist
from dtaidistance import dtw

def normalize_poses(sequence):
    """
    Aplana y normaliza (L2) la secuencia de poses para Cosine Similarity.
    """
    seq = np.array(sequence)
    seq_flat = seq.reshape(seq.shape[0], -1) 
    
    norms = np.linalg.norm(seq_flat, axis=1, keepdims=True)
    norms[norms == 0] = 1 # Evitar división por 0
    return seq_flat / norms

def evaluate_dance(player_seq, expert_seq):
    # 1. Normalizar secuencias
    player_norm = normalize_poses(player_seq)
    expert_norm = normalize_poses(expert_seq)
    
    # 2. Calcular matriz de distancias (Cosine distance = 1 - Cosine Similarity)
    distance_matrix = cdist(player_norm, expert_norm, metric='cosine')
    
    # 3. Aplicar DTW
    dtw_distance = dtw.distance_matrix_fast(distance_matrix)
    
    # 4. Convertir distancia a Score (0-100)
    max_dist = len(expert_seq) * 2.0 
    similarity_ratio = 1 - (dtw_distance / max_dist)
    score_100 = max(0, min(100, similarity_ratio * 100))
    
    # 5. Clasificar movimiento
    if score_100 >= 90: tier = "Perfect"
    elif score_100 >= 70: tier = "Good"
    elif score_100 >= 50: tier = "Ok"
    else: tier = "Miss"
        
    return score_100, tier

# Simulación
expert_poses = np.random.rand(50, 17, 2) 
player_poses = expert_poses.copy() + np.random.normal(0, 0.05, (50, 17, 2))

score, tier = evaluate_dance(player_poses, expert_poses)
print(f"Puntaje: {score:.2f}/100 - {tier}")
```
