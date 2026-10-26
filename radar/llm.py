"""Llamadas a Claude (SDK oficial). Salida JSON por output_config.format con fallback a parseo de texto.
Modelo default claude-opus-5 (RADAR_MODEL). Fallback server-side por refusal activado (beta), se apaga solo si el SDK/API lo rechaza."""
from __future__ import annotations
import json, re
import anthropic
from . import config

_client = None


def cliente() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY or None, max_retries=3)
    return _client


def _extraer_json(texto: str):
    texto = texto.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", texto, re.S)
    if m:
        texto = m.group(1).strip()
    i, j = texto.find("{"), texto.rfind("}")
    if i >= 0 and j > i:
        texto = texto[i:j + 1]
    return json.loads(texto)


def json_call(system: str, user, schema: dict, effort: str = "medium", max_tokens: int = 16000, model: str | None = None) -> dict:
    """Devuelve un dict validado contra `schema` (JSON schema). Reintenta sin formato estructurado si la API lo rechaza."""
    base = dict(
        model=model or config.MODEL,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
    )
    extra = dict(extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"}, extra_body={"fallbacks": "default"})
    intentos = [dict(base, **extra), base, _sin_formato(base)]
    ultimo = None
    for kw in intentos:
        try:
            r = cliente().messages.create(**kw)
            break
        except anthropic.BadRequestError as e:
            ultimo = e
            continue
    else:
        raise ultimo
    if r.stop_reason == "refusal":
        raise RuntimeError(f"refusal: {getattr(r.stop_details, 'category', None)}")
    texto = "".join(b.text for b in r.content if b.type == "text")
    try:
        if r.stop_reason == "max_tokens":
            raise json.JSONDecodeError("max_tokens: salida cortada", texto, 0)
        out = _extraer_json(texto)
    except json.JSONDecodeError as e:
        _log_fallo(texto, str(e))
        # reintento único sin formato estructurado y con más margen de salida
        kw = _sin_formato(base); kw["max_tokens"] = min(max_tokens * 2, 64000)
        r = cliente().messages.create(**kw)
        texto = "".join(b.text for b in r.content if b.type == "text")
        out = _extraer_json(texto)
    out["_usage"] = {"in": r.usage.input_tokens, "out": r.usage.output_tokens,
                     "cache_read": getattr(r.usage, "cache_read_input_tokens", None), "model": r.model}
    return out


def _log_fallo(texto: str, err: str) -> None:
    import datetime as dt
    p = config.RAW / f"llm-fallo-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
    p.write_text(f"{err}\n\n{texto}")
    print(f"[llm] JSON inválido ({err[:80]}), reintento sin formato. Log: {p.name}")


def _sin_formato(kw: dict) -> dict:
    kw = dict(kw)
    kw["output_config"] = {"effort": kw["output_config"]["effort"]}
    extra = "\n\nRespondé SOLO con el JSON, sin texto alrededor."
    c = kw["messages"][0]["content"]
    c = c + extra if isinstance(c, str) else list(c) + [{"type": "text", "text": extra}]
    kw["messages"] = [{"role": "user", "content": c}]
    return kw
