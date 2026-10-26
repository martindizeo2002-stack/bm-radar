"""Baja comentarios de las piezas top (apify~instagram-comment-scraper) → data/comentarios/<semana>.jsonl"""
from __future__ import annotations
from . import config, apify


def correr(piezas_top: list[dict], por_pieza: int = 50, lote: int = 25) -> list[dict]:
    sem = config.semana_iso()
    salida = []
    urls = [p["url"] for p in piezas_top if p.get("url")]
    por_url = {p["url"].rstrip("/"): p["id"] for p in piezas_top}
    for i in range(0, len(urls), lote):
        chunk = urls[i:i + lote]
        items = apify.correr(config.ACTORS["ig_comments"], {"directUrls": chunk, "resultsLimit": por_pieza},
                             tag=f"com-{sem}-{i//lote}")
        for it in items:
            post_url = (it.get("postUrl") or it.get("url") or "").split("/c/")[0].rstrip("/")
            salida.append({
                "pieza_id": por_url.get(post_url),
                "post_url": post_url or None,
                "texto": (it.get("text") or "")[:1000],
                "autor": it.get("ownerUsername"),
                "likes": it.get("likesCount"),
                "respuestas": it.get("repliesCount"),
                "fecha": (it.get("timestamp") or "")[:19],
                "semana": sem,
            })
    path = config.COMENTARIOS / f"{sem}.jsonl"
    prev = config.leer_jsonl(path)
    config.escribir_jsonl(path, prev + salida)
    sin_match = sum(1 for s in salida if not s["pieza_id"])
    print(f"[comentarios] {len(salida)} bajados, {sin_match} sin pieza asociada")
    return salida


def por_pieza(sem: str | None = None) -> dict[str, list[dict]]:
    sem = sem or config.semana_iso()
    out: dict[str, list[dict]] = {}
    for c in config.leer_jsonl(config.COMENTARIOS / f"{sem}.jsonl"):
        if c.get("pieza_id"):
            out.setdefault(c["pieza_id"], []).append(c)
    return out
