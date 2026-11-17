"""Resumen de todas las encuestas pendientes de aprobar (rama de propuestas frente a main) para el texto de la propuesta.

Uso: python scripts/resumen_pr.py <encuestas.csv de main>   → escribe trabajo/pr.md
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from comun import TRABAJO, config, leer_encuestas
from wikipedia import informe

main = pd.read_csv(sys.argv[1], parse_dates=["start", "end"])
rama = leer_encuestas()
clave = lambda d: list(zip(d.firm, d.start, d.end))
en_main = set(clave(main))
nuevas = rama[[k not in en_main for k in clave(rama)]]
correcciones = []
cols = ["PP", "PSOE", "VOX", "FA"]
m = main.set_index(["firm", "start", "end"])
for i, r in rama[[k in en_main for k in clave(rama)]].iterrows():
    b = m.loc[(r.firm, r.start, r.end)]
    if isinstance(b, pd.DataFrame):
        b = b.iloc[0]
    dif = [p for p in cols if pd.notna(r[p]) and pd.notna(b[p]) and
