"""Meeting figures: Fig 1 degree vs betweenness (Alaska highlighted); Fig 2 robustness, full vs Lower 48."""
import os; os.chdir(os.path.dirname(os.path.abspath(__file__))); os.makedirs("data", exist_ok=True); os.makedirs("out", exist_ok=True)

import pickle, numpy as np, pandas as pd, networkx as nx, random
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from adjustText import adjust_text
plt.rcParams.update({"font.size":10})
df=pd.read_csv("out/centrality.csv")
G=pickle.load(open("data/G_domestic.pkl","rb"))
df["region"]=["Alaska" if G.nodes[n]["lon"]<-130 and G.nodes[n]["lat"]>50 else
              ("Hawaii/Pacific" if G.nodes[n]["lat"]<24 or G.nodes[n]["lon"]<-150 else "Lower 48") for n in df.iata]
fig,ax=plt.subplots(figsize=(8,5.6))
C={"Lower 48":"#2e86ab","Alaska":"#d1495b","Hawaii/Pacific":"#e0a458"}
for reg,d in df.groupby("region"):
    ax.scatter(d.degree,d.betweenness,s=16,alpha=.6,color=C[reg],label=f"{reg} ({len(d)})")
lab=set(df.nlargest(12,"betweenness").iata)|set(df.nlargest(6,"degree").iata)
T=[ax.text(r.degree,r.betweenness,r.iata,fontsize=8.5) for _,r in df[df.iata.isin(lab)].iterrows()]
adjust_text(T,ax=ax,arrowprops=dict(arrowstyle="-",color="gray",lw=.5))
ax.set(xlabel="Degree (nonstop domestic destinations)",ylabel="Betweenness centrality (normalized)",
       title="Big hubs vs. bridges: Alaska's gateways have high betweenness despite few routes")
ax.legend(title="Region (airports)"); ax.grid(alpha=.3); fig.tight_layout()
fig.savefig("out/fig1_degree_vs_betweenness.png",dpi=200)

# Fig 2: rerun full-network LCC curves (cheap) + load Lower-48 curves
G.remove_edges_from([("BLD","GCW"),("GCN","PGA")]); G.remove_nodes_from([n for n in list(G) if G.degree(n)==0])
N=len(G)
def lcc(H): return max(len(c) for c in nx.connected_components(H))/N
def run(kind,seed=0,steps=60):
    H=G.copy(); o=list(H); random.Random(seed).shuffle(o); L=[lcc(H)]
    for k in range(steps):
        if kind=="random": n=o[k]
        elif kind=="degree": n=max(H.degree,key=lambda x:x[1])[0]
        else: b=nx.betweenness_centrality(H); n=max(b,key=b.get)
        H.remove_node(n); L.append(lcc(H))
    return np.array(L)
full={"Random (mean of 30)":np.mean([run("random",s) for s in range(30)],0),
      "Highest degree first":run("degree"),"Highest betweenness first":run("betweenness")}
l48=pickle.load(open("out/lower48_curves.pkl","rb"))
low={"Random (mean of 30)":l48["Lr"],"Highest degree first":l48["Ld"],"Highest betweenness first":l48["Lb"]}
col={"Random (mean of 30)":"#888888","Highest degree first":"#d1495b","Highest betweenness first":"#2e86ab"}
fig,axs=plt.subplots(1,2,figsize=(12,4.8),sharey=True)
for ax,(t,R) in zip(axs,[("All US domestic (605 airports)",full),("Lower 48 only (408 airports)",low)]):
    for k,L in R.items(): ax.plot(L*100,label=k,color=col[k],lw=2.2)
    ax.set(title=t,xlabel="Airports closed (recomputed after each closure)"); ax.grid(alpha=.3)
axs[0].set_ylabel("% of airports still in largest connected component")
axs[0].annotate("ANC, then SEA closed:\nAlaska cut off",xy=(2,full["Highest betweenness first"][2]*100),
                xytext=(12,80),arrowprops=dict(arrowstyle="->"),fontsize=9)
axs[1].legend(loc="upper right"); fig.suptitle("Targeted closures fragment the network far faster than random ones",y=1.0)
fig.tight_layout(); fig.savefig("out/fig2_robustness.png",dpi=200,bbox_inches="tight")
