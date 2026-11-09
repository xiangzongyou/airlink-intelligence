"""Sensitivity check: repeat Level 1 on the contiguous US only (drop Alaska & Hawaii)."""
import os; os.chdir(os.path.dirname(os.path.abspath(__file__))); os.makedirs("data", exist_ok=True); os.makedirs("out", exist_ok=True)

import pickle, random, numpy as np, pandas as pd, networkx as nx
from scipy.stats import spearmanr
G=pickle.load(open("data/G_domestic.pkl","rb"))
G.remove_edges_from([("BLD","GCW"),("GCN","PGA")])
drop=[n for n in G if G.nodes[n]["lon"]<-130 or G.nodes[n]["lat"]<24]   # Alaska, Hawaii, Pacific
G.remove_nodes_from(drop); G.remove_nodes_from([n for n in list(G) if G.degree(n)==0])
G=G.subgraph(max(nx.connected_components(G),key=len)).copy()
N=len(G); print("Lower-48 network:",N,"airports,",G.number_of_edges(),"routes")
deg=dict(G.degree()); b=nx.betweenness_centrality(G)
rho,_=spearmanr([deg[n] for n in G],[b[n] for n in G])
td=set(sorted(G,key=deg.get)[-20:]); tb=set(sorted(G,key=b.get)[-20:])
print(f"Spearman rho={rho:.3f}, top-20 overlap {len(td&tb)}/20")
print("top-10 betweenness:",[(n,deg[n],round(b[n],3)) for n in sorted(G,key=b.get)[::-1][:10]])
print("high betweenness, not top-20 degree:",sorted(tb-td))
def lcc(H): return max(len(c) for c in nx.connected_components(H))/N
def run(kind,seed=0):
    H=G.copy(); o=list(H); random.Random(seed).shuffle(o); L=[1.0]; seq=[]
    for k in range(60):
        n=o[k] if kind=="random" else (max(H.degree,key=lambda x:x[1])[0] if kind=="degree" else max((bb:=nx.betweenness_centrality(H)),key=bb.get))
        seq.append(n); H.remove_node(n); L.append(lcc(H))
    return np.array(L),seq
Lr=np.mean([run("random",s)[0] for s in range(30)],0)
Ld,sd=run("degree"); Lb,sb=run("betweenness")
for k,L in [("random",Lr),("degree",Ld),("betweenness",Lb)]:
    print(f"{k:12s} LCC% after 10/30/60: {L[10]*100:.1f} {L[30]*100:.1f} {L[60]*100:.1f}")
print("betweenness order:",sb[:12])
pickle.dump({"Lr":Lr,"Ld":Ld,"Lb":Lb},open("out/lower48_curves.pkl","wb"))
