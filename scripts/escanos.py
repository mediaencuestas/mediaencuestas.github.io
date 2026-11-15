"""Traslado de la media nacional a provincias + D'Hondt. Fase 1: solo resultados."""
import numpy as np, pandas as pd
from scipy.special import logit, expit
from scipy.optimize import brentq

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from comun import BASE
DATA = str(BASE) + "/"
R = pd.read_csv(DATA + "results.csv", dtype={"code": str})
S = pd.read_csv(DATA + "summary.csv", dtype={"code": str})
EP = pd.read_csv(DATA + "ep2024.csv", dtype={"code": str})
C26 = pd.read_csv(DATA + "constituencies_2026.csv", dtype={"code": str})


def base_table(election):
    """Proporción de voto válido (incluido el blanco) por provincia y partido."""
    v = R[R.election == election].pivot_table(index="code", columns="label", values="votes", aggfunc="sum").fillna(0)
    s = S[S.election == election].set_index("code")
    v["BLANCO"] = s.blank
    valid = s.valid.reindex(v.index)
    v["OTH"] = v.get("OTH", 0) + (valid - v.sum(axis=1)).clip(lower=0)   # cuadre con el total válido
    shares = v.div(valid, axis=0)
    seats = R[R.election == election].pivot_table(index="code", columns="label", values="seats", aggfunc="sum").fillna(0)
    return shares, valid, seats


def dhondt(votes, seats, valid, thr=0.03):
    """votes: dict partido->votos. Devuelve dict partido->escaños."""
    elig = {p: v for p, v in votes.items() if p not in ("BLANCO", "OTH") and v >= thr * valid and v > 0}
    out = {p: 0 for p in votes}
    if not elig:
        return out
    names = list(elig); vv = np.array([elig[p] for p in names], float)
    q = np.concatenate([vv / k for k in range(1, seats + 1)])
    owner = np.tile(np.arange(len(names)), seats)
    for i in owner[np.argsort(-q, kind="stable")[:seats]]:
        out[names[i]] += 1
    return out


def project(shares, valid, target, method="logit", iters=4):
    """Lleva las proporciones provinciales a los objetivos nacionales `target` (proporción del voto válido)."""
    s = shares.copy()
    w = valid / valid.sum()
    tgt = {p: t for p, t in target.items() if p in s.columns}
    for _ in range(iters):
        for p, t in tgt.items():
            x = s[p].values
            if method == "logit":
                m = x > 0
                if not m.any():
                    continue
                lx = logit(np.clip(x[m], 1e-6, 1 - 1e-6))
                f = lambda d: (w.values[m] * expit(lx + d)).sum() - t
                d = brentq(f, -15, 15)
                x = x.copy(); x[m] = expit(lx + d)
            elif method == "uniforme":
                cur = (w.values * x).sum(); x = np.clip(x + (t - cur) * (x > 0) / max(w.values[x > 0].sum(), 1e-9), 0, 1)
            elif method == "proporcional":
                cur = (w.values * x).sum(); x = x * (t / cur if cur > 0 else 0)
            s[p] = x
        # el resto de candidaturas se reescala para que cada provincia sume 1
        tcols = list(tgt); rest = [c for c in s.columns if c not in tcols]
        st = s[tcols].sum(axis=1); sr = s[rest].sum(axis=1)
        over = st > 0.995
        s.loc[over, tcols] = s.loc[over, tcols].div(st[over], axis=0) * 0.995
        st = s[tcols].sum(axis=1)
        s[rest] = s[rest].mul(((1 - st) / sr.replace(0, np.nan)).fillna(0), axis=0)
    return s


def seats_from_shares(s, valid, seats_by_code):
    rows = {}
    for code in s.index:
        votes = (s.loc[code] * valid[code]).to_dict()
        rows[code] = dhondt(votes, int(seats_by_code[code]), valid[code])
    return pd.DataFrame(rows).T.fillna(0).astype(int)
