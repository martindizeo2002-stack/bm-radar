"""Datos de DEMO para ver el radar antes de tener token. Marcados demo=True en todo el JSON."""
from __future__ import annotations
import random, datetime as dt
from . import config

CUENTAS = ["woker.oficial", "nicolorenzon", "importador.pro", "ecom.argento", "marca.propia.ar", "china.sin.miedo"]
CAPTIONS = [
    "No compres en Alibaba. Te explico por qué en 1688 el mismo producto sale la mitad. Comentá COSTOS",
    "Importar desde Paraguay te sale más caro que traerlo de China. La cuenta completa acá",
    "¿Cuánto se necesita para arrancar a importar? Menos de lo que pensás. Comentá GUIA",
    "Tu proveedor local es tu competencia. Así te copian el producto en 3 semanas",
    "Vendés en Mercado Libre y el 80% de tu venta depende de ellos. Eso no es un negocio, es un alquiler",
    "El trader: la palabra que nadie entiende. Es tu mano derecha en China",
    "Cada producto de este container: cuánto costó, cuánto se vende. Comentá LISTA",
    "Monotributista: sí podés importar. Te muestro cómo",
    "Un día te cae ARCA. Del gris al blanco sin morir en el intento",
    "Marca propia vs genérico: el precio lo ponés vos o te lo pone el mercado",
]


def generar(n: int = 60) -> list[dict]:
    random.seed(7)
    sem = config.semana_iso()
    hoy = config.ahora()
    out = []
    for i in range(n):
        c = random.choice(CUENTAS)
        views = random.choice([None, random.randint(3000, 400000)])
        likes = random.randint(80, 9000)
        com = int(likes * random.uniform(0.02, 0.35))
        out.append({
            "id": f"ig_demo{i:03d}", "plataforma": "ig", "cuenta": c,
            "url": f"https://www.instagram.com/p/DEMO{i:03d}/",
            "tipo_media": random.choice(["reel", "reel", "reel", "carrusel", "post"]),
            "fecha": (hoy - dt.timedelta(days=random.uniform(0.5, 6.5))).strftime("%Y-%m-%dT%H:%M:%S"),
            "caption": random.choice(CAPTIONS), "hashtags": [], "likes": likes, "comentarios": com, "views": views,
            "video_url": None, "thumb": None, "duracion": random.choice([None, 31, 48, 62]),
            "semana": sem, "semana_primera": sem, "scraped_at": hoy.isoformat(timespec="seconds"), "demo": True,
        })
    return out


def perfiles_demo() -> dict:
    return {c: {"seguidores": random.randint(20000, 900000), "actualizado": config.ahora().strftime("%Y-%m-%d")} for c in CUENTAS}
