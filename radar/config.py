from __future__ import annotations
import os, json, datetime as dt
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
RAW = DATA / "raw"
PIEZAS = DATA / "piezas"
COMENTARIOS = DATA / "comentarios"
ANALISIS = DATA / "analisis"
RECREACIONES = DATA / "recreaciones"
SITE_DATA = ROOT / "site" / "data"
SEMILLAS = ROOT / "semillas.json"
for p in (RAW, PIEZAS, COMENTARIOS, ANALISIS, RECREACIONES, SITE_DATA):
    p.mkdir(parents=True, exist_ok=True)

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
HUB_URL = os.getenv("HUB_URL", "https://bm-hub-ventas.netlify.app/.netlify/functions/panel")
HUB_KEY = os.getenv("HUB_KEY", "")
MODEL = os.getenv("RADAR_MODEL", "claude-opus-5")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# motor de transcripción: groq (nube, whisper-large-v3-turbo, receta de creator-lab) o local (mlx-whisper en la Mac)
TRANSCRIPCION = os.getenv("RADAR_TRANSCRIPCION") or ("groq" if GROQ_API_KEY else "local")
GROQ_RPM = int(os.getenv("GROQ_REQUESTS_PER_MINUTE", "20"))
GUION_MODEL = os.getenv("RADAR_GUION_MODEL", "claude-sonnet-5")  # mismo modelo que etiquetó los reels de Nahue
TZ_OFFSET = -3  # ART

ACTORS = {
    "ig_posts": "apify~instagram-scraper",
    "ig_comments": "apify~instagram-comment-scraper",
    "tiktok": "clockworks~tiktok-scraper",
    "yt": "streamers~youtube-scraper",
    "ads": "curious_coder~facebook-ads-library-scraper",
}

# Workspace BM (para prompts de recreación). Si un archivo no existe, se saltea.
# El radar vive en ~/bm-radar (fuera de Desktop, para que launchd pueda leerlo); apps/radar-contenido es un symlink.
BM_ROOT = Path(os.getenv("BM_ROOT", "/Users/tincho/Desktop/brandmasters"))
REFS = ROOT / "refs"  # copia local de las referencias del workspace: launchd no puede leer ~/Desktop (TCC)
REFS.mkdir(exist_ok=True)


def _ref(rel: str) -> Path:
    """Devuelve la referencia del workspace si se puede leer (y refresca la copia local); si no, la copia local."""
    orig, copia = BM_ROOT / rel, REFS / Path(rel).name
    try:
        txt = orig.read_text()
        if not copia.exists() or copia.read_text() != txt:
            copia.write_text(txt)
        return orig
    except OSError:
        return copia


FUENTES_VOZ = [_ref("conocimiento/marketing/voz-nahue.md"), _ref("cerebro/reglas/copys.md"), _ref("cerebro/reglas/estilo-comunicacion.md")]
BANCO_ANGULOS = _ref("entregables-comunicacion/banco-angulos-bm-2026-09-22.md")


def ahora() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=TZ_OFFSET)))


def semana_iso(d: dt.datetime | None = None) -> str:
    d = d or ahora()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def cargar_semillas() -> dict:
    if not SEMILLAS.exists():
        return {"instagram": [], "tiktok": [], "youtube": [], "ads": []}
    return json.loads(SEMILLAS.read_text())


from contextlib import contextmanager


@contextmanager
def lock_piezas():
    """Lock de proceso sobre data/piezas/todas.jsonl: todo read-modify-write va adentro."""
    import fcntl
    f = open(DATA / ".piezas.lock", "w")
    fcntl.flock(f, fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def leer_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    # split("\n") y no splitlines(): los captions traen U+2028/U+2029 que splitlines() corta
    for line in path.read_text().split("\n"):
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def escribir_jsonl(path: Path, rows: list[dict]) -> None:
    """Escritura atómica (tmp + rename): un lector nunca ve el archivo a medio escribir."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    tmp.replace(path)
