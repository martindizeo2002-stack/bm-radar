# Radar de Contenido BM (Apify)

> **Ubicación real: `~/bm-radar`** (desde el 1-oct-2026). `brandmasters/apps/radar-contenido` es un symlink.
> Está fuera de Desktop para que launchd pueda leerlo y publicar solo. Invocar con `~/bm-radar/radar.sh <comando>`
> (la forma vieja `../../.venv/bin/python3 run.py` ya no resuelve desde la carpeta real).

## Se actualiza solo (launchd)
| Job | Cuándo | Qué hace | Log |
|---|---|---|---|
| `com.tincho.bm-historias` | 03, 09, 15, 21 | historias (semillas cada 12 h) | `~/bm-historias/log/historias.log` |
| `com.tincho.bm-barrido` | 09:35, 21:35 | posts de 3 días, slides, lectura de carruseles | `~/bm-barrido/log/barrido.log` |
| `com.tincho.bm-radar-auto` | 10:10, 22:10 | `auto.sh` → `run.py auto`: integra barrido, transcribe reels (Groq), analiza lo nuevo, rearma las vistas por cuenta, build y **deploy** | `~/bm-radar/log/auto.log` · `data/auto-estado.json` |

- Requiere la Mac encendida y despierta a esa hora (si está dormida, launchd corre al despertar).
- Bajo launchd no se puede leer el workspace: las referencias (banco de ángulos, voz, copys) se leen de `refs/` (copia que se refresca en cada corrida interactiva) y la pestaña Guion conserva su último build.
- Deploy bajo launchd: `netlify deploy` con `NETLIFY_AUTH_TOKEN` en `.env`, `CI=true` y stdin vacío (así no se cuelga).
- Probar a mano: `launchctl kickstart gui/$(id -u)/com.tincho.bm-radar-auto` y mirar `log/auto.log`.

Escanea cuentas semilla de Instagram con Apify, puntúa (comentarios primero, como pidió Rama), analiza con Claude, recrea en voz de Nahue y manda ideas al kanban del hub. Plan completo: `PLAN.md`.

## Setup (una vez)
```bash
cd ~/bm-radar
cp .env.example .env      # completar APIFY_TOKEN, ANTHROPIC_API_KEY, HUB_KEY
./radar.sh demo   # ver el radar con datos de demo
```
Python: usa el venv del workspace (`../../.venv`, ya tiene requests, anthropic, python-dotenv).

## Uso
```bash
P=~/bm-radar/radar.sh   # y abajo: $P <comando> en vez de $P <comando>
$P historico            # 1ª vez: baseline por cuenta (100 piezas c/u) + seguidores
$P semanal              # piezas de los últimos 7 días
$P comentarios          # comentarios del top 100
$P analizar --top 50    # clasificación + ángulo BM + recreable
$P minar                # dolores/jerga/preguntas de los comentarios
$P lote --top 10 --kanban   # recrea top 10 y las manda al kanban del hub
$P recrear <id|url> --kanban
$P pedido woker.oficial,otracuenta --dias 30 --top 20
$P build && $P deploy
$P lunes                # todo lo anterior encadenado
$P guion [--cuenta X]    # anatomía del guion (schema creator-lab, a ciegas) + benchmark vs Nahue → data/analisis/guion-benchmark.md
$P cuenta ramiro.cubria --dias 30   # vista profunda: 300 posts, videos → transcript, carruseles leídos, análisis, pestaña Cuentas
```

## Sitio
`site/index.html` lee `site/data/latest.json`. Clave = la del hub. Función `netlify/functions/kanban.mjs` (proxy al hub para "Mandar al kanban" desde el navegador). Env del sitio: `HUB_PASSWORD`, `HUB_URL`.

## Medios (vista profunda por cuenta)
- Reels: `data/media/<id>.mp4` (gitignored, ~12 MB c/u) → mlx-whisper large-v3-turbo local → `transcript`. Algunos videos de IG vienen DASH sin audio: se baja `audioUrl` aparte (`<id>.audio.mp4`) y Whisper usa ese.
- Carruseles: cada slide a `site/slides/<id>/NN.jpg` (720px) → Claude visión lee texto literal + visual + diseño/estructura/cierre (`slides_texto`, `lectura`).
- Las URLs de Apify son firmadas y vencen: bajar medios en la misma corrida del scrape.
- `data/.piezas.lock`: todo read-modify-write de `todas.jsonl` va con `config.lock_piezas()`; escritura atómica.

## Jobs automáticos (launchd, fuera de Desktop por TCC)
- **Historias** `~/bm-historias` (com.tincho.bm-historias): corre 03/09/15/21; historias de las semillas cada 12 h (umbral 11 h: dispara 09 y 21). Datos en `data/historias` (symlink).
- **Barrido de carruseles** `~/bm-barrido` (com.tincho.bm-barrido): 09:35 y 21:35. Apify últimos 3 días de todas las semillas, baja slides y miniaturas, lee cada carrusel nuevo con Claude. Venv propio `~/bm-barrido/.venv`. Datos en `data/barrido` (symlink). Log `~/bm-barrido/log/barrido.log`. ~USD 0,26 por corrida de Apify.
- Integración: `run.py barrido [--analizar]` o cualquier `run.py build` sincroniza posts, slides, miniaturas y lecturas a la base. El deploy sigue siendo manual (launchd no puede correr netlify ni leer Desktop).

## Competencia profunda
- `radar/competencia.py`: YouTube completo con subtítulos (Apify streamers) + anuncios Meta (curious_coder) → `data/competencia/<handle>/{yt.jsonl, ads.json, corpus.json}`.
- `run.py profundo --cuentas a,b [--todo|--dias N] --etapa transcribir|carruseles|analizar|cuentas|todo [--motor local|groq]`.
- Sin crédito en la API de Anthropic: partir en lotes (`data/lotes/`) y procesar con subagentes de Claude Code; `python -m radar.aplicar_workflow <journal.jsonl>` aplica sus resultados.

## Acceso
- Sin contraseña desde el 29-sep-2026 (pedido Tincho). `noindex`. El proxy `/api/kanban` solo acepta altas nuevas en Ideas con ID `radar-...` (nunca edita filas del hub).

## Datos
- `data/raw/` datasets crudos de Apify (trazabilidad + costo)
- `data/piezas/todas.jsonl` acumulado normalizado (fuente para baseline)
- `data/comentarios/<semana>.jsonl` · `data/analisis/` · `data/recreaciones/`
- `data/perfiles.json` seguidores por cuenta

## Reglas
- Nunca cuentas IG propias para scrapear: Apify usa las suyas.
- Dato faltante = null, jamás 0 (contrato panel-bm).
- El kanban del hub se escribe por su API en prod; NUNCA se deploya el hub desde acá.
