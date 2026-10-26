# Radar de Contenido BM

Scrapea con Apify las cuentas de Instagram que seguimos (semillas), puntúa cada pieza, la analiza con Claude, la recrea en la voz de Nahue y manda la idea al kanban del hub. Publica todo en un sitio estático: https://bm-radar-contenido.netlify.app

Hoy corre en la Mac de Tincho con launchd, dos veces por día, y se deploya solo a Netlify. Este repo tiene el código; la data (unos 4 GB entre JSONL, videos, slides y miniaturas) no está acá.

## Cómo integrarlo a la app

Tres caminos, de menor a mayor esfuerzo:

1. **Leer los JSON que ya publica el sitio.** Cada corrida deja los archivos en `https://bm-radar-contenido.netlify.app/data/...` (lista abajo). Es lo más rápido: la app los consume y el pipeline sigue corriendo en la Mac. Ojo: el sitio no manda headers CORS, así que un `fetch` desde otro dominio falla. Dos salidas: agregar un bloque `[[headers]]` con `Access-Control-Allow-Origin` en `netlify.toml` y redeployar, o leerlos desde una función del lado del servidor de la app.
2. **Mover solo el frontend.** `site/index.html` es una sola página (HTML + JS sin build) que lee esos JSON con rutas relativas. Se puede portar como vista de la app apuntando a las URLs del punto 1.
3. **Correr el pipeline en un servidor.** Python 3.9+, `requirements.txt`, ffmpeg, y las variables de `.env.example`. Hay que reemplazar launchd por cron o un scheduler y revisar las rutas fijas a `/Users/tincho/...` (ver "Rutas fijas").

## JSON que publica el sitio

Hay un ejemplo recortado de cada uno en `ejemplos/`.

| Archivo | Qué trae |
|---|---|
| `data/latest.json` | Ventana de 30 días: KPIs, piezas con score y análisis, semillas con baseline, tendencias. Es el principal. |
| `data/historico.json` | Piezas anteriores a la ventana, versión liviana (carga diferida). |
| `data/detalle/<cuenta>.json` | Transcript, slides y análisis de las piezas viejas de una cuenta. |
| `data/cuentas/index.json` | Cuentas con vista profunda (n piezas, si tiene dossier). |
| `data/cuentas/<cuenta>.json` | Vista profunda de una cuenta: piezas, transcripts, carruseles leídos, dossier. |
| `data/historias.json` | Historias de Nahue (con métricas de la Graph API) y de la competencia (frame, transcript, stickers). |
| `data/guion.json`, `data/guion-pasajes.json` | Anatomía de guion por reel (9 dimensiones) y benchmark contra Nahue. |
| `data/2026-Wnn.json` | Copia de `latest.json` por semana ISO. |
| `thumbs/<id>.jpg`, `slides/<id>/NN.jpg`, `historias/...` | Miniaturas, slides de carruseles (720 px) y frames de historias. |

Contrato de datos: un dato que falta viene `null`, nunca `0`. Las URLs de medios de Apify son firmadas y vencen; por eso el sitio sirve sus propias copias (`thumb_local`, `slides_local`).

## Pipeline

| Job (launchd) | Horario | Qué hace | Código |
|---|---|---|---|
| `com.tincho.bm-historias` | 03:05, 09:05, 15:05, 21:05 | Historias de Nahue (Graph API) y de las semillas (Apify, cada 12 h) | `jobs/historias/historias.py` |
| `com.tincho.bm-barrido` | 09:35, 21:35 | Posts de los últimos 3 días de todas las semillas, baja slides y los lee con Claude | `jobs/barrido/barrido.py` |
| `com.tincho.bm-radar-auto` | 10:10, 22:10 | `auto.sh` → `run.py auto`: integra el barrido, transcribe reels (Groq), analiza lo nuevo, rearma las vistas por cuenta, build y deploy | `run.py`, `radar/` |

Los plist están en `launchd/`. En la Mac, `data/historias` y `data/barrido` del radar son symlinks a la carpeta `data/` de cada job.

## Mapa del repo

```
run.py              CLI: demo, historico, semanal, comentarios, analizar, minar, recrear, lote,
                    pedido, cuenta, guion, profundo, barrido, build, deploy, auto, lunes
radar/
  apify.py          cliente REST de Apify (Bearer), guarda los datasets crudos
  ingest_ig.py      normaliza a "pieza" y acumula data/piezas/todas.jsonl
  score.py          comentarios 50% · outlier vs mediana de la cuenta 30% · tasa 20%
  comentarios.py    baja comentarios del top
  analizar.py       Claude con JSON schema: formato, hook, ángulo del banco BM, si es recreable
  recrear.py        recrea en voz de Nahue (refs/) y detecta violaciones de las reglas de copy
  guion.py          anatomía de guion (9 dimensiones), a ciegas, benchmark vs Nahue
  cuenta.py, profundo.py, competencia.py   vista profunda por cuenta, YouTube y Ad Library
  media.py, thumbs.py, carruseles.py       videos, audio, transcripción, miniaturas, slides
  hub.py            alta de ideas en el kanban del hub
  build_site.py     arma site/data/*.json
  llm.py            cliente de Claude (modelo por env RADAR_MODEL)
  config.py         rutas, env, semillas, lock de todas.jsonl
site/index.html     el sitio (una página)
netlify/functions/kanban.mjs   proxy /api/kanban hacia el hub
refs/               voz de Nahue, reglas de copy y banco de ángulos (los usa recrear.py)
semillas.json       cuentas que se scrapean (tag "propia" = se excluye del análisis)
jobs/               los dos jobs que corren aparte (historias y barrido)
docs/OPERACION.md   manual de operación de la Mac · docs/PLAN.md plan original
ejemplos/           un ejemplo recortado de cada JSON
```

## Variables de entorno

Ver `.env.example`. Las claves no están en el repo: pedíselas a Tincho.

- Radar: `APIFY_TOKEN`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `HUB_KEY`, `HUB_URL`, `RADAR_MODEL`, `NETLIFY_SITE_ID`, `NETLIFY_AUTH_TOKEN`.
- Job de historias: `APIFY_TOKEN`, `GROQ_API_KEY`, `META_ACCESS_TOKEN`, `META_IG_USER_ID`, `META_API_VERSION`.
- Job de barrido: `APIFY_TOKEN`, `ANTHROPIC_API_KEY`, `RADAR_MODEL`.

## Kanban del hub

`radar/hub.py` y `netlify/functions/kanban.mjs` hacen `POST` a la función `panel` del hub con header `x-hub-key` y body `{token, action: "cadd", tab: "Ideas", data}`. Solo dan de alta filas nuevas con ID `radar-...`; nunca editan. Si la app pasa a ser la que recibe las ideas, este es el único punto a cambiar.

## Correr local

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # completar
.venv/bin/python3 run.py demo # sitio con datos de demo, sin gastar Apify
.venv/bin/python3 run.py build
```

## Rutas fijas

`radar.sh`, `auto.sh`, `launchd/*.plist` y el default de `BM_ROOT` en `radar/config.py` apuntan a `/Users/tincho/...`. El resto usa rutas relativas al repo.

## Costos

Apify plan Starter con tope de USD 50 por mes (ciclo del 24 al 23). Historias unos USD 10 por mes, barrido unos USD 0,26 por corrida, Claude aparte.
