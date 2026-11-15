"""Step 4: backup airport pairs.

A backup pair (A, B) is two airports where closing either one alone leaves every
destination reachable, but closing both cuts some airports off.
For each pair we report what gets cut off, how many trips are lost, and how far
apart A and B are (pairs close together could share one hazard, e.g. a storm).

Input:  ../airlink_app/app_data/airports.csv, routes.csv, single_closure.csv
        (the cleaned network: 605 airports, 2,883 routes)
Output: backup_pairs.csv (next to this script)
Runtime: about 1-2 minutes.
"""
import os, itertools
import numpy as np, pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "airlink_app", "app_data")
SHARED_HAZARD_MILES = 150     # assumption: pairs this close can be hit by the same weather event

ap = pd.read_csv(os.path.join(D, "airports.csv"))
rt = pd.read_csv(os.path.join(D, "routes.csv"))
sc = pd.read_csv(os.path.join(D, "single_closure.csv"))
codes = list(ap.iata); idx = {c: i for i, c in enumerate(codes)}; n = len(codes)
E = np.array([[idx[a], idx[b]] for a, b in zip(rt.src, rt.dst)])


def components(closed):
    keep = np.ones(n, bool); keep[list(closed)] = False
    e = E[keep[E[:, 0]] & keep[E[:, 1]]]
    A = csr_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n))
    return connected_components(A, directed=False)[1], keep


lab0, _ = components(())
main0 = np.bincount(lab0).argmax()


def impact(closed):
    """Trips lost (open airport pairs that could reach each other before, but not after) and airports cut off."""
    lab, keep = components(closed)
    before = sum(k * (k - 1) // 2 for k in (((lab0 == c) & keep).sum() for c in np.unique(lab0[keep])))
    s = np.bincount(lab[keep]); after = int((s * (s - 1) // 2).sum())
    main = s.argmax()
    cut = [codes[i] for i in range(n) if keep[i] and lab0[i] == main0 and lab[i] != main]
    return before - after, cut


# sanity check against the single-closure table
lost, cut = impact([idx["ATL"]])
assert (lost, len(cut)) == (6489, 11), (lost, len(cut))

safe = set(sc.loc[sc.main_effect != "Loss of access", "iata"])
cand = [idx[c] for c in codes if c in safe and lab0[idx[c]] == main0]
rows = []
for a, b in itertools.combinations(cand, 2):
    lost, cut = impact([a, b])
    if lost > 0:
        rows.append((codes[a], codes[b], len(cut), lost, " ".join(cut)))

df = pd.DataFrame(rows, columns=["airport_a", "airport_b", "airports_cut_off", "trips_lost", "cut_off_list"])
P = ap.set_index("iata")
la1, lo1, la2, lo2 = (np.radians(P.loc[df[c], k].values) for c, k in
                      [("airport_a", "lat"), ("airport_a", "lon"), ("airport_b", "lat"), ("airport_b", "lon")])
h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
df["miles_apart"] = np.round(3958.8 * 2 * np.arcsin(np.sqrt(h))).astype(int)
df["shared_hazard_risk"] = df.miles_apart <= SHARED_HAZARD_MILES
for side in ["a", "b"]:
    df[f"city_{side}"] = df[f"airport_{side}"].map(P.city)
df["region"] = df.airport_a.map(P.region)
df = df.sort_values(["trips_lost", "miles_apart"], ascending=[False, True])
df.to_csv(os.path.join(HERE, "backup_pairs.csv"), index=False)

print(f"airports safe to close alone (main network): {len(cand)}")
print(f"backup pairs found: {len(df)}")
print(f"within {SHARED_HAZARD_MILES} miles of each other: {df.shared_hazard_risk.sum()}")
print(df.groupby("region").size().to_string())
print(df[["airport_a", "airport_b", "miles_apart", "airports_cut_off", "cut_off_list"]].to_string(index=False))
