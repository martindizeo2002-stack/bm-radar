"""Scoring honesto: métrica principal = comentarios (Rama). Secundarias: tasa de comentarios, outlier vs mediana de la cuenta,
engagement por seguidor, velocidad. Dato faltante = None, jamás 0."""
from __future__ import annotations
import json, statistics, datetime as dt
from . import config


def _mediana(vals: list) -> float | None:
    vals = [v for v in vals if isinstance(v, (int, float)) and v > 0]
    return statistics.median(vals) if len(vals) >= 5 else None


def baseline(piezas: list[dict]) -> dict:
    """Mediana de views y likes por cuenta sobre sus últimas 30 piezas (excluye la semana actual para no auto-inflar)."""
    por_cuenta: dict[str, list[dict]] = {}
    for p in piezas:
        por_cuenta.setdefault(p["cuenta"], []).append(p)
    out = {}
    for c, ps in por_cuenta.items():
        ps = sorted(ps, key=lambda x: x.get("fecha") or "", reverse=True)[:30]
        out[c] = {"n": len(ps), "med_views": _mediana([p.get("views") for p in ps]),
                  "med_likes": _mediana([p.get("likes") for p in ps]),
                  "med_com": _mediana([p.get("comentarios") for p in ps])}
    return out


def puntuar(piezas: list[dict], base: dict, perfiles: dict, ahora: dt.datetime | None = None) -> list[dict]:
    ahora = ahora or config.ahora()
    for p in piezas:
        b = base.get(p["cuenta"], {})
        seg = (perfiles.get(p["cuenta"]) or {}).get("seguidores")
        com = p.get("comentarios") or 0
        views, likes = p.get("views"), p.get("likes")
        if isinstance(likes, (int, float)) and likes < 0:
            likes = None
            p["likes"] = None
        p["tasa_com"] = round(com / views, 4) if views and views > 0 else None
        if views and b.get("med_views"):
            p["outlier"] = round(views / b["med_views"], 2)
        elif likes and b.get("med_likes"):
            p["outlier"] = round(likes / b["med_likes"], 2)
        else:
            p["outlier"] = None
        p["outlier_com"] = round(com / b["med_com"], 2) if b.get("med_com") else None
        p["eng_x_seg"] = round(((likes or 0) + com) / seg, 4) if seg else None
        try:
            f = dt.datetime.fromisoformat(p["fecha"].replace("Z", "")).replace(tzinfo=dt.timezone.utc)
            dias = max((ahora - f).total_seconds() / 86400, 0.5)
        except Exception:
            dias = None
        p["dias"] = round(dias, 1) if dias else None
        p["velocidad"] = round(com / dias, 1) if dias else None
    # score compuesto por rangos (sin mezclar unidades): comentarios 50%, outlier 30%, tasa 20%
    def rank(key):
        vals = sorted({p[key] for p in piezas if p.get(key) is not None})
        pos = {v: i for i, v in enumerate(vals)}
        n = max(len(vals) - 1, 1)
        return {id(p): (pos[p[key]] / n if p.get(key) is not None else None) for p in piezas}
    rc, ro, rt = rank("comentarios"), rank("outlier"), rank("tasa_com")
    for p in piezas:
        partes = [(rc[id(p)], .5), (ro[id(p)], .3), (rt[id(p)], .2)]
        usadas = [(v, w) for v, w in partes if v is not None]
        if not usadas:
            p["score"] = None
            continue
        wtot = sum(w for _, w in usadas)
        p["score"] = round(100 * sum(v * w for v, w in usadas) / wtot)
    return piezas


def semana(piezas: list[dict], sem: str) -> list[dict]:
    return [p for p in piezas if p.get("semana") == sem]


def top(piezas: list[dict], n: int = 100, por: str = "comentarios") -> list[dict]:
    return sorted([p for p in piezas if p.get(por) is not None], key=lambda p: p[por], reverse=True)[:n]


def tendencias(piezas: list[dict]) -> dict:
    """Agregados cross-cuentas de la semana: formatos y hooks repetidos (requiere análisis)."""
    formatos: dict[str, int] = {}
    hooks: dict[str, list] = {}
    for p in piezas:
        a = p.get("analisis") or {}
        if a.get("formato"):
            formatos[a["formato"]] = formatos.get(a["formato"], 0) + 1
        if a.get("hook_patron"):
            hooks.setdefault(a["hook_patron"], []).append(p["cuenta"])
    hooks_rep = {h: sorted(set(c)) for h, c in hooks.items() if len(set(c)) >= 2}
    return {"formatos": dict(sorted(formatos.items(), key=lambda x: -x[1])),
            "hooks_repetidos": dict(sorted(hooks_rep.items(), key=lambda x: -len(x[1])))}
