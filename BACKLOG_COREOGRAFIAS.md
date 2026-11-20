# BACKLOG DE COREOGRAFÍAS Y EXPANSIÓN MUSICAL — POSES LOCAS

**Última actualización:** 20 de Noviembre de 2026  
**Propósito:** Registro vivo de canciones con coreografías icónicas compatibles con detección por cámara frontal (MediaPipe Pose — torso, brazos, cabeza, cadera y saltos), organizadas por prioridad de implementación.

---

## Leyenda de Modos de Coreografía
* **Clásico (`COREO`):** Avanza cuando el jugador completa la pose (sin tiempo límite).
* **Sincronizado por Tiempo (`TIMED_COREO` — Experimental):** Cada paso está anclado a ventanas temporales reales de la canción (`[start, end]`) para músicas cuya letra dicta los pasos en tiempo real.

---

## Prioridad 1 — Próxima Fase (Prueba Piloto de `TIMED_COREO`)

| Canción | Artista | BPM | Audio en Disco | Tipo | Pasos / Poses Clave |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Waka Waka** | Shakira | 127 | ✅ `waka_waka.wav` (`199.0s`) | `TIMED_COREO` | Marcha con brazos (`Mueve los Brazos!`), `Baila! Mueve Caderas`, palmas sobre cabeza (`Letra O!`), `Balanceo Suave Flow!`, `Salto Mortal!` |
| **Danza Kuduro** | Don Omar | 130 | ✅ `danza_kuduro.wav` (`196.2s`) | `TIMED_COREO` | `Brazos Arriba!` ("La mano arriba"), `Manos Cintura!` ("Cintura sola"), `Girando!` ("Da media vuelta"), `Limpiaparabrisas!`, `Baila! Mueve Caderas` |
| **La Bomba** | Azul Azul | 128 | ❌ Pendiente `.wav` | `TIMED_COREO` | *Nuevas:* `Mano Cabeza + Mano Cintura`, `Una Mano Arriba`, `Bomba Abajo` (`Agacharse!`) + `Baila! Mueve Caderas` |

---

## Prioridad 2 — Coreografías en Español / Familiares (Alta Compatibilidad)

| Canción | Artista | BPM | Audio en Disco | Target Principal | Pasos Insignia y Detectores Requeridos |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **El Baile del Gorila** | Melody | 128 | ❌ Pendiente `.wav` | Niños (`JUNIOR`) | `Brazos Arriba!` ("manos hacia arriba"), brazos abajo, golpeteo de pecho estilo gorila *(nuevo detector)*, `Pose de Mono!` |
| **Mayonesa** | Chocolate | 136 | ❌ Pendiente `.wav` | Fiesta / Familia | Batiendo mayonesa con ambas manos en círculo frontal *(variante `Remolino DJ` bimanual)*, `Manos Cintura!`, `Baila! Mueve Caderas`, `Girando!` |
| **Chu Chu Ua** | Piñón Fijo | 112 | ❌ Pendiente `.wav` | Niños (`JUNIOR`) | `T-Pose!` ("brazo extendido"), `Fuerte!` ("puño cerrado"), `Mueve la Cabeza!`, `Agacharse!`, `Saludo Militar!` |
| **El Tiburón** | Proyecto 1 / Henry Méndez | 130 | ❌ Pendiente `.wav` | Fiesta / Cardio | **Aleta de Tiburón** sobre la cabeza *(palmas juntas en punta arriba)*, `Balanceo Suave Flow!` lateral |

---

## Prioridad 3 — Clásicos Internacionales y Virales

| Canción | Artista | BPM | Audio en Disco | Target Principal | Pasos Insignia y Detectores Requeridos |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Gangnam Style** | PSY | 132 | ❌ Pendiente `.wav` | Adultos / Flow / Fiesta | **Lazo de Vaquero** *(mano derecha en círculo sobre la cabeza + mano izquierda al frente)*, cruzado saltando (`Salto Mortal!`) |
| **Baby Shark** | Pinkfong | 115 | ❌ Pendiente `.wav` | Niños (`JUNIOR`) | **Boca de Tiburón** *(brazos abriendo/cerrando verticalmente frente al torso)*, aleta dorsal (`Letra O!`), nado (`Onda Electro!`) |
| **I Like to Move It** | Reel 2 Real (Madagascar) | 124 | ❌ Pendiente `.wav` | Niños / Fiesta | `Baila! Mueve Caderas`, `Salto Mortal!`, `Fuerte!`, `Mueve los Brazos!` |
| **Swish Swish / Floss Mix** | Katy Perry / Pop | 120 | ❌ Pendiente `.wav` | Niños / Flow | **Floss Dance** *(oscilación sincronizada de ambas muñecas delante y detrás de las caderas)* |
| **Wake Me Up Before You Go-Go** | Wham! | 162 | ❌ Pendiente `.wav` | Cardio / Retro | Palmas arriba, `Salto Mortal!`, `Fiebre Disco!`, `Limpiaparabrisas!` |
| **Hot N Cold** | Katy Perry | 132 | ❌ Pendiente `.wav` | Niños / Cognitivo | Gestos literales contrastados (`Manos Cabeza`, `Fuerte!`, `Brazos Arriba!`, `Agacharse!`) |
| **Dance Monkey** | Tones and I | 98 | ❌ Pendiente `.wav` | Flow / Groove | Groove continuo de caderas, `Remolino DJ!`, `Onda Electro!`, `Pose de Mono!` |
