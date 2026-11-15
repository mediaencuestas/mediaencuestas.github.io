"""Medias diarias (ponderada y simple), peso de cada casa y prueba de robustez.

Ponderada: cada encuesta pesa recencia × frecuencia de la casa × muestra.
  - recencia: 0,5 ** (días desde el punto medio del campo / vida media), ignorando las de más de `edad_maxima_dias`
  - frecuencia: la ola más reciente de cada casa pesa 1, la anterior 0,5, la siguiente 0,25…
  - muestra: raíz(min(n, techo) / referencia)
Simple: promedio sin pesos de las encuestas con fin de campo en los últimos 28 días.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from comun import PARTIDOS, NOMBRES, SALIDA, TRABAJO, BASE, config, leer_encuestas, para_media


def pesos(pool, t, P):
    pool = pool.copy()
    edad = (t - pool.mid).dt.days.clip(lower=0)
    rango = pool.groupby("firm").end.rank(ascending=False, method="first") - 1
    pool["w"] = 0.5 ** (edad / P["vida_media_dias"]) * P["decaimiento_casa"] ** rango * pool.w_n
    return pool


def media_pond(pool, partidos, minimo):
    out = {}
    for p in partidos:
        m = pool[p].notna()
        out[p] = float(np.average(pool.loc[m, p], weights=pool.loc[m, "w"])) if m.sum() >= minimo and pool.loc[m, "w"].sum() > 0 else None
    return out


def calcular(cfg=None):
    cfg = cfg or config()
    P = cfg["media"]
    df = para_media(leer_encuestas(), cfg)
    n = df.n.fillna(df.n.median()).clip(upper=P["techo_muestra"])
    df["w_n"] = np.sqrt(n / P["muestra_referencia"])
    ultimo = df.end.max()
    dias = pd.date_range(P["inicio"], ultimo, freq="D")
    filas = []
    for t in dias:
        win = df[(df.end <= t) & (df.end > t - pd.Timedelta(days=P["ventana_simple_dias"]))]
        pool = pesos(df[(df.end <= t) & (df.end > t - pd.Timedelta(days=P["edad_maxima_dias"]))], t, P)
        r = {"date": t.strftime("%Y-%m-%d")}
        pond = media_pond(pool, PARTIDOS, P["minimo_encuestas"])
        for p in PARTIDOS:
            x = win[p].dropna()
            r[p] = None if pond[p] is None else round(pond[p], 2)
            r[p + "_simple"] = round(float(x.mean()), 2) if len(x) >= P["minimo_encuestas"] else None
        r["n_ventana"] = len(win)
        filas.append(r)
    medias = pd.DataFrame(filas)

    # hoy
    ult, prev = filas[-1], filas[max(0, len(filas) - 29)]
    r23 = pd.read_csv(BASE / "res23.csv").set_index("party").share.to_dict()
    hoy = [{"party": p, "nombre": NOMBRES[p], "fecha": ult["date"], "hoy": ult[p], "simple": ult[p + "_simple"],
            "cambio28": None if ult[p] is None or prev[p] is None else round(ult[p] - prev[p], 2),
            "r23j": r23.get(p), "vs23j": None if ult[p] is None or r23.get(p) is None else round(ult[p] - r23[p], 2)}
           for p in PARTIDOS]

    # peso de cada casa hoy y robustez (quitar una casa cada vez)
    t = ultimo
    pool = pesos(df[(df.end <= t) & (df.end > t - pd.Timedelta(days=P["edad_maxima_dias"]))], t, P)
    tot = pool.w.sum()
    win = df[df.end > t - pd.Timedelta(days=P["ventana_simple_dias"])]
    cnt = win.firm.value_counts()
    peso = [{"firm": f, "pond": round(float(g.w.sum() / tot), 4), "simple": round(float(cnt.get(f, 0) / len(win)), 4)}
            for f, g in pool.groupby("firm")]
    peso = sorted([x for x in peso if x["pond"] >= 0.005 or x["simple"] > 0], key=lambda x: -x["pond"])
    cuatro = ["PP", "PSOE", "VOX", "FA"]
    full = media_pond(pool, cuatro, P["minimo_encuestas"])
    rob = []
    for f, g in pool.groupby("firm"):
        sin = media_pond(pool[pool.firm != f], cuatro, P["minimo_encuestas"])
        r = {"firm": f, "peso": round(100 * float(g.w.sum() / tot), 2), "olas": len(g), "dias": int((t - g.end.max()).days)}
        for p in cuatro:
            r["d" + p] = None if sin[p] is None or full[p] is None else round(sin[p] - full[p], 3)
        r["max"], r["max_party"] = max(((abs(r["d" + p] or 0), p) for p in cuatro))
        rob.append(r)
    rob = sorted([r for r in rob if r["peso"] >= 0.5], key=lambda r: -r["peso"])
    neff = 1 / sum((r["peso"] / 100) ** 2 for r in rob) if rob else None
    return df, medias, hoy, peso, rob, neff


def main():
    cfg = config()
    df, medias, hoy, peso, rob, neff = calcular(cfg)
    TRABAJO.mkdir(exist_ok=True)
    SALIDA.mkdir(parents=True, exist_ok=True)
    medias.to_csv(TRABAJO / "media_ponderada_diaria.csv", index=False)
    todas = leer_encuestas()
    usadas = set(zip(df.firm, df.start, df.end))
    enc = todas.copy()
    enc["en_media"] = [(f, s, e) in usadas for f, s, e in zip(enc.firm, enc.start, enc.end)]
    enc = enc.sort_values("end", ascending=False)
    for c in ["start", "end"]:
        enc[c] = enc[c].dt.strftime("%Y-%m-%d")
    enc = enc.drop(columns=[c for c in ["added"] if c in enc.columns])
    dump = lambda nombre, obj: (SALIDA / nombre).write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    limpio = lambda d: d.astype(object).where(pd.notna(d), None).to_dict("records")
    dump("encuestas.json", limpio(enc))
    dump("medias.json", limpio(medias))
    dump("hoy.json", hoy)
    dump("pesos.json", {"casas": peso, "robustez": rob, "casas_efectivas": None if neff is None else round(neff, 1)})
    print("media a", hoy[0]["fecha"], "·", ", ".join(f"{r['party']} {r['hoy']}" for r in hoy[:4]), "· casas efectivas", round(neff or 0, 1))


if __name__ == "__main__":
    main()
