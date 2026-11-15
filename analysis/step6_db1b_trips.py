"""Step 6: real door-to-door air trips from the BTS DB1B ticket survey (2014, April-June).

DB1B is a 10% sample of domestic airline tickets. The Market table has one row per directional trip
("market") with the airports flown through in order, e.g. "SAV:ATL:DEN".

Input:  Origin_and_Destination_Survey_DB1BMarket_2014_2.zip in this folder
        (TranStats > Airline Origin and Destination Survey (DB1B) > DB1BMarket, 2014 Quarter 2;
         the prezipped file, ~1.6 GB unzipped, is read in chunks, never unzipped to disk)
Output: db1b_itineraries_2014q2.csv  one row per airport sequence: route, origin, dest, stops,
                                     sample passengers, estimated passengers per day
                                     (sample x 10 / 91 days)
        printed summary: how many travelers connect, and the connecting share at the big hubs
"""
import os, glob, zipfile
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
zips = sorted(glob.glob(os.path.join(HERE, "Origin_and_Destination_Survey_DB1BMarket_2014_2*.zip")))
if not zips:
    raise SystemExit("DB1B zip not found in analysis/ (it is ~93 MB, too big for the repo). Download it from\n"
                     "  https://www.transtats.bts.gov/DataIndex.asp : Airline Origin and Destination Survey (DB1B) > DB1BMarket >\n"
                     "  Download, year 2014, Quarter 2 (the prezipped file is fine), and put the zip in analysis/.")
z = zips[-1]
DAYS, SAMPLE = 91, 0.10      # April-June 2014; DB1B is a 10% sample of tickets

parts, rows = [], 0
with zipfile.ZipFile(z) as zf:
    name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
    for ch in pd.read_csv(zf.open(name), usecols=["Origin", "Dest", "AirportGroup", "Passengers"], chunksize=1_000_000):
        rows += len(ch)
        parts.append(ch.groupby("AirportGroup", as_index=False).Passengers.sum())
g = pd.concat(parts).groupby("AirportGroup", as_index=False).Passengers.sum()
g = g.rename(columns={"AirportGroup": "route", "Passengers": "sample_passengers"})
seq = g.route.str.split(":")
g["origin"], g["dest"], g["stops"] = seq.str[0], seq.str[-1], seq.str.len() - 2
g["passengers_per_day"] = (g.sample_passengers / SAMPLE / DAYS).round(2)
g = g[g.origin != g.dest].sort_values("sample_passengers", ascending=False)
g.to_csv(os.path.join(HERE, "db1b_itineraries_2014q2.csv"), index=False)

tot = g.passengers_per_day.sum()
print(f"rows read: {rows:,}; distinct airport sequences: {len(g):,}")
print(f"estimated door-to-door air trips per day (Apr-Jun 2014): {tot:,.0f}")
print("by number of stops:", (g.groupby("stops").passengers_per_day.sum() / tot).round(3).to_dict())
# connecting share at hubs: of the travelers who use an airport, how many only change planes there
use, conn = {}, {}
for r, p in zip(g.route, g.passengers_per_day):
    a = r.split(":")
    for k, x in enumerate(a):
        use[x] = use.get(x, 0) + p
        if 0 < k < len(a) - 1: conn[x] = conn.get(x, 0) + p
for h in ["ATL", "ORD", "DFW", "DEN", "CLT", "IAH", "MSP", "DTW", "LAX", "JFK", "ANC"]:
    print(f"  {h}: {use.get(h, 0):9,.0f} travelers/day use it, {conn.get(h, 0) / max(use.get(h, 1), 1):.0%} only connect there")
