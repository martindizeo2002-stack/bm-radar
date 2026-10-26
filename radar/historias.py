"""Historias capturadas por el job diario (~/bm-historias, launchd) → pestaña Historias del radar.

data/historias es un symlink a ~/bm-historias/data (el job vive fuera de Desktop por TCC).
Nahue: Graph API (texto, alcance, respuestas, navegación). Creadores: Apify (frame, transcript, stickers).
"""
from __future__ import annotations
import json, shutil
from . import config

SRC = config.DATA / "historias"
DEST = config.ROOT / "site" / "historias"


def sync_cuentas() -> None:
    """cuentas.json del job = semillas IG activas que no son propias (el job no puede leer Desktop)."""
    if not SRC.exists():
        return
    s = config.cargar_semillas()
    c = [x["handle"] for x in s.get("instagram", []) if x.get("activa") and "propia" not in x.get("tags", []) and x.get("historias", True)]
    (SRC.resolve().parent / "cuentas.json").write_text(json.dumps(c, indent=1))


def _leer(p) -> list[dict]:
    return [json.loads(l) for l in p.read_text().split("\n") if l.strip()] if p.exists() else []


def site_json() -> dict:
    sync_cuentas()
    rows = []
    for carpeta in ("nahue", "competencia"):
        for h in _leer(SRC / carpeta / "historias.jsonl"):
            fr = h.get("frame")
            if fr:
                src, dst = SRC / carpeta / fr, DEST / carpeta / fr
                if src.exists() and not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                fr = f"historias/{carpeta}/{fr}" if dst.exists() else None
            m = h.get("metricas") or {}
            alc = m.get("reach")
            rows.append({"id": h["id"], "cuenta": h.get("cuenta"), "fecha": h.get("fecha"), "tipo": h.get("tipo"),
                         "dur": h.get("duracion"), "caption": (h.get("caption") or "")[:400], "tx": (h.get("transcript") or "")[:600],
                         "st": h.get("stickers") or {}, "fr": fr, "url": h.get("permalink"),
                         "m": {"alcance": alc, "respuestas": m.get("replies"), "shares": m.get("shares"), "visitas": m.get("profile_visits"),
                               "follows": m.get("follows"), "salidas": m.get("tap_exit"), "avances": m.get("tap_forward"),
                               "salida_pct": round(m["tap_exit"] / alc * 100, 1) if alc and m.get("tap_exit") is not None else None,
                               "resp_k": round(m["replies"] / alc * 1000, 1) if alc and m.get("replies") is not None else None} if m else None,
                         "m_at": h.get("metricas_at")})
    est = json.loads((SRC / "estado.json").read_text()) if (SRC / "estado.json").exists() else {}
    data = {"generado": config.ahora().isoformat(timespec="seconds"), "historias": sorted(rows, key=lambda r: r["fecha"] or "", reverse=True),
            "competencia_ultima": est.get("competencia_ts"), "competencia_usd": est.get("competencia_usd")}
    (config.SITE_DATA / "historias.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return data
