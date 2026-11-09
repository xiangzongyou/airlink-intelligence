import os; os.chdir(os.path.dirname(os.path.abspath(__file__))); os.makedirs("data", exist_ok=True); os.makedirs("out", exist_ok=True)
import pandas as pd
cols=["id","name","city","country","iata","icao","lat","lon","alt","tz","dst","tzdb","type","source"]
a=pd.read_csv("data/airports.dat",header=None,na_values="\\N",names=cols)
ax=pd.read_csv("data/airports-extended.dat",header=None,na_values="\\N",names=cols)
r=pd.read_csv("data/routes.dat",header=None,na_values="\\N",
  names=["airline","airline_id","src","src_id","dst","dst_id","codeshare","stops","equip"])
r=r[r.stops==0]
ends=pd.concat([r[["src","src_id"]].set_axis(["iata","id"],axis=1),r[["dst","dst_id"]].set_axis(["iata","id"],axis=1)])
missing=ends[~ends.id.isin(a.id)].drop_duplicates("iata")
print("route endpoints (IATA) not in airports.dat:", len(missing))
# try recovering by id or iata in extended file
ax_id=ax.set_index("id"); ax_iata=ax.dropna(subset=["iata"]).drop_duplicates("iata").set_index("iata")
def find(row):
    if pd.notna(row.id) and row.id in ax_id.index: return ax_id.loc[row.id,"country"]
    if row.iata in ax_iata.index: return ax_iata.loc[row.iata,"country"]
    return None
missing["country"]=missing.apply(find,axis=1)
print("recovered from extended file:", missing.country.notna().sum())
us=missing[missing.country=="United States"]
print("missing airports that are US:", len(us))
print(sorted(us.iata))
print("still unknown:", sorted(missing[missing.country.isna()].iata))
# DUT-ANC check
print("DUT-ANC routes:", len(r[((r.src=="DUT")&(r.dst=="ANC"))|((r.src=="ANC")&(r.dst=="DUT"))]))
