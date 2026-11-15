"""Al cerrar sin aprobar la propuesta de encuestas, apunta en datos/descartadas.csv las que traía,
para que el lector de Wikipedia no las vuelva a proponer.

Uso: python scripts/rechazar.py <encuestas.csv de la rama> <número de la pull request>
"""
import os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from comun import DATOS, leer_encuestas

rama = pd.read_csv(sys.argv[1], parse_dates=["start", "end"])
pr = sys.argv[2]
main = leer_encuestas()
clave = lambda d: set(zip(d.firm, d.start, d.end))
nuevas = clave(rama) - clave(main)
p = DATOS / "descartadas.csv"
desc = pd.read_csv(p, parse_dates=["start", "end"])
filas = [{"firm": f, "start": s, "end": e, "motivo": f"rechazada al cerrar la propuesta #{pr}"} for f, s, e in sorted(nuevas) if (f, s, e) not in clave(desc)]
if filas:
    out = pd.concat([desc, pd.DataFrame(filas)], ignore_index=True)
    for c in ("start", "end"):
        out[c] = pd.to_datetime(out[c]).dt.strftime("%Y-%m-%d")
    out.to_csv(p, index=False)
print(f"{len(filas)} encuestas apuntadas como descartadas")
