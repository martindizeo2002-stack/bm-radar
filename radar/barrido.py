"""Integra al radar lo que junta el job de launchd ~/bm-barrido (carruseles y posts cada 12 h).
data/barrido es un symlink a ~/bm-barrido/data (el job vive fuera de Desktop por TCC)."""
from __future__ import annotations
import json, shutil
from . import config, ingest_ig

SRC = config.DATA / "barrido"
SITE = config.ROOT / "site"


def _leer(p) -> list[dict]:
    return [json.loads(l) for l in p.read_text().split("\n") if l.strip()] if p.exists() else []


def sync_cuentas() -> None:
    """cuentas.json del job = todas las semillas IG activas (incluida la propia, como baseline)."""
    if not SRC.exists():
        return
    s = config.cargar_semillas()
    c = [x["handle"] for x in s.get("instagram", []) if x.get("activa", True)]
    (SRC.resolve().parent / "cuentas.json").write_text(json.dumps(c, indent=1))


def sync() -> dict:
    sync_cuentas()
    if not SRC.exists():
        return {}
    posts = _leer(SRC / "posts.jsonl")
    piezas = [p for p in (ingest_ig.normalizar(it) for it in posts) if p]
    if piezas:
        ingest_ig.guardar(piezas)
    lect = {r["id"]: r for r in _leer(SRC / "lecturas.jsonl")}
    actuales = {p["id"]: p for p in ingest_ig.todas()}
    cambios, n_sl, n_th, n_lec = {}, 0, 0, 0
    for p in piezas:
        pid = p["id"]
        th_src, th_dst = SRC / "thumbs" / f"{pid}.jpg", SITE / "thumbs" / f"{pid}.jpg"
        if th_src.exists() and not th_dst.exists():
            shutil.copy2(th_src, th_dst); n_th += 1
        sl = SRC / "slides" / pid
        if p.get("tipo_media") == "carrusel" and sl.exists():
            dst = SITE / "slides" / pid
            dst.mkdir(parents=True, exist_ok=True)
            for f in sorted(sl.glob("*.jpg")):
                if not (dst / f.name).exists():
                    shutil.copy2(f, dst / f.name); n_sl += 1
            locs = sorted(f"slides/{pid}/{f.name}" for f in dst.glob("*.jpg"))
            if locs and actuales.get(pid, {}).get("slides_local") != locs:
                cambios.setdefault(pid, {})["slides_local"] = locs
        r = lect.get(pid)
        if r and not actuales.get(pid, {}).get("slides_texto"):
            cambios.setdefault(pid, {}).update({"slides_texto": r["slides_texto"], "lectura": r["lectura"]})
            n_lec += 1
    if cambios:
        ingest_ig.enriquecer(cambios)
    est = json.loads((SRC / "estado.json").read_text()) if (SRC / "estado.json").exists() else {}
    res = {"posts": len(piezas), "slides_copiadas": n_sl, "thumbs_copiadas": n_th, "lecturas_aplicadas": n_lec, "ultima_corrida": est.get("fecha")}
    print(f"[barrido] {res}")
    return res
