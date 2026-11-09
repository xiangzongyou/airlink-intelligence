"""Minimal TopoJSON -> lon/lat rings decoder (states only), so the figure needs no extra libraries."""
import json, numpy as np
def states_lonlat(path):
    T = json.load(open(path)); sx, sy = T["transform"]["scale"]; tx, ty = T["transform"]["translate"]
    arcs = []
    for a in T["arcs"]:
        xy = np.cumsum(np.array(a, dtype=float), axis=0); arcs.append(np.c_[xy[:, 0] * sx + tx, xy[:, 1] * sy + ty])
    def ring(ix): return np.vstack([arcs[i] if i >= 0 else arcs[~i][::-1] for i in ix])
    out = []
    for g in T["objects"]["states"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        for p in polys:
            r = ring(p[0]); r[r[:, 0] > 0, 0] -= 360; out.append(r)
    return out
