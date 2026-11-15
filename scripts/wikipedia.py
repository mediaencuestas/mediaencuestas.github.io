"""Lee la tabla actual de encuestas de Wikipedia y añade a datos/encuestas.csv las que aún no están.

No publica nada: se ejecuta en una rama y GitHub abre una «pull request» con las encuestas nuevas.
Al aprobarla (botón «Merge»), entran en la base y se recalcula la web.

Uso:  python scripts/wikipedia.py            (descarga la página)
      python scripts/wikipedia.py --html f    (lee un fichero HTML local, para pruebas)
"""
import argparse
import os
import sys
from datetime import date

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(__file__))
from comun import DATOS, TRABAJO, PARTIDOS, NOMBRES, config, en_veda, hoy, leer_encuestas, guardar_encuestas, rango_fechas

API = "https://en.wikipedia.org/w/api.php"
AGENTE = "demoscopia-media-encuestas/1.0 (GitHub Actions; lector de la tabla de encuestas)"

# enlace de la cabecera -> código de partido
CABECERAS = [("People%27s_Party", "PP"), ("Socialist_Workers", "PSOE"), ("Vox_(political_party)", "VOX"),
             ("Broad_Front", "FA"), ("Valencian_Front", "FV"), ("Comprom", "FV"), ("Republican_Left_of_Catalonia", "ERC"),
             ("Together_for_Catalonia", "JUNTS"), ("EH_Bildu", "BILDU"), ("Basque_Nationalist", "PNV"),
             ("Galician_Nationalist", "BNG"), ("Canarian_Coalition", "CC"), ("Adelante_Andaluc", "ADELANTE"),
             ("Podemos", "PODEMOS"), ("Se_Acab", "SALF")]
OBLIGATORIAS = ["PP", "PSOE", "VOX", "FA"]


def descargar(pagina):
    r = requests.get(API, params={"action": "parse", "page": pagina, "prop": "text|revid", "format": "json",
                                  "formatversion": 2}, headers={"User-Agent": AGENTE}, timeout=60)
    r.raise_for_status()
    j = r.json()["parse"]
    return j["text"], j["revid"]


def tabla_actual(html):
    """Primera tabla de encuestas que tiene columna del Frente Amplio."""
    soup = BeautifulSoup(html, "html.parser")
    for sup in soup.select("sup.reference"):
        sup.decompose()                          # notas al pie [1], [2]…
    for t in soup.select("table.wikitable"):
        cab = t.find("tr")
        if cab and "Fieldwork" in cab.get_text() and cab.find("a", href=lambda h: h and "Broad_Front" in h):
            return t
    raise SystemExit("No encuentro la tabla de encuestas con el Frente Amplio: ¿ha cambiado la página de Wikipedia?")


def columnas(tabla):
    cols = []
    for th in tabla.find("tr").find_all("th"):
        txt = th.get_text(" ", strip=True)
        a = th.find("a")
        href = a.get("href", "") if a else ""
        code = next((c for k, c in CABECERAS if k in href), None)
        if code is None:
            low = txt.lower()
            code = ("firm" if "polling firm" in low else "date" if "fieldwork" in low else "n" if "sample" in low
                    else "turnout" if "turnout" in low else "lead" if "lead" in low else "otro:" + (txt or href))
        cols += [code] * int(th.get("colspan", 1))
    falta = [c for c in OBLIGATORIAS + ["firm", "date", "n"] if c not in cols]
    if falta:
        raise SystemExit(f"Faltan columnas en la tabla de Wikipedia: {falta}. Revisa el lector.")
    return cols


def rejilla(tabla, ncols):
    """Filas de datos como listas de celdas, expandiendo rowspan y colspan (una celda combinada aparece repetida)."""
    pend = {}                                   # columna -> [filas restantes, celda]
    filas = []
    for tr in tabla.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        fila, it, c = [None] * ncols, iter(tds), 0
        while c < ncols:
            if c in pend:
                fila[c] = pend[c][1]
                pend[c][0] -= 1
                if pend[c][0] == 0:
                    del pend[c]
                c += 1
                continue
            td = next(it, None)
            if td is None:
                break
            cs, rs = int(td.get("colspan", 1)), int(td.get("rowspan", 1))
            for k in range(cs):
                if c + k < ncols:
                    fila[c + k] = td
                    if rs > 1:
                        pend[c + k] = [rs - 1, td]
            c += cs
        filas.append(fila)
    return filas


def valor(td):
    if td is None:
        return np.nan
    t = td.get_text("|", strip=True).split("|")[0].replace(",", "").strip()
    try:
        return float(t)
    except ValueError:
        return np.nan


def leer_tabla(html, revid, cfg):
    t = tabla_actual(html)
    cols = columnas(t)
    idx = {c: i for i, c in reversed(list(enumerate(cols)))}    # primera aparición de cada código
    hoy_ = hoy()
    alias = cfg.get("alias_casas", {})
    url = f"https://en.wikipedia.org/w/index.php?title={cfg['wikipedia_pagina']}&oldid={revid}"
    out = []
    for f in rejilla(t, len(cols)):
        celda = f[idx["firm"]]
        if celda is None:
            continue
        etiqueta = celda.get_text(" ", strip=True)
        if etiqueta.startswith("CIS (") or "election" in etiqueta.lower():
            continue                                             # reinterpretaciones del CIS y filas de resultados
        firm, _, media = etiqueta.partition("/")
        firm = alias.get(firm.strip(), firm.strip())
        if firm in cfg["no_proponer"]:
            continue
        try:
            ini, fin = rango_fechas(f[idx["date"]].get_text(" ", strip=True), hoy_.year)
            if fin > hoy_ + pd.Timedelta(days=7):
                ini, fin = rango_fechas(f[idx["date"]].get_text(" ", strip=True), hoy_.year - 1)
        except Exception:
            print("  · fecha ilegible, se salta:", etiqueta, f[idx["date"]].get_text(" ", strip=True))
            continue
        r = {"firm": firm, "media": media.strip() or None, "start": ini, "end": fin, "n": valor(f[idx["n"]]),
             "source": "Wikipedia (lector automático)", "url": url, "added": date.today().isoformat()}
        for p in PARTIDOS:
            if p != "FA":
                r[p] = valor(f[idx[p]]) if p in idx else np.nan
        fa_td, fv_td = f[idx["FA"]], f[idx["FV"]] if "FV" in idx else None
        fa, fv = valor(fa_td), valor(fv_td)
        if fv_td is not None and fv_td is fa_td:
            r["FA"], r["fa_note"] = fa, "FA+Compromís (conjunto)"
        elif not np.isnan(fv):
            r["FA"], r["fa_note"] = fa + fv, "FA + Compromís (suma)"
        else:
            r["FA"], r["fa_note"] = fa, "FA (Compromís sin dato)"
        if np.isnan(r["PP"]) or np.isnan(r["PSOE"]):
            continue
        out.append(r)
    df = pd.DataFrame(out).drop_duplicates(["firm", "start", "end"])
    return df


def clasificar(nuevas, base, descartadas):
    """Separa lo leído en: nuevas, correcciones (misma casa y fecha, cifras distintas) y ya conocidas."""
    nuevas_, correcciones = [], []
    for _, r in nuevas.iterrows():
        if ((descartadas.firm == r.firm) & (descartadas.start == r.start) & (descartadas.end == r.end)).any():
            continue
        misma = base[(base.firm == r.firm) & (base.end == r.end)]
        if len(misma):
            b = misma.iloc[0]
            dif = [p for p in ["PP", "PSOE", "VOX", "FA"] if pd.notna(r[p]) and pd.notna(b[p]) and abs(r[p] - b[p]) > 0.05]
            if dif:
                correcciones.append((misma.index[0], r, dif))
            continue
        # ola anterior de un tracking que ya tenemos más avanzado (misma casa y mismo inicio, fin posterior)
        if ((base.firm == r.firm) & (base.start == r.start) & (base.end > r.end)).any():
            continue
        nuevas_.append(r)
    return pd.DataFrame(nuevas_), correcciones


def fmt(v):
    return "–" if pd.isna(v) else f"{v:.1f}".replace(".", ",")


def informe(nuevas, correcciones, base, cfg):
    excl = set(cfg["excluir_de_la_media"])
    lin = ["Encuestas leídas de Wikipedia que todavía no están en la base. **Revisa las cifras y pulsa «Merge pull request» para aprobarlas.** "
           "Al aprobar, la media y los escaños se recalculan y la web se actualiza sola en unos minutos.", ""]
    if len(nuevas):
        lin += ["### Nuevas", "", "| Casa | Medio | Campo | Muestra | PP | PSOE | Vox | FA | Podemos | SALF | Aviso |",
                "|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in nuevas.sort_values("end", ascending=False).iterrows():
            avisos = []
            if r.firm in excl:
                avisos.append("no cuenta en la media (casa excluida)")
            if r.firm not in set(base.firm):
                avisos.append("**casa nueva**: comprueba que es una encuesta")
            if pd.isna(r.n):
                avisos.append("sin muestra")
            prev = base[(base.firm == r.firm)].sort_values("end").tail(1)
            if len(prev):
                d = abs(r.PP - prev.PP.iloc[0]) + abs(r.PSOE - prev.PSOE.iloc[0])
                if d > 5:
                    avisos.append(f"**cambio grande** frente a su ola anterior ({d:.1f} pts en PP+PSOE)")
            campo = f"{r.start:%d-%m}→{r.end:%d-%m-%Y}"
            lin.append(f"| {r.firm} | {r.media or ''} | {campo} | {'' if pd.isna(r.n) else int(r.n)} | {fmt(r.PP)} | {fmt(r.PSOE)} | "
                       f"{fmt(r.VOX)} | {fmt(r.FA)} | {fmt(r.PODEMOS)} | {fmt(r.SALF)} | {'; '.join(avisos)} |")
        lin.append("")
    if correcciones:
        lin += ["### Correcciones (Wikipedia ha cambiado cifras de una encuesta que ya teníamos)", ""]
        for i, r, dif in correcciones:
            b = base.loc[i]
            cambios = ", ".join(f"{NOMBRES[p]} {fmt(b[p])} → {fmt(r[p])}" for p in dif)
            lin.append(f"- **{r.firm}** ({r.end:%d-%m-%Y}): {cambios}")
        lin.append("")
    lin += ["---", "**Si una encuesta está mal:** abre la pestaña «Files changed», pulsa los tres puntos del fichero `datos/encuestas.csv` → "
            "«Edit file», corta su línea y pégala en `datos/descartadas.csv` (así no se vuelve a proponer). Después, «Merge».",
            "", "Si no quieres ninguna, cierra la pull request sin aprobarla («Close pull request»)."]
    return "\n".join(lin)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html")
    a = ap.parse_args()
    cfg = config()
    TRABAJO.mkdir(exist_ok=True)
    salida_gh = os.environ.get("GITHUB_OUTPUT")

    def salida(k, v):
        if salida_gh:
            with open(salida_gh, "a") as f:
                f.write(f"{k}={v}\n")

    if en_veda(cfg):
        print("Periodo de veda de la LOREG: no se proponen encuestas nuevas.")
        salida("hay_cambios", "no")
        return
    if a.html:
        html, revid = open(a.html, encoding="utf-8").read(), 0
    else:
        html, revid = descargar(cfg["wikipedia_pagina"])
    leidas = leer_tabla(html, revid, cfg)
    base = leer_encuestas()
    p = DATOS / "descartadas.csv"
    desc = pd.read_csv(p, parse_dates=["start", "end"]) if p.exists() else pd.DataFrame(columns=["firm", "start", "end"])
    nuevas, correcciones = clasificar(leidas, base, desc)
    print(f"Leídas {len(leidas)} filas · nuevas {len(nuevas)} · correcciones {len(correcciones)}")
    if not len(nuevas) and not correcciones:
        salida("hay_cambios", "no")
        return
    df = base.copy()
    for i, r, _ in correcciones:
        for k in ["start", "n", "media", "fa_note"] + PARTIDOS:
            df.at[i, k] = r[k]
        df.at[i, "source"], df.at[i, "url"] = "Wikipedia (corrección, lector automático)", r.url
    df = pd.concat([df, nuevas], ignore_index=True)
    guardar_encuestas(df)
    (TRABAJO / "pr.md").write_text(informe(nuevas, correcciones, base, cfg), encoding="utf-8")
    casas = ", ".join(sorted(set(nuevas.firm))) if len(nuevas) else "correcciones"
    titulo = f"{len(nuevas)} encuesta{'s' if len(nuevas) != 1 else ''} nueva{'s' if len(nuevas) != 1 else ''}: {casas}"
    if correcciones:
        titulo += f" (+{len(correcciones)} corrección{'es' if len(correcciones) > 1 else ''})"
    salida("hay_cambios", "si")
    salida("titulo", titulo[:200])
    print(titulo)


if __name__ == "__main__":
    main()
