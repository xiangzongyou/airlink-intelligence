import pandas as pd, numpy as np, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import os
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
D = os.path.join(HERE, "..", "airlink_app", "app_data") + os.sep
ap = pd.read_csv(D + "airports.csv").merge(pd.read_csv("communities.csv"), on="iata")
rt = pd.read_csv(D + "routes.csv"); r = pd.read_csv("q2_regional_impact_big.csv")
P = ap.set_index("iata")
COL = {0: "#1E6BFF", 1: "#FF2E93", 2: "#7C3AED", 5: "#FF9500", 3: "#16A765", 4: "#E0B000", 6: "#00A6B4"}
NAME = {0: "West", 1: "East Coast", 2: "Midwest–Southeast", 5: "Texas", 3: "Interior/North AK", 4: "Yukon-Kuskokwim AK", 6: "Southeast AK"}
# state outlines from the us-atlas file (lon/lat), drawn light for context
import topojson_helper as th
states = th.states_lonlat(os.path.join(HERE, "us_states_topojson.json"))
fig = plt.figure(figsize=(15, 9.5)); gs = fig.add_gridspec(2, 2, width_ratios=[1.45, 1], height_ratios=[1, 1], wspace=.42, hspace=.25)
def panel(ax, region, xlim, ylim, title, aspect):
    for ring in states: ax.plot(ring[:, 0], ring[:, 1], color="#c9d2db", lw=.5, zorder=1)
    sub = ap[ap.region == region]; inside = rt[rt.src.isin(sub.iata) & rt.dst.isin(sub.iata)]
    same = inside[inside.src.map(P.community) == inside.dst.map(P.community)]
    segs = [[(P.lon[a], P.lat[a]), (P.lon[b], P.lat[b])] for a, b in zip(same.src, same.dst)]
    ax.add_collection(LineCollection(segs, colors=[COL.get(P.community[a], "#999") for a in same.src], lw=.5, alpha=.35, zorder=2))
    for k, g in sub.groupby("community"):
        ax.scatter(g.lon, g.lat, s=8 + g.degree * 1.2, c=COL.get(k, "#9aa3ad"), edgecolor="white", lw=.4, zorder=3,
                   label=NAME.get(k) if k in COL and len(g) > 5 else None)
    for c in sub.nlargest(6 if region == "Lower 48" else 5, "degree").iata:
        ax.annotate(c, (P.lon[c], P.lat[c]), xytext=(4, 3), textcoords="offset points", fontsize=8.5, weight="bold", zorder=4)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect(aspect); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title(title, loc="left", fontsize=12, weight="bold")
a1 = fig.add_subplot(gs[0, 0]); panel(a1, "Lower 48", (-125, -66), (24, 50), "Lower 48: communities follow airline hubs", 1.3)
a1.legend(loc="lower left", fontsize=8.5, frameon=False, markerscale=.8)
a2 = fig.add_subplot(gs[1, 0]); panel(a2, "Alaska", (-170, -129), (54, 72), "Alaska: communities follow geography", 2.0)
a2.legend(loc="lower left", fontsize=8.5, frameon=False, markerscale=.8)
# right: national vs regional impact
a3 = fig.add_subplot(gs[:, 1])
top = r.sort_values("ratio", ascending=False)
top = top[top.iata.isin(["KTN", "JNU", "DFW", "BET", "FAI", "ANI", "AKN", "OTZ", "IAH", "DEN", "ATL", "ANC"])].copy()
top = top.sort_values("reg_pct")
y = np.arange(len(top))
a3.barh(y + .2, top.reg_pct, height=.38, color=[COL[int(c)] for c in top.comm], label="% of its region's airports cut off")
a3.barh(y - .2, top.pct_trips_lost, height=.38, color="#b8c0cc", label="% of all US trips lost")
a3.set_yticks(y); a3.set_yticklabels([f"{i} · {NAME[int(c)]}" for i, c in zip(top.iata, top.comm)], fontsize=9.5)
for yy, v in zip(y, top.reg_pct): a3.text(v + .8, yy + .2, f"{v:.0f}%", va="center", fontsize=8.5, weight="bold")
for yy, v in zip(y, top.pct_trips_lost): a3.text(v + .8, yy - .2, f"{v:.1f}%", va="center", fontsize=8, color="#5d6b85")
a3.set_xlabel("percent"); a3.legend(loc="lower right", fontsize=9, frameon=False)
for s in ["top", "right"]: a3.spines[s].set_visible(False)
a3.set_title("Q2: small nationally, severe regionally\n(single-airport closures)", loc="left", fontsize=12, weight="bold")
fig.suptitle("Level 2: airport communities (Louvain, modularity Q = 0.385) and regional impact of closures", fontsize=14, weight="bold", x=.06, ha="left")
fig.savefig("fig3_communities_q2.png", dpi=170, bbox_inches="tight")
