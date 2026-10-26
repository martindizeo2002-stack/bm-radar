"""Medios de las piezas: videos de reels (→ transcript con Groq whisper-large-v3-turbo o mlx-whisper local) y slides de carruseles (→ site/slides/<id>/NN.jpg).
Las URLs de Apify son firmadas y vencen en horas: bajar justo después del scrape."""
from __future__ import annotations
import subprocess, shutil, time
from concurrent.futures import ThreadPoolExecutor
import requests
from . import config, ingest_ig

VIDEOS = config.DATA / "media"
SLIDES = config.ROOT / "site" / "slides"
VIDEOS.mkdir(parents=True, exist_ok=True)
SLIDES.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"}
WHISPER = "mlx-community/whisper-large-v3-turbo"
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3-turbo"
TMP = config.DATA / "tmp"
IDIOMAS = {"spanish": "es", "english": "en", "portuguese": "pt", "italian": "it", "french": "fr"}


def _bajar(url: str, dest, timeout=120) -> bool:
    try:
        with requests.get(url, headers=UA, timeout=timeout, stream=True) as r:
            if r.status_code != 200:
                return False
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
        return dest.stat().st_size > 0
    except Exception:
        return False


def bajar_videos(piezas: list[dict], hilos: int = 6) -> dict:
    tareas = [(p, VIDEOS / f"{p['id']}.mp4") for p in piezas if p.get("tipo_media") == "reel" and p.get("video_url")]
    tareas = [(p, d) for p, d in tareas if not d.exists()]
    with ThreadPoolExecutor(hilos) as ex:
        ok = list(ex.map(lambda t: _bajar(t[0]["video_url"], t[1]), tareas))
    print(f"[media] videos bajados {sum(ok)}/{len(tareas)} (fallidos {len(ok)-sum(ok)})")
    # audio suelto: algunos videos de IG vienen DASH solo-video (sin pista de audio)
    aud = [(p, VIDEOS / f"{p['id']}.audio.mp4") for p in piezas if p.get("tipo_media") == "reel" and p.get("audio_url")]
    aud = [(p, d) for p, d in aud if not d.exists() and not _tiene_audio(VIDEOS / f"{p['id']}.mp4")]
    with ThreadPoolExecutor(hilos) as ex:
        oka = list(ex.map(lambda t: _bajar(t[0]["audio_url"], t[1]), aud))
    if aud:
        print(f"[media] audios sueltos bajados {sum(oka)}/{len(aud)}")
    return {t[0]["id"]: o for t, o in zip(tareas, ok)}


def bajar_audios(piezas: list[dict], hilos: int = 8) -> int:
    """Para transcribir alcanza el audio (~10x más liviano que el video). Si la pieza no trae audio_url, baja el video."""
    aud, vid = [], []
    for p in piezas:
        if p.get("tipo_media") != "reel" or p.get("transcript") or p.get("sin_habla"):
            continue
        a, v = VIDEOS / f"{p['id']}.audio.mp4", VIDEOS / f"{p['id']}.mp4"
        if a.exists() or _tiene_audio(v):
            continue
        if p.get("audio_url"):
            aud.append((p["audio_url"], a))
        elif p.get("video_url") and not v.exists():
            vid.append((p["video_url"], v))
    with ThreadPoolExecutor(hilos) as ex:
        ok = list(ex.map(lambda t: _bajar(t[0], t[1]), aud + vid))
    print(f"[media] audios {sum(ok[:len(aud)])}/{len(aud)} · videos sin audio_url {sum(ok[len(aud):])}/{len(vid)}")
    return sum(ok)


def _tiene_audio(f) -> bool:
    if not f.exists():
        return False
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    return "audio" in r.stdout


def transcribir(piezas: list[dict], forzar: bool = False, motor: str | None = None) -> int:
    """Transcribe los reels con medio bajado. motor: groq (default si hay GROQ_API_KEY) o local (mlx-whisper)."""
    motor = motor or config.TRANSCRIPCION
    cambios, n = {}, 0
    for p in piezas:
        v = VIDEOS / f"{p['id']}.mp4"
        a = VIDEOS / f"{p['id']}.audio.mp4"
        if a.exists() and not _tiene_audio(v):
            v = a
        if not v.exists() or ((p.get("transcript") or p.get("sin_habla")) and not forzar):
            continue
        try:
            texto, idioma = _groq(v) if motor == "groq" else _mlx(v)
            if texto is None or len(texto.split()) < 6:
                # sin pista de audio o solo música: regla de creator-lab (< 6 palabras no es guion). Se marca para no reintentar.
                cambios[p["id"]] = {"transcript": "", "sin_habla": True, "transcript_motor": motor}
                p.update(cambios[p["id"]])
                continue
            cambios[p["id"]] = {"transcript": texto, "idioma": idioma, "transcript_motor": motor, "sin_habla": False}
            p.update(cambios[p["id"]])
            n += 1
            if n % 10 == 0:
                print(f"[whisper:{motor}] {n} transcriptos…")
        except Exception as e:
            print(f"[whisper:{motor}] {p['id']} error {e}")
    if cambios:
        ingest_ig.enriquecer(cambios)
    print(f"[whisper:{motor}] {n} transcriptos nuevos")
    return n


def _mlx(v) -> tuple[str, str | None]:
    import mlx_whisper
    r = mlx_whisper.transcribe(str(v), path_or_hf_repo=WHISPER, language=None, verbose=None)
    texto = " ".join(s["text"].strip() for s in r.get("segments", [])).strip() or r.get("text", "").strip()
    return texto, r.get("language")


_ultimo_groq = [0.0]


def _groq(v) -> tuple[str | None, str | None]:
    """ffmpeg → FLAC mono 16 kHz (sube ~10x menos que el mp4) → Groq. Sin pista de audio = (None, None)."""
    if not config.GROQ_API_KEY:
        raise RuntimeError("falta GROQ_API_KEY en .env")
    if not _tiene_audio(v):
        return None, None
    TMP.mkdir(exist_ok=True)
    flac = TMP / f"{v.stem}.flac"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-vn", "-ar", "16000", "-ac", "1", str(flac)],
                   check=True, capture_output=True, timeout=120)
    try:
        for intento in range(5):
            espera = 60 / max(config.GROQ_RPM, 1) - (time.time() - _ultimo_groq[0])
            if espera > 0:
                time.sleep(espera)
            _ultimo_groq[0] = time.time()
            with open(flac, "rb") as fh:
                r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"}, timeout=120,
                                  files={"file": (flac.name, fh, "audio/flac")},
                                  data={"model": GROQ_MODEL, "response_format": "verbose_json", "temperature": "0"})
            if r.status_code == 429 or r.status_code >= 500:
                pausa = float(r.headers.get("retry-after") or 10 * (intento + 1))
                print(f"[whisper:groq] HTTP {r.status_code}, reintento en {pausa:.0f}s")
                time.sleep(min(pausa, 120))
                continue
            if r.status_code != 200:
                raise RuntimeError(f"Groq HTTP {r.status_code}: {r.text[:200]}")
            j = r.json()
            idioma = (j.get("language") or "").lower()
            return (j.get("text") or "").strip(), IDIOMAS.get(idioma, idioma or None)
        raise RuntimeError("Groq: reintentos agotados")
    finally:
        flac.unlink(missing_ok=True)


def bajar_slides(piezas: list[dict], ancho: int = 720, hilos: int = 8) -> int:
    tareas = []
    for p in piezas:
        if p.get("tipo_media") != "carrusel" or not p.get("slides"):
            continue
        carpeta = SLIDES / p["id"]
        carpeta.mkdir(exist_ok=True)
        for i, url in enumerate(p["slides"], 1):
            d = carpeta / f"{i:02d}.jpg"
            if not d.exists():
                tareas.append((url, d))
    with ThreadPoolExecutor(hilos) as ex:
        ok = list(ex.map(lambda t: _bajar(t[0], t[1], 60), tareas))
    if shutil.which("sips"):
        for (_, d), o in zip(tareas, ok):
            if o:
                subprocess.run(["sips", "-Z", str(ancho), "-s", "format", "jpeg", "-s", "formatOptions", "72", str(d), "--out", str(d)], capture_output=True)
    cambios = {}
    for p in piezas:
        if p.get("tipo_media") == "carrusel":
            locs = sorted(f"slides/{p['id']}/{f.name}" for f in (SLIDES / p["id"]).glob("*.jpg")) if (SLIDES / p["id"]).exists() else []
            if locs:
                cambios[p["id"]] = {"slides_local": locs}
                p["slides_local"] = locs
    if cambios:
        ingest_ig.enriquecer(cambios)
    print(f"[media] slides bajadas {sum(ok)}/{len(tareas)}")
    return sum(ok)
