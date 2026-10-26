"""Aplica a todas.jsonl los resultados de un workflow de subagentes (análisis por pieza y lectura de carruseles),
leyendo el journal.jsonl del workflow. Se usa cuando la API de Anthropic no está disponible."""
from __future__ import annotations
import json, sys
from . import ingest_ig


def leer_journal(path: str) -> list[dict]:
    out = []
    for line in open(path):
        line = line.strip()
        if line:
            e = json.loads(line)
            if e.get("type") == "result" and e.get("result"):
                out.append(e["result"])
    return out


def aplicar(journal: str, modelo: str = "subagente-claude-code") -> dict:
    ids = {p["id"]: p for p in ingest_ig.todas()}
    cambios, n_a, n_c, fuera = {}, 0, 0, 0
    for r in leer_journal(journal):
        for a in r.get("piezas") or []:
            pid = a.get("id")
            if pid not in ids:
                fuera += 1
                continue
            p = ids[pid]
            an = {k: v for k, v in a.items() if k != "id"}
            an["modelo"] = modelo
            an["con_medios"] = bool(p.get("transcript") or p.get("slides_texto"))
            cambios.setdefault(pid, {})["analisis"] = an
            n_a += 1
        for c in r.get("carruseles") or []:
            pid = c.get("id")
            if pid not in ids:
                fuera += 1
                continue
            cambios.setdefault(pid, {}).update({"slides_texto": c["slides"], "lectura": {k: c.get(k, "") for k in ("diseno", "estructura", "cierre")}})
            n_c += 1
    if cambios:
        ingest_ig.enriquecer(cambios)
    res = {"analisis": n_a, "carruseles": n_c, "ids_desconocidos": fuera}
    print(f"[aplicar] {res}")
    return res


if __name__ == "__main__":
    aplicar(sys.argv[1])
