import os; os.chdir(os.path.dirname(os.path.abspath(__file__))); os.makedirs("data", exist_ok=True); os.makedirs("out", exist_ok=True)
import pandas as pd
r = pd.read_csv("data/routes.dat", header=None, na_values="\\N",
    names=["airline","airline_id","src","src_id","dst","dst_id","codeshare","stops","equip"])
a = pd.read_csv("data/airports.dat", header=None, na_values="\\N",
    names=["id","name","city","country","iata","icao","lat","lon","alt","tz","dst","tzdb","type","source"])
print("routes:", len(r), " airports:", len(a))
r = r[r.stops==0].copy()
print("nonstop:", len(r))
cmap = a.set_index("id")["country"]
r["src_c"] = r.src_id.map(cmap); r["dst_c"] = r.dst_id.map(cmap)
us = (r.src_c=="United States") | (r.dst_c=="United States")
f = r[us].copy()
f["kind"] = (f.src_c=="United States") & (f.dst_c=="United States")
print("US-endpoint records:", len(f), " domestic:", f.kind.sum(), " international:", (~f.kind).sum())
# routes with a US-looking endpoint that failed to match airport file
miss = r[r.src_id.isna() | r.dst_id.isna() | r.src_c.isna() | r.dst_c.isna()]
print("nonstop records with an unmatched endpoint:", len(miss))
f.to_csv("data/us_routes.csv", index=False)
