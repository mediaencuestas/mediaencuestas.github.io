"""Escribe estado.json y partidos.json en public/datos y una portada mínima en public/index.html."""
import json, os, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(__file__))
from comun import COLORES, NOMBRES, PARTIDOS, SALIDA, config, en_veda, leer_encuestas, para_media

cfg = config()
SALIDA.mkdir(parents=True, exist_ok=True)
hoy = json.loads((SALIDA / "hoy.json").read_text(encoding="utf-8"))
df = para_media(leer_encuestas(), cfg)
estado = {"actualizado": datetime.now(timezone.utc).isoformat(timespec="minutes"), "fecha_media": hoy[0]["fecha"],
          "encuestas_en_media": int(len(df)), "casas": int(df.firm.nunique()), "excluidas": cfg["excluir_de_la_media"],
          "veda": cfg.get("veda"), "en_veda": en_veda(cfg), "parametros": cfg["media"]}
(SALIDA / "estado.json").write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
(SALIDA / "partidos.json").write_text(json.dumps([{"party": p, "nombre": NOMBRES[p], "color": COLORES[p]} for p in PARTIDOS], ensure_ascii=False), encoding="utf-8")
ficheros = sorted(f.name for f in SALIDA.glob("*.json"))
(SALIDA.parent / "index.html").write_text(
    "<!doctype html><meta charset=utf-8><title>Datos · media de encuestas</title>"
    f"<h1>Datos de la media de encuestas</h1><p>Actualizado {estado['actualizado']} · media a {estado['fecha_media']}</p><ul>"
    + "".join(f'<li><a href="datos/{f}">{f}</a></li>' for f in ficheros) + "</ul>", encoding="utf-8")
print("publicado:", ", ".join(ficheros))
