# Radar de Contenido BM (Apify + Sandcastles) · PLAN v0.1 · 24-sep-2026

Origen: call Cubria 24-sep ("20-30 perfiles, los 100 más comentados de la semana, recrear para importaciones"). Objetivo Tincho: que Apify sea "una monstruosidad": scraping a pedido + fábrica de contenido (reels, carruseles, historias, nicho y viral) integrada al BM Hub.

## 0. Restricciones que mandan
- ⛔ Hub prod (bm-hub-ventas) se desarrolla en la máquina de Mateo. NO se deploya desde hub-ventas/. El radar vive como **sitio Netlify propio** (mismo look, misma clave impo2026) y el hub lo linkea (1 línea, Mateo). Cuando Mateo pushee el hub a GitHub, se absorbe.
- Apify: cuenta de ellos, proxies de ellos. Nunca cuentas IG propias para scrapear.
- Reglas de copy BM aplican a toda recreación: sin rayas, sin Álvaro, sin jubilados como pieza, sin decisor, sin números de Nahue, jerga verificada en corpus, chat = equipo (no Nahue), keyword en caption.
- Data del kanban de contenido vive en el Sheet "Contenido BM — Ideas e Historias" (1nM8ubHmKG93VEJbDe6IkE3X6NU6qdSflCLiKh1Skl8I) vía Apps Script (cget/cadd/cedit). El radar escribe ahí, no inventa otra base.

## 0b. Sandcastles (sandcastles.ai): el motor de inteligencia, ya pagado
Tincho tiene cuenta. Plataforma de outliers cross-nicho (IG, TikTok, YT Shorts): watchlist de canales (Pro 150 / Visionary 250), transcript al instante de cualquier video, análisis hook + estructura + estilo, tópicos y formatos ganadores, sugerencias de video. **MCP oficial para Claude** en `https://mcp.sandcastles.ai/` (OAuth con la cuenta, planes Pro+). Sin API REST salvo Titan ($399). "Data bulk export" solo Visionary+. Créditos: 1 crédito = 1 análisis o 1 guion (Pro 100/mes, Visionary 250/mes). Refresh watchlist: Pro 12 h, Visionary 6 h.

Tools MCP: analyze · channels-add · channels-recap · channels-search · channels-suggest · topic · formats-watchlist · hooks-watchlist · video-suggest · videos-watchlist.

### Reparto Apify vs Sandcastles
| Necesidad | Quién | Por qué |
|---|---|---|
| Transcripts IG/TikTok/YT Shorts | **Sandcastles** (analyze) | instantáneo, sin whisper local, con análisis de hook/estructura incluido |
| Análisis "por qué pegó" (hook, formato, estilo) | **Sandcastles** primero, Claude encima para mapear a ángulos BM | ya viene hecho, ahorra tokens |
| Outliers cross-nicho (millones de videos, fuera de nuestras semillas) | **Sandcastles** (topic, video-suggest, channels-suggest) | Apify solo ve las cuentas que le damos |
| Watchlist 150-250 canales con recap semanal | **Sandcastles** (videos-watchlist, formats/hooks-watchlist) | tracking incluido en el plan |
| Top 100 más comentados (métrica Rama) sobre 30 perfiles, métricas crudas, histórico 200 piezas | **Apify** instagram-scraper | volumen barato ($2/sem), datos nuestros, sin gastar créditos |
| Minería de comentarios (dolores, jerga, preguntas) | **Apify** comment-scraper | Sandcastles no baja comentarios |
| Ad Library competidores | **Apify** | fuera del alcance de Sandcastles |
| Descubrimiento por hashtag/keyword | **Apify** search + Sandcastles channels-suggest | dos caminos, se cruzan |
| Alimentar el radar (sitio) automáticamente | **Apify** (webhook → Netlify) + Sandcastles vía Claude Code headless local | Sandcastles no tiene API en Pro/Visionary: solo se lee desde Claude |

Créditos Sandcastles son el cuello (100-250/mes). Uso: Apify arma el embudo ancho (900 piezas/sem) y puntúa; Sandcastles analiza solo el top 25-50 semanal + lo que Tincho pida a mano. Capa local whisper queda como fallback, no como default.

### Flujo lunes (v0.1)
1. Dom 23:00 Apify corre semillas IG/TikTok/YT/Ads → Blobs → scoring → Top 100.
2. Lun 5:00 Claude Code headless (launchd, ~/bm-radar/) toma top 25-50, pide `analyze` a Sandcastles (transcript + hook + estructura), suma `videos-watchlist` + `formats-watchlist` + `hooks-watchlist` + `topic` de la semana, mapea a Banco de 50 ángulos, genera recreaciones y las manda al tab Ideas (cadd) + JSON al radar.
3. Lun 6:00 radar listo para la weekly con setters.

## 1. Módulos

### M0 · Semillas (admin en el radar)
Lista editable de fuentes con tags (nicho impo/ecom, competencia, tofu-farmer, bizop, internacional):
- IG: 20-30 perfiles (Rama). Arranque propuesto desde competencia/ (Woker, Lorenzón, Cubria) + cuentas que pase Tincho.
- TikTok: 10-20 perfiles + searchQueries ("importar de china", "vender en mercado libre", "marca propia").
- YouTube: 10-20 canales (nicho + Benji-style packaging).
- Meta Ad Library: páginas competidoras + keywords AR ("importar de china", "importación", "ecommerce").
- Hashtags/keywords IG: descubrimiento de cuentas nuevas (searchType profile/hashtag).

### M1 · Ingesta semanal (Apify)
| Fuente | Actor | Input clave | Salida |
|---|---|---|---|
| IG posts/reels | apify/instagram-scraper | directUrls perfiles, resultsType posts, onlyPostsNewerThan "7 days" | likes, comments, views, plays, caption, videoUrl, timestamp |
| IG comentarios | apify/instagram-comment-scraper | top 100 piezas de la semana, resultsLimit 50-100 | texto, likes, replies |
| TikTok | clockworks/tiktok-scraper | profiles + searchQueries, oldestPostDate, downloadSubtitles | plays, likes, comments, shares, transcript |
| YouTube | streamers/youtube-scraper | canales sort newest, dateFilter week, subtitles | views, likes, comments, título, transcript |
| Ads | curious_coder/facebook-ads-library-scraper | páginas + búsqueda AR, activeStatus active | copy, creativo, start_date (longevidad = ganador) |
| Propia | Graph API (ya existe, scripts/ig_metricas.py) | @nahue.urso | baseline para comparar |

Modos: **semanal** (7 días, automático), **histórico** (1 vez por cuenta nueva: últimas 100-200 piezas = evergreens), **a pedido** ("dame lo más comentado de X en 30 días" desde el radar o desde Claude Code).

### M2 · Scoring (radar)
Por pieza: comentarios (métrica Rama), tasa de comentarios (comments/views), outlier vs mediana de la cuenta (x veces, estilo Sortfeed), engagement por seguidor, velocidad (por día desde publicación).
Rankings: Top 100 comentados · Outliers >3x · Formatos en tendencia (agregado cross-cuentas) · Hooks repetidos (mismo patrón en ≥3 cuentas = tendencia) · Evergreens · Ads longevos.

### M3 · Análisis Claude (por pieza y por lote)
- Clasificación: formato (talking head, on-site/depo, texto en pantalla, POV, carrusel, meme, listicle, screen, entrevista), tipo (TOFU/problema/solución/producto/mentalidad), nivel de conciencia, patrón de hook (textual), beats de estructura, CTA/keyword, por qué farmea comentarios.
- Mapeo al Banco de 50 ángulos BM (ID) + veredicto "recreable: sí/no + cómo se traduce a importaciones".
- Minería de comentarios: dolores, objeciones, preguntas frecuentes, jerga real (alimenta regla de jerga y FAQ setters).
- Ads: ángulos pagos activos, cuáles llevan meses corriendo, qué apagaron.
- Transcripción + análisis base: Sandcastles `analyze` (IG/TikTok/YT Shorts). Fallback: subtítulos Apify (TikTok/YT) y mlx-whisper local para IG.

### M4 · Fábrica de recreación
Desde una pieza (o lote top 10 del lunes) genera:
- Guion reel en voz de Nahue (moldes de formatos-guion-video-bm).
- Carrusel slide por slide con estilo del banco (15 estilos) → entrada directa a /carrusel-ia para render.
- Secuencia de historias (/historias).
- 5 hooks alternativos + caption con keyword.
Cada salida = fila nueva en tab Ideas del Sheet (cadd) con estado Idea, fuente, link original, score. Aparece en el kanban del hub sin tocar el hub.

### M5 · Competencia semanal (pedido 17-ago)
Por competidor: qué subieron, qué pegó, ángulos nuevos, ads nuevos/apagados, cambios de landing (reusa scripts/comp_landing.mjs). Diff semana vs semana. Alerta "copió recurso": similitud caption/hook contra corpus propio (instagram-indice/).

### M6 · Feedback loop
Marcar recreada → publicada → métricas propias (Graph API) vs predicción. Rendimiento por fuente ("cuenta X nos dio 3 bangers") y por formato. Entra al /domingo y /mensual.

### M7 · Radar (sitio)
bm-radar-contenido.netlify.app (nombre provisional). Contrato visual = skill panel-bm (números grandes, cero prosa, tooltips). Vistas:
1. Semana: KPIs (piezas escaneadas, bangers, ideas generadas, recreadas, publicadas) + Top 100 filtrable (plataforma, cuenta, formato, tipo, ángulo, score).
2. Pieza: thumbnail, caption, métricas, transcript, análisis, botones Recrear (reel / carrusel / historia) y Mandar al kanban.
3. Semillas: alta/baja/tags, botón "Correr ahora" (histórico o semanal).
4. Competencia: diff semanal por competidor + ads activos.
5. Comentarios: dolores/jerga/preguntas de la semana.
Acceso: misma clave que el hub. Datos: Netlify Blobs (JSON por semana) + Sheet para ideas.

## 2. Arquitectura
- **Capa cloud (siempre encendida):** Apify Schedules (dom 23:00 ART) → webhook ACTOR.RUN.SUCCEEDED → función Netlify ingesta dataset → Blobs. Scoring + clasificación Claude (Haiku 4.5 para clasificar, Fable/Opus para guiones) en función background o por chunks. Lunes 6:00 el radar está listo para la weekly con setters.
- **Capa local (Mac, launchd en ~/bm-radar/, no en Desktop):** Claude Code headless con MCP Sandcastles: analyze del top 25-50 + watchlist recap + recreaciones → Blobs + Sheet Ideas. Fallback whisper local. Si la Mac está apagada el radar igual muestra Top 100 y scoring (sin transcripts ni recreaciones hasta la próxima corrida).
- **A pedido:** endpoint /api/run recibe {cuentas, ventana, plataforma} → dispara Apify → devuelve dataset. Mismo endpoint lo usa Claude Code desde el workspace (CLI `radar.py`).
- Secrets: APIFY_TOKEN (nuevo), ANTHROPIC_API_KEY (ya existe a nivel team), HUB_PASSWORD, PANEL_SHEET_URL (mismo Apps Script del hub). Sandcastles: OAuth del MCP en la sesión de Claude Code de Tincho (`/mcp` → authorize), sin secret en Netlify.

## 3. Costos (estimado semanal)
| Ítem | Volumen | USD |
|---|---|---|
| IG posts 30 perfiles x 30 | 900 | 2 |
| IG comentarios 100 x 50 | 5.000 | 11 |
| TikTok 20 x 20 + search | 500 | 1 |
| YouTube 20 x 10 | 200 | 0,5 |
| Ad Library | 500 | 0,4 |
| Claude clasificación + guiones | 300 piezas | 3-5 |
| **Total** | | **~18-20/sem ≈ 80/mes** |
Plan Apify: Starter $19/mes (Free se bloquea al agotar $5). Excedente se factura. Histórico inicial (30 cuentas x 200) ≈ $15 una vez.

## 4. Lo que necesito de Tincho
0. Autorizar MCP Sandcastles: sesión interactiva de Claude Code en brandmasters → `/mcp` → sandcastles → Authenticate (ya quedó registrado el server). Decir qué plan tiene (Pro 100 créditos / Visionary 250).
1. APIFY_TOKEN: console.apify.com → Settings → Integrations → API tokens. Plan Starter.
2. Lista semilla (o OK para que proponga 30 y las corrija).
3. Decisión: sitio aparte linkeado desde el hub (recomendado) vs paquete a Mateo.
4. Decisión: plataformas (solo IG como dijo Rama, o IG+TikTok+YT+Ads).

## 5. Fases
- F1 (día 1-2): M0+M1+M2 IG + radar vista Semana + Pieza. Primer Top 100 real.
- F2 (día 3-4): M3 clasificación + M4 fábrica → kanban. Primer lunes con 10 ideas automáticas.
- F3 (semana 2): TikTok, YouTube, Ads, M5 competencia, transcripción local.
- F4 (semana 3): M6 feedback loop + integración /domingo.

## 6. Estado de ejecución
- **24-sep-2026 (F1 construida):** pipeline Python en `apps/radar-contenido/` (ingesta IG Apify, perfiles, scoring, comentarios, análisis Claude, recreación, kanban vía API del hub en prod, build del sitio). Sitio `bm-radar-contenido.netlify.app` (clave del hub) con demo. Función `/api/kanban` (proxy al hub). Decisión Tincho: **solo Apify primero, Sandcastles después** (MCP ya registrado, OAuth pendiente).
- **Bloqueado por Tincho:** APIFY_TOKEN, ANTHROPIC_API_KEY, HUB_KEY en `.env`; lista de 20-30 semillas (hoy 3).
- **Siguiente:** `run.py historico` (baseline) → `run.py semanal` → `analizar` → `lote --kanban` → primer lunes real. Después TikTok/YT/Ads (F3), launchd lunes 5:00 (F2), Sandcastles.
- **25-sep-2026:** 18 semillas (sumadas 7 cuentas de IA + fidel_guajardo; fidel_guajaro era typo). Vista profunda por cuenta (`run.py cuenta`): Cubria 296 posts desde mar-2026, 118 en 30 días (80 reels transcriptos con Whisper local, 38 carruseles / 242 slides leídos con visión). Pestaña Cuentas en el radar. Workflow de rediseño en curso (5 críticos, 3 maquetas, jurado) → `PROPUESTA-REDISENO.md`. Sandcastles sigue en espera.
- **25-sep-2026 (integración creator-lab 1/4):** `radar/guion.py` + `run.py guion`: anatomía del guion con el schema de creator-lab (9 dimensiones, mismas definiciones que los 361 reels de Nahue), clasificación A CIEGAS (solo transcript: sin métricas, caption ni cuenta), modelo `RADAR_GUION_MODEL` (default claude-sonnet-5). Benchmark por cuenta vs Nahue → `data/analisis/guion-benchmark.md` (Rel = views / mediana cuenta-trimestre). `run.py cuenta` etiqueta solo. `analizar.py` también pasó a ciegas (sin likes/comentarios/views/outlier en el input). 136 piezas etiquetadas (Cubria 80, ramiro.contenido 56). Pendientes creator-lab: 2) transcripción cloud Groq/Fireworks (falta GROQ_API_KEY), 3) roles por pasaje, 4) performance map + muro de thumbs en el sitio.
- **25-sep-2026 (integración creator-lab 2/4):** transcripción cloud Groq `whisper-large-v3-turbo` en `radar/media.py` (ffmpeg → FLAC mono 16 kHz → API, pacing GROQ_REQUESTS_PER_MINUTE=20, reintentos 429/5xx). Motor por `RADAR_TRANSCRIPCION` (default groq si hay GROQ_API_KEY; `local` = mlx). Mismo texto que mlx, 1-3 s por reel. `run.py analizar` (y `lunes`) ahora baja + transcribe + etiqueta guion del top antes de analizar, re-analiza las que tenían solo caption y borra los mp4 ya transcriptos. < 6 palabras o sin pista de audio = `sin_habla` (no se reintenta). W39: 9 reels transcriptos + re-analizados en 1:27.
- **25-sep-2026 (integración creator-lab 4/4, DEPLOYADA):** pestaña **Guion** en el radar: selector cuenta (15+ reels etiquetados) × dimensión (9), KPIs (reels, mejor/peor etiqueta con 5+ reels, selección, comparación con Nahue), chips por etiqueta (Rel mediano · n), mapa de performance SVG (x = Rel log, y = com/1K log, línea 1x, gris contexto #55555E + azul selección #3987e5 validado con dataviz; hover con tooltip, click abre drawer), tabla de medianas con columna Nahue, muro de miniaturas de a 48 con "ver más". Datos: `site/data/guion.json` (build_site → guion.site_json); miniaturas de Nahue = frame t=1s de los videos locales (site/thumbs/nahue/, 4,4 MB). Fix de paso: pestañas scrollean dentro de la barra en móvil (antes desbordaba a 612 px) y tablas de Cuentas con scroll propio. Verificado con Playwright local + prod: 27 combinaciones, 0 errores de consola, sin scroll horizontal a 390 px. Pendiente creator-lab: 3/4 roles por pasaje.
- **25-sep-2026 (Guion v2 + creator-lab 3/4, DEPLOYADO):** Tincho: "el mapa de performance no se entiende". Se sacó el scatter; ahora **barras divergentes desde 1x** por etiqueta (escala log 0,25x-4x, raya blanca = Nahue misma etiqueta y período, Rel · com/1K · reels), click en fila filtra el muro. **Filtro de período** 30/90/180/365 días/todo (por fecha de publicación, aplica también a la columna Nahue; se recuerda en localStorage). **Roles por pasaje** (script anatomy de creator-lab): `guion.roles()` parte cada guion en ≤14 tramos y etiqueta hook/contexto/problema/ejemplo/consejo/remate/CTA/otro (Sonnet 5); competencia en `todas.jsonl` campo `pasajes`, Nahue en `instagram-indice/creator-lab/pasajes.jsonl`. Card "Anatomía del guion · top vs resto" (tercio top vs tercio bajo por Rel: secuencia más común, % con cada rol, posición mediana) + drawer con el guion por tramos (`site/data/guion-pasajes.json`, carga diferida). `run.py guion` y `_medios_top` (lunes) etiquetan roles solos. Lectura Nahue: los roles casi no separan top de resto (mayor diferencia: problema −14 pts en el top). Refresco de Nahue: `scripts/ig_videos.py` + `scripts/creator_lab_refresh.py` (Groq + schema del radar + snapshot + análisis + roles).
- **25-sep-2026 (objetivo por pieza + historias diarias, DEPLOYADO):** (1) **Objetivo** de cada reel (alcance / lead_magnet / gatillo + keyword) clasificado por Claude desde caption+guion sin métricas (`guion.objetivos*`; Nahue en `instagram-indice/creator-lab/objetivos.jsonl`: 196/150/61; competencia en `todas.jsonl` campo `objetivo`). Selector Objetivo en Guion: lead magnet se mide en **leads/1K** = usuarios únicos que comentaron la keyword (Graph API, `scripts/ig_comentarios.py` incremental → `instagram-indice/comentarios-reels.jsonl`) contra la mediana de los lead magnets; competencia usa com/1K como aproximación. Gatillo muestra "Agendas atribuidas —" hasta el paso 2 (Grupo Estadístico + comentó→agendó). (2) **Historias**: job launchd `com.tincho.bm-historias` en `~/bm-historias/` (fuera de Desktop por TCC; symlink `data/historias` y `scripts/bm-historias`), 03/09/15/21 hs: Nahue por Graph API en cada corrida (texto, alcance, respuestas, navegación, visitas; queda la última lectura antes de vencer), creadores de Semillas por Apify `datavoyantlab/advanced-instagram-stories-scraper` (sin login) 1 vez cada 20 h (~US$0,16/día). Guarda frame jpg + transcript Groq, borra el video. `cuentas.json` se sincroniza desde semillas en cada build (semilla con `"historias": false` queda afuera). Pestaña Historias en el radar (Nahue: respuestas, alcance, salida %; creadores: voz, stickers, costo). Gotcha: Groq/Cloudflare devuelve 403 "error code: 1010" al User-Agent de Python-urllib → header propio. Pendiente: visión sobre los frames (el CTA de los creadores está escrito en la imagen), paso 2 de atribución, deploy automático del radar (netlify CLI no corre bajo launchd).
- **25 al 29-sep-2026:** ventana de 30 días completa en el sitio (825 piezas, arregla el 'solo 2 carruseles de Cubria'); 20 cuentas con vista profunda (732 piezas analizadas, 399 transcripts, 301 carruseles leídos); competencia profunda de Woker (780 IG + 678 YouTube + 58 anuncios) y Nico Lorenzón (848 IG desde 2020 + 27 YouTube, sin anuncios encontrados), todo transcripto, leído y analizado con ángulo de comunicación y tipo de ángulo; historias cada 12 h y barrido de carruseles cada 12 h por launchd; sitio sin contraseña. Dossier de mercado y oportunidades en `competencia/mercado-2026-09-29/`.
- **1-oct-2026:** el radar se actualiza solo. Carpeta real `~/bm-radar`; job `com.tincho.bm-radar-auto` 10:10 y 22:10 integra, transcribe, analiza, arma y deploya. Ver README.
