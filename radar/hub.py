"""Escribe ideas en el kanban del hub (Sheet 'Contenido BM — Ideas e Historias') vía la función panel del hub en prod.
No toca el código del hub: usa la misma API que usa contenido.html."""
from __future__ import annotations
import time, json
import requests
from . import config


def cadd_idea(data: dict) -> dict:
    if not config.HUB_KEY:
        raise RuntimeError("Falta HUB_KEY en .env (la clave del hub)")
    body = {"token": "impo2026-panel", "action": "cadd", "tab": "Ideas", "data": data}
    r = requests.post(config.HUB_URL, headers={"x-hub-key": config.HUB_KEY, "content-type": "application/json"},
                      data=json.dumps(body), timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"hub cadd {r.status_code}: {r.text[:200]}")
    j = r.json()
    if isinstance(j, dict) and j.get("error"):
        raise RuntimeError(f"hub cadd error: {j['error']}")
    return j


def _guion_txt(rec: dict, formato: str) -> str:
    if formato == "carrusel":
        return ("\n".join(f"{x.get('n')}. {x.get('texto','')}" for x in rec.get("slides", [])) + f"\n\nCaption: {rec.get('caption','')}")[:6000]
    return (f"{rec.get('hook','')}\n\n" + "\n".join(f"[{x.get('beat')}] {x.get('texto','')}" for x in rec.get("guion", []))
            + f"\n\nCTA: {rec.get('cta','')}\n\nCaption: {rec.get('caption','')}")[:6000]


def idea_desde_recreacion(pieza: dict, rec: dict, formato: str) -> dict:
    """Mapea una recreación al esquema del tab Ideas (mismas columnas que usa el hub)."""
    cuadrante = {"tofu": "tofu", "problema": "problema", "solucion": "solucion", "producto": "producto",
                 "mentalidad": "confianza"}.get((pieza.get("analisis") or {}).get("tipo", "problema"), "problema")
    return {
        "ID": f"radar-{pieza['id']}-{formato}-{int(time.time())}",
        "Canal": "Instagram",
        "Titulo": rec.get("titulo") or rec.get("hook") or pieza.get("caption", "")[:80],
        "Cuadrante": cuadrante,
        "Angulo": (pieza.get("analisis") or {}).get("angulo_bm_nombre", ""),
        "Formato": "carrusel" if formato == "carrusel" else "reel",
        "Estado": "Idea",
        "Creada": config.ahora().strftime("%Y-%m-%d"),
        "Referencias": pieza.get("url", ""),  # el Sheet no tiene columna Fuente
        "Guion": _guion_txt(rec, formato),
        "Notas": f"Radar · @{pieza.get('cuenta')} · {pieza.get('comentarios')} com · {pieza.get('views') or '—'} views · score {pieza.get('score')}",
    }
