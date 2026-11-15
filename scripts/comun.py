"""Definiciones comunes: partidos, rutas, configuración y lectura de la base de encuestas."""
import json
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
BASE = DATOS / "base"
TERR = DATOS / "territorial"
SALIDA = RAIZ / "public" / "datos"          # lo que se publica en GitHub Pages
TRABAJO = RAIZ / "trabajo"                  # ficheros intermedios (no se publican)

PARTIDOS = ["PP", "PSOE", "VOX", "FA", "PODEMOS", "SALF", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC", "ADELANTE"]
NOMBRES = {"PP": "PP", "PSOE": "PSOE", "VOX": "Vox", "FA": "FA + aliados", "PODEMOS": "Podemos", "SALF": "SALF",
           "ERC": "ERC", "JUNTS": "Junts", "BILDU": "EH Bildu", "PNV": "PNV", "BNG": "BNG", "CC": "Coalición Canaria",
           "ADELANTE": "Adelante Andalucía"}
COLORES = {"PP": "#1d84ce", "PSOE": "#e30613", "VOX": "#5ac035", "FA": "#e5197d", "PODEMOS": "#7b3f8c", "SALF": "#8a6d3b",
           "ERC": "#f2a900", "JUNTS": "#20c0b0", "BILDU": "#2a9d8f", "PNV": "#3a7d44", "BNG": "#76b3dd", "CC": "#e0c000",
           "ADELANTE": "#6c8e23"}
COLUMNAS = ["firm", "media", "start", "end", "n"] + PARTIDOS + ["fa_note", "source", "url", "added"]


def config():
    return json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))


def hoy():
    return pd.Timestamp(date.today())


def en_veda(cfg=None, dia=None):
    """True si `dia` cae en el periodo en que la LOREG (art. 69.7) prohíbe publicar encuestas."""
    cfg = cfg or config()
    v = cfg.get("veda")
    if not v:
        return False
    dia = pd.Timestamp(dia) if dia is not None else hoy()
    return pd.Timestamp(v["desde"]) <= dia <= pd.Timestamp(v["hasta"])


def leer_encuestas():
    df = pd.read_csv(DATOS / "encuestas.csv", dtype={"firm": str, "media": str})
    df["start"] = pd.to_datetime(df.start)
    df["end"] = pd.to_datetime(df.end)
    return df


def guardar_encuestas(df):
    df = df.copy()
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = np.nan
    df = df[COLUMNAS].sort_values(["end", "firm"], ascending=[False, True])
    for p in PARTIDOS:
        df[p] = pd.to_numeric(df[p], errors="coerce").round(2)
    df["n"] = pd.to_numeric(df.n, errors="coerce").round(0).astype("Int64")
    df.to_csv(DATOS / "encuestas.csv", index=False, date_format="%Y-%m-%d")


def para_media(df, cfg=None):
    """Encuestas que entran en las medias: sin casas excluidas, una ola por tracking."""
    cfg = cfg or config()
    df = df[~df.firm.isin(cfg["excluir_de_la_media"])].copy()
    df = df[df.PP.notna() & df.PSOE.notna()]
    df = df.sort_values("end").drop_duplicates(["firm", "start"], keep="last")   # trackings acumulados
    df = df.drop_duplicates(["firm", "end"], keep="last")
    df = df.sort_values("end", ascending=False).reset_index(drop=True)
    df["mid"] = df.start + (df.end - df.start) / 2
    return df


MESES = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def rango_fechas(texto, anio):
    """'10–13 Nov' | '26 Oct–13 Nov' | '27 Oct' | '28 Feb–7 Mar 2025' -> (inicio, fin)."""
    s = re.sub(r"\s+", " ", texto.replace("-", "–").replace("—", "–")).strip()
    m = re.search(r"(\d{4})$", s)
    if m:
        anio = int(m.group(1))
        s = s[: m.start()].strip()
    partes = [p.strip() for p in s.split("–")]

    def p(x, mes_defecto=None):
        t = x.split()
        return int(t[0]), (MESES[t[1][:3]] if len(t) > 1 else mes_defecto)

    if len(partes) == 1:
        d, mo = p(partes[0])
        e = pd.Timestamp(anio, mo, d)
        return e, e
    d2, mo2 = p(partes[1])
    d1, mo1 = p(partes[0], mo2)
    fin = pd.Timestamp(anio, mo2, d2)
    inicio = pd.Timestamp(anio if mo1 <= mo2 else anio - 1, mo1, d1)
    return inicio, fin
