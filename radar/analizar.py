"""Análisis por pieza (formato, hook, tipo, ángulo BM, recreable) y minería de comentarios."""
from __future__ import annotations
import json
from . import config, llm, ingest_ig

FORMATOS = ["talking_head", "on_site_depo", "texto_pantalla", "pov_sketch", "carrusel", "meme", "listicle",
            "screen_recording", "entrevista_podcast", "caso_cliente", "demo_producto", "otro"]
TIPOS = ["tofu", "problema", "solucion", "producto", "mentalidad"]
TIPOS_ANGULO = ["dolor", "miedo", "deseo_aspiracional", "oportunidad_why_now", "contrarian", "enemigo_comun", "error_comun",
                "educativo_como", "prueba_caso", "autoridad_credencial", "historia_personal", "oferta_directa", "curiosidad_revelacion",
                "lifestyle", "humor_entretenimiento", "otro"]
NIVELES = ["inconsciente", "consciente_problema", "consciente_solucion", "consciente_producto", "mas_consciente"]

SCHEMA_PIEZA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "piezas": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "id": {"type": "string"},
                "formato": {"type": "string", "enum": FORMATOS},
                "tipo": {"type": "string", "enum": TIPOS},
                "nivel_conciencia": {"type": "string", "enum": NIVELES},
                "hook_texto": {"type": "string"},
                "hook_patron": {"type": "string", "description": "patrón abstracto reutilizable, 3-8 palabras, ej: 'no hagas X, hacé Y' / 'la cuenta en pantalla' / 'pregunta incómoda al avatar'"},
                "estructura": {"type": "array", "items": {"type": "string"}, "description": "beats en orden, 3-6"},
                "cta": {"type": "string"},
                "keyword": {"type": "string"},
                "por_que_pega": {"type": "string", "description": "qué mecanismo del contenido invita a comentar o a mirar, 1-2 oraciones. Solo desde el contenido: no ves métricas"},
                "angulo_bm_id": {"type": "integer", "description": "0 si no mapea"},
                "angulo_bm_nombre": {"type": "string"},
                "recreable": {"type": "boolean"},
                "como_recrear": {"type": "string", "description": "cómo se traduce a importaciones/marca propia para BM, 1-3 oraciones. Vacío si no recreable"},
                "temas": {"type": "array", "items": {"type": "string"}},
                "recurso_prometido": {"type": "string", "description": "qué se promete a cambio del comentario o follow (guía, prompt, plantilla, clase). Vacío si nada"},
                "angulo_comunicacion": {"type": "string", "description": "el ángulo en 4-10 palabras, en el idioma del mercado, ej: 'tu proveedor te está cagando', 'importar con poca plata', 'el producto que nadie trae'"},
                "tipo_angulo": {"type": "string", "enum": TIPOS_ANGULO},
                "avatar": {"type": "string", "description": "a quién le habla, 3-8 palabras (ej: 'emprendedor que arranca de cero', 'comercio que revende local')"},
                "promesa": {"type": "string", "description": "la promesa o resultado que ofrece la pieza, 1 línea. Vacío si no hay"},
            },
            "required": ["id", "formato", "tipo", "nivel_conciencia", "hook_texto", "hook_patron", "estructura", "cta",
                         "keyword", "por_que_pega", "angulo_bm_id", "angulo_bm_nombre", "recreable", "como_recrear", "temas", "recurso_prometido",
                         "angulo_comunicacion", "tipo_angulo", "avatar", "promesa"],
        }}
    },
    "required": ["piezas"],
}

SCHEMA_COMENTARIOS = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "dolores": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                    "properties": {"tema": {"type": "string"}, "n": {"type": "integer"}, "ejemplos": {"type": "array", "items": {"type": "string"}}},
                    "required": ["tema", "n", "ejemplos"]}},
        "objeciones": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                       "properties": {"tema": {"type": "string"}, "n": {"type": "integer"}, "ejemplos": {"type": "array", "items": {"type": "string"}}},
                       "required": ["tema", "n", "ejemplos"]}},
        "preguntas": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                      "properties": {"pregunta": {"type": "string"}, "n": {"type": "integer"}}, "required": ["pregunta", "n"]}},
        "jerga": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                  "properties": {"palabra": {"type": "string"}, "contexto": {"type": "string"}}, "required": ["palabra", "contexto"]}},
        "ideas_contenido": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["dolores", "objeciones", "preguntas", "jerga", "ideas_contenido"],
}


def _banco() -> str:
    if config.BANCO_ANGULOS.exists():
        return config.BANCO_ANGULOS.read_text()[:30000]
    return "(banco de ángulos no disponible)"


def _system_pieza() -> str:
    return f"""Sos el analista de contenido de Brandmasters / ImpoMasters (BM): infoproducto de Nahuel Urso que enseña a importar de China, crear marca propia y vender multicanal. Avatar: dueños de negocio físico o ecommerce en Argentina y LATAM que todavía no importan (miedo, no saben la cuenta) o importan mal (broker, Paraguay, Once, Alibaba caro).

Tu tarea: dado un lote de piezas de Instagram de OTRAS cuentas (nicho, competencia o cuentas que farmean comentarios), clasificar cada una y decidir si se puede recrear para BM.

Reglas:
- formato: cómo está filmada/armada. tipo: función en el embudo (tofu = volumen/curiosidad masiva; problema = agita dolor; solucion = enseña mecanismo; producto = oferta/caso; mentalidad = actitud).
- hook_patron es lo reutilizable: el molde del gancho, no el texto.
- por_que_pega: explicá el mecanismo de comentarios (pregunta abierta, lista incompleta, polémica, 'comentá X', identificación, error común) o de views (curiosidad, número, contraste).
- angulo_bm_id: elegí el ID del banco de abajo que mejor calza; 0 si no calza con ninguno. Si la pieza es TOFU genérico (mentalidad, negocios en general) suele ser 0 y aun así puede ser recreable.
- angulo_comunicacion: la idea madre que usa para enganchar, con las palabras del mercado. tipo_angulo: el mecanismo psicológico dominante (uno solo). avatar y promesa: a quién le habla y qué le promete, concretos.
- recreable: true si hay una traducción natural a importar/marca propia/vender. como_recrear: concreto, en una línea, sin genérico.
- No ves métricas a propósito (regla de creator-lab: clasificar a ciegas y cruzar con performance después). Juzgá solo caption, transcript y slides.
- Español rioplatense, seco. Nada de emojis.

BANCO DE ÁNGULOS BM (ID · comunicación · evidencia · estado):
{_banco()}
"""


def _resumen_pieza(p: dict) -> str:
    t = f"\nTRANSCRIPT: {p['transcript'][:2500]}" if p.get("transcript") else ""
    sl = ""
    if p.get("slides_texto"):
        sl = "\nSLIDES: " + " | ".join(f"{x.get('n')}. {x.get('texto','')}" for x in p["slides_texto"])[:2500]
    return f"[id={p['id']}] @{p['cuenta']} · {p['tipo_media']} · {p.get('fecha','')[:10]}\nCAPTION: {p.get('caption','')[:900]}{t}{sl}"


def piezas(lista: list[dict], lote: int = 8, effort: str = "medium", forzar: bool = False, hilos: int = 4) -> list[dict]:
    """Analiza las piezas sin `analisis` (o todas si forzar). Persiste en todas.jsonl y en data/analisis/<semana>.jsonl."""
    pendientes = [p for p in lista if forzar or not p.get("analisis")]
    if not pendientes:
        print("[analizar] nada pendiente")
        return lista
    system = _system_pieza()
    por_id = {p["id"]: p for p in lista}
    hechos = []
    chunks = [pendientes[i:i + lote] for i in range(0, len(pendientes), lote)]

    def _uno(chunk):
        user = "Analizá estas piezas y devolvé un item por id:\n\n" + "\n\n".join(_resumen_pieza(p) for p in chunk)
        return chunk, llm.json_call(system, user, SCHEMA_PIEZA, effort=effort)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(hilos) as ex:
        for k, (chunk, out) in enumerate(ex.map(_uno, chunks), 1):
            for a in out.get("piezas", []):
                p = por_id.get(a.get("id"))
                if not p:
                    continue
                p["analisis"] = {kk: v for kk, v in a.items() if kk != "id"}
                p["analisis"]["modelo"] = out["_usage"]["model"]
                p["analisis"]["con_medios"] = bool(p.get("transcript") or p.get("slides_texto"))
                hechos.append(p)
            print(f"[analizar] lote {k}/{len(chunks)}: {len(chunk)} piezas · tokens in {out['_usage']['in']} out {out['_usage']['out']} cache {out['_usage']['cache_read']}")
    _persistir(hechos)
    return lista


def _persistir(hechos: list[dict]) -> None:
    if not hechos:
        return
    ingest_ig.enriquecer({p["id"]: {"analisis": p["analisis"]} for p in hechos})
    sem = config.semana_iso()
    path = config.ANALISIS / f"{sem}.jsonl"
    prev = {r["id"]: r for r in config.leer_jsonl(path)}
    for p in hechos:
        prev[p["id"]] = {"id": p["id"], "cuenta": p["cuenta"], "url": p["url"], "analisis": p["analisis"]}
    config.escribir_jsonl(path, list(prev.values()))


def comentarios(coms: list[dict], sem: str | None = None, max_n: int = 400) -> dict:
    """Minería de comentarios de la semana → dolores, objeciones, preguntas, jerga, ideas."""
    sem = sem or config.semana_iso()
    textos = [c["texto"] for c in coms if c.get("texto") and len(c["texto"]) > 8][:max_n]
    if len(textos) < 20:
        print(f"[comentarios] solo {len(textos)} comentarios, no alcanza (mín 20)")
        return {}
    system = """Sos analista de voz del cliente para Brandmasters / ImpoMasters (importar de China, marca propia, ecommerce, Argentina). Recibís comentarios reales de Instagram de cuentas del nicho. Extraé dolores, objeciones, preguntas frecuentes, jerga textual del público (palabras que usan ellos, no marketing) e ideas de contenido que respondan a eso. Contá aproximado (n) cuántos comentarios tocan cada tema. Ejemplos textuales, cortos. Español rioplatense. Sin emojis."""
    user = "COMENTARIOS (uno por línea):\n" + "\n".join(f"- {t[:240]}" for t in textos)
    out = llm.json_call(system, user, SCHEMA_COMENTARIOS, effort="medium")
    out["n_comentarios"] = len(textos)
    out["semana"] = sem
    (config.ANALISIS / f"comentarios-{sem}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"[comentarios] analizados {len(textos)} · dolores {len(out.get('dolores', []))}")
    return out
