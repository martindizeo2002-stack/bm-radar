"""Ingesta Instagram vía apify~instagram-scraper. Normaliza a 'pieza' y acumula en data/piezas/."""
from __future__ import annotations
import datetime as dt
from . import config, apify


def _perfil_url(handle: str) -> str:
    h = handle.strip().lstrip("@").split("/")[-1]
    return f"https://www.instagram.com/{h}/"


def semana_de(fecha: str) -> str:
    """Semana ISO de la fecha de publicación (no del scrape)."""
    try:
        d = dt.datetime.fromisoformat(fecha[:19])
        y, w, _ = d.isocalendar()
        return f"{y}-W{w:02d}"
    except Exception:
        return config.semana_iso()


def normalizar(item: dict, semana: str | None = None) -> dict | None:
    sc = item.get("shortCode") or item.get("shortcode")
    if not sc:
        return None
    tipo = item.get("type", "")
    pt = (item.get("productType") or "").lower()
    if tipo == "Video" or pt == "clips":
        tipo_media = "reel"
    elif tipo == "Sidecar":
        tipo_media = "carrusel"
    else:
        tipo_media = "post"
    views = item.get("videoPlayCount") or item.get("videoViewCount") or None
    ts = item.get("timestamp") or ""
    semana = semana_de(ts) if ts else (semana or config.semana_iso())
    return {
        "id": f"ig_{sc}",
        "plataforma": "ig",
        "cuenta": (item.get("ownerUsername") or "").lower(),
        "cuenta_fuente": (item.get("inputUrl") or "").rstrip("/").split("/")[-1].lower() or None,
        "url": item.get("url") or f"https://www.instagram.com/p/{sc}/",
        "tipo_media": tipo_media,
        "fecha": ts[:19],
        "caption": (item.get("caption") or "")[:2000],
        "hashtags": item.get("hashtags") or [],
        "likes": (item.get("likesCount") if isinstance(item.get("likesCount"), int) and item.get("likesCount") >= 0 else None),  # -1 = likes ocultos
        "comentarios": item.get("commentsCount") or 0,
        "views": views,
        "video_url": item.get("videoUrl"),
        "audio_url": item.get("audioUrl"),
        "slides": [u for u in (item.get("images") or []) if u] or [c.get("displayUrl") for c in (item.get("childPosts") or []) if c.get("displayUrl")],
        "fijado": bool(item.get("isPinned")),
        "thumb": item.get("displayUrl"),
        "duracion": item.get("videoDuration"),
        "semana": semana,
        "scraped_at": config.ahora().isoformat(timespec="seconds"),
    }


def correr(modo: str = "semanal", limite: int | None = None, cuentas: list[str] | None = None,
           dias: int = 7) -> list[dict]:
    """modo semanal: últimos `dias` días. modo historico: últimas `limite` piezas por cuenta (default 100)."""
    sem = config.cargar_semillas()
    handles = cuentas or [c["handle"] for c in sem.get("instagram", []) if c.get("activa", True)]
    if not handles:
        raise SystemExit("semillas.json sin cuentas de instagram activas")
    entrada = {
        "directUrls": [_perfil_url(h) for h in handles],
        "resultsType": "posts",
        "addParentData": False,
    }
    if modo == "historico":
        entrada["resultsLimit"] = limite or 100
    else:
        entrada["resultsLimit"] = limite or 40
        desde = (config.ahora() - dt.timedelta(days=dias)).strftime("%Y-%m-%d")
        entrada["onlyPostsNewerThan"] = desde
    items = apify.correr(config.ACTORS["ig_posts"], entrada, tag=f"ig-{modo}")
    piezas = [p for p in (normalizar(i) for i in items) if p]
    guardar(piezas)
    return piezas


def perfiles(cuentas: list[str] | None = None) -> dict:
    """Seguidores por cuenta (resultsType details) → data/perfiles.json."""
    import json
    sem = config.cargar_semillas()
    handles = cuentas or [c["handle"] for c in sem.get("instagram", []) if c.get("activa", True)]
    items = apify.correr(config.ACTORS["ig_posts"],
                         {"directUrls": [_perfil_url(h) for h in handles], "resultsType": "details",
                          "resultsLimit": 1, "addParentData": False}, tag="ig-perfiles")
    out = {}
    for it in items:
        u = (it.get("username") or "").lower()
        if u:
            out[u] = {"seguidores": it.get("followersCount"), "posts": it.get("postsCount"),
                      "nombre": it.get("fullName"), "bio": (it.get("biography") or "")[:300],
                      "actualizado": config.ahora().strftime("%Y-%m-%d")}
    path = config.DATA / "perfiles.json"
    prev = json.loads(path.read_text()) if path.exists() else {}
    prev.update(out)
    path.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
    print(f"[perfiles] {len(out)} cuentas actualizadas")
    return prev


ENRIQUECIDO = ("analisis", "recreacion", "transcript", "idioma", "slides_texto", "slides_local", "lectura")


def enriquecer(cambios: dict) -> None:
    """Aplica {id: {campo: valor}} sobre todas.jsonl."""
    path = config.PIEZAS / "todas.jsonl"
    with config.lock_piezas():
        rows = config.leer_jsonl(path)
        for r in rows:
            if r["id"] in cambios:
                r.update(cambios[r["id"]])
        config.escribir_jsonl(path, rows)


def guardar(piezas: list[dict]) -> None:
    """Acumula en data/piezas/todas.jsonl deduplicando por id (gana la más nueva: métricas actualizadas)."""
    path = config.PIEZAS / "todas.jsonl"
    with config.lock_piezas():
        _guardar(path, piezas)


def _guardar(path, piezas: list[dict]) -> None:
    prev = {p["id"]: p for p in config.leer_jsonl(path)}
    for p in piezas:
        viejo = prev.get(p["id"])
        if viejo:
            p["semana_primera"] = viejo.get("semana_primera") or viejo.get("semana")
            for k in ENRIQUECIDO:  # análisis, transcripts, recreaciones: el re-scrape solo actualiza métricas
                if k in viejo and k not in p:
                    p[k] = viejo[k]
        else:
            p.setdefault("semana_primera", p["semana"])
        prev[p["id"]] = p
    config.escribir_jsonl(path, list(prev.values()))
    print(f"[piezas] +{len(piezas)} → total {len(prev)}")


def todas() -> list[dict]:
    return config.leer_jsonl(config.PIEZAS / "todas.jsonl")
