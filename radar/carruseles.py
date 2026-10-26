"""Lectura de carruseles slide por slide con visión de Claude: texto literal de cada slide + visual + diseño."""
from __future__ import annotations
import base64
from concurrent.futures import ThreadPoolExecutor
from . import config, llm, ingest_ig

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "slides": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                   "properties": {"n": {"type": "integer"}, "texto": {"type": "string", "description": "texto literal que aparece en la slide"},
                                  "visual": {"type": "string", "description": "qué se ve, 1 línea"}},
                   "required": ["n", "texto", "visual"]}},
        "diseno": {"type": "string", "description": "estilo visual del carrusel en 1-2 líneas: tipografía, fondo, fotos, colores, marcas"},
        "estructura": {"type": "string", "description": "cómo avanza el argumento de slide a slide, 1-2 líneas"},
        "cierre": {"type": "string", "description": "qué pide la última slide"},
    },
    "required": ["slides", "diseno", "estructura", "cierre"],
}
SYSTEM = "Leés carruseles de Instagram. Transcribí el texto literal de cada slide en orden (respetá mayúsculas y números, sin inventar), describí qué se ve en una línea y resumí diseño, estructura y cierre. Español."


def leer(p: dict) -> dict | None:
    locs = p.get("slides_local") or []
    if not locs:
        return None
    bloques = []
    for i, rel in enumerate(locs[:20], 1):
        f = config.ROOT / "site" / rel
        if not f.exists():
            continue
        bloques.append({"type": "text", "text": f"Slide {i}:"})
        bloques.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.standard_b64encode(f.read_bytes()).decode()}})
    bloques.append({"type": "text", "text": f"Caption: {p.get('caption','')[:600]}\nLeé el carrusel completo."})
    out = llm.json_call(SYSTEM, bloques, SCHEMA, effort="low", max_tokens=8000)
    out.pop("_usage", None)
    return out


def correr(piezas: list[dict], forzar: bool = False, hilos: int = 5) -> int:
    pend = [p for p in piezas if p.get("tipo_media") == "carrusel" and p.get("slides_local") and (forzar or not p.get("slides_texto"))]

    def _uno(p):
        try:
            return p, leer(p)
        except Exception as e:
            print(f"[carrusel] {p['id']} error {str(e)[:120]}")
            return p, None

    cambios = {}
    with ThreadPoolExecutor(hilos) as ex:
        for p, out in ex.map(_uno, pend):
            if out:
                cambios[p["id"]] = {"slides_texto": out["slides"], "lectura": {k: out[k] for k in ("diseno", "estructura", "cierre")}}
                p["slides_texto"], p["lectura"] = out["slides"], cambios[p["id"]]["lectura"]
    if cambios:
        ingest_ig.enriquecer(cambios)
    print(f"[carrusel] {len(cambios)}/{len(pend)} carruseles leídos")
    return len(cambios)
