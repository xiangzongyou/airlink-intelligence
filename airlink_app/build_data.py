"""Prepare data for the AirLink Intelligence Streamlit app.

Downloads OpenFlights (2014 snapshot), applies the project's cleaning rules, and writes
small CSVs to app_data/:
  airports.csv        one row per US airport: location, region, degree, betweenness, ranks
  routes.csv          one row per undirected airport pair, with operating airline codes
  single_closure.csv  impact of closing each airport alone (Q1: detours vs. loss of access)
  robustness.csv      Level 1 curves: random / degree / betweenness closures, all US and Lower 48

Run once:  python build_data.py   (about 1-2 minutes)
"""
import os, random, urllib.request
os.chdir(os.path.dirname(os.path.abspath(__file__)))   # write app_data/ next to this script
import numpy as np, pandas as pd, networkx as nx
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path

BASE = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/"
RAW, OUT = "raw", "app_data"
os.makedirs(RAW, exist_ok=True); os.makedirs(OUT, exist_ok=True)
for f in ["routes.dat", "airports.dat", "airports-extended.dat", "airlines.dat"]:
    if not os.path.exists(f"{RAW}/{f}"):
        print("downloading", f); urllib.request.urlretrieve(BASE + f, f"{RAW}/{f}")

AP_COLS = ["id","name","city","country","iata","icao","lat","lon","alt","tz","dst","tzdb","type","source"]
a  = pd.read_csv(f"{RAW}/airports.dat", header=None, na_values="\\N", names=AP_COLS)
ax = pd.read_csv(f"{RAW}/airports-extended.dat", header=None, na_values="\\N", names=AP_COLS)
# main airport file first; extended file fills airports missing from it (proposal fallback)
ap = pd.concat([a, ax]).dropna(subset=["iata"]).drop_duplicates("iata").set_index("iata")

r = pd.read_csv(f"{RAW}/routes.dat", header=None, na_values="\\N",
                names=["airline","airline_id","src","src_id","dst","dst_id","codeshare","stops","equip"])
r = r[r.stops == 0].copy()
r["src_c"], r["dst_c"] = r.src.map(ap.country), r.dst.map(ap.country)
dom = r[(r.src_c == "United States") & (r.dst_c == "United States") & (r.src != r.dst)]

# ---- cleaning rules (see project notes) ----
SIGHTSEEING = {frozenset(("BLD","GCW")), frozenset(("GCN","PGA"))}   # helicopter / scenic tours
CARGO_ONLY  = {(frozenset(("ATL","DFW")), "CI")}                       # China Airlines freighter leg
dom = dom[~dom.apply(lambda x: frozenset((x.src, x.dst)) in SIGHTSEEING, axis=1)]
dom = dom[~dom.apply(lambda x: (frozenset((x.src, x.dst)), x.airline) in CARGO_ONLY, axis=1)]

# ---- graph ----
pairs = dom.assign(a1=dom[["src","dst"]].min(axis=1), a2=dom[["src","dst"]].max(axis=1))
routes = (pairs.groupby(["a1","a2"])
          .agg(airlines=("airline", lambda s: " ".join(sorted(set(s.dropna())))),
               records=("airline","size"),
               codeshare_only=("codeshare", lambda s: bool((s == "Y").all())))
          .reset_index().rename(columns={"a1":"src","a2":"dst"}))
G = nx.Graph(); G.add_edges_from(zip(routes.src, routes.dst))

def region(lat, lon):
    if lat > 51 and lon < -129: return "Alaska"
    if lat < 24 or lon < -150:  return "Hawaii/Pacific"
    return "Lower 48"

deg = dict(G.degree()); btw = nx.betweenness_centrality(G)
airports = pd.DataFrame({"iata": list(G)})
for col in ["name","city","lat","lon","tzdb"]:
    airports[col] = airports.iata.map(ap[col])
airports["region"] = [region(la, lo) for la, lo in zip(airports.lat, airports.lon)]
airports["degree"] = airports.iata.map(deg)
airports["betweenness"] = airports.iata.map(btw).round(5)
airports["degree_rank"] = airports.degree.rank(ascending=False, method="min").astype(int)
airports["betweenness_rank"] = airports.betweenness.rank(ascending=False, method="min").astype(int)
main = max(nx.connected_components(G), key=len)
airports["in_main_network"] = airports.iata.isin(main)

# ---- Q1: impact of closing each airport alone ----
idx = {n: i for i, n in enumerate(airports.iata)}
n = len(idx)
rows = [idx[s] for s in routes.src] + [idx[d] for d in routes.dst]
cols = [idx[d] for d in routes.dst] + [idx[s] for s in routes.src]
A = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
D0 = shortest_path(A, unweighted=True, directed=False)
main_mask = airports.in_main_network.values
iu = np.triu_indices(n, 1)

def closure_impact(closed):
    keep = np.ones(n, bool); keep[list(closed)] = False
    D1 = np.full((n, n), np.inf)
    sub = np.where(keep)[0]
    D1[np.ix_(sub, sub)] = shortest_path(A[sub][:, sub], unweighted=True, directed=False)
    valid = keep[iu[0]] & keep[iu[1]] & np.isfinite(D0[iu])
    d0, d1 = D0[iu][valid], D1[iu][valid]
    lost = np.isinf(d1); det = (~lost) & (d1 > d0)
    comps = nx.connected_components(G.subgraph(airports.iata.values[sub]))
    biggest = max(comps, key=len, default=set())
    cut = [airports.iata[i] for i in sub if main_mask[i] and airports.iata[i] not in biggest]
    return dict(trips_total=int(valid.sum()), trips_lost=int(lost.sum()),
                trips_detoured=int(det.sum()),
                mean_extra_connections=round(float((d1[det] - d0[det]).mean()), 2) if det.any() else 0.0,
                airports_cut_off=len(cut), cut_off_list=" ".join(sorted(cut)))

print("computing single-closure impacts ...")
sc = []
for code, i in idx.items():
    d = closure_impact([i]); d["iata"] = code; sc.append(d)
sc = pd.DataFrame(sc)
sc["pct_trips_lost"] = (100 * sc.trips_lost / sc.trips_total).round(3)
sc["pct_trips_detoured"] = (100 * sc.trips_detoured / sc.trips_total).round(3)
sc["main_effect"] = np.select([sc.trips_lost > 0, sc.trips_detoured > 0],
                              ["Loss of access", "Detours only"], "No change")
sc.to_csv(f"{OUT}/single_closure.csv", index=False)

# ---- Level 1 robustness curves ----
print("computing robustness curves ...")
def curves(H0, steps=60, seeds=30):
    N = H0.number_of_nodes()
    lcc = lambda H: max((len(c) for c in nx.connected_components(H)), default=0) / N
    def run(kind, seed=0):
        H = H0.copy(); order = list(H); random.Random(seed).shuffle(order); L = [lcc(H)]
        for k in range(steps):
            if kind == "random": v = order[k]
            elif kind == "degree": v = max(H.degree, key=lambda x: x[1])[0]
            else: b = nx.betweenness_centrality(H); v = max(b, key=b.get)
            H.remove_node(v); L.append(lcc(H))
        return np.array(L)
    return {"Random (mean of 30)": np.mean([run("random", s) for s in range(seeds)], 0),
            "Highest degree first": run("degree"),
            "Highest betweenness first": run("betweenness")}
lower = G.subgraph(airports[airports.region == "Lower 48"].iata)
lower = lower.subgraph(max(nx.connected_components(lower), key=len)).copy()
rob = []
for scope, H in [("All US domestic", G), ("Lower 48 only", lower)]:
    for strat, L in curves(H).items():
        rob += [{"scope": scope, "strategy": strat, "airports_closed": k, "pct_in_largest_component": round(100 * v, 2)}
                for k, v in enumerate(L)]
pd.DataFrame(rob).to_csv(f"{OUT}/robustness.csv", index=False)

airports.to_csv(f"{OUT}/airports.csv", index=False)
routes.to_csv(f"{OUT}/routes.csv", index=False)
print(f"done: {len(airports)} airports, {len(routes)} routes -> {OUT}/")
