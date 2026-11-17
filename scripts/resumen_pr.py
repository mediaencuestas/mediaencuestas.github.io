"""Resumen de las encuestas pendientes de aprobar para el texto de la propuesta.

Uso: python scripts/resumen_pr.py <encuestas.csv de main>
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from comun import TRABAJO, config, leer_encuestas
from wikipedia import informe

main = pd.read_csv(sys.argv[1], parse_dates=["start", "end"])
rama = leer_encuestas()


def clave(d):
    return list(zip(d.firm, d.start, d.end))


en_main = set(clave(main))
es_nueva = [k not in en_main for k in clave(rama)]
nuevas = rama[es_nueva]
viejas = rama[[not x for x in es_nueva]]
correcciones = []
for i, r in viejas.iterrows():
    filtro = (main.firm == r.firm) & (main.start == r.start)
    filtro = filtro & (main.end == r.end)
    idx = main[filtro].index[0]
    b = main.loc[idx]
    dif = []
    for p in ["PP", "PSOE", "VOX", "FA"]:
        if pd.notna(r[p]) and pd.notna(b[p]):
            if abs(r[p] - b[p]) > 0.05:
                dif.append(p)
    if dif:
        correcciones.append((idx, r, dif))

TRABAJO.mkdir(exist_ok=True)
texto = informe(nuevas, correcciones, main, config())
(TRABAJO / "pr.md").write_text(texto, encoding="utf-8")

n = len(nuevas)
s = "s" if n != 1 else ""
titulo = f"{n} encuesta{s} pendiente{s} de aprobar"
if correcciones:
    titulo += f" (+{len(correcciones)} correcciones)"
print(titulo)
