# Poses Locas AR - Project Context

## Descripción General
Juego interactivo de baile y fitness en Realidad Aumentada (AR) utilizando Python, OpenCV, y MediaPipe para seguimiento corporal en tiempo real.

## Estado Actual (Última Actualización)
- **Interfaz (UI):** 
  - Completamente limpia en el centro para no obstruir la vista del jugador. 
  - Textos flotantes reducidos y movidos a la izquierda. 
  - Botones interactivos con el mouse (esquina inferior derecha): `[P]` Pausa y `[M]` Música.
- **Sistema de Poses:**
  - *Estáticas:* Brazos Arriba, T-Pose, Fuerte (Bíceps), Saludo Militar, Letra Y, Letra O.
  - *Dinámicas:* Mueve Caderas, Mueve Cabeza. Cuentan golpes (hits) de movimiento y generan partículas.
- **Retroalimentación (Feedback):**
  - Barra de progreso "Dwell-time" para dar tolerancia a los sensores de la cámara.
  - Efectos visuales de partículas (fuegos artificiales, explosiones de colores).
  - Efectos de sonido integrados mediante PyGame (música de fondo, éxito, fallo).
  - Dibujo de esqueleto de colores ("Traffic light limbs" parcial - actual es verde/rojo general).

## Tareas Pendientes / Próximos Pasos
1. **Investigación de UX (Mejoras visuales):**
   - Implementar "Traffic Light Limbs" por segmento (pintar brazos de verde si están bien, amarillo si están cerca, rojo si están mal).
   - Implementar silueta "Fantasma" atenuada para mostrar la siguiente pose que el jugador debe realizar.
2. **Nuevas Poses:**
   - Crear pose de "Mono" (manos bajo las axilas).
   - Crear nuevas poses de animales y letras.
3. **Música:**
   - Buscar e integrar música libre de derechos (Creative Commons) más animada tipo "Just Dance".
