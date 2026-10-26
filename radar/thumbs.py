"""Baja las miniaturas (displayUrl de Apify, links firmados que vencen) a site/thumbs/<id>.jpg y las achica con sips (macOS)."""
from __future__ import annotations
import subprocess, shutil
import requests
from . import config

THUMBS = config.ROOT / "site" / "thumbs"
THUMBS.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"}


def bajar(piezas: list[dict], ancho: int = 480, forzar: bool = False, hilos: int = 8) -> int:
    """Baja en paralelo (las URLs de Apify vencen en 1-2 días: conviene bajar apenas se scrapea)."""
    from concurrent.futures import ThreadPoolExecutor
    pend = [p for p in piezas if p.get("thumb") and (forzar or not (THUMBS / f"{p['id']}.jpg").exists())]
    with ThreadPoolExecutor(hilos) as ex:
        n = sum(ex.map(lambda p: _una(p, ancho), pend))
    print(f"[thumbs] {n}/{len(pend)} bajadas · {sum(1 for _ in THUMBS.glob('*.jpg'))} en total")
    return n


def _una(p: dict, ancho: int) -> int:
    url, dest = p.get("thumb"), THUMBS / f"{p['id']}.jpg"
    if True:
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code != 200 or not r.content:
                return 0
            dest.write_bytes(r.content)
            if shutil.which("sips"):
                subprocess.run(["sips", "-Z", str(ancho), "-s", "format", "jpeg", "-s", "formatOptions", "70", str(dest), "--out", str(dest)],
                               capture_output=True)
            return 1
        except Exception:
            return 0


def existe(pieza_id: str) -> bool:
    return (THUMBS / f"{pieza_id}.jpg").exists()
