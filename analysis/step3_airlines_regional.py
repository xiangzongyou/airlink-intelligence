"""Q2 step 2: which airlines define/bridge communities; national vs. regional impact of each closure."""
import pandas as pd, networkx as nx, numpy as np
import os
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
D = os.path.join(HERE, "..", "airlink_app", "app_data") + os.sep
ap = pd.read_csv(D + "airports.csv").merge(pd.read_csv("communities.csv"), on="iata")
rt = pd.read_csv(D + "routes.csv").fillna({"airlines": ""})
sc = pd.read_csv(D + "single_closure.csv").fillna({"cut_off_list": ""})
com = ap.set_index("iata").community
NAMES = {"DL": "Delta", "US": "US Airways", "AA": "American", "UA": "United", "WN": "Southwest", "AS": "Alaska Airlines",
         "B6": "JetBlue", "F9": "Frontier", "NK": "Spirit", "G4": "Allegiant", "VX": "Virgin America", "HA": "Hawaiian"}
rt["c1"], rt["c2"] = rt.src.map(com), rt.dst.map(com)
rt["inside"] = rt.c1 == rt.c2
ex = rt.assign(al=rt.airlines.str.split()).explode("al")
big = ex[ex.al.isin(NAMES)]
print("== Lower-48 communities: top airlines on routes INSIDE each community ==")
for k in [0, 1, 2, 5]:
    s = big[big.inside & (big.c1 == k)].al.value_counts()
    tot = rt[rt.inside & (rt.c1 == k)].shape[0]
    print(f"community {k}: " + ", ".join(f"{NAMES[a]} {100*n/tot:.0f}%" for a, n in s.head(4).items()) + f"  (of {tot} routes)")
print("\n== airlines bridging communities (share of each airline's routes that cross between communities) ==")
g = big.groupby("al").agg(routes=("inside", "size"), crossing=("inside", lambda x: (~x).sum()))
g["pct_crossing"] = (100 * g.crossing / g.routes).round(0)
print(g.sort_values("crossing", ascending=False).rename(index=NAMES).head(8).to_string())

# ---- national vs regional impact of single closures ----
size = ap.community.value_counts()
def worst_region(cut_list):
    if not cut_list: return (None, 0, 0.0)
    cnt = pd.Series([com[c] for c in cut_list.split()]).value_counts()
    k = (cnt / size[cnt.index]).idxmax()
    return (int(k), int(cnt[k]), float(cnt[k] / size[k]))
r = sc.merge(ap[["iata", "city", "region", "degree", "community"]], on="iata")
r[["worst_comm", "cut_in_comm", "regional_share"]] = r.cut_off_list.apply(lambda x: pd.Series(worst_region(x)))
r = r[r.airports_cut_off > 0].copy()
r["regional_pct"] = (100 * r.regional_share).round(1)
# "minor nationally, severe regionally": < 1% of national trips lost, >= 10% of one community cut off
r["flag"] = (r.pct_trips_lost < 1) & (r.regional_pct >= 10)
print(f"\n== {len(r)} closures cut someone off; {r.flag.sum()} are minor nationally (<1% trips lost) but cut off >=10% of a community ==")
cols = ["iata", "city", "region", "degree", "pct_trips_lost", "airports_cut_off", "worst_comm", "cut_in_comm", "regional_pct"]
print(r[r.flag].sort_values("regional_pct", ascending=False)[cols].head(15).to_string(index=False))
print("\nfor contrast, the nationally biggest closures:")
print(r.sort_values("pct_trips_lost", ascending=False)[cols].head(6).to_string(index=False))
r.to_csv("q2_regional_impact.csv", index=False)

# ---- regional impact restricted to real regions (communities with >= 20 airports) ----
# Tiny communities are excluded: losing 1 of 3 airports would read as 33%.
names = {0: "West (DEN/LAS/LAX/SLC)", 1: "East Coast (CLT/PHL/DCA)", 2: "Midwest-Southeast (ATL/ORD/MSP/DTW)",
         3: "Interior/North Alaska (ANC/FAI)", 4: "Yukon-Kuskokwim, AK (BET)", 5: "Texas (DFW/IAH)", 6: "Southeast Alaska (JNU/KTN)"}
big = set(size[size >= 20].index)
def per_comm(lst):
    out = {}
    for c in (lst.split() if isinstance(lst, str) else []):
        k = com[c]
        if k in big: out[k] = out.get(k, 0) + 1
    if not out: return pd.Series([None, 0, 0.0])
    k = max(out, key=lambda x: out[x] / size[x]); return pd.Series([k, out[k], round(100 * out[k] / size[k], 1)])
rb = pd.read_csv("q2_regional_impact.csv")
rb[["comm", "cut_in", "reg_pct"]] = rb.cut_off_list.apply(per_comm)
rb = rb[rb.cut_in > 0].copy(); rb["ratio"] = (rb.reg_pct / rb.pct_trips_lost).round(1)
rb["region_name"] = rb.comm.map(names)
print("\n== closures ranked by how much worse they are for one region than for the nation ==")
print(rb.sort_values("ratio", ascending=False)[["iata", "city", "degree", "pct_trips_lost", "region_name", "cut_in", "reg_pct", "ratio"]].head(12).to_string(index=False))
rb.to_csv("q2_regional_impact_big.csv", index=False)
