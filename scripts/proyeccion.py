"""Proyección de escaños con la media ponderada del último día.

Dos versiones:
  resultados  · base = resultado del 23J por provincia; Podemos con su mapa de las europeas de 2024 y FA + aliados
                con el resto del espacio de Sumar 2023 (las europeas no reparten a Sumar).
  micro       · base corregida con el patrón territorial de los microdatos (CIS 3584, 40dB, More in Common),
                y barómetros del CIS de ene–sep 2026 con medio peso), ficheros de datos/territorial/
                (se generan aparte con territorial.py cuando hay microdatos nuevos).
                FA + Podemos se proyectan como un único espacio y luego se reparten: el peso de Podemos en cada
                territorio sale de los microdatos, encogido hacia su mapa de las europeas cuando hay pocos votantes de Podemos.
Traslado logístico a la media nacional, D'Hondt con barrera del 3 % y escaños de 2026, y simulaciones de Monte Carlo.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit, logit

sys.path.insert(0, os.path.dirname(__file__))
from comun import NOMBRES, SALIDA, TERR, TRABAJO, config
from escanos import C26, DATA, EP, base_table, dhondt, project

TP = ["PP", "PSOE", "VOX", "FA", "PODEMOS", "SALF", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC", "ADELANTE"]
LABEL = {"ADELANTE": "AA"}
K_POD = 150     # votantes de Podemos «ficticios» que pesa su mapa de las europeas frente a los microdatos
BLOQUES = {
    "PP + Vox": ["PP", "VOX"],
    "PP + Vox + SALF": ["PP", "VOX", "SALF"],
    "PSOE + FA + Podemos": ["PSOE", "FA", "PODEMOS"],
    "Bloque de la investidura de 2023": ["PSOE", "FA", "PODEMOS", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC"],
}


def preparar():
    cand = pd.read_csv(DATA + "candidacies_2026.csv", dtype={"code": str})
    runs = cand.groupby("label").code.apply(set).to_dict()
    runs["FA"] = runs.get("FA", set()) | runs.get("FV", set())
    s, valid, _ = base_table("2023")
    codes = list(C26.code)
    s = s.reindex(codes).fillna(0)
    valid = valid.reindex(codes)
    seats = C26.set_index("code").seats
    return runs, s, valid, codes, seats


def base_resultados(runs, s, codes):
    ep = EP.pivot_table(index="code", columns="label", values="votes", aggfunc="sum").fillna(0).reindex(codes).fillna(0)
    ep_sh = ep.div(ep.sum(axis=1), axis=0)
    b = pd.DataFrame(index=codes)
    for p in ["PP", "PSOE", "VOX", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC", "BLANCO"]:
        b[p] = s[p]
    b["PP"] += s["UPN"]
    pod_runs = pd.Series([c in runs["PODEMOS"] for c in codes], index=codes)
    # Podemos parte de su propio mapa en las europeas de 2024 (lo único que hay de Podemos solo);
    # el resto del espacio de Sumar 2023 es FA + aliados. Las europeas no se usan para repartir a Sumar.
    space = s.SUMAR + np.where(b.index.isin(["35", "38"]), s.NC, 0)
    b["PODEMOS"] = np.where(pod_runs, np.minimum(ep_sh.PODEMOS, 0.75 * space), 0)
    b["FA"] = space - b["PODEMOS"]
    b["SALF"] = ep_sh.SALF
    b["ADELANTE"] = s.SUMAR * 0.5
    b["OTH"] = s.drop(columns=[c for c in s.columns if c in b.columns or c in ("UPN", "SUMAR", "NC", "AA")]).sum(axis=1)
    for p in [c for c in b.columns if c not in ("BLANCO", "OTH")]:
        lab = LABEL.get(p, p)
        if lab in runs:
            no = [c for c in codes if c not in runs[lab]]
            b.loc[no, "OTH"] += b.loc[no, p]
            b.loc[no, p] = 0
    return b.div(b.sum(axis=1), axis=0)


def base_micro(runs, s, codes, med):
    comb = pd.read_csv(TERR / "territorial_ccaa.csv", index_col=0)
    podlo = pd.read_csv(TERR / "territorial_podemos_ccaa.csv", index_col=0)
    det = pd.read_csv(TERR / "territorial_detalle_prov.csv", dtype={0: str}, index_col=0)
    det.index = det.index.astype(str).str.zfill(2)
    det = det.reindex(codes)
    rg = det.CCAA

    def idx(q):
        a = pd.Series([comb.loc[r, q] if (r in comb.index and q in comb.columns and pd.notna(comb.loc[r, q])) else 1.0 for r in rg], index=codes)
        return a * (det[q].fillna(1.0) if q in det.columns else 1.0)

    s23 = s.copy()
    s23["PP"] = s23["PP"] + s23["UPN"]
    b2 = pd.DataFrame(index=codes)
    for p in ["PP", "PSOE", "VOX", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC"]:
        b2[p] = s23[p] * idx(p)
    b2["SPACE"] = (s23["SUMAR"] + np.where(s23.index.isin(["35", "38"]), s23["NC"], 0)) * idx("SPACE")
    for p in ["SALF", "ADELANTE"]:
        b2[p] = med[p] / 100 * idx(p)
    b2["BLANCO"] = s23["BLANCO"]
    b2["OTH"] = (1 - b2.sum(axis=1)).clip(lower=0.01)
    space_runs = pd.Series([(c in runs["FA"]) or (c in runs["PODEMOS"]) for c in codes], index=codes)
    for p in [c for c in b2.columns if c not in ("BLANCO", "OTH")]:
        if p == "SPACE":
            no = [c for c in codes if not space_runs[c]]
        else:
            lab = LABEL.get(p, p)
            no = [c for c in codes if c not in runs[lab]] if lab in runs else []
        b2.loc[no, "OTH"] += b2.loc[no, p]
        b2.loc[no, p] = 0
    # Podemos dentro del espacio: microdatos (comunidad + detalle provincial del CIS), encogidos hacia su mapa
    # de las europeas de 2024 según cuántos votantes de Podemos hay en los microdatos de esa comunidad
    micro_lo = pd.Series([podlo.logodds.get(r, np.nan) for r in rg], index=codes)
    n_pod = pd.Series([podlo.n_podemos.get(r, 0) for r in rg], index=codes).fillna(0)
    lam = n_pod / (n_pod + K_POD)
    ep = EP.pivot_table(index="code", columns="label", values="votes", aggfunc="sum").fillna(0).reindex(codes).fillna(0)
    ep_sh = ep.div(ep.sum(axis=1), axis=0).PODEMOS
    space23 = s23["SUMAR"] + np.where(s23.index.isin(["35", "38"]), s23["NC"], 0)
    f_ep = (ep_sh / space23).clip(0.02, 0.98)
    pod_ok = pd.Series([c in runs["PODEMOS"] and c in runs["FA"] for c in codes], index=codes)
    wv = (space23 * pod_ok).fillna(0)
    lo_ep = np.log(f_ep / (1 - f_ep))
    lo_ep = (lo_ep - (lo_ep * wv).sum() / wv.sum()).where(pod_ok, 0)
    lo_micro = (micro_lo.fillna(0) + det["POD_LO"].fillna(0))
    pod_l = (lam * lo_micro + (1 - lam) * lo_ep).fillna(0)
    return b2.div(b2.sum(axis=1), axis=0), pod_l


def proyectar(micro, cfg, runs, s, valid, codes, seats, med):
    target = {p: (med[p] if pd.notna(med[p]) else 0) / 100 for p in TP}
    if micro:
        b, pod_l = base_micro(runs, s, codes, med)
        tgt2 = {p: t for p, t in target.items() if p not in ("FA", "PODEMOS")}
        tgt2["SPACE"] = target["FA"] + target["PODEMOS"]
        proj = project(b, valid, tgt2, "logit")
        pod_ok = pd.Series([c in runs["PODEMOS"] for c in codes], index=codes)
        fa_ok = pd.Series([c in runs["FA"] for c in codes], index=codes)

        def frac(c0):
            f = expit(pod_l + c0).where(pod_ok, 0.0)
            return f.where(fa_ok, pod_ok.astype(float))

        wv = valid / valid.sum()
        c0 = brentq(lambda c: (wv * proj["SPACE"] * frac(c)).sum() - target["PODEMOS"], -12, 12)
        fr = frac(c0)
        proj["PODEMOS"] = proj["SPACE"] * fr
        proj["FA"] = proj["SPACE"] * (1 - fr)
        proj = proj.drop(columns="SPACE")
    else:
        proj = project(base_resultados(runs, s, codes), valid, target, "logit")

    central = pd.DataFrame({c: dhondt((proj.loc[c] * valid[c]).to_dict(), int(seats[c]), valid[c]) for c in codes}).T.fillna(0).astype(int)
    nat = central.sum().reindex(TP).fillna(0).astype(int)

    rng = np.random.default_rng(20261129)
    w = (valid / valid.sum()).values
    nsim = cfg.get("simulaciones", 10000)
    sims = np.zeros((nsim, len(TP)), int)
    lp = logit(np.clip(proj[TP].values, 1e-7, 1 - 1e-7))
    present = proj[TP].values > 1e-6
    tg = np.array([target[p] for p in TP])
    sd = np.array([2.0 * np.sqrt(min(target[p], 0.25) / 0.25) for p in TP]) / 100
    for k in range(nsim):
        e = rng.normal(0, sd)
        e -= e.sum() * (tg / tg.sum())
        x = lp + rng.normal(0, 0.10, lp.shape)
        sh = np.where(present, expit(x), 0)
        natv = (w[:, None] * sh).sum(axis=0)
        goal = np.clip(tg + e, 0.0005, None)
        sh = np.where(present, expit(x + logit(goal) - logit(np.clip(natv, 1e-7, None))), 0)
        tot = sh.sum(axis=1)
        sh *= np.where(tot > 0.995, 0.995 / tot, 1)[:, None]
        row = np.zeros(len(TP), int)
        for i, c in enumerate(codes):
            votes = {p: sh[i, j] * valid[c] for j, p in enumerate(TP)}
            votes["OTH"] = (1 - sh[i].sum()) * valid[c] * 0.9
            votes["BLANCO"] = (1 - sh[i].sum()) * valid[c] * 0.1
            r = dhondt(votes, int(seats[c]), valid[c])
            row += np.array([r[p] for p in TP])
        sims[k] = row
    S = pd.DataFrame(sims, columns=TP)
    partidos = sorted([{"party": p, "nombre": NOMBRES[p], "voto": round(100 * target[p], 2), "escanos": int(nat[p]),
                        "p05": int(S[p].quantile(.05)), "p50": int(S[p].median()), "p95": int(S[p].quantile(.95))} for p in TP],
                      key=lambda r: (-r["escanos"], -r["voto"]))
    bloques = []
    for nombre, ps in BLOQUES.items():
        tot = S[ps].sum(axis=1)
        bloques.append({"bloque": nombre, "partidos": " + ".join(NOMBRES[p] for p in ps), "escanos": int(nat[ps].sum()),
                        "p05": int(tot.quantile(.05)), "p95": int(tot.quantile(.95)), "prob176": round(100 * float((tot >= 176).mean()), 1)})
    return partidos, bloques, central


def main():
    cfg = config()
    med = pd.read_csv(TRABAJO / "media_ponderada_diaria.csv").iloc[-1]
    runs, s, valid, codes, seats = preparar()
    nom = C26.set_index("code").name
    out = {"fecha_media": med["date"]}
    centrales = {}
    for clave, micro in [("micro", True), ("resultados", False)]:
        partidos, bloques, central = proyectar(micro, cfg, runs, s, valid, codes, seats, med)
        centrales[clave] = central
        out[clave] = {"partidos": partidos, "bloques": bloques}
        print(clave, " · ".join(f"{r['nombre']} {r['escanos']}" for r in partidos if r["escanos"]), "| PP+Vox", bloques[0]["escanos"], f"({bloques[0]['prob176']} %)")
    provincias = []
    for c in codes:
        rep = lambda cen: {p: int(cen.loc[c, p]) for p in TP if p in cen.columns and cen.loc[c, p] > 0}
        a, b = rep(centrales["resultados"]), rep(centrales["micro"])
        cambios = {p: b.get(p, 0) - a.get(p, 0) for p in set(a) | set(b) if b.get(p, 0) != a.get(p, 0)}
        provincias.append({"code": c, "provincia": nom[c], "escanos": int(seats[c]), "micro": b, "resultados": a,
                           "cambios": ", ".join(f"{NOMBRES[p]} {'+' if v > 0 else '−'}{abs(v)}" for p, v in sorted(cambios.items(), key=lambda x: -x[1]))})
    out["provincias"] = provincias
    out["metodo"] = {"simulaciones": cfg.get("simulaciones", 10000), "barrera": "3 % por circunscripción",
                     "microdatos": "CIS 3584 (provincias), 40dB (7 oleadas) y More in Common (4 oleadas)"}
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "escanos.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
