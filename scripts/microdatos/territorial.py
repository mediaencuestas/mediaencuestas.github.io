"""Patrón territorial combinado (CIS + 40dB + More in Common), una casa = un voto.
v4: la casa CIS suma el macroestudio 3584 y los barómetros de ene–sep 2026 (estos con medio peso);
    Podemos dentro del espacio sin encoger aquí: se encoge en proyeccion.py hacia su mapa de las europeas.

Para cada casa h, comunidad r y partido q:
  factor_h(r,q) = cuota actual (voto+simpatía, sobre quienes citan partido) / cuota en el recuerdo del 23J
  rel_h(r,q)    = factor_h(r,q) / factor_h(España,q)      -> se cancela el nivel (y el sesgo) de cada casa
  encogido: rel^λ con λ = n/(n+50), n = entrevistados que recuerdan ese partido en r
Combinado: media geométrica de las casas disponibles (mismo peso cada casa).
El espacio de Sumar (FA + Compromís + Ara Més + UPC + Podemos) se trata como un bloque frente al recuerdo de Sumar (+NC en Canarias).
Reparto interno: proporción de Podemos dentro del bloque en r, relativa a la de la casa en las CCAA donde Podemos se presenta;
combinada en log-odds entre casas.
SALF y Adelante: cuota en r relativa a la nacional de la casa.
Detalle provincial dentro de cada comunidad: del CIS 3584 (tablas por provincia), encogido.
"""
import glob, unicodedata, re
import numpy as np, pandas as pd, pyreadstat

OUT = "/home/claude/demo/out/"
K = 50
PODEMOS_NO = {"Cataluña", "Comunitat Valenciana", "Canarias", "Illes Balears"}   # Podemos va dentro de otra lista

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", " ", s)

def ccaa_name(lbl):
    n = norm(lbl)
    for key, std in [("andaluc", "Andalucía"), ("aragon", "Aragón"), ("asturias", "Asturias"), ("balear", "Illes Balears"),
                     ("canari", "Canarias"), ("cantabria", "Cantabria"), ("la mancha", "Castilla-La Mancha"), ("leon", "Castilla y León"),
                     ("catalu", "Cataluña"), ("valencia", "Comunitat Valenciana"), ("extremadura", "Extremadura"), ("galicia", "Galicia"),
                     ("madrid", "Madrid"), ("murcia", "Murcia"), ("navarra", "Navarra"), ("vasco", "País Vasco"), ("rioja", "La Rioja"),
                     ("ceuta", "Ceuta y Melilla"), ("melilla", "Ceuta y Melilla")]:
        if key in n:
            return std
    return None

def cur_party(lbl):
    n = norm(lbl)
    if n.startswith("unidad del pueblo canario") or "compromis" in n or n.startswith("ara mes") or "frente amplio" in n or n.startswith("sumar"):
        return "SPACE_FA"
    rules = [("podemos", "PODEMOS"), ("psoe", "PSOE"), ("upn", "PP"), ("pp ", "PP"), (" pp", "PP"), ("vox", "VOX"), ("salf", "SALF"),
             ("se acabo", "SALF"), ("erc", "ERC"), ("esquerra", "ERC"), ("junts", "JUNTS"), ("jxcat", "JUNTS"), ("pnv", "PNV"),
             ("bildu", "BILDU"), ("coalicion canaria", "CC"), ("cca", "CC"), ("bng", "BNG"), ("adelante", "ADELANTE")]
    if n.strip() in ("pp", "cc"):
        return {"pp": "PP", "cc": "CC"}[n.strip()]
    for k, v in rules:
        if k in " " + n + " ":
            return v
    if n.strip().startswith("otro") or "teruel" in n or "soria" in n or "drago" in n:
        return "OTH"
    return None          # blanco, nulo, no votaría, no sabe, no contesta…

def rec_party(lbl):
    n = norm(lbl)
    if n.strip() == "sumar" or n.startswith("sumar"): return "SUMAR"
    if "nueva canarias" in n: return "SUMAR"           # en Canarias NC va hoy dentro de UPC
    rules = [("psoe", "PSOE"), ("upn", "PP"), ("vox", "VOX"), ("erc", "ERC"), ("esquerra", "ERC"), ("junts", "JUNTS"),
             ("pnv", "PNV"), ("bildu", "BILDU"), ("coalicion canaria", "CC"), ("bng", "BNG")]
    if n.strip() in ("pp",) or n.startswith("pp "): return "PP"
    if n.strip() == "cc": return "CC"
    for k, v in rules:
        if k in " " + n + " ": return v
    if n.strip().startswith("otro") or "cup" in n or "vaciada" in n or "upl" in n: return "OTH"
    return None

def load_house(files, geo, w, cur_vars, rec_var):
    rows = []
    for f in files:
        df, m = pyreadstat.read_sav(f)
        L = m.variable_value_labels
        cur = None
        for v in cur_vars:
            if v in df.columns:
                c = df[v].map(lambda x, v=v: cur_party(L[v].get(x, "")) if pd.notna(x) else None)
                cur = c if cur is None else cur.where(cur.notna(), c)
        rec = df[rec_var].map(lambda x: rec_party(L[rec_var].get(x, "")) if pd.notna(x) else None)
        rows.append(pd.DataFrame({"ccaa": df[geo].map(lambda x: ccaa_name(L[geo].get(x, ""))), "w": df[w], "cur": cur, "rec": rec}))
    return pd.concat(rows, ignore_index=True)

houses = {}
f40 = [f for f in glob.glob("/home/claude/raw2/**/03_Datos_*.sav", recursive=True) if "MACOSX" not in f and "Flash" not in f]
houses["40dB"] = load_house(f40, "ccaa", "ponde", ["p3", "p4"], "p6")
fmic = glob.glob("/home/claude/raw2/microdatos-2026-*/*.sav")
houses["More in Common"] = load_house(fmic, "comunidad_autonoma", "peso", ["intencion_voto_simpatia"], "voto_2023_final")

# CIS barómetros ene–sep 2026 (microdatos): se suman a la casa CIS con medio peso (son más antiguos que el 3584)
W_BAR = 0.5
NOWB = {1: "PSOE", 2: "PP", 3: "VOX", 21: "SPACE_FA", 29: "SPACE_FA", 8: "PODEMOS", 28: "SALF", 101: "ADELANTE", 503: "CC",
        901: "ERC", 902: "JUNTS", 1201: "BNG", 1501: "PP", 1601: "PNV", 1602: "BILDU", 6: "OTH", 8995: "OTH"}
RECB = {1: "PSOE", 2: "PP", 3: "VOX", 21: "SUMAR", 901: "ERC", 902: "JUNTS", 1201: "BNG", 503: "CC", 1501: "PP",
        1601: "PNV", 1602: "BILDU", 6: "OTH", 8995: "OTH"}
_bar = []
for f in sorted(glob.glob("/home/claude/cisraw/MD*/*.sav")):
    d_, m_ = pyreadstat.read_sav(f, usecols=["CCAA", "VOTOSIMG", "RECUVOTOGR", "PESOCCAA"])
    lab = m_.variable_value_labels["CCAA"]
    _bar.append(pd.DataFrame({"ccaa": d_.CCAA.map(lambda x: ccaa_name(lab.get(x, ""))), "w": d_.PESOCCAA,
                              "cur": d_.VOTOSIMG.map(NOWB), "rec": d_.RECUVOTOGR.map(RECB)}))
BAR = pd.concat(_bar, ignore_index=True)
N_BAR = len(BAR)

# CIS 3584: tablas por provincia -> se agregan a comunidad con el N de cada provincia
cur3 = pd.read_csv(OUT + "cis3584_voto_prov.csv", dtype={0: str}, index_col=0)
rec3 = pd.read_csv(OUT + "cis3584_recuerdo_prov.csv", dtype={0: str}, index_col=0)
p2c_cis = pd.read_csv(OUT + "prov_ccaa.csv", index_col=0).CCAA
_, meta = pyreadstat.read_sav("/home/claude/cisraw/MD3577/3577.sav", metadataonly=True)
cisname = {int(k): ccaa_name(v) for k, v in meta.variable_value_labels["CCAA"].items()}
prov_ccaa = pd.Series({f"{int(p):02d}": cisname[int(c)] for p, c in p2c_cis.items()})
cur3["SPACE_FA"] = cur3["FA"]; cur3 = cur3.drop(columns=["FA"])

PARTIES = ["PP", "PSOE", "VOX", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC"]
def shares_by_ccaa(h, barometros=True):
    if h == "CIS":
        N = cur3["N"]; g = prov_ccaa.reindex(cur3.index)
        c = cur3.drop(columns="N").mul(N, axis=0).groupby(g).sum(); r = rec3.drop(columns="N").mul(rec3["N"], axis=0).groupby(g).sum()
        nc = cur3.drop(columns="N").mul(N, axis=0).groupby(g).sum(); nr = rec3.drop(columns="N").mul(rec3["N"], axis=0).groupby(g).sum()
        if barometros:
            D = BAR
            # PESOCCAA suma aprox. el número de entrevistas: se usa como recuento, con medio peso
            cb = D[D.cur.notna()].pivot_table(index="ccaa", columns="cur", values="w", aggfunc="sum").fillna(0) * W_BAR
            rb = D[D.rec.notna()].pivot_table(index="ccaa", columns="rec", values="w", aggfunc="sum").fillna(0) * W_BAR
            ncb = D[D.cur.notna()].pivot_table(index="ccaa", columns="cur", values="w", aggfunc="count").fillna(0) * W_BAR
            nrb = D[D.rec.notna()].pivot_table(index="ccaa", columns="rec", values="w", aggfunc="count").fillna(0) * W_BAR
            c = c.add(cb, fill_value=0); r = r.add(rb, fill_value=0); nc = nc.add(ncb, fill_value=0); nr = nr.add(nrb, fill_value=0)
    else:
        D = houses[h]
        c = D[D.cur.notna()].pivot_table(index="ccaa", columns="cur", values="w", aggfunc="sum").fillna(0)
        r = D[D.rec.notna()].pivot_table(index="ccaa", columns="rec", values="w", aggfunc="sum").fillna(0)
        nc = D[D.cur.notna()].pivot_table(index="ccaa", columns="cur", values="w", aggfunc="count").fillna(0)
        nr = D[D.rec.notna()].pivot_table(index="ccaa", columns="rec", values="w", aggfunc="count").fillna(0)
    for t in (c, nc):
        t["SPACE"] = t.get("SPACE_FA", 0) + t.get("PODEMOS", 0)
    return c, r, nc, nr

rel, podfrac, small, ns, npod = {}, {}, {}, {}, {}
for h in ["CIS", "40dB", "More in Common"]:
    c, r, nc, nr = shares_by_ccaa(h)
    cs = c.div(c.drop(columns=["SPACE"]).sum(axis=1), axis=0); rs = r.div(r.sum(axis=1), axis=0)
    cn = c.sum(); rn = r.sum(); csn = cn / cn.drop("SPACE").sum(); rsn = rn / rn.sum()
    out = {}
    for q in PARTIES + ["SPACE"]:
        rq = "SUMAR" if q == "SPACE" else q
        if q not in cs or rq not in rs: continue
        f = (cs[q] / rs[rq].replace(0, np.nan)); fn = csn[q] / rsn[rq]
        lam = nr[rq] / (nr[rq] + K)
        out[q] = ((f / fn).clip(0.2, 5) ** lam).where(rs[rq] > 0)
    for q in ["SALF", "ADELANTE"]:
        if q in cs:
            out[q] = ((cs[q] / csn[q]).clip(0.1, 10) ** (nc[q] / (nc[q] + K))) if csn[q] > 0 else None
    rel[h] = pd.DataFrame(out)
    runs = [x for x in c.index if x not in PODEMOS_NO]
    fr = (c["PODEMOS"] / c["SPACE"]).where(c.index.isin(runs))
    frn = c.loc[runs, "PODEMOS"].sum() / c.loc[runs, "SPACE"].sum()
    lo = np.log(fr / (1 - fr)) - np.log(frn / (1 - frn))
    podfrac[h] = lo.clip(-3, 3).where(c.index.isin(runs))
    npod[h] = nc["PODEMOS"].where(c.index.isin(runs))
    ns[h] = int(nr.sum().sum()) if h != "CIS" else int(rec3["N"].sum())

ccaa_all = sorted(set().union(*[set(x.index) for x in rel.values()]))
comb = pd.concat([np.log(rel[h].reindex(ccaa_all)) for h in rel], keys=list(rel)).groupby(level=1).mean()
comb = np.exp(comb)
# Podemos: media de las casas ponderada por sus votantes de Podemos en cada comunidad
_lo = pd.concat([podfrac[h].reindex(ccaa_all) for h in podfrac], axis=1, keys=list(podfrac))
_n = pd.concat([npod[h].reindex(ccaa_all) for h in npod], axis=1, keys=list(npod)).where(_lo.notna())
pod_lo = (_lo * _n).sum(axis=1) / _n.sum(axis=1)
pod_n = _n.sum(axis=1)

# detalle provincial del CIS dentro de cada comunidad (provincia / su comunidad), encogido
c_c, r_c, _, _ = shares_by_ccaa("CIS", barometros=False)
cs_c = c_c.div(c_c.drop(columns=["SPACE"]).sum(axis=1), axis=0); rs_c = r_c.div(r_c.sum(axis=1), axis=0)
cp = cur3.drop(columns="N"); cp["SPACE"] = cp["SPACE_FA"] + cp["PODEMOS"]; cp = cp.div(cp.drop(columns=["SPACE"]).sum(axis=1), axis=0)
rp = rec3.drop(columns="N"); rp = rp.div(rp.sum(axis=1), axis=0)
det = {}
for q in PARTIES + ["SPACE"]:
    rq = "SUMAR" if q == "SPACE" else q
    fprov = cp[q] / rp[rq].replace(0, np.nan)
    fcc = (cs_c[q] / rs_c[rq].replace(0, np.nan)).reindex(prov_ccaa.reindex(cp.index)).values
    lam = (rp[rq] * rec3["N"]) / (rp[rq] * rec3["N"] + K)
    det[q] = ((fprov / fcc).clip(0.33, 3) ** lam).fillna(1.0)
for q in ["SALF", "ADELANTE"]:
    sh = cur3[q]; shc = (cs_c[q]).reindex(prov_ccaa.reindex(cp.index)).values
    lam = (sh * cur3["N"]) / (sh * cur3["N"] + K)
    det[q] = ((sh / pd.Series(shc, index=sh.index).replace(0, np.nan)).clip(0.2, 5) ** lam).fillna(1.0)
fr_p = (cur3["PODEMOS"] / (cur3["SPACE_FA"] + cur3["PODEMOS"])); fr_c = (c_c["PODEMOS"] / c_c["SPACE"]).reindex(prov_ccaa.reindex(cp.index)).values
lo_p = (np.log(fr_p / (1 - fr_p)) - np.log(fr_c / (1 - fr_c))).replace([np.inf, -np.inf], np.nan)
lam = (cur3["PODEMOS"] * cur3["N"]) / (cur3["PODEMOS"] * cur3["N"] + K)      # encogido por votantes de Podemos en la provincia
det_pod = (lo_p.clip(-2, 2) * lam).fillna(0)

comb.to_csv(OUT + "territorial_ccaa.csv"); pd.DataFrame({"logodds": pod_lo, "n_podemos": pod_n}).to_csv(OUT + "territorial_podemos_ccaa.csv")
pd.DataFrame(det).assign(POD_LO=det_pod, CCAA=prov_ccaa.reindex(cp.index)).to_csv(OUT + "territorial_detalle_prov.csv")
print("entrevistas por casa (con recuerdo):", ns, "| barómetros CIS leídos:", N_BAR, "(peso", W_BAR, ")")
print("Podemos, votantes por comunidad (todas las casas):", pod_n.round(0).dropna().astype(int).to_dict())
print("Madrid, índice territorial por casa:")
print(pd.DataFrame({h: rel[h].loc["Madrid"] for h in rel}).round(2).to_string())
print("Podemos dentro del espacio (log-odds frente a su media, Madrid):", {h: round(podfrac[h].get("Madrid", np.nan), 2) for h in podfrac}, "combinado", round(pod_lo.get("Madrid"), 2))
