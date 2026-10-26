"""Cliente mínimo de la API REST de Apify (sin SDK). Token por header Bearer."""
from __future__ import annotations
import time, json, datetime as dt
import requests
from . import config

API = "https://api.apify.com/v2"


class ApifyError(RuntimeError):
    pass


def _headers() -> dict:
    if not config.APIFY_TOKEN:
        raise ApifyError("Falta APIFY_TOKEN en .env (console.apify.com → Settings → Integrations → API tokens)")
    return {"Authorization": f"Bearer {config.APIFY_TOKEN}", "Content-Type": "application/json"}


def correr(actor: str, entrada: dict, timeout_s: int = 900, tag: str = "") -> list[dict]:
    """Arranca un run, espera a que termine y devuelve los items del dataset.
    Guarda el dataset crudo en data/raw/<fecha>_<actor>_<tag>.json (trazabilidad + costo)."""
    r = requests.post(f"{API}/acts/{actor}/runs", headers=_headers(), json=entrada,
                      params={"waitForFinish": 60}, timeout=90)
    if r.status_code >= 300:
        raise ApifyError(f"start {actor}: {r.status_code} {r.text[:300]}")
    run = r.json()["data"]
    run_id, ds = run["id"], run["defaultDatasetId"]
    t0 = time.time()
    status = run.get("status")
    while status in ("READY", "RUNNING"):
        if time.time() - t0 > timeout_s:
            raise ApifyError(f"run {run_id} superó {timeout_s}s (status {status})")
        time.sleep(8)
        status = requests.get(f"{API}/actor-runs/{run_id}", headers=_headers(), timeout=60).json()["data"]["status"]
    if status != "SUCCEEDED":
        raise ApifyError(f"run {run_id} terminó {status}")
    items = dataset(ds)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    (config.RAW / f"{stamp}_{actor.replace('~', '_')}_{tag or 'run'}.json").write_text(
        json.dumps({"run_id": run_id, "dataset": ds, "entrada": entrada, "n": len(items), "items": items},
                   ensure_ascii=False))
    print(f"[apify] {actor} run={run_id} items={len(items)} ({int(time.time()-t0)}s)")
    return items


def dataset(ds_id: str) -> list[dict]:
    out, offset, limit = [], 0, 1000
    while True:
        r = requests.get(f"{API}/datasets/{ds_id}/items", headers=_headers(),
                         params={"clean": "true", "format": "json", "limit": limit, "offset": offset}, timeout=120)
        if r.status_code >= 300:
            raise ApifyError(f"dataset {ds_id}: {r.status_code} {r.text[:200]}")
        chunk = r.json()
        out.extend(chunk)
        if len(chunk) < limit:
            return out
        offset += limit


def ultimo_run(actor: str) -> dict | None:
    r = requests.get(f"{API}/acts/{actor}/runs", headers=_headers(), params={"limit": 1, "desc": 1}, timeout=60)
    items = r.json().get("data", {}).get("items", [])
    return items[0] if items else None
