"""Fábrica de recreación: de una pieza ajena a guion de reel, carrusel, historias y hooks en voz de Nahue.
Aplica las reglas duras de copy BM. Guarda en data/recreaciones/<id>.json y en la pieza."""
from __future__ import annotations
import json, re
from . import config, llm, ingest_ig

REGLAS_DURAS = """REGLAS DURAS (no negociables):
- Voz de Nahuel Urso, primera persona, rioplatense, seco, sin emojis, sin mayúsculas gritadas, sin signos de apertura (¿ ¡).
- PROHIBIDO el guion largo (—). Usá punto, dos puntos o punto medio (·).
- Jamás nombrar a Álvaro/Voltra, ni a competidores (Woker, Lorenzón, etc.).
- Nada de 'jubilados' o 'plan B para la jubilación' como pieza.
- Nada de 'vení con tu pareja/socio' ni empujar co-decisor.
- Nunca números de facturación de Nahue ni de Casa Perfecta salvo 'más de 7 contenedores por mes'. JAMÁS 'planta propia en China'.
- Del otro lado del chat está el EQUIPO, nunca prometer chat con Nahue.
- Sin precio ni rango de precio. Sin nombrar el programa ni entregables.
- Keyword en el CTA y en el caption (una palabra en mayúscula al final, ej: 'Comentá COSTOS').
- Casos de alumnos: solo genéricos ('un alumno de Rosario') salvo que la pieza original ya sea un caso propio de BM.
- Marca propia se MUESTRA, no se explica. Entrar por dolor.
- Jerga del lead: importador, trader, container, despachante, proveedor. NO broker, NO intermediario.
"""

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "reel": {"type": "object", "additionalProperties": False, "properties": {
            "titulo": {"type": "string"}, "hook": {"type": "string"},
            "guion": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                      "properties": {"beat": {"type": "string"}, "texto": {"type": "string"}, "visual": {"type": "string"}},
                      "required": ["beat", "texto", "visual"]}},
            "cta": {"type": "string"}, "caption": {"type": "string"}, "keyword": {"type": "string"},
            "formato_sugerido": {"type": "string"}, "duracion_seg": {"type": "integer"}},
            "required": ["titulo", "hook", "guion", "cta", "caption", "keyword", "formato_sugerido", "duracion_seg"]},
        "carrusel": {"type": "object", "additionalProperties": False, "properties": {
            "titulo": {"type": "string"},
            "slides": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                       "properties": {"n": {"type": "integer"}, "texto": {"type": "string"}, "visual": {"type": "string"}},
                       "required": ["n", "texto", "visual"]}},
            "caption": {"type": "string"}, "keyword": {"type": "string"}, "estilo_sugerido": {"type": "string"}},
            "required": ["titulo", "slides", "caption", "keyword", "estilo_sugerido"]},
        "historias": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                      "properties": {"n": {"type": "integer"}, "en_pantalla": {"type": "string"}, "hablado": {"type": "string"}, "sticker": {"type": "string"}},
                      "required": ["n", "en_pantalla", "hablado", "sticker"]}},
        "hooks": {"type": "array", "items": {"type": "string"}, "description": "5 hooks alternativos"},
        "nota_estratega": {"type": "string", "description": "por qué esta recreación puede funcionar para BM y qué riesgo tiene, 2 oraciones"},
    },
    "required": ["reel", "carrusel", "historias", "hooks", "nota_estratega"],
}

BANNED = [(r"—", "guion largo"), (r"\b[Áá]lvaro\b|\bVoltra\b", "Álvaro/Voltra"), (r"\bjubil", "jubilación"),
          (r"\b[Ww]oker\b|\b[Ll]orenz[oó]n\b", "competidor"), (r"planta propia", "planta propia"),
          (r"\bbroker\b|\bintermediario\b", "jerga vetada"), (r"[¿¡]", "signo de apertura")]


def _voz() -> str:
    partes = []
    for f in config.FUENTES_VOZ:
        if f.exists():
            partes.append(f"### {f.name}\n" + f.read_text()[:16000])
    return "\n\n".join(partes) or "(perfil de voz no disponible: escribí seco, rioplatense, directo)"


def _system() -> str:
    return f"""Sos el guionista de contenido de Brandmasters / ImpoMasters. Recreás piezas ganadoras de otras cuentas para la cuenta de Nahuel Urso (@nahue.urso), traduciéndolas al mundo de importar de China, marca propia y vender sin depender de nadie. No copiás: tomás el mecanismo (hook, estructura, por qué pega) y lo reescribís desde el sistema de Nahue.

{REGLAS_DURAS}

PERFIL DE VOZ Y REGLAS DE COPY (fuente de verdad):
{_voz()}

Formatos que rinden en la cuenta: on-site en el depósito (2,02x) > talking head (0,89x). 'La cuenta en pantalla' y 'caso en 3 pasos' son moldes propios validados. Hook 'Si vos estás...' está muerto: no usarlo.
"""


def _user(p: dict) -> str:
    a = p.get("analisis") or {}
    return f"""PIEZA ORIGINAL (@{p['cuenta']}, {p['tipo_media']}, {p.get('comentarios')} comentarios, {p.get('views') or '—'} views, outlier {p.get('outlier') or '—'}x)
CAPTION: {p.get('caption','')[:1200]}
{('TRANSCRIPT: ' + p['transcript'][:2500]) if p.get('transcript') else ''}
ANÁLISIS: formato {a.get('formato')} · tipo {a.get('tipo')} · hook_patron "{a.get('hook_patron')}" · por qué pega: {a.get('por_que_pega')}
ÁNGULO BM: {a.get('angulo_bm_id')} {a.get('angulo_bm_nombre')} · cómo recrear: {a.get('como_recrear')}

Entregá: reel (guion por beats con texto hablado + visual), carrusel (7-9 slides, texto corto por slide, primera slide = hook), 5 historias (en pantalla vs hablado, sticker/CTA), 5 hooks alternativos, nota de estratega."""


def limpiar(obj):
    """Aplica reglas mecánicas (guion largo → dos puntos/punto) recursivamente."""
    if isinstance(obj, str):
        s = re.sub(r"\s*—\s*", ": ", obj)
        return s.replace("¿", "").replace("¡", "")
    if isinstance(obj, list):
        return [limpiar(x) for x in obj]
    if isinstance(obj, dict):
        return {k: limpiar(v) for k, v in obj.items()}
    return obj


def violaciones(obj) -> list[str]:
    texto = json.dumps(obj, ensure_ascii=False)
    return sorted({nombre for pat, nombre in BANNED if re.search(pat, texto)})


def pieza(p: dict, effort: str = "high") -> dict:
    out = llm.json_call(_system(), _user(p), SCHEMA, effort=effort, max_tokens=16000)
    usage = out.pop("_usage", None)
    out = limpiar(out)
    out["violaciones"] = violaciones(out)
    out["modelo"] = (usage or {}).get("model")
    out["generado"] = config.ahora().isoformat(timespec="seconds")
    out["pieza_id"] = p["id"]
    (config.RECREACIONES / f"{p['id']}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    p["recreacion"] = {k: out[k] for k in ("reel", "carrusel", "historias", "hooks", "nota_estratega", "violaciones", "generado")}
    _persistir(p)
    print(f"[recrear] {p['id']} @{p['cuenta']} · violaciones {out['violaciones'] or 'ninguna'}")
    return out


def _persistir(p: dict) -> None:
    ingest_ig.enriquecer({p["id"]: {"recreacion": p["recreacion"]}})
