"""Level 1: critical airports (degree vs betweenness) and robustness to closures.
Network: US domestic nonstop passenger routes (OpenFlights 2014), undirected, cleaned."""
import os; os.chdir(os.path.dirname(os.path.abspath(__file__))); os.makedirs("data", exist_ok=True); os.makedirs("out", exist_ok=True)

import pickle, random, numpy as np, pandas as pd, networkx as nx
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.stats import spearmanr

G = pickle.load(open("data/G_domestic.pkl", "rb"))
# --- cleaning rules agreed so far ---
EXCLUDE = {("BLD","GCW"): "sightseeing (Papillon helicopters)",
           ("GCN","PGA"): "sightseeing (Scenic Airlines)",
           ("ATL","DFW"): None}  # ATL-DFW: only drop the China Airlines cargo tag, edge stays
for (u,v),why in EXCLUDE.items():
    if why and G.has_edge(u,v): G.remove_edge(u,v)
if G.has_edge("ATL","DFW"): G["ATL"]["DFW"]["airlines"].discard("CI")
G.remove_nodes_from([n for n in list(G) if G.degree(n)==0])
N = G.number_of_nodes()
cc = sorted(nx.connected_components(G), key=len, reverse=True)
print(f"cleaned network: {N} airports, {G.number_of_edges()} routes, components={[len(c) for c in cc]}")

# --- 1. centrality ---
deg = dict(G.degree()); btw = nx.betweenness_centrality(G, normalized=True)
df = pd.DataFrame({"iata":list(G), "name":[G.nodes[n]["name"] for n in G],
                   "city":[G.nodes[n]["city"] for n in G],
                   "degree":[deg[n] for n in G], "betweenness":[btw[n] for n in G]})
df["deg_rank"] = df.degree.rank(ascending=False, method="min").astype(int)
df["btw_rank"] = df.betweenness.rank(ascending=False, method="min").astype(int)
df = df.sort_values("betweenness", ascending=False)
df.to_csv("out/centrality.csv", index=False)
rho,_ = spearmanr(df.degree, df.betweenness)
top20d = set(df.nlargest(20,"degree").iata); top20b = set(df.nlargest(20,"betweenness").iata)
print(f"Spearman rho(degree, betweenness) = {rho:.3f};  top-20 overlap = {len(top20d & top20b)}/20")
print("In top-20 betweenness but not top-20 degree:", sorted(top20b-top20d))
print("In top-20 degree but not top-20 betweenness:", sorted(top20d-top20b))
print(df.head(15)[["iata","city","degree","deg_rank","betweenness","btw_rank"]].to_string(index=False))

# scatter
fig, ax = plt.subplots(figsize=(7.5,5.5))
ax.scatter(df.degree, df.betweenness, s=14, alpha=.5, color="#4a6fa5")
lab = set(df.head(12).iata) | set(df.nlargest(8,"degree").iata)
# flag outliers: high betweenness relative to degree
df["ratio"] = df.betweenness/df.degree
lab |= set(df[df.degree<40].nlargest(6,"betweenness").iata)
for _,r in df[df.iata.isin(lab)].iterrows():
    ax.annotate(r.iata,(r.degree,r.betweenness),fontsize=8,xytext=(3,3),textcoords="offset points")
ax.set_xlabel("Degree (number of nonstop domestic destinations)")
ax.set_ylabel("Betweenness centrality (normalized)")
ax.set_title(f"Degree vs. betweenness, US domestic network (Spearman ρ = {rho:.2f})")
ax.grid(alpha=.3); fig.tight_layout(); fig.savefig("out/fig1_degree_vs_betweenness.png", dpi=200)

# --- 2. robustness ---
def lcc_frac(H): return max((len(c) for c in nx.connected_components(H)), default=0)/N
def eff(H): return nx.global_efficiency(H)*H.number_of_nodes()*(H.number_of_nodes()-1)/(N*(N-1)) if H.number_of_nodes()>1 else 0
E0 = eff(G)
STEPS = 120  # remove up to ~20% of airports
def attack(kind, seed=None):
    H = G.copy(); rng = random.Random(seed); order = list(H); rng.shuffle(order)
    L=[lcc_frac(H)]; E=[1.0]
    for k in range(STEPS):
        if kind=="random": n = order[k]
        elif kind=="degree": n = max(H.degree, key=lambda x:x[1])[0]
        else:
            b = nx.betweenness_centrality(H); n = max(b, key=b.get)
        H.remove_node(n); L.append(lcc_frac(H)); E.append(eff(H)/E0 if k%5==4 else np.nan)
    return np.array(L), pd.Series(E).interpolate().values
res = {}
R = [attack("random", s) for s in range(30)]
res["Random (mean of 30)"] = (np.mean([r[0] for r in R],0), np.mean([r[1] for r in R],0), np.std([r[0] for r in R],0))
res["Highest degree first"] = attack("degree")+(None,)
res["Highest betweenness first"] = attack("betweenness")+(None,)
x = np.arange(STEPS+1)
fig, axs = plt.subplots(1,2,figsize=(12,4.8))
cols = {"Random (mean of 30)":"#888888","Highest degree first":"#d1495b","Highest betweenness first":"#2e86ab"}
for k,(L,E,sd) in res.items():
    axs[0].plot(x, L*100, label=k, color=cols[k], lw=2)
    if sd is not None: axs[0].fill_between(x,(L-sd)*100,(L+sd)*100,color=cols[k],alpha=.15)
    axs[1].plot(x, E*100, label=k, color=cols[k], lw=2)
axs[0].set(xlabel="Airports closed", ylabel="% of airports in largest connected component",
           title="Fragmentation"); axs[1].set(xlabel="Airports closed",
           ylabel="Global efficiency (% of original)", title="Efficiency (detour cost)")
for a in axs: a.grid(alpha=.3); a.legend(); a.set_ylim(0,102)
fig.tight_layout(); fig.savefig("out/fig2_robustness.png", dpi=200)
summ=[]
for k,(L,E,_) in res.items():
    half = next((i for i,v in enumerate(L) if v<0.5*L[0]), None)
    summ.append({"strategy":k,"LCC% after 10":round(L[10]*100,1),"LCC% after 30":round(L[30]*100,1),
                 "LCC% after 60":round(L[60]*100,1),"Eff% after 10":round(E[10]*100,1),
                 "Eff% after 30":round(E[30]*100,1),"closures to halve LCC":half})
s=pd.DataFrame(summ); s.to_csv("out/robustness_summary.csv",index=False); print(s.to_string(index=False))
print("first 10 removed (betweenness, adaptive):")
