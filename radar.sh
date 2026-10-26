#!/bin/zsh
# Lanzador del radar. Uso: ~/bm-radar/radar.sh <comando> [args]   (ej: radar.sh build, radar.sh cuenta woker.oficial)
# Usa el venv del workspace (tiene mlx-whisper para transcribir local) si se puede leer; si no, el venv propio del radar.
cd /Users/tincho/bm-radar || exit 1
PY=/Users/tincho/Desktop/brandmasters/.venv/bin/python3
[ -x "$PY" ] || PY=/Users/tincho/bm-radar/.venv/bin/python3
exec "$PY" run.py "$@"
