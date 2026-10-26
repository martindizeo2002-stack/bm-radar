# Radar de Contenido · anexo del rediseño v2

25-sep-2026 · datos al corte vie 25/09 03:02 (latest.json regenerado por otra sesión a esa hora). Si los datos cambian: `python3 maquetas/_v2-datos.py` y `node maquetas/_v2-capturas.mjs`.

## 1. Qué cambió contra la v1 de la propuesta

- **Cuentas y Comentarios ya no quedan afuera.** Cuentas sube a vista principal y Comentarios pasa a Voz del lead.
- **Diseño nuevo.** El crema con stencil, sellos, cinta y mono era el tic de IA "distintivo". Vuelve el oscuro BM con navy y dorado.
- **Capturas de la versión final.** Las de `capturas/propuesta/` son de las 02:38, con datos viejos (S39·01 con el ángulo falso). No usarlas.
- **Ventana móvil.** La semana lun a dom con madurez de 72 h dejaba sin rankear lo de viernes a domingo, para siempre.
- **P no se bloquea.** De las 40 de la selección, solo 4 tienen análisis con medios y ángulo del banco.
- **Un solo ranking: C×.** La v1 ordenaba por el mayor entre V× y C× (la #01 iba por views).
- **El P0 quedó en 4 tareas para el lunes**, más 3 del mismo finde que no bloquean. Mesa v1 y señal honesta pasan a la semana del 28, después de tus decisiones.
- **El Plan escribe al Sheet.** No hay calendario paralelo en Blobs.
- **Sale "Tu posición @nahue.urso".** El 279 contra 0 salía de 2 reels sin caption, con conteos inflados por keyword.
- **Sale el puntaje de los "jurados".** Eran agentes simulados, no data.

## 2. Diseño

- **Tokens:** fondo #0B0F17, superficie #121A27, navy #1F2A3D (activo y elevado), texto #EEF1F6, #A7B0C0 y #8995AA (todos pasan 4,5:1 sobre las tres superficies).
- **Dorado #F2B70D** para acento, botón primario y la marca banger. #B8963E para barras secundarias.
- **Semáforo:** ▲ #2E9E5B, ◆ #C7811C, ▼ #E24B63. El validador de dataviz (dark, #121A27) da todo PASS y CVD 6,1 en la banda legal, porque el glifo siempre acompaña. Sobre el navy, el verde y el rojo solo van como texto grande.
- **Tipografía:** Archivo para todo el texto y Archivo ancho (wdth 118, peso 800) como única display para los números. No hay mono ni condensada.
- **El semáforo es solo objetivo contra real:** semillas vivas contra 30, selección analizada, comentarios del nicho contra 200. Nunca rankea.
- **Banger (C× de 3 o más):** marca dorada en la miniatura, no semáforo.
- **Dato faltante:** el placeholder del contrato con `title` que explica qué falta. Nunca 0 ni prosa en la celda.
- **Aclaraciones:** van al `title` del propio número o título, más una leyenda de una línea arriba de la Cola que en el celu se puede tocar. No hay íconos "i".
- **Muestra chica:** si la base tiene menos de 8 piezas, va el placeholder atenuado. Si la mediana de la base es menor a 10 comentarios, el número va atenuado y queda fuera de la selección (hoy 20 piezas: yax.media reel tiene mediana 2).
- **Sin el campo fijado** (641 de 1.793 piezas: woker, yax.media, peter.visuals, marketingharry, instacoachmike, aiagently y nahue.urso, entre otras): no se filtra y se avisa en el `title`.

## 3. Vistas

- **Semana pasada (paso 0):** lo elegido, la etapa en el Sheet leída con cget y, si ya se publicó, el C de Nahue contra su mediana (hoy reel 14 con n=77, carrusel 51,5 con n=14). Hoy muestra las 2 filas radar-* de Woker, en Idea.
- **Cola:** arranca en el Muro con todo (140 de la ventana + lo que entra desde Cuentas). El tamaño de la miniatura depende del C×. "Selección" es un filtro (C× de 1,5 o más con base sana), no otra pantalla. Filtros por formato y carril. Madurando va abajo.
- **Mesa, ficha díptico:** a la izquierda el original con sus slides reales, C× con su base, V× solo en reels, kw% y C org, el chip C/T/S/V, hook, estructura, ángulo, "Nahue y el tema" y CTA. A la derecha la versión Nahue con el guion a dos columnas (imagen / Nahue dice), el carrusel par a par y las historias. Sin recreación, el esqueleto fantasma con los beats del original.
- **Mesa, decisión:** P, G y D sin tope (4 piezas por día, decisión de Tincho 25-sep); solo cuenta lo elegido. P sin ángulo abre el banco de 50 y elegís vos. D pide motivo.
- **Plan = vista del Sheet** "Contenido BM · Ideas e Historias". Muestra las ideas por etapa (97: 53 guionadas, 11 grabadas, 18 publicadas), lo elegido para la semana y la cobertura del banco (33 de 50 sin pieza).
- **Alertas del Plan:** las Historias del Sheet están frenadas desde el 30/08 y 58 de 97 ideas no tienen ángulo.
- **Cuentas:** cabezal de ritmo (3,9 por día; picos a las 20, 16 y 23 hs ART), tabla keyword, recurso y comentarios, hooks con su mediana, tipo de pieza, top 10 por C×, biblioteca con búsqueda en caption, hook, transcript y slides, y botón "A la Cola".
- **Dossier de Cubria:** en la maqueta lo escribí yo desde los agregados. En prod lo escribe `run.py cuenta` (hoy `dossier:false` en las dos cuentas).
- **Voz del lead:** solo castellano. Los temas en inglés salen de la vista (5, entre ellos los dolores #1 y #2, con n=12 y n=9). Cita literal, n y botones "A FAQ setters" y "A la regla de jerga".
- **Historias:** frame por frame con "Copiar", pensada para el celu del setter y el editor. Manda los frames al tab Historias del Sheet.

## 4. Métricas

- **C× (el único que ordena):** comentarios dividido la mediana de comentarios de las últimas 30 piezas maduras de la cuenta en ese formato, sin fijados. Umbral de la selección: 1,5.
- **V×:** views dividido la mediana de views de los reels de la cuenta. Es un dato secundario y solo aplica a reels.
- **kw% y C org:** kw% es el comentario más repetido sobre los comentarios bajados (con 20 o más). C org es C× por (1 menos kw%). Ejemplo en la captura de la Mesa: el carrusel de Cubria da 11× bruto, pero el 98% de los comentarios dice "IA", así que queda en 0,3× orgánico.
- **Madurez:** una pieza entra por la ventana solo con 72 h cumplidas.
- **Hit rate:** recreaciones publicadas con C×72 de 1,5 o más, sobre el total publicado. Pasa a ser el número de la weekly a los 60 días.

## 5. P1 · semana del 28 y la siguiente

- **Mesa v1 [M].** Cola, Mesa y Plan con P/G/D. Escribe al Sheet (cadd con ID fijo y cedit para la etapa) y lee con cget. No tiene estado propio.
- **Señal honesta [S].** Las reglas de base de la sección 2.
- **Regla de ángulo [S].** P abre el banco cuando falta el ángulo.
- **Semana pasada [S]** con la foto semanal que ya se guarda desde el P0.
- **Cuentas v2 [M].** Dossier escrito en la corrida, filtros por keyword, patrón y formato, y "A la Cola". Correr `run.py cuenta` sobre todas las semillas, no solo las 2 de Cubria.
- **Voz del lead [S].** Bajar comentarios de @nahue.urso y del nicho (hoy 14 de 684), filtrar castellano y conectar los botones a la FAQ de setters y a la regla de jerga.
- **"Nahue ya hizo este ángulo" [M].** Clasificar los 371 reels de Nahue contra el banco de 50. Hoy solo existe el tema del creator-lab (361 reels), que es lo que muestra la maqueta.
- **ID del banco en la columna Angulo del Sheet.** Es lo que permite medir cuántas semanas lleva cada ángulo sin salir.
- **Kanban con guion [S].** Llenar Guion, Estructura, Referencias, Semana y Arquetipo, que ya existen en el Sheet y hoy llegan vacías.
- **Recurso vivo [S].** Si el recurso no existe, la pieza no se produce (la calculadora del ángulo #12 está rota).
- **Dos carriles [S].** Del nicho se toman temas; de los farmers, formato y mecánica.
- **Costos [S].** Guardar el `usageTotalUsd` de cada corrida de Apify y los `_usage` de Claude, mostrar USD de la semana y del mes en el cabezal, poner un tope mensual y pedir confirmación con el costo estimado en cada botón que gasta.
- **Modelo por tarea.** Haiku para clasificar y Opus solo para guiones, como decía el PLAN. Hoy `analizar` usa claude-opus-5 en cada pieza.
- **30 farmers del nicho hispano [M].** Buscar con Apify por hashtag y keyword (importación, ecommerce, emprendimiento). Al dar de alta una cuenta, bajar sus 30 días (unos USD 0,20 por cuenta).
- **launchd del domingo [S]** en `~/bm-radar/`, no en Desktop.

## 6. P2 · el mes que viene

- **Recrear desde el radar [L].** El pipeline es Python y Netlify Functions no lo corre. El paso intermedio es [S]: el botón deja un pedido en Blobs y la Mac lo procesa con el pipeline local.
- **Snapshots y C×72 [M].** Depende del schedule diario (hoy el scrape es manual y solo los lunes) y multiplica el costo de Apify.
- **Resultado y hit rate por semilla [M].**
- **Alta de semillas desde el panel [M].**
- **El lunes sin la Mac [L].** Schedule de Apify con webhook a Netlify.
- **Alertas miércoles y viernes [M].**
- **Patrones de hook cerrados [S].** Hoy los patrones de Cubria son texto libre y casi todos tienen n=1, así que no se pueden comparar.

## 7. Qué se borra

- **Del cabezal y la tabla:** la tira de KPIs genéricos, el score compuesto, la tasa en %, eng/seg y com/día.
- **Las tabs Grilla y Competencia.** Comentarios pasa a ser Voz del lead.
- **Las pills** ("recreable" aparece en 94 de 97 piezas).
- **Los íconos "i"**, Inter y los colores de Tailwind.
- **El `?v=Date.now()`** del fetch.
- **Las maquetas v1** (mesa-del-lunes, muro y sala) y `capturas/propuesta/`.

## 8. Costos hoy

- **Apify:** USD 6,21 en 13 corridas desde el 24-sep (leído por API, `usageTotalUsd`).
- **Claude:** sin dato, porque los tokens no se guardan.
- **Estimación del PLAN:** unos USD 80 por mes.

## 9. Archivos

- **Maqueta:** `maquetas/radar-v2.html`, que lee `maquetas/v2-datos.json`.
- **Datos:** `maquetas/_v2-datos.py` los arma desde todas.jsonl, latest.json, cuentas/, recreaciones/, comentarios/, el creator-lab de Nahue y el banco de ángulos. Suma dos lecturas de solo lectura: el costo de Apify y `maquetas/sheet-cget-2026-09-25.json` (cget del Sheet). Las miniaturas que faltaban quedaron en `maquetas/thumbs-v2/`. No toca site/ ni data/.
- **Capturas:** `capturas/propuesta-v2/` (14 PNG, desktop 1440 y celu 390), generadas con `maquetas/_v2-capturas.mjs`. Sin errores de consola ni desborde.
- **Estado de la maqueta:** las decisiones P/G/D viven en el localStorage del navegador solo para probar. En prod viven en el Sheet.
