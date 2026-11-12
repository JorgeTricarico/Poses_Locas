#!/bin/bash
set -e

# =====================================================================
# POSES LOCAS — LANZADOR AUTONOMO PARA LINUX / RASPBERRY PI
# =====================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configurar entorno de usuario y runtime dir
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR="/run/user/$(id -u)"
fi

# Detección de servidor gráfico (Wayland / XWayland)
if [ -z "$WAYLAND_DISPLAY" ] && [ -e "$XDG_RUNTIME_DIR/wayland-0" ]; then
    export WAYLAND_DISPLAY="wayland-0"
fi

if [ -z "$DISPLAY" ]; then
    export DISPLAY=":0"
fi

# Configurar Qt5 / OpenCV para usar el backend xcb (compatible con XWayland)
export QT_QPA_PLATFORM=xcb

# Soporte de audio para SDL / Pygame en Pipewire / PulseAudio
export SDL_AUDIODRIVER=pulseaudio
export SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR=0

# Detectar intérprete de Python preferido
PYTHON_BIN=""
if [ -x "/home/jorge/miniforge3/envs/mp_env/bin/python" ]; then
    PYTHON_BIN="/home/jorge/miniforge3/envs/mp_env/bin/python"
elif [ -x "$HOME/miniforge3/envs/mp_env/bin/python" ]; then
    PYTHON_BIN="$HOME/miniforge3/envs/mp_env/bin/python"
elif [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
else
    PYTHON_BIN="$(which python3)"
fi

LOG_FILE="$SCRIPT_DIR/game.log"
echo "=== INICIANDO POSES LOCAS [$(date)] ===" > "$LOG_FILE"
echo "Python: $PYTHON_BIN" >> "$LOG_FILE"
echo "DISPLAY=$DISPLAY, WAYLAND_DISPLAY=$WAYLAND_DISPLAY" >> "$LOG_FILE"

# Liberar cualquier proceso previo que pudiera mantener bloqueada la camara USB
pkill -f "poses_locas.py" 2>/dev/null || true
sleep 0.2

exec "$PYTHON_BIN" poses_locas.py "$@" 2>&1 | tee -a "$LOG_FILE"
