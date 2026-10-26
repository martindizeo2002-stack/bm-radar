#!/bin/zsh
# Corrida desatendida del Radar de Contenido BM (launchd com.tincho.bm-radar-auto, 10:10 y 22:10).
# Vive en ~/bm-radar (fuera de Desktop por TCC). Integra el barrido de 12 h, transcribe, analiza, arma el sitio y publica.
cd /Users/tincho/bm-radar || exit 1
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin HOME=/Users/tincho CI=true NETLIFY_TELEMETRY_DISABLED=1 PYTHONUNBUFFERED=1
set -a; source .env; set +a
LOG=log/auto.log
echo "===== $(date '+%Y-%m-%d %H:%M') inicio" >> $LOG
# launchd lo dispara al despertar la Mac y la red puede no estar: esperar hasta 20 min
for i in {1..60}; do curl -s -m 8 -o /dev/null https://api.netlify.com && break; sleep 20; done
# si el barrido de carruseles todavía está corriendo, esperar hasta 25 min
for i in {1..50}; do pgrep -f "bm-barrido/barrido.py" >/dev/null || break; sleep 30; done
.venv/bin/python3 run.py auto >> $LOG 2>&1 &
PID=$!
for i in {1..360}; do kill -0 $PID 2>/dev/null || break; sleep 10; done   # tope 60 min
if kill -0 $PID 2>/dev/null; then kill -9 $PID; echo "$(date '+%Y-%m-%d %H:%M') CORTADO: superó 60 min" >> $LOG; else wait $PID; echo "$(date '+%Y-%m-%d %H:%M') fin (código $?)" >> $LOG; fi
