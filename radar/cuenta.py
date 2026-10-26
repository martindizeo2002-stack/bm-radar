"""Vista profunda de una cuenta: todas sus piezas de N días + agregados + dossier → site/data/cuentas/<handle>.json"""
from __future__ import annotations
import json, statistics, datetime as dt
from collections import Counter, defaultdict
from . import config, ingest_ig, thumbs

CUENTAS = config.SITE_DATA / "cuentas"
CUENTAS.mkdir(parents=True, exist_ok=True)
DIAS_SEM = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def _med(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return statistics.median(vals) if vals else None


def _art(fecha: str):
    try:
        return dt.datetime.fromisoformat(fecha[:19]) + dt.timedelta(hours=config.TZ_OFFSET)
    except Exception:
        return None


def piezas_de(handle: str, dias: int | None = None) -> list[dict]:
    h = handle.lower().lstrip("@")
    ps = [p for p in ingest_ig.todas() if p["cuenta"] == h or p.get("cuenta_fuente") == h]
    if dias:
        corte = (config.ahora() - dt.timedelta(days=dias)).strftime("%Y-%m-%d")
        ps = [p for p in ps if (p.get("fecha") or "") >= corte]
    return sorted(ps, key=lambda p: p.get("fecha") or "", reverse=True)


def agregados(ps: list[dict]) -> dict:
    no_fij = [p for p in ps if not p.get("fijado")]
    fechas = [_art(p["fecha"]) for p in no_fij if p.get("fecha")]
    fechas = [f for f in fechas if f]
    dias_span = max((max(fechas) - min(fechas)).days + 1, 1) if fechas else None
    por_formato = defaultdict(list)
    for p in no_fij:
        por_formato[p["tipo_media"]].append(p)
    formatos = {k: {"n": len(v), "med_com": _med([x.get("comentarios") for x in v]), "med_likes": _med([x.get("likes") for x in v]),
                    "med_views": _med([x.get("views") for x in v])} for k, v in por_formato.items()}
    kw = defaultdict(list)
    for p in no_fij:
        k = ((p.get("analisis") or {}).get("keyword") or "").strip().upper()
        if k:
            kw[k].append(p)
    keywords = sorted([{"keyword": k, "n": len(v), "com_total": sum(x.get("comentarios") or 0 for x in v),
                        "med_com": _med([x.get("comentarios") for x in v]),
                        "recurso": next(((x.get("analisis") or {}).get("recurso_prometido") for x in v if (x.get("analisis") or {}).get("recurso_prometido")), "")}
                       for k, v in kw.items()], key=lambda x: -x["com_total"])
    tipos = Counter((p.get("analisis") or {}).get("tipo") for p in no_fij if p.get("analisis"))
    formas = Counter((p.get("analisis") or {}).get("formato") for p in no_fij if p.get("analisis"))
    hooks = defaultdict(list)
    for p in no_fij:
        h = (p.get("analisis") or {}).get("hook_patron")
        if h:
            hooks[h].append(p.get("comentarios") or 0)
    hooks = sorted([{"patron": h, "n": len(v), "med_com": _med(v)} for h, v in hooks.items()], key=lambda x: (-x["n"], -(x["med_com"] or 0)))
    horas = Counter(f.hour for f in fechas)
    dsem = Counter(DIAS_SEM[f.weekday()] for f in fechas)
    serie = defaultdict(lambda: {"n": 0, "com": 0})
    for p in no_fij:
        f = _art(p.get("fecha") or "")
        if f:
            d = f.strftime("%Y-%m-%d")
            serie[d]["n"] += 1
            serie[d]["com"] += p.get("comentarios") or 0
    durs = [p.get("duracion") for p in no_fij if p.get("tipo_media") == "reel" and p.get("duracion")]
    slides_n = [len(p.get("slides") or []) for p in no_fij if p.get("tipo_media") == "carrusel" and p.get("slides")]
    return {
        "n": len(no_fij), "fijados": len(ps) - len(no_fij), "dias": dias_span,
        "por_dia": round(len(no_fij) / dias_span, 2) if dias_span else None,
        "com_total": sum(p.get("comentarios") or 0 for p in no_fij),
        "med_com": _med([p.get("comentarios") for p in no_fij]),
        "med_likes": _med([p.get("likes") for p in no_fij]),
        "med_views_reel": _med([p.get("views") for p in no_fij if p.get("tipo_media") == "reel"]),
        "dur_med_reel": round(_med(durs), 1) if durs else None,
        "slides_med": _med(slides_n),
        "formatos": formatos, "tipos": dict(tipos.most_common()), "formatos_analisis": dict(formas.most_common()),
        "keywords": keywords[:30], "hooks": hooks[:25],
        "horas": {str(h): horas.get(h, 0) for h in range(24)},
        "dias_semana": {d: dsem.get(d, 0) for d in DIAS_SEM},
        "serie": [{"fecha": d, **v} for d, v in sorted(serie.items())],
        "con_transcript": sum(1 for p in no_fij if p.get("transcript")),
        "con_slides": sum(1 for p in no_fij if p.get("slides_texto")),
        "analizadas": sum(1 for p in no_fij if p.get("analisis")),
    }


CAMPOS = ["id", "cuenta", "cuenta_fuente", "url", "tipo_media", "fecha", "caption", "likes", "comentarios", "views", "duracion",
          "fijado", "analisis", "guion", "recreacion", "transcript", "idioma", "slides_texto", "slides_local", "lectura"]


def _pieza(p: dict, med_hist) -> dict:
    d = {k: p.get(k) for k in CAMPOS if k in p}
    com, views = p.get("comentarios") or 0, p.get("views")
    d["outlier_com"] = round(com / med_hist, 2) if med_hist else None
    d["outlier"] = d["outlier_com"]  # en la vista de cuenta el outlier es por comentarios vs mediana histórica de la cuenta
    d["tasa_com"] = round(com / views, 4) if views else None
    f = _art(p.get("fecha") or "")
    dias = max((config.ahora().replace(tzinfo=None) - f).total_seconds() / 86400, 0.5) if f else None
    d["velocidad"] = round(com / dias, 1) if dias else None
    d["thumb_local"] = f"thumbs/{p['id']}.jpg" if thumbs.existe(p["id"]) else None
    return d


def build(handle: str, dias: int = 30) -> dict:
    h = handle.lower().lstrip("@")
    ps30 = piezas_de(h, dias)
    todas = piezas_de(h)
    med_hist = _med([p.get("comentarios") for p in todas if not p.get("fijado")])
    perf = json.loads((config.DATA / "perfiles.json").read_text()).get(h, {}) if (config.DATA / "perfiles.json").exists() else {}
    dossier_p = config.ANALISIS / f"dossier-{h}.json"
    out = {
        "handle": h, "dias": dias, "generado": config.ahora().isoformat(timespec="seconds"),
        "perfil": perf, "historico": {"n": len(todas), "desde": (todas[-1].get("fecha") or "")[:10] if todas else None, "med_com": med_hist},
        "agregados": agregados(ps30),
        "piezas": [_pieza(p, med_hist) for p in ps30],
        "dossier": json.loads(dossier_p.read_text()) if dossier_p.exists() else None,
    }
    (CUENTAS / f"{h}.json").write_text(json.dumps(out, ensure_ascii=False))
    idx_p = CUENTAS / "index.json"
    idx = json.loads(idx_p.read_text()) if idx_p.exists() else {}
    idx[h] = {"handle": h, "dias": dias, "n": out["agregados"]["n"], "generado": out["generado"], "dossier": bool(out["dossier"])}
    idx_p.write_text(json.dumps(idx, ensure_ascii=False))
    print(f"[cuenta] @{h} · {out['agregados']['n']} piezas {dias}d · transcripts {out['agregados']['con_transcript']} · carruseles leídos {out['agregados']['con_slides']} · dossier {bool(out['dossier'])}")
    return out
