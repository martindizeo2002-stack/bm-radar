"""Barrido de carruseles del Radar de Contenido BM. Corre bajo launchd cada 12 h (09:35 y 21:35 ART).

Vive fuera de Desktop por TCC (launchd no puede leer ~/Desktop). El radar lo lee por el symlink
apps/radar-contenido/data/barrido -> ~/bm-barrido/data y lo integra con `run.py barrido` (o en cada `run.py build`).

Qué hace:
1. Apify instagram-scraper sobre las semillas de cuentas.json (lo escribe el radar): posts de los últimos 3 días.
2. Guarda el crudo mínimo en data/posts.jsonl (por shortCode; gana lo más nuevo: métricas actualizadas).
3. Carruseles: baja cada slide a data/slides/<id>/NN.jpg y la miniatura a data/thumbs/<id>.jpg (las URLs vencen).
4. Lee cada carrusel nuevo con Claude (visión): texto literal por slide, visual, diseño, estructura y cierre.
   Resultado en data/lecturas.jsonl. Si la API falla (sin crédito), queda pendiente para la próxima corrida.
Uso manual: .venv/bin/python3 barrido.py [--dias 3] [--sin-lectura]
"""
from __future__ import annotations
import base64, json, socket, subprocess, sys, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
import anthropic

BASE = Path(__file__).resolve().parent
DATA, LOG = BASE / "data", BASE / "log" / "barrido.log"
SLIDES, THUMBS = DATA / "slides", DATA / "thumbs"
POSTS, LECT, ESTADO = DATA / "posts.jsonl", DATA / "lecturas.jsonl", DATA / "estado.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"}
CAMPOS = ["shortCode", "type", "productType", "url", "ownerUsername", "inputUrl", "caption", "hashtags", "likesCount", "commentsCount",
          "videoPlayCount", "videoViewCount", "videoUrl", "audioUrl", "displayUrl", "images", "videoDuration", "timestamp", "isPinned"]


def env() -> dict:
    out = {}
    for line in (BASE / ".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


ENV = env()


def log(m: str) -> None:
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M} {m}\n")
    print(m, flush=True)


def leer_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().split("\n") if l.strip()] if p.exists() else []


def escribir_jsonl(p: Path, rows: list[dict]) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    tmp.replace(p)


def esperar_red(max_min: int = 20) -> bool:
    """launchd dispara el job cuando la Mac despierta y la red todavía no levantó: esperar el DNS antes de arrancar."""
    t0 = time.time()
    while time.time() - t0 < max_min * 60:
        try:
            socket.gethostbyname("api.apify.com")
            return True
        except OSError:
            time.sleep(20)
    return False


def _pedir(metodo: str, url: str, intentos: int = 5, espera: int = 30, **kw) -> requests.Response:
    """Reintenta solo errores de red (DNS, conexión cortada, timeout). Un error HTTP se devuelve tal cual."""
    for i in range(intentos):
        try:
            return requests.request(metodo, url, **kw)
        except (requests.ConnectionError, requests.Timeout):
            if i == intentos - 1:
                raise
            time.sleep(espera)


def apify(cuentas: list[str], dias: int) -> tuple[list[dict], dict]:
    H = {"Authorization": f"Bearer {ENV['APIFY_TOKEN']}"}
    entrada = {"directUrls": [f"https://www.instagram.com/{c}/" for c in cuentas], "resultsType": "posts", "resultsLimit": 25,
               "onlyPostsNewerThan": f"{dias} days", "addParentData": False}
    # el POST se reintenta solo si la conexión no llegó a salir: sin waitForFinish, así un corte no deja una corrida paga huérfana
    r = _pedir("POST", "https://api.apify.com/v2/acts/apify~instagram-scraper/runs", intentos=3, espera=60, headers=H, json=entrada, timeout=60)
    r.raise_for_status()
    run = r.json()["data"]
    t0 = time.time()
    while run["status"] in ("READY", "RUNNING"):
        if time.time() - t0 > 1800:
            raise RuntimeError(f"run {run['id']} superó 30 min")
        time.sleep(10)
        run = _pedir("GET", f"https://api.apify.com/v2/actor-runs/{run['id']}", headers=H, timeout=60).json()["data"]
    if run["status"] != "SUCCEEDED":
        raise RuntimeError(f"run {run['id']} terminó {run['status']}")
    items = _pedir("GET", f"https://api.apify.com/v2/datasets/{run['defaultDatasetId']}/items", headers=H, params={"clean": "true", "limit": 5000}, timeout=120).json()
    return items, run


def bajar(url: str, dest: Path, ancho: int | None = None) -> bool:
    try:
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code != 200 or not r.content:
            return False
        dest.write_bytes(r.content)
        if ancho:
            subprocess.run(["sips", "-Z", str(ancho), "-s", "format", "jpeg", "-s", "formatOptions", "72", str(dest), "--out", str(dest)], capture_output=True)
        return True
    except Exception:
        return False


SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "slides": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                   "properties": {"n": {"type": "integer"}, "texto": {"type": "string"}, "visual": {"type": "string"}}, "required": ["n", "texto", "visual"]}},
        "diseno": {"type": "string"}, "estructura": {"type": "string"}, "cierre": {"type": "string"},
    },
    "required": ["slides", "diseno", "estructura", "cierre"],
}
SYSTEM = "Leés carruseles de Instagram. Transcribí el texto literal de cada slide en orden (respetá mayúsculas y números, sin inventar), describí qué se ve en una línea y resumí diseño, estructura y cierre. Español."


def leer_carrusel(cli: anthropic.Anthropic, pid: str, caption: str) -> dict:
    """Si la respuesta llega cortada o con JSON inválido, reintenta una vez con el doble de margen."""
    try:
        return _leer_carrusel(cli, pid, caption, 8000)
    except json.JSONDecodeError:
        return _leer_carrusel(cli, pid, caption, 16000)


def _leer_carrusel(cli: anthropic.Anthropic, pid: str, caption: str, max_tokens: int) -> dict:
    bloques = []
    for i, f in enumerate(sorted((SLIDES / pid).glob("*.jpg"))[:20], 1):
        bloques += [{"type": "text", "text": f"Slide {i}:"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.standard_b64encode(f.read_bytes()).decode()}}]
    bloques.append({"type": "text", "text": f"Caption: {caption[:600]}\nLeé el carrusel completo."})
    r = cli.messages.create(model=ENV.get("RADAR_MODEL", "claude-opus-5"), max_tokens=max_tokens, system=SYSTEM,
                            messages=[{"role": "user", "content": bloques}],
                            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}})
    if r.stop_reason == "refusal":
        raise RuntimeError("refusal")
    if r.stop_reason == "max_tokens":
        raise json.JSONDecodeError("respuesta cortada por max_tokens", "", 0)
    return json.loads("".join(b.text for b in r.content if b.type == "text"))


def main() -> None:
    dias = int(sys.argv[sys.argv.index("--dias") + 1]) if "--dias" in sys.argv else 3
    cuentas = json.loads((BASE / "cuentas.json").read_text())
    SLIDES.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)
    if not esperar_red():
        log("[barrido] sin red después de 20 min: no se corrió")
        return
    try:
        items, run = apify(cuentas, dias)
    except Exception as e:
        log(f"[barrido] error Apify: {e}")
        return
    prev = {p["shortCode"]: p for p in leer_jsonl(POSTS)}
    nuevos = 0
    for it in items:
        sc = it.get("shortCode")
        if not sc:
            continue
        d = {k: it.get(k) for k in CAMPOS if it.get(k) is not None}
        if not d.get("images") and it.get("childPosts"):
            d["images"] = [c.get("displayUrl") for c in it["childPosts"] if c.get("displayUrl")]
        d["barrido_at"] = dt.datetime.now().isoformat(timespec="seconds")
        nuevos += sc not in prev
        prev[sc] = d
    escribir_jsonl(POSTS, list(prev.values()))
    # medios: slides de carruseles + miniatura de todo lo nuevo en esta corrida
    tareas = []
    for it in items:
        sc = it.get("shortCode")
        if not sc:
            continue
        pid = f"ig_{sc}"
        if it.get("displayUrl") and not (THUMBS / f"{pid}.jpg").exists():
            tareas.append((it["displayUrl"], THUMBS / f"{pid}.jpg", 480))
        if it.get("type") == "Sidecar":
            urls = [u for u in (it.get("images") or []) if u] or [c.get("displayUrl") for c in (it.get("childPosts") or []) if c.get("displayUrl")]
            (SLIDES / pid).mkdir(exist_ok=True)
            for i, u in enumerate(urls, 1):
                dst = SLIDES / pid / f"{i:02d}.jpg"
                if not dst.exists():
                    tareas.append((u, dst, 720))
    with ThreadPoolExecutor(8) as ex:
        ok = list(ex.map(lambda t: bajar(*t), tareas))
    # lectura con Claude de los carruseles que todavía no tienen
    leidos = {r["id"] for r in leer_jsonl(LECT)}
    pend = [(f"ig_{p['shortCode']}", p.get("caption") or "") for p in prev.values()
            if p.get("type") == "Sidecar" and f"ig_{p['shortCode']}" not in leidos and any((SLIDES / f"ig_{p['shortCode']}").glob("*.jpg"))]
    n_lect, err = 0, None
    if pend and "--sin-lectura" not in sys.argv:
        cli = anthropic.Anthropic(api_key=ENV["ANTHROPIC_API_KEY"], max_retries=3)
        with open(LECT, "a") as f:
            for pid, cap in pend:
                try:
                    out = leer_carrusel(cli, pid, cap)
                    f.write(json.dumps({"id": pid, "slides_texto": out["slides"], "lectura": {k: out[k] for k in ("diseno", "estructura", "cierre")},
                                        "leido_at": dt.datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")
                    f.flush()
                    n_lect += 1
                except anthropic.APIStatusError as e:
                    err = f"{e.status_code} {str(e)[:120]}"
                    break  # sin crédito o caída: queda pendiente para la próxima corrida
                except Exception as e:
                    err = str(e)[:120]
    car = sum(1 for it in items if it.get("type") == "Sidecar")
    est = {"ts": time.time(), "fecha": dt.datetime.now().isoformat(timespec="seconds"), "run": run["id"], "usd": run.get("usageTotalUsd"),
           "items": len(items), "nuevos": nuevos, "carruseles": car, "medios_bajados": sum(ok), "medios_fallidos": len(ok) - sum(ok),
           "leidos": n_lect, "pendientes_lectura": len(pend) - n_lect, "error_lectura": err}
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1))
    log(f"[barrido] {len(items)} posts de {len({it.get('ownerUsername') for it in items})} cuentas · {nuevos} nuevos · {car} carruseles · "
        f"medios {sum(ok)}/{len(ok)} · leídos {n_lect}/{len(pend)}{' · error ' + err if err else ''} · USD {run.get('usageTotalUsd')}")


if __name__ == "__main__":
    main()
