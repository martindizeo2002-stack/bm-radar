#!/usr/bin/python3
"""Captura de historias de IG antes de que venzan (24 h). Corre bajo launchd 4 veces por día (03/09/15/21 ART).

- Nahue (@nahue.urso): Graph API de la cuenta propia, en CADA corrida. Texto, alcance, respuestas, navegación
  (avances / retrocesos / salidas / siguiente), shares, follows, visitas al perfil. Actualiza las métricas en cada
  pasada mientras la historia vive: queda la última lectura antes de vencer.
- Creadores marcados (cuentas.json): Apify datavoyantlab/advanced-instagram-stories-scraper, sin login, cada 12 h
  (si pasaron 11 h desde la última: dispara a las 09 y a las 21). ~$0,32/día con 21 cuentas. Pedido Tincho 29-sep-2026.
- Medios: se guarda solo un frame jpg (360 px). Video → audio → Groq whisper-large-v3-turbo → transcript, y se borra.

Vive fuera de ~/Desktop (launchd no puede leer Desktop por TCC). Solo stdlib + ffmpeg/sips del sistema.
Secrets en .env (chmod 600). El radar lo lee por symlink: apps/radar-contenido/data/historias → ~/bm-historias/data.
"""
from __future__ import annotations
import json, os, subprocess, sys, time, uuid, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
TMP = BASE / "tmp"
ART = timezone(timedelta(hours=-3))
ACTOR = "datavoyantlab~advanced-instagram-stories-scraper"
FFMPEG = next((p for p in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg") if os.path.exists(p)), "ffmpeg")

env = {}
for line in (BASE / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()


def log(m: str) -> None:
    print(f"{datetime.now(ART):%Y-%m-%d %H:%M} {m}", flush=True)


def http_json(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 60, retries: int = 3):
    for i in range(retries):
        try:
            # User-Agent propio: Cloudflare (Groq) bloquea el de Python-urllib con 403 "error code: 1010"
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "bm-historias/1.0", **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            if e.code in (429, 500, 502, 503) or "80002" in body:
                time.sleep(20 * (i + 1)); continue
            return {"error": body, "code": e.code}
        except Exception as e:
            time.sleep(10 * (i + 1))
            if i == retries - 1:
                return {"error": str(e)}
    return {"error": "reintentos agotados"}


def bajar(url: str, dest: Path, timeout: int = 90) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
            while chunk := r.read(1 << 16):
                f.write(chunk)
        return dest.stat().st_size > 0
    except Exception:
        dest.unlink(missing_ok=True)
        return False


def leer(path: Path) -> dict:
    out = {}
    if path.exists():
        for l in path.read_text().split("\n"):
            if l.strip():
                r = json.loads(l)
                out[r["id"]] = r
    return out


def escribir(path: Path, rows: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in sorted(rows.values(), key=lambda x: x.get("fecha", ""))) + "\n")
    tmp.replace(path)


# ---------- medios: frame + transcript ----------

def frame(src: Path, dest: Path, es_video: bool) -> bool:
    if es_video:
        for ss in ("1", "0"):  # historias de menos de 1 s no tienen cuadro en el segundo 1
            r = subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", ss, "-i", str(src), "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "5", str(dest)],
                               capture_output=True, timeout=60)
            if r.returncode == 0 and dest.exists():
                return True
        return False
    r = subprocess.run(["/usr/bin/sips", "-Z", "640", "-s", "format", "jpeg", "-s", "formatOptions", "70", str(src), "--out", str(dest)],
                       capture_output=True, timeout=60)
    return r.returncode == 0 and dest.exists()


def transcribir(video: Path) -> str | None:
    key = env.get("GROQ_API_KEY")
    if not key:
        return None
    flac = TMP / f"{video.stem}.flac"
    r = subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(video), "-vn", "-ar", "16000", "-ac", "1", str(flac)], capture_output=True, timeout=90)
    if r.returncode != 0 or not flac.exists() or flac.stat().st_size < 2000:
        flac.unlink(missing_ok=True)
        return None
    b = uuid.uuid4().hex
    partes = []
    for k, v in (("model", "whisper-large-v3-turbo"), ("temperature", "0"), ("response_format", "json")):
        partes.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    partes.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{flac.name}"\r\nContent-Type: audio/flac\r\n\r\n'.encode()
                  + flac.read_bytes() + f"\r\n--{b}--\r\n".encode())
    res = http_json("https://api.groq.com/openai/v1/audio/transcriptions", data=b"".join(partes),
                    headers={"Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={b}"}, timeout=120)
    flac.unlink(missing_ok=True)
    txt = (res.get("text") or "").strip() if isinstance(res, dict) else ""
    return txt if len(txt.split()) >= 4 else ""


def medios(h: dict, url_media: str, es_video: bool, carpeta: Path, url_thumb: str | None = None) -> None:
    """Completa h['frame'] y h['transcript'] una sola vez (las URLs vencen).
    url_thumb: miniatura de respaldo. La Graph API no da media_url en videos con música con derechos y a veces el
    video no baja: sin esto la historia quedaba sin imagen en el radar."""
    dest = carpeta / f"{h['id']}.jpg"
    if dest.exists() and ("transcript" in h or not es_video):
        h["frame"] = f"{carpeta.name}/{dest.name}"
        return
    src = TMP / (h["id"] + (".mp4" if es_video else ".src"))
    if url_media and bajar(url_media, src):
        try:
            if frame(src, dest, es_video):
                h["frame"] = f"{carpeta.name}/{dest.name}"
            if es_video and "transcript" not in h:
                t = transcribir(src)
                if t is not None:
                    h["transcript"] = t
        finally:
            src.unlink(missing_ok=True)
    if not dest.exists() and url_thumb:
        img = TMP / (h["id"] + ".thumb")
        if bajar(url_thumb, img):
            try:
                if frame(img, dest, False):
                    h["frame"] = f"{carpeta.name}/{dest.name}"
            finally:
                img.unlink(missing_ok=True)


# ---------- Nahue: Graph API ----------

def nahue() -> int:
    V, IG, TOKEN = env.get("META_API_VERSION", "v23.0"), env["META_IG_USER_ID"], env["META_ACCESS_TOKEN"]
    g = lambda path, **p: http_json(f"https://graph.facebook.com/{V}/{path}?" + urllib.parse.urlencode({**p, "access_token": TOKEN}))
    r = g(f"{IG}/stories", fields="id,media_type,media_url,thumbnail_url,permalink,timestamp,caption")
    if "error" in r:
        log(f"[nahue] error {str(r['error'])[:200]}")
        return 0
    path = DATA / "nahue" / "historias.jsonl"
    rows = leer(path)
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for s in r.get("data", []):
        h = rows.get(s["id"], {"id": s["id"], "cuenta": "nahue.urso", "primera_vista": ahora})
        h.update(fecha=s.get("timestamp"), tipo=(s.get("media_type") or "").lower(), caption=s.get("caption") or "",
                 permalink=s.get("permalink"), ultima_vista=ahora)
        ins = g(f"{s['id']}/insights", metric="reach,replies,shares,total_interactions,follows,profile_visits,views")
        m = {d["name"]: (d.get("values") or [{}])[0].get("value") for d in ins.get("data", [])} if "error" not in ins else {}
        nav = g(f"{s['id']}/insights", metric="navigation", breakdown="story_navigation_action_type")
        for d in nav.get("data", []):
            m["navigation"] = (d.get("total_value") or {}).get("value")
            for b in (d.get("total_value") or {}).get("breakdowns", []):
                for x in b.get("results", []):
                    m[x["dimension_values"][0]] = x["value"]
        if m:
            h["metricas"] = m
            h["metricas_at"] = ahora
        es_v = s.get("media_type") == "VIDEO" and bool(s.get("media_url"))  # sin media_url solo queda la miniatura
        medios(h, s.get("media_url") or s.get("thumbnail_url"), es_v, DATA / "nahue" / "media", url_thumb=s.get("thumbnail_url"))
        rows[s["id"]] = h
    escribir(path, rows)
    log(f"[nahue] {len(r.get('data', []))} activas · {len(rows)} en total")
    return len(r.get("data", []))


# ---------- creadores marcados: Apify ----------

def _sticker(x: dict) -> dict:
    st = {}
    for k in ("story_link_stickers", "story_cta"):
        for s in x.get(k) or []:
            u = ((s.get("story_link") or {}).get("url")) or (s.get("links") or [{}])[0].get("webUri") if isinstance(s, dict) else None
            if u:
                st.setdefault("links", []).append(u)
    for s in x.get("story_polls") or []:
        st.setdefault("encuestas", []).append(((s.get("poll_sticker") or {}).get("question")) or "")
    for s in x.get("story_questions") or []:
        st.setdefault("preguntas", []).append(((s.get("question_sticker") or {}).get("question")) or "")
    for s in x.get("reel_mentions") or []:
        st.setdefault("menciones", []).append(((s.get("user") or {}).get("username")) or "")
    if x.get("story_music_stickers"):
        st["musica"] = True
    if x.get("story_countdowns"):
        st["cuenta_regresiva"] = True
    return st


def competencia(forzar: bool = False) -> int:
    est_path = DATA / "estado.json"
    est = json.loads(est_path.read_text()) if est_path.exists() else {}
    if not forzar and time.time() - est.get("competencia_ts", 0) < 11 * 3600:  # cada 12 h (09 y 21 ART), pedido Tincho 29-sep
        return 0
    cuentas = json.loads((BASE / "cuentas.json").read_text())
    if not cuentas:
        return 0
    H = {"Authorization": f"Bearer {env['APIFY_TOKEN']}", "Content-Type": "application/json"}
    run = http_json(f"https://api.apify.com/v2/acts/{ACTOR}/runs", data=json.dumps({"usernames": cuentas}).encode(), headers=H)
    rid = (run.get("data") or {}).get("id")
    if not rid:
        log(f"[competencia] no arrancó: {str(run)[:200]}")
        return 0
    for _ in range(60):
        time.sleep(10)
        st = (http_json(f"https://api.apify.com/v2/actor-runs/{rid}", headers=H).get("data") or {})
        if st.get("status") in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
    if st.get("status") != "SUCCEEDED":
        log(f"[competencia] run {rid} terminó {st.get('status')}")
        return 0
    items = http_json(f"https://api.apify.com/v2/datasets/{st['defaultDatasetId']}/items?clean=true&format=json", headers=H)
    items = items if isinstance(items, list) else []
    path = DATA / "competencia" / "historias.jsonl"
    rows = leer(path)
    nuevas = 0
    for x in items:
        hid = str(x.get("id") or x.get("pk"))
        cu = (x.get("user") or {}).get("username") or x.get("username") or ""
        h = rows.get(hid) or {"id": hid, "cuenta": cu}
        es_video = x.get("media_type") == 2
        h.update(fecha=datetime.fromtimestamp(x.get("taken_at") or 0, timezone.utc).isoformat(timespec="seconds"),
                 vence=datetime.fromtimestamp(x.get("expiring_at") or 0, timezone.utc).isoformat(timespec="seconds"),
                 tipo="video" if es_video else "imagen", duracion=x.get("video_duration"), code=x.get("code"),
                 caption=((x.get("caption") or {}).get("text") if isinstance(x.get("caption"), dict) else x.get("caption")) or "",
                 stickers=_sticker(x), run=rid)
        if hid not in rows:
            nuevas += 1
        url = ((x.get("video_versions") or [{}])[0].get("url")) if es_video else (((x.get("image_versions2") or {}).get("candidates") or [{}])[0].get("url"))
        thumb = ((x.get("image_versions2") or {}).get("candidates") or [{}])[0].get("url")
        medios(h, url, es_video, DATA / "competencia" / "media", url_thumb=thumb)
        rows[hid] = h
    escribir(path, rows)
    est.update(competencia_ts=time.time(), competencia_run=rid, competencia_usd=st.get("usageTotalUsd"))
    est_path.write_text(json.dumps(est))
    log(f"[competencia] {len(items)} historias de {len({x.get('user', {}).get('username') for x in items})} cuentas · {nuevas} nuevas · run {rid} · USD {st.get('usageTotalUsd')}")
    return nuevas


def esperar_red(max_min: int = 20) -> bool:
    """launchd dispara el job cuando la Mac despierta y la red todavía no levantó: esperar el DNS antes de arrancar."""
    import socket
    t0 = time.time()
    while time.time() - t0 < max_min * 60:
        try:
            socket.gethostbyname("api.apify.com")
            return True
        except OSError:
            time.sleep(20)
    return False


def main():
    for d in (DATA / "nahue" / "media", DATA / "competencia" / "media", TMP):
        d.mkdir(parents=True, exist_ok=True)
    if not esperar_red():
        log("[red] sin red después de 20 min: no se corrió")
        return
    forzar = "--forzar" in sys.argv
    try:
        nahue()
    except Exception as e:
        log(f"[nahue] falló: {e!r}")
    if "--solo-nahue" not in sys.argv:
        try:
            competencia(forzar)
        except Exception as e:
            log(f"[competencia] falló: {e!r}")


if __name__ == "__main__":
    main()
