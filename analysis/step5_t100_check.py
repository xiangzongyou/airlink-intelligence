"""Step 5: check the OpenFlights network against BTS T-100 Domestic Segment (2014).

Input:  T_T100D_SEGMENT_ALL_CARRIER_*.zip in this folder (downloaded from TranStats:
        T-100 Domestic Segment (All Carriers), 2014, all months)
        ../airlink_app/app_data/airports.csv, routes.csv, and backup_pairs.csv (step 4)
Output: t100_routes_2014.csv  one row per undirected airport pair with scheduled
                              passenger service in 2014 (yearly passengers, seats,
                              departures; June values too), flagged if in OpenFlights
        printed summary of how well the two sources agree
Only class F rows (scheduled passenger service) with passengers > 0 are used.
"""
import os, glob, zipfile
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "airlink_app", "app_data")
zips = sorted(glob.glob(os.path.join(HERE, "T_T100D_SEGMENT_ALL_CARRIER*.zip")))
if not zips:
    raise SystemExit("T-100 zip not found in analysis/. Download it from https://www.transtats.bts.gov/DataIndex.asp :\n"
                     "  Air Carrier Statistics (Form 41 Traffic) - All Carriers > T-100 Domestic Segment (All Carriers) > Download,\n"
                     "  year 2014, all months (fields: see README), and put the zip in analysis/.")
z = zips[-1]
with zipfile.ZipFile(z) as f:
    name = [n for n in f.namelist() if n.startswith("T_T100D") and n.endswith(".csv")][0]
    t = pd.read_csv(f.open(name))
t = t[(t.CLASS == "F") & (t.PASSENGERS > 0) & (t.ORIGIN != t.DEST)].copy()
t["a"] = t[["ORIGIN", "DEST"]].min(axis=1); t["b"] = t[["ORIGIN", "DEST"]].max(axis=1)

year = t.groupby(["a", "b"]).agg(passengers=("PASSENGERS", "sum"), seats=("SEATS", "sum"),
                                 departures=("DEPARTURES_PERFORMED", "sum"), miles=("DISTANCE", "max"))
june = t[t.MONTH == 6].groupby(["a", "b"]).agg(passengers_june=("PASSENGERS", "sum"), seats_june=("SEATS", "sum"),
                                               departures_june=("DEPARTURES_PERFORMED", "sum"))
r = year.join(june).fillna(0).reset_index()

ap = pd.read_csv(os.path.join(D, "airports.csv")); rt = pd.read_csv(os.path.join(D, "routes.csv"))
of = set(zip(rt[["src", "dst"]].min(axis=1), rt[["src", "dst"]].max(axis=1)))
r["in_openflights"] = [(a, b) in of for a, b in zip(r.a, r.b)]
r["both_airports_in_openflights"] = r.a.isin(ap.iata) & r.b.isin(ap.iata)
for c in ["passengers", "seats", "departures", "miles", "passengers_june", "seats_june", "departures_june"]:
    r[c] = r[c].astype(int)
r.sort_values("passengers", ascending=False).to_csv(os.path.join(HERE, "t100_routes_2014.csv"), index=False)

found = r.in_openflights.sum()
print(f"T-100 2014 scheduled passenger routes: {len(r)} airport pairs, {r.passengers.sum():,} passengers")
print(f"OpenFlights routes confirmed by T-100: {found}/{len(of)} ({found / len(of):.1%})")
print(f"OpenFlights airports missing from T-100: {sorted(set(ap.iata) - set(r.a) - set(r.b))}")
print(f"Share of T-100 passengers flying on OpenFlights routes: {r.loc[r.in_openflights, 'passengers'].sum() / r.passengers.sum():.1%}")
extra = r[~r.in_openflights & r.both_airports_in_openflights]
print(f"T-100 routes between OpenFlights airports that OpenFlights lacks: {len(extra)} "
      f"({extra.passengers.sum() / r.passengers.sum():.1%} of passengers); biggest:")
print(extra.nlargest(8, "passengers")[["a", "b", "passengers"]].to_string(index=False))

# do the step-4 backup pairs survive with the fuller T-100 route list?
bp_path = os.path.join(HERE, "backup_pairs.csv")
if os.path.exists(bp_path):
    bp = pd.read_csv(bp_path)
    links = {}
    for a, b in zip(r.a, r.b):
        links.setdefault(a, set()).add(b); links.setdefault(b, set()).add(a)
    print("\nBackup pairs: do the cut-off airports have other T-100 links?")
    for _, x in bp.iterrows():
        cut = set(x.cut_off_list.split()); pair = {x.airport_a, x.airport_b}
        other = set().union(*(links.get(c, set()) for c in cut)) - cut - pair
        print(f"  {x.airport_a}+{x.airport_b} -> {x.cut_off_list}: "
              + ("confirmed (no other links)" if not other else f"other links in T-100: {' '.join(sorted(other))}"))
