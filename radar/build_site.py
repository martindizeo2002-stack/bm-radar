"""Ensambla site/data/latest.json (y copia por semana) para el radar estático."""
from __future__ import annotations
import json, datetime as dt
from . import config, score, ingest_ig, thumbs

VENTANA_DIAS = 30  # el sitio lleva todas las piezas de los últimos N días; período, objetivo y orden se filtran en la vista


def _kpis(sem_piezas: list[dict], todas: list[dict], base: dict) -> dict:
    cuentas = {p["cuenta"] for p in sem_piezas}
    bangers = [p for p in sem_piezas if (p.get("outlier") or 0) >= 3]
    return {
        "piezas": len(sem_piezas),
        "cuentas": len(cuentas),
        "bangers": len(bangers),
        "comentarios": sum(p.get("comentarios") or 0 for p in sem_piezas),
        "analizadas": sum(1 for p in sem_piezas if p.get("analisis")),
        "recreables": sum(1 for p in sem_piezas if (p.get("analisis") or {}).get("recreable")),
        "recreadas": sum(1 for p in sem_piezas if p.get("recreacion")),
        "con_views": sum(1 for p in sem_piezas if p.get("views")),
        "cuentas_con_baseline": sum(1 for c in cuentas if base.get(c, {}).get("med_views") or base.get(c, {}).get("med_likes")),
    }


def _semillas(sem_piezas: list[dict], base: dict, perfiles: dict) -> list[dict]:
    sem = config.cargar_semillas()
    out = []
    por_cuenta: dict[str, list[dict]] = {}
    for p in sem_piezas:
        por_cuenta.setdefault(p["cuenta"], []).append(p)
    for c in sem.get("instagram", []):
        h = c["handle"].lower().lstrip("@")
        ps = por_cuenta.get(h, [])
        out.append({
            "handle": h, "tags": c.get("tags", []), "activa": c.get("activa", True), "nota": c.get("nota", ""),
            "seguidores": (perfiles.get(h) or {}).get("seguidores"),
            "piezas_semana": len(ps),
            "comentarios_semana": sum(p.get("comentarios") or 0 for p in ps) if ps else None,
            "bangers": sum(1 for p in ps if (p.get("outlier") or 0) >= 3),
            "med_views": (base.get(h) or {}).get("med_views"),
            "med_likes": (base.get(h) or {}).get("med_likes"),
            "n_baseline": (base.get(h) or {}).get("n"),
        })
    return out


def _comentarios_resumen(sem: str) -> dict | None:
    path = config.ANALISIS / f"comentarios-{sem}.json"
    return json.loads(path.read_text()) if path.exists() else None


def build(sem: str | None = None, piezas: list[dict] | None = None, perfiles: dict | None = None, demo: bool = False) -> dict:
    sem = sem or config.semana_iso()
    todas = piezas if piezas is not None else ingest_ig.todas()
    if perfiles is None:
        pp = config.DATA / "perfiles.json"
        perfiles = json.loads(pp.read_text()) if pp.exists() else {}
    base = score.baseline([p for p in todas if p.get("semana") != sem] or todas)
    sem_piezas = score.puntuar(score.semana(todas, sem), base, perfiles)
    tendencias = score.tendencias(sem_piezas)
    desde = (config.ahora() - dt.timedelta(days=VENTANA_DIAS)).strftime("%Y-%m-%d")
    # antes: top 100 por comentarios de la semana ISO → escondía los carruseles de casos (pocos comentarios por diseño)
    ventana = score.puntuar([p for p in todas if (p.get("fecha") or "")[:10] >= desde], base, perfiles)
    top = sorted(ventana, key=lambda p: -(p.get("comentarios") or 0))
    campos = ["id", "plataforma", "cuenta", "cuenta_fuente", "url", "tipo_media", "fecha", "semana", "caption", "likes", "comentarios", "views",
              "duracion", "tasa_com", "outlier", "outlier_com", "eng_x_seg", "dias", "velocidad", "score", "fijado",
              "analisis", "guion", "objetivo", "recreacion", "transcript", "slides_texto", "slides_local", "lectura", "demo"]
    data = {
        "generado": config.ahora().isoformat(timespec="seconds"),
        "semana": sem,
        "demo": demo or any(p.get("demo") for p in sem_piezas),
        "kpis": _kpis(sem_piezas, todas, base),
        "piezas": [dict({k: p.get(k) for k in campos if k in p}, thumb_local=(f"thumbs/{p['id']}.jpg" if thumbs.existe(p['id']) else None)) for p in top],
        "ventana_dias": VENTANA_DIAS,
        "tendencias": tendencias,
        "semillas": _semillas(sem_piezas, base, perfiles),
        "comentarios": _comentarios_resumen(sem),
        "fuentes": {"piezas": "Apify instagram-scraper (apify~instagram-scraper)", "comentarios": "Apify instagram-comment-scraper",
                    "analisis": config.MODEL, "corte": config.ahora().strftime("%Y-%m-%d %H:%M ART")},
    }
    config.SITE_DATA.mkdir(parents=True, exist_ok=True)
    (config.SITE_DATA / "latest.json").write_text(json.dumps(data, ensure_ascii=False))
    historico(todas, base, perfiles, desde)
    try:
        from . import guion  # import tardío: guion importa llm (anthropic) y build_site corre también sin API
        guion.site_json()
    except OSError as e:
        # bajo launchd no se puede leer instagram-indice/ (Desktop): queda el guion.json del último build interactivo
        print(f"[build] guion sin actualizar ({type(e).__name__}): se conserva el último")
    from . import historias
    historias.site_json()
    try:
        from . import barrido
        barrido.sync_cuentas()  # la lista de cuentas del job de carruseles sale de semillas.json en cada build
    except OSError as e:
        print(f"[build] no pude sincronizar cuentas del barrido: {e}")
    (config.SITE_DATA / f"{sem}.json").write_text(json.dumps(data, ensure_ascii=False))
    print(f"[build] {sem} · {len(sem_piezas)} piezas semana · top {len(top)} · demo={data['demo']}")
    return data


LITE_AN = ("tipo", "formato", "recreable", "tipo_angulo", "angulo_comunicacion", "hook_texto", "keyword", "angulo_bm_id", "angulo_bm_nombre")
DETALLE = ("caption", "transcript", "idioma", "slides_texto", "slides_local", "lectura", "analisis", "recreacion", "guion")


def historico(todas: list[dict], base: dict, perfiles: dict, desde: str) -> dict:
    """Todo lo publicado antes de la ventana: site/data/historico.json (liviano, para la grilla 'Todo')
    y site/data/detalle/<cuenta>.json (transcript, slides, análisis) que la vista carga al abrir una pieza vieja."""
    viejas = score.puntuar([p for p in todas if (p.get("fecha") or "")[:10] < desde], base, perfiles)
    out, det = [], {}
    for p in viejas:
        a = p.get("analisis") or {}
        d = {k: p.get(k) for k in DETALLE if p.get(k)}
        cta = p.get("cuenta_fuente") or p.get("cuenta")
        out.append({
            "id": p["id"], "cuenta": p.get("cuenta"), "cuenta_fuente": p.get("cuenta_fuente"), "url": p.get("url"),
            "tipo_media": p.get("tipo_media"), "fecha": p.get("fecha"), "semana": p.get("semana"),
            "caption": (p.get("caption") or "")[:300], "likes": p.get("likes"), "comentarios": p.get("comentarios"),
            "views": p.get("views"), "duracion": p.get("duracion"), "fijado": p.get("fijado"),
            "outlier": p.get("outlier"), "tasa_com": p.get("tasa_com"), "score": p.get("score"), "objetivo": p.get("objetivo"),
            "analisis": {k: a.get(k) for k in LITE_AN if a.get(k) is not None} or None,
            "thumb_local": f"thumbs/{p['id']}.jpg" if thumbs.existe(p["id"]) else None,
            "hist": 1, "det": 1 if d else 0,
        })
        if d:
            det.setdefault(cta, {})[p["id"]] = d
    (config.SITE_DATA / "historico.json").write_text(json.dumps({"generado": config.ahora().isoformat(timespec="seconds"), "desde_ventana": desde,
                                                               "piezas": out}, ensure_ascii=False, separators=(",", ":")))
    carpeta = config.SITE_DATA / "detalle"
    carpeta.mkdir(exist_ok=True)
    for cta, piezas in det.items():
        (carpeta / f"{cta}.json").write_text(json.dumps(piezas, ensure_ascii=False, separators=(",", ":")))
    print(f"[build] histórico: {len(out)} piezas anteriores a {desde} · {sum(1 for x in out if x['thumb_local'])} con miniatura · detalle de {len(det)} cuentas")
    return {"n": len(out), "detalle": len(det)}
