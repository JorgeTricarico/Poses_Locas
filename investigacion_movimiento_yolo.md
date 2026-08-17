# Reconocimiento y Clasificación de Movimientos con YOLO Pose en Tiempo Real

## 1. Estrategias para Reconocer Movimientos

El análisis de movimiento humano a partir de *Pose Estimation* (como YOLOv8 Pose) transforma los píxeles de un video en coordenadas (keypoints) del cuerpo. A partir de estos puntos espaciales bidimensionales o tridimensionales, existen principalmente tres enfoques para identificar movimientos en el tiempo:

### A. Heurísticas Estáticas y Geométricas (Basadas en Reglas)
Se calculan distancias o ángulos entre las articulaciones clave en cada *frame*. Un movimiento se define por una transición simple entre estados numéricos predefinidos.
- **Ventajas:** Extremadamente rápido (ideal para tiempo real), no requiere recolección de datos ni entrenamiento, fácilmente interpretable.
- **Desventajas:** Frágil ante variaciones de perspectiva de cámara, difícil de escalar para movimientos complejos.
- **Casos de Uso:** Conteo de repeticiones deportivas (sentadillas, flexiones, curl de bíceps), evaluación de postura ergonómica estática.

### B. Dynamic Time Warping (DTW)
Técnica clásica para medir la similitud entre dos secuencias temporales que pueden variar en velocidad o ritmo. Se compara la secuencia de keypoints del usuario con una secuencia "plantilla" o "ideal".
- **Ventajas:** No requiere grandes datasets (funciona con "one-shot learning" o un solo ejemplo), robusto a diferentes velocidades de ejecución.
- **Desventajas:** Computacionalmente costoso si la ventana de tiempo es grande; sensible a pequeñas variaciones espaciales si no se normalizan bien los datos.
- **Casos de Uso:** Comparación de swings de tenis o golf, evaluación de pasos de baile.

### C. Modelos de Machine Learning Secuencial (LSTM, GRU, 1D-CNN, Transformers)
Se acumulan los keypoints extraídos durante una ventana de tiempo (ej. los últimos 30 frames). Estos datos se aplanan y se utilizan como entrada temporal para una red neuronal recurrente o basada en atención.
- **Ventajas:** Alta precisión en movimientos dinámicos, complejos y superpuestos; generaliza excepcionalmente bien a diferentes biotipos y perspectivas.
- **Desventajas:** Requiere recopilar, etiquetar y entrenar un dataset de secuencias de video (muy laborioso). Mayor consumo de recursos de GPU/CPU en inferencia.
- **Casos de Uso:** Traducción de lenguaje de señas, reconocimiento de acciones de seguridad (caídas, peleas), análisis biomecánico complejo.

## 2. Ejemplos de Código en Python

### Ejemplo 1: Extracción de Keypoints con YOLOv8 y Cálculo de Ángulos (Heurística)
Este script en tiempo real lee la webcam, extrae la pose y calcula el ángulo del codo para determinar un estado de "Contracción" o "Extensión".

```python
import cv2
import numpy as np
import math
from ultralytics import YOLO

# Cargar modelo de pose pre-entrenado
model = YOLO('yolov8n-pose.pt')

def calculate_angle(p1, p2, p3):
    """Calcula el ángulo entre tres puntos (x, y) en grados."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    # Usando el arco tangente para los vectores formados por las articulaciones
    angle = math.degrees(math.atan2(y3 - y2, x3 - x2) - math.atan2(y1 - y2, x1 - x2))
    angle = abs(angle)
    return 360 - angle if angle > 180 else angle

cap = cv2.VideoCapture(0) # Iniciar webcam

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    # Inferencia de pose
    results = model(frame, verbose=False)
    
    if results[0].keypoints is not None and len(results[0].keypoints.xy) > 0:
        keypoints = results[0].keypoints.xy[0].cpu().numpy()
        
        # YOLOv8 COCO format: 5=Hombro Izq, 7=Codo Izq, 9=Muñeca Izq
        if len(keypoints) >= 10: 
            shoulder = keypoints[5]
            elbow = keypoints[7]
            wrist = keypoints[9]
            
            # Verificar que los puntos tienen un nivel de confianza válido (YOLO devuelve 0,0 en fallos)
            if all(pt[0] != 0 and pt[1] != 0 for pt in [shoulder, elbow, wrist]):
                angle = calculate_angle(shoulder, elbow, wrist)
                
                # Regla de heurística simple: Curl de bíceps
                estado = "Contraido" if angle < 50 else "Extendido"
                
                cv2.putText(frame, f'Angulo: {int(angle)} - {estado}', 
                            tuple(map(int, elbow)), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 255, 0), 2)

    cv2.imshow('Analisis YOLO Pose', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
        
cap.release()
cv2.destroyAllWindows()
```

### Ejemplo 2: Estructura para Clasificador Secuencial Temporal (PyTorch LSTM)
Para clasificar secuencias, se requiere mantener un historial y pasarlo a un modelo secuencial en tiempo real.

```python
import torch
import torch.nn as nn
from collections import deque

class PoseLSTM(nn.Module):
    def __init__(self, input_size=34, hidden_size=64, num_classes=3):
        # input_size=34 asumiendo 17 keypoints x (X, Y)
        super(PoseLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)
        
    def forward(self, x):
        # x shape: (batch_size, sequence_length, features)
        out, _ = self.lstm(x)
        # Clasificar utilizando únicamente el output del último frame temporal
        out = self.fc(out[:, -1, :])
        return out

# --- Uso en tiempo real simulado ---
seq_length = 30 # Usar los últimos 30 frames de la acción
pose_history = deque(maxlen=seq_length)

model_lstm = PoseLSTM()
model_lstm.eval()

# (Este bloque iría dentro del bucle de captura de video después de extraer keypoints)
# Supongamos que obtenemos los keypoints y los aplanamos:
# keypoints_flat = results[0].keypoints.xy[0].cpu().numpy().flatten() # (34 features)
# pose_history.append(keypoints_flat)

# if len(pose_history) == seq_length:
#     input_tensor = torch.tensor([list(pose_history)], dtype=torch.float32)
#     with torch.no_grad():
#         prediction = model_lstm(input_tensor)
#         class_idx = torch.argmax(prediction).item()
#         print(f"Clase de movimiento predicha en este instante: {class_idx}")
```
