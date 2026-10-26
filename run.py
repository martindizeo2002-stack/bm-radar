#!/usr/bin/env python3
"""CLI del Radar de Contenido BM.

  run.py demo                         datos de demo → sitio (sin token)
  run.py historico [--limite 100]     últimas N piezas por cuenta semilla (baseline) + perfiles
  run.py semanal [--dias 7]           piezas de la última semana → scoring → sitio
  run.py perfiles                     seguidores por cuenta
  run.py comentarios [--top 100] [--por 50]
  run.py analizar [--top 50]          clasificación Claude del top de la semana
  run.py minar                        minería de comentarios de la semana
  run.py recrear <id|url> [--kanban]  guion reel + carrusel + historias + hooks
  run.py lote [--top 10] [--kanban]   recrea el top N recreable
  run.py pedido <cuentas,coma> [--dias 30] [--limite 50]   a pedido, sin tocar semillas
  run.py thumbs                       baja miniaturas del top de la semana a site/thumbs/
  run.py cuenta <handle> [--dias 30] [--limite 300] [--sin-scrape]
  run.py guion [--cuenta X] [--forzar]  anatomía del guion (schema creator-lab, a ciegas) + benchmark vs Nahue
                                      vista profunda: videos → transcript (whisper local), carruseles leídos slide por slide, análisis, site/data/cuentas/<handle>.json
  run.py build                        miniaturas + regenera site/data/latest.json
  run.py deploy                       netlify deploy --prod (crea el sitio la 1ª vez)
  run.py auto                         corrida desatendida de launchd: barrido → transcribe → analiza → vistas → build → deploy
  run.py lunes                        semanal + perfiles + comentarios + analizar + minar + lote + build + deploy
"""
from __future__ import annotations
import sys, os, json, argparse, subprocess, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from radar import config, ingest_ig, score, comentarios, analizar, recrear, build_site, hub, fixture, thumbs, media, carruseles, cuenta, guion

NETLIFY = os.path.expanduser("~/.npm-global/bin/netlify")


def _perfiles() -> dict:
    p = config.DATA / "perfiles.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _semana_puntuada() -> list[dict]:
    todas = ingest_ig.todas()
    sem = config.semana_iso()
    base = score.baseline([p for p in todas if p.get("semana") != sem] or todas)
    return score.puntuar(score.semana(todas, sem), base, _perfiles())


def cmd_demo(a):
    piezas = fixture.generar(60)
    perfiles = fixture.perfiles_demo()
    (config.DATA / "perfiles.json").write_text(json.dumps(perfiles, ensure_ascii=False, indent=1))
    ingest_ig.guardar(piezas)
    build_site.build(demo=True)


def cmd_historico(a):
    ingest_ig.correr("historico", limite=a.limite)
    ingest_ig.perfiles()
    build_site.build()


def cmd_semanal(a):
    ingest_ig.correr("semanal", dias=a.dias)
    build_site.build()


def cmd_perfiles(a):
    ingest_ig.perfiles(); build_site.build()


def cmd_comentarios(a):
    sem = [p for p in _semana_puntuada() if p["cuenta"] not in _propias()]
    top = score.top(sem, a.top, "comentarios")
    comentarios.correr(top, por_pieza=a.por)


def _propias() -> set:
    return {c["handle"].lower() for c in config.cargar_semillas().get("instagram", []) if "propia" in c.get("tags", [])}


def _medios_top(ps: list[dict]) -> None:
    """Reels del top: bajar → transcribir (Groq si hay key) → anatomía del guion. Borra los mp4 ya transcriptos (solo sirven para whisper)."""
    reels = [p for p in ps if p.get("tipo_media") == "reel" and not p.get("transcript") and not p.get("sin_habla")]
    if reels:
        media.bajar_videos(reels)
        media.transcribir(reels)
        for p in reels:
            if p.get("transcript") or p.get("sin_habla"):
                for f in (media.VIDEOS / f"{p['id']}.mp4", media.VIDEOS / f"{p['id']}.audio.mp4"):
                    f.unlink(missing_ok=True)
    guion.etiquetar(ps)
    guion.roles_competencia(ps)
    guion.objetivos_competencia(ps)


def cmd_analizar(a):
    sem = [p for p in _semana_puntuada() if p["cuenta"] not in _propias() and (p.get("cuenta_fuente") or p["cuenta"]) not in _propias()]
    top = score.top(sem, a.top, "comentarios")
    _medios_top(top)
    # analizar las nuevas + re-analizar las que se analizaron solo con caption y ahora tienen transcript
    rehacer = [p for p in top if not p.get("analisis") or (p.get("transcript") and not (p.get("analisis") or {}).get("con_medios"))]
    analizar.piezas(rehacer, forzar=True)
    build_site.build()


def cmd_minar(a):
    coms = config.leer_jsonl(config.COMENTARIOS / f"{config.semana_iso()}.jsonl")
    analizar.comentarios(coms)
    build_site.build()


def _buscar(ref: str) -> dict:
    todas = ingest_ig.todas()
    for p in todas:
        if p["id"] == ref or p["url"].rstrip("/") == ref.rstrip("/") or ref in p["url"]:
            return p
    raise SystemExit(f"no encuentro la pieza {ref} en data/piezas/todas.jsonl")


def _recrear_y_mandar(p: dict, kanban: bool):
    if not p.get("analisis"):
        analizar.piezas([p])
    rec = recrear.pieza(p)
    if kanban:
        for fmt in ("reel", "carrusel"):
            r = hub.cadd_idea(hub.idea_desde_recreacion(p, rec[fmt], fmt))
            print(f"[kanban] {fmt} → fila {r.get('row')}")


def cmd_recrear(a):
    p = _buscar(a.ref)
    _recrear_y_mandar(p, a.kanban)
    build_site.build()


def cmd_lote(a):
    sem = _semana_puntuada()
    top = score.top(sem, max(a.top * 3, 30), "comentarios")
    analizar.piezas(top)
    propias = _propias()
    recreables = [p for p in top if (p.get("analisis") or {}).get("recreable") and not p.get("recreacion")
                  and p["cuenta"] not in propias and (p.get("cuenta_fuente") or p["cuenta"]) not in propias][:a.top]
    print(f"[lote] {len(recreables)} piezas recreables")
    for p in recreables:
        _recrear_y_mandar(p, a.kanban)
    build_site.build()


def cmd_pedido(a):
    cuentas = [c.strip() for c in a.cuentas.split(",") if c.strip()]
    modo = "historico" if a.dias >= 60 else "semanal"
    piezas = ingest_ig.correr(modo, limite=a.limite, cuentas=cuentas, dias=a.dias)
    base = score.baseline(ingest_ig.todas())
    piezas = score.puntuar(piezas, base, _perfiles())
    top = score.top(piezas, a.top, "comentarios")
    print(json.dumps([{k: p.get(k) for k in ("cuenta", "comentarios", "views", "outlier", "url", "caption")} for p in top],
                     ensure_ascii=False, indent=1)[:12000])
    build_site.build()


def cmd_thumbs(a):
    thumbs.bajar(_ventana())
    build_site.build()


def cmd_cuenta(a):
    """Vista profunda: scrape largo + videos/slides + transcripts + carruseles leídos + análisis + JSON de la cuenta."""
    import datetime as dt
    h = a.handle.lower().lstrip("@")
    if not a.sin_scrape:
        ingest_ig.correr("historico", limite=a.limite, cuentas=[h])
        ingest_ig.perfiles(cuentas=[h])
    ps = cuenta.piezas_de(h, a.dias)
    media.bajar_videos(ps)
    media.bajar_slides(ps)
    thumbs.bajar(cuenta.piezas_de(h))
    media.transcribir(cuenta.piezas_de(h, a.dias))
    carruseles.correr(cuenta.piezas_de(h, a.dias))
    ps = cuenta.piezas_de(h, a.dias)
    # re-analizar las que no tienen análisis o se analizaron solo con el caption y ahora tienen transcript/slides
    rehacer = [p for p in ps if not p.get("analisis")
               or ((p.get("transcript") or p.get("slides_texto")) and not (p.get("analisis") or {}).get("con_medios"))]
    analizar.piezas(rehacer, forzar=True)
    guion.etiquetar(cuenta.piezas_de(h, a.dias))
    cuenta.build(h, a.dias)
    build_site.build()


def cmd_guion(a):
    """Anatomía del guion (schema creator-lab, a ciegas) sobre reels con transcript + benchmark contra Nahue."""
    todas = ingest_ig.todas()
    objetivo = [p for p in todas if not a.cuenta or p["cuenta"] == a.cuenta.lower().lstrip("@")]
    guion.etiquetar(objetivo, forzar=a.forzar)
    print(f"[roles] competencia: {guion.roles_competencia(ingest_ig.todas() if not a.cuenta else [p for p in ingest_ig.todas() if p['cuenta'] == a.cuenta.lower().lstrip('@')], forzar=a.forzar)} reels")
    print(f"[objetivo] competencia: {guion.objetivos_competencia(ingest_ig.todas(), forzar=a.forzar)} reels")
    if not a.cuenta:
        print(f"[roles] nahue: {guion.roles_nahue(forzar=a.forzar)} reels")
        print(f"[objetivo] nahue: {guion.objetivos_nahue(forzar=a.forzar)} reels")
    print(guion.benchmark(ingest_ig.todas()))
    print(f"→ {config.ANALISIS / 'guion-benchmark.md'}")


def _ventana() -> list[dict]:
    """Piezas de los últimos VENTANA_DIAS días (lo que lleva el sitio)."""
    import datetime as dt
    desde = (config.ahora() - dt.timedelta(days=build_site.VENTANA_DIAS)).strftime("%Y-%m-%d")
    return [p for p in ingest_ig.todas() if (p.get("fecha") or "")[:10] >= desde]


def cmd_profundo(a):
    from radar import profundo
    cs = [c.strip() for c in a.cuentas.split(",") if c.strip()]
    dias = None if a.todo else a.dias
    if a.etapa in ("transcribir", "todo"):
        profundo.transcribir(cs, dias, a.motor)
    if a.etapa in ("carruseles", "todo"):
        profundo.leer_carruseles(cs, dias)
    if a.etapa in ("analizar", "todo"):
        profundo.analizar_todo(cs, dias)
    if a.etapa in ("cuentas", "todo"):
        profundo.cuentas_build(cs, a.dias)


def cmd_barrido(a):
    from radar import barrido
    barrido.sync()
    if a.analizar:
        from radar import analizar
        ps = [p for p in ingest_ig.todas() if (p.get("slides_texto") or p.get("transcript")) and not (p.get("analisis") or {}).get("con_medios")
              and (p.get("fecha") or "") >= (config.ahora() - __import__("datetime").timedelta(days=3)).strftime("%Y-%m-%d")]
        analizar.piezas(ps, forzar=True)
    build_site.build()


def cmd_build(a):
    try:
        from radar import barrido
        barrido.sync()  # integra lo que juntó el job de 12 h (~/bm-barrido)
    except Exception as e:
        print(f"[barrido] no pude sincronizar: {e}")
    thumbs.bajar(_ventana())
    build_site.build()


def cmd_deploy(a):
    site_id = os.getenv("NETLIFY_SITE_ID", "")
    if not site_id:
        raise SystemExit("Falta NETLIFY_SITE_ID en .env. Crear el sitio: netlify sites:create --name bm-radar-contenido")
    cwd = str(config.ROOT)
    cmd = [NETLIFY, "deploy", "--prod", "--dir", "site", "--functions", "netlify/functions", "--site", site_id, "--no-build"]
    print("$", " ".join(cmd))
    # CI + stdin vacío + token por entorno: así el CLI no se cuelga bajo launchd (probado 1-oct-2026)
    env = dict(os.environ, CI="true", NETLIFY_TELEMETRY_DISABLED="1",
               PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:" + os.environ.get("PATH", ""))
    for intento in range(3):  # un corte de red al publicar no puede dejar el sitio viejo 12 h
        try:
            subprocess.run(cmd, cwd=cwd, check=True, env=env, stdin=subprocess.DEVNULL, timeout=1500)
            break
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if intento == 2:
                raise
            print(f"[deploy] falló el intento {intento + 1}, reintento en 90 s")
            time.sleep(90)


def cmd_auto(a):
    """Corrida desatendida (launchd, después del barrido de 12 h): integra lo nuevo, transcribe, analiza, arma vistas y publica."""
    import datetime as dt, json, time
    from radar import barrido, media, analizar, cuenta
    t0 = time.time()
    res = {"inicio": config.ahora().isoformat(timespec="seconds")}
    res["barrido"] = barrido.sync()
    desde = (config.ahora() - dt.timedelta(days=4)).strftime("%Y-%m-%d")
    nuevas = [p for p in ingest_ig.todas() if (p.get("fecha") or "")[:10] >= desde]
    reels = [p for p in nuevas if p.get("tipo_media") == "reel" and not p.get("transcript") and not p.get("sin_habla")]
    try:
        media.bajar_audios(reels)
        res["transcriptos"] = media.transcribir(reels, motor="groq" if config.GROQ_API_KEY else None)
    except Exception as e:
        res["error_transcripcion"] = str(e)[:200]
    nuevas = [p for p in ingest_ig.todas() if (p.get("fecha") or "")[:10] >= desde]
    pend = [p for p in nuevas if not p.get("analisis") or not (p.get("analisis") or {}).get("tipo_angulo")
            or ((p.get("transcript") or p.get("slides_texto")) and not (p.get("analisis") or {}).get("con_medios"))]
    try:
        analizar.piezas(pend, forzar=True)
        res["analizadas"] = len(pend)
    except Exception as e:
        res["error_analisis"] = str(e)[:200]  # sin crédito o caída: se publica igual y se analiza en la próxima
    idx_p = config.SITE_DATA / "cuentas" / "index.json"
    for h in (json.loads(idx_p.read_text()) if idx_p.exists() else {}):
        try:
            cuenta.build(h, 30)
        except Exception as e:
            print(f"[auto] cuenta {h}: {e}")
    thumbs.bajar(_ventana())
    build_site.build()
    cmd_deploy(a)
    res.update(fin=config.ahora().isoformat(timespec="seconds"), segundos=int(time.time() - t0))
    (config.DATA / "auto-estado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"[auto] {json.dumps(res, ensure_ascii=False)}")


def cmd_lunes(a):
    cmd_semanal(argparse.Namespace(dias=7))
    ingest_ig.perfiles()
    cmd_comentarios(argparse.Namespace(top=100, por=50))
    cmd_analizar(argparse.Namespace(top=50))
    cmd_minar(a)
    cmd_lote(argparse.Namespace(top=10, kanban=True))
    cmd_deploy(a)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("demo").set_defaults(f=cmd_demo)
    h = sp.add_parser("historico"); h.add_argument("--limite", type=int, default=100); h.set_defaults(f=cmd_historico)
    s = sp.add_parser("semanal"); s.add_argument("--dias", type=int, default=7); s.set_defaults(f=cmd_semanal)
    sp.add_parser("perfiles").set_defaults(f=cmd_perfiles)
    c = sp.add_parser("comentarios"); c.add_argument("--top", type=int, default=100); c.add_argument("--por", type=int, default=50); c.set_defaults(f=cmd_comentarios)
    an = sp.add_parser("analizar"); an.add_argument("--top", type=int, default=50); an.set_defaults(f=cmd_analizar)
    sp.add_parser("minar").set_defaults(f=cmd_minar)
    r = sp.add_parser("recrear"); r.add_argument("ref"); r.add_argument("--kanban", action="store_true"); r.set_defaults(f=cmd_recrear)
    lo = sp.add_parser("lote"); lo.add_argument("--top", type=int, default=10); lo.add_argument("--kanban", action="store_true"); lo.set_defaults(f=cmd_lote)
    pe = sp.add_parser("pedido"); pe.add_argument("cuentas"); pe.add_argument("--dias", type=int, default=30); pe.add_argument("--limite", type=int, default=50); pe.add_argument("--top", type=int, default=20); pe.set_defaults(f=cmd_pedido)
    sp.add_parser("thumbs").set_defaults(f=cmd_thumbs)
    cu = sp.add_parser("cuenta"); cu.add_argument("handle"); cu.add_argument("--dias", type=int, default=30); cu.add_argument("--limite", type=int, default=300); cu.add_argument("--sin-scrape", dest="sin_scrape", action="store_true"); cu.set_defaults(f=cmd_cuenta)
    g = sp.add_parser("guion"); g.add_argument("--cuenta", default=""); g.add_argument("--forzar", action="store_true"); g.set_defaults(f=cmd_guion)
    pr = sp.add_parser("profundo"); pr.add_argument("--cuentas", required=True); pr.add_argument("--dias", type=int, default=31); pr.add_argument("--todo", action="store_true")
    pr.add_argument("--motor", default=None); pr.add_argument("--etapa", default="todo", choices=["transcribir", "carruseles", "analizar", "cuentas", "todo"]); pr.set_defaults(f=cmd_profundo)
    ba = sp.add_parser("barrido"); ba.add_argument("--analizar", action="store_true"); ba.set_defaults(f=cmd_barrido)
    sp.add_parser("build").set_defaults(f=cmd_build)
    sp.add_parser("deploy").set_defaults(f=cmd_deploy)
    sp.add_parser("auto").set_defaults(f=cmd_auto)
    sp.add_parser("lunes").set_defaults(f=cmd_lunes)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
