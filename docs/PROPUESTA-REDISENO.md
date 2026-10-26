# Radar de Contenido · rediseño v2

25-sep-2026 · maqueta con datos reales al corte vie 25/09 03:02 · el detalle está en `PROPUESTA-REDISENO-anexo.md`

## Veredicto

- **Hoy es una vidriera: no deja decidir y Cubria queda al costado.** El score mezcla views con comentarios, no se guarda qué se eligió y lo que está en la pestaña Cuentas no puede entrar a la semana. De las 40 piezas de la selección, solo 17 tienen análisis.
- **Propuesta: el radar pasa a ser la weekly del lunes, en 4 pasos.** Semana pasada (qué se eligió y cómo le fue a Nahue), Cola (las 141 en muro, ordenadas solo por C×), Mesa (P/G/D con la versión Nahue al lado) y Plan (vista del Sheet de contenido, sin armar otro tablero).
- **Mucho más Cubria.** Cuentas pasa a vista principal: sus 118 piezas de 30 días con búsqueda en 80 transcripts y 38 carruseles leídos, keywords que farmean, hall of fame por C× y un dossier de una pantalla. Cualquier pieza entra a la Cola aunque no sea de la semana. Lo que farmea es regalar una herramienta (mediana 489 comentarios), no su oferta (4,5).
- **Voz del lead para los setters.** Dolores, objeciones y jerga con cita literal y n, solo en castellano, con botón a la FAQ de setters. Hoy solo 14 de 684 comentarios bajados son del nicho.
- **Diseño:** oscuro de los paneles BM, navy #1F2A3D y dorado #F2B70D, una sola display para números, glifos solo en el semáforo (▲◆▼) y colores validados con dataviz. Se van crema, stencil, sellos y mono.

## Capturas (versión final, datos de las 03:02)

- **Cola:** `capturas/propuesta-v2/cola-desktop.png`
- **Mesa con la versión Nahue:** `capturas/propuesta-v2/mesa-desktop.png`
- **Cuenta Cubria:** `capturas/propuesta-v2/cuenta-cubria-desktop.png`
- **Celu (390px, sin scroll horizontal):** `plan-mobile.png`, `cuenta-mobile.png` e `historias-mobile.png`, más Cola, Mesa y Voz.
- **Maqueta andando:** `cd apps/radar-contenido/maquetas && python3 -m http.server 8791` y abrir http://localhost:8791/radar-v2.html. Andan P, G, D, J y K.

## P0 · para el lunes 28

- **Semana cerrada sin perder piezas [S].** Ventana de 7 días que cierra 72 h antes del corte (hoy: 15 al 22 sep, 140 piezas). Lo más nuevo queda en Madurando (63) y entra a la Cola siguiente, así nada se queda sin rankear.
- **El lote deja de llenar el kanban solo [S].** Hoy `run.py lunes` manda 20 filas "Idea" sin que nadie decida.
- **Kanban sin duplicados [S].** ID fijo `radar-<id>-<formato>`, sin timestamp, y cget habilitado en el proxy para chequear antes de cada cadd. El hub ya responde cget: hoy leí sus 97 filas.
- **Gate del lado del servidor [M].** Hoy la clave `contenido2026` viaja en el HTML y latest.json, cuentas/ramiro.cubria.json (448 KB con transcripts), slides y thumbs se bajan sin clave. La clave va a una función que setea una cookie firmada; edge function sobre `/data/**`, `/slides/**`, `/thumbs/**` y `/api/**`; cedit solo sobre filas `radar-*`. Clave nueva y propia del radar: la actual quedó expuesta.
- **El mismo finde, sin bloquear el lunes:** `run.py` ya transcribe con Groq los reels del top; falta leer los slides de los carruseles y correr los dos sobre toda la selección de la ventana antes de analizar. Además, foto semanal en Blobs desde ya y fix del desborde de 72px en el celu. Sin launchd (va en P1), la corrida se larga a mano.

## Decisiones de Tincho (25-sep)

1. **Sin tope semanal.** Nahue sube 4 piezas por día (28 por semana): la Mesa no bloquea Producir. Solo cuenta lo elegido.
2. **ManyChat fuera del flujo.** La keyword no frena ninguna pieza ni es motivo de descarte.
3. **Cuentas de IA en inglés = fuente de formato.** Quedan en el carril Formato: se toma el formato, el tema lo pone BM.
4. **Sandcastles: por ahora no.** Todo sale de Apify y Whisper.

Siguiente paso: implementar el P0 y la v2 en una sola sesión, porque hoy hay otra sesión editando el mismo sitio.
