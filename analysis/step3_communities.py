"""Q2 step 1: communities (Louvain modularity) vs. time zones."""
import pandas as pd, networkx as nx, numpy as np
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
import os
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
D = os.path.join(HERE, "..", "airlink_app", "app_data") + os.sep
ap = pd.read_csv(D + "airports.csv"); rt = pd.read_csv(D + "routes.csv")
G = nx.Graph(); G.add_nodes_from(ap.iata); G.add_edges_from(zip(rt.src, rt.dst))

# Louvain is randomized: run 20 seeds, keep the highest-modularity partition, report stability
runs = []
for seed in range(20):
    C = nx.community.louvain_communities(G, seed=seed, resolution=1.0)
    runs.append((nx.community.modularity(G, C), seed, C))
runs.sort(key=lambda x: -x[0]); Q, seed, C = runs[0]
lab = {n: i for i, c in enumerate(sorted(C, key=len, reverse=True)) for n in c}
ap["community"] = ap.iata.map(lab)
print(f"best modularity Q = {Q:.3f} (seed {seed}); range over 20 seeds: {runs[-1][0]:.3f}-{runs[0][0]:.3f}")
print("communities:", len(C), " sizes:", sorted([len(c) for c in C], reverse=True))
# stability: how similar are partitions across seeds?
labs = [[{n: i for i, c in enumerate(r[2]) for n in c}[x] for x in ap.iata] for r in runs]
print(f"mean NMI between seed partitions: {np.mean([normalized_mutual_info_score(labs[0], l) for l in labs[1:]]):.3f}")

# time zones as the geographic comparison
tz = ap.tzdb.fillna("unknown")
print(f"\nvs time zones:  NMI = {normalized_mutual_info_score(tz, ap.community):.3f}   ARI = {adjusted_rand_score(tz, ap.community):.3f}")
print(f"vs region (L48/AK/HI): NMI = {normalized_mutual_info_score(ap.region, ap.community):.3f}")

# describe each community: size, biggest hubs, dominant time zone and its share
rows = []
for k, g in ap.groupby("community"):
    hubs = g.nlargest(4, "degree").iata.tolist()
    top_tz = g.tzdb.value_counts()
    rows.append(dict(community=k, airports=len(g), hubs=" ".join(hubs),
                     main_timezone=top_tz.index[0].replace("America/", "").replace("Pacific/", ""),
                     tz_share=round(top_tz.iloc[0] / len(g), 2),
                     states_hint=" ".join(g.nlargest(6, "degree").city.str.split().str[0].tolist())))
desc = pd.DataFrame(rows); print("\n" + desc.to_string(index=False))
# share of routes inside vs between communities
inside = sum(lab[u] == lab[v] for u, v in G.edges()); print(f"\nroutes inside a community: {inside}/{G.number_of_edges()} ({100*inside/G.number_of_edges():.0f}%)")
ap[["iata", "community"]].to_csv("communities.csv", index=False); desc.to_csv("community_summary.csv", index=False)
