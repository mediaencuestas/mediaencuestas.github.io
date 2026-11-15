"""Lee del preelectoral CIS 3584 (avance, hoja «Provincia») el voto+simpatía sobre quienes citan partido (P5aR)
y el recuerdo de voto del 23J (C1aR) en las 52 provincias. Salida: cuotas por provincia y partido y N."""
import openpyxl, pandas as pd, pyreadstat

XL = "/mnt/user-data/uploads/MICRODATOS/CIS/3584-multi_A.xlsx"
OUT = "/home/claude/demo/out/"
_, meta = pyreadstat.read_sav("/home/claude/cisraw/MD3577/3577.sav", metadataonly=True)
label2code = {v: f"{int(k):02d}" for k, v in meta.variable_value_labels["PROV"].items()}

CUR = {"PSOE": "PSOE", "PP": "PP", "VOX": "VOX", "Frente Amplio": "FA", "ERC": "ERC", "EH Bildu": "BILDU", "Se Acabó la Fiesta": "SALF",
       "Podemos": "PODEMOS", "Compromís": "FA", "Adelante Andalucía": "ADELANTE", "BNG": "BNG", "Junts": "JUNTS", "EAJ-PNV": "PNV",
       "UPC": "FA", "UPN-PP": "PP", "Ara Més": "FA", "Coalición Canaria": "CC"}
REC = {"PP": "PP", "PSOE": "PSOE", "VOX": "VOX", "Sumar": "SUMAR", "ERC": "ERC", "Junts": "JUNTS", "EH Bildu": "BILDU", "EAJ-PNV": "PNV",
       "BNG": "BNG", "CCa": "CC", "UPN": "PP", "PACMA": "OTH", "Otro partido": "OTH"}

rows = list(openpyxl.load_workbook(XL, read_only=True, data_only=True)["Provincia"].iter_rows(values_only=True))
hdr = rows[7]
cols = {i: label2code[h] for i, h in enumerate(hdr) if h in label2code}

def block(title, mapping):
    i0 = next(i for i, r in enumerate(rows) if r[0] == title)
    out, n = {}, {}
    for r in rows[i0 + 3:i0 + 60]:
        if r[0] is None: continue
        if str(r[0]).startswith("Pregunta"): break
        name = str(r[0])
        if name == "(N)":
            n = {c: r[i] for i, c in cols.items()}; break
        key = next((v for k, v in mapping.items() if name.startswith(k)), None)
        if key is None: continue
        for i, c in cols.items():
            out.setdefault(c, {}); out[c][key] = out[c].get(key, 0) + (r[i] or 0)
    df = pd.DataFrame(out).T.fillna(0)
    df = df.div(df.sum(axis=1), axis=0)          # cuotas sobre quienes citan un partido
    df["N"] = pd.Series(n)
    return df

cur = block("Pregunta 5aR", CUR); rec = block("Pregunta C1aR", REC)
cur.to_csv(OUT + "cis3584_voto_prov.csv"); rec.to_csv(OUT + "cis3584_recuerdo_prov.csv")
print(len(cur), "provincias")
print((100 * cur.loc[["28", "08", "41", "46"], ["PP", "PSOE", "VOX", "FA", "PODEMOS", "SALF"]]).round(1).to_string())
print((100 * rec.loc[["28", "08"], ["PP", "PSOE", "VOX", "SUMAR"]]).round(1).to_string())
