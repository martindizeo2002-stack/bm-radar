"""Procesamiento profundo en lote: transcribe reels, lee carruseles, analiza con medios y arma la vista por cuenta.
Uso desde run.py:  run.py profundo --cuentas a,b [--dias 31 | --todo] [--motor local|groq] [--etapa transcribir|carruseles|analizar|cuentas|todo]"""
from __future__ import annotations
import time
from . import media, carruseles, analizar, cuenta


def piezas(cuentas: list[str], dias: int | None) -> list[dict]:
    out = []
    for h in cuentas:
        out += cuenta.piezas_de(h, dias)
    return out


def transcribir(cuentas: list[str], dias: int | None, motor: str | None = None) -> int:
    ps = [p for p in piezas(cuentas, dias) if p.get("tipo_media") == "reel"]
    ps.sort(key=lambda p: p.get("fecha") or "", reverse=True)  # lo más nuevo primero
    t = time.time()
    n = media.transcribir(ps, motor=motor)
    print(f"[profundo] transcribir {len(ps)} reels de {len(cuentas)} cuentas · {n} nuevos · {int(time.time()-t)}s")
    return n


def leer_carruseles(cuentas: list[str], dias: int | None, hilos: int = 6) -> int:
    ps = [p for p in piezas(cuentas, dias) if p.get("tipo_media") == "carrusel"]
    t = time.time()
    n = carruseles.correr(ps, hilos=hilos)
    print(f"[profundo] carruseles {len(ps)} · {n} leídos · {int(time.time()-t)}s")
    return n


def analizar_todo(cuentas: list[str], dias: int | None, hilos: int = 5) -> int:
    ps = piezas(cuentas, dias)
    rehacer = [p for p in ps if not p.get("analisis")
               or not (p.get("analisis") or {}).get("tipo_angulo")
               or ((p.get("transcript") or p.get("slides_texto")) and not (p.get("analisis") or {}).get("con_medios"))]
    t = time.time()
    analizar.piezas(rehacer, forzar=True, hilos=hilos)
    print(f"[profundo] análisis {len(rehacer)} de {len(ps)} piezas · {int(time.time()-t)}s")
    return len(rehacer)


def cuentas_build(cuentas: list[str], dias: int = 30) -> None:
    for h in cuentas:
        cuenta.build(h, dias)
