import os; os.chdir(os.path.dirname(os.path.abspath(__file__))); os.makedirs("data", exist_ok=True); os.makedirs("out", exist_ok=True)
import pandas as pd, networkx as nx, pickle
cols=["id","name","city","country","iata","icao","lat","lon","alt","tz","dst","tzdb","type","source"]
a=pd.read_csv("data/airports.dat",header=None,na_values="\\N",names=cols)
ax=pd.read_csv("data/airports-extended.dat",header=None,na_values="\\N",names=cols)
# merged airport table keyed by IATA: main file first, extended fills gaps
ap=pd.concat([a,ax]).dropna(subset=["iata"]).drop_duplicates("iata").set_index("iata")
r=pd.read_csv("data/routes.dat",header=None,na_values="\\N",
  names=["airline","airline_id","src","src_id","dst","dst_id","codeshare","stops","equip"])
r=r[r.stops==0].copy()
r["src_c"]=r.src.map(ap.country); r["dst_c"]=r.dst.map(ap.country)
r=r.dropna(subset=["src_c","dst_c"])
US="United States"
dom=r[(r.src_c==US)&(r.dst_c==US)]
usx=r[(r.src_c==US)|(r.dst_c==US)]
print("domestic records:",len(dom)," US-endpoint records:",len(usx))
def graph(df):
    G=nx.Graph()
    for (s,d),g in df.groupby(["src","dst"]):
        if s==d: continue
        al=set(g.airline)
        if G.has_edge(s,d): G[s][d]["airlines"]|=al
        else: G.add_edge(s,d,airlines=al)
    for n in G:
        row=ap.loc[n]; G.nodes[n].update(name=row["name"],city=row.city,country=row.country,
            lat=row.lat,lon=row.lon,tz=row.tzdb)
    return G
for name,df in [("domestic",dom),("us_plus_intl",usx)]:
    G=graph(df); cc=sorted(nx.connected_components(G),key=len,reverse=True)
    print(f"\n{name}: {G.number_of_nodes()} airports, {G.number_of_edges()} undirected routes, "
          f"{len(cc)} components, largest={len(cc[0])}")
    for c in cc[1:]: print("   separate component:",sorted(c))
    pickle.dump(G,open(f"data/G_{name}.pkl","wb"))
