"""AirLink Intelligence: interactive demo of the US airport network (CAP 6318).
Run:  streamlit run app.py   (after: python build_data.py)
"""
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx, pydeck as pdk, streamlit as st
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path

DATA = Path(__file__).resolve().parent / "app_data"   # works from any working directory

st.set_page_config(page_title="AirLink Intelligence", page_icon="✈️", layout="wide")

# ---------- colors (aeronautical chart palette) ----------
# bright, playful palette
NAVY, MAGENTA, RED, AMBER, ROUTE = [30, 107, 255], [124, 58, 237], [255, 59, 48], [255, 149, 0], [30, 107, 255]
FONT = "Arial Rounded MT Bold, Nunito, Trebuchet MS, Verdana, sans-serif"
INK = "#1B2A4A"
# candy colors for states; neighbors never share a color (computed from state borders)
CANDY = ["#FFC8DD", "#FFF0A8", "#BDF2C9", "#CDE3FF", "#FFD8A8", "#E3D0FF"]
STATE_COLOR = {"MO": 0, "TN": 1, "KY": 2, "NY": 3, "AR": 4, "CO": 5, "IA": 1, "ID": 0, "MN": 2, "NE": 3, "OK": 1,
               "PA": 4, "SD": 5, "VA": 0, "WY": 2, "GA": 3, "IL": 4, "MA": 5, "MD": 1, "MT": 3, "NV": 2, "OH": 0,
               "UT": 4, "WV": 5, "AL": 2, "AZ": 1, "IN": 3, "KS": 4, "MI": 5, "MS": 0, "NC": 2, "ND": 1, "NH": 3,
               "NM": 4, "OR": 5, "TX": 0, "VT": 1, "WI": 3, "CA": 0, "CT": 2, "LA": 5, "ME": 1, "WA": 2, "AK": 5,
               "DC": 2, "DE": 0, "FL": 1, "NJ": 5, "RI": 3, "SC": 4, "HI": 3}
SCOPES = {"All US": dict(latitude=48, longitude=-118, zoom=2.4),
          "Lower 48": dict(latitude=38.5, longitude=-96, zoom=3.2),
          "Alaska": dict(latitude=61, longitude=-153, zoom=3.4),
          "Hawaii/Pacific": dict(latitude=20.8, longitude=-157.5, zoom=5.8)}

# ---------- data ----------
@st.cache_data
def load():
    ap = pd.read_csv(DATA / "airports.csv")
    rt = pd.read_csv(DATA / "routes.csv").fillna({"airlines": ""})
    sc = pd.read_csv(DATA / "single_closure.csv").fillna({"cut_off_list": ""})
    rob = pd.read_csv(DATA / "robustness.csv")
    return ap, rt, sc, rob

@st.cache_resource
def network(_ap, _rt):
    idx = {c: i for i, c in enumerate(_ap.iata)}
    r = [idx[s] for s in _rt.src] + [idx[d] for d in _rt.dst]
    c = [idx[d] for d in _rt.dst] + [idx[s] for s in _rt.src]
    A = csr_matrix((np.ones(len(r)), (r, c)), shape=(len(idx), len(idx)))
    D0 = shortest_path(A, unweighted=True, directed=False)
    G = nx.Graph(); G.add_nodes_from(_ap.iata); G.add_edges_from(zip(_rt.src, _rt.dst))
    # edge betweenness: share of shortest trips that use each route (how critical the route is)
    eb = nx.edge_betweenness_centrality(G)
    eb_col = np.array([eb.get((u, v), eb.get((v, u), 0.0)) for u, v in zip(_rt.src, _rt.dst)])
    return idx, A, D0, G, eb_col

ap, rt, sc, rob = load()
idx, A, D0, G, EB = network(ap, rt)
rt = rt.assign(eb=EB)
ap = ap.merge(sc[["iata", "main_effect", "trips_lost", "trips_detoured", "airports_cut_off"]], on="iata")
LABEL = {c: f"{c} · {city} ({name})" for c, city, name in zip(ap.iata, ap.city, ap.name)}
CODE = {v: k for k, v in LABEL.items()}
coords = ap.set_index("iata")[["lon", "lat"]]

def scenario(closed_codes):
    """Impact of closing a set of airports simultaneously."""
    n = len(idx); keep = np.ones(n, bool)
    for c in closed_codes: keep[idx[c]] = False
    sub = np.where(keep)[0]
    D1 = np.full((n, n), np.inf)
    D1[np.ix_(sub, sub)] = shortest_path(A[sub][:, sub], unweighted=True, directed=False)
    iu = np.triu_indices(n, 1)
    valid = keep[iu[0]] & keep[iu[1]] & np.isfinite(D0[iu])
    d0, d1 = D0[iu][valid], D1[iu][valid]
    lost, det = np.isinf(d1), np.isfinite(d1) & (d1 > d0)
    H = G.subgraph([c for c in ap.iata if c not in closed_codes])
    biggest = max(nx.connected_components(H), key=len)
    cut = [c for c in H if c not in biggest and ap.in_main_network.values[idx[c]]]
    return dict(total=int(valid.sum()), lost=int(lost.sum()), det=int(det.sum()),
                extra=float((d1[det] - d0[det]).mean()) if det.any() else 0.0, cut=sorted(cut))

# ---------- map clicks -> selected airport (must run before widgets render) ----------
def clicked_airport():
    """Return the IATA code clicked on either map engine, or None."""
    try:
        ev = st.session_state.get("map_plotly")
        if ev:
            for p in ev["selection"]["points"]:
                cd = p.get("customdata")
                code = cd[0] if isinstance(cd, (list, tuple)) else cd
                if code in LABEL: return code
        ev = st.session_state.get("map_deck")
        if ev:
            objs = ev["selection"]["objects"].get("airports", [])
            if objs: return objs[0].get("iata")
    except (KeyError, TypeError, AttributeError):
        pass
    return None

clicked = clicked_airport()
if clicked and clicked != st.session_state.get("_last_click"):
    st.session_state["_last_click"] = clicked
    st.session_state["airport"] = LABEL[clicked]

def close_airport(code):
    cur = st.session_state.get("closed", [])
    if LABEL[code] not in cur: st.session_state["closed"] = cur + [LABEL[code]]

# ---------- sidebar ----------
with st.sidebar:
    st.title("AirLink Intelligence")
    st.caption("US domestic nonstop passenger routes, OpenFlights (June 2014). CAP 6318 team project.")
    scope = st.radio("Map view", list(SCOPES), horizontal=True, key="scope")
    size_by = st.radio("Size airports by", ["Betweenness", "Degree"], horizontal=True,
                       help="Degree: number of nonstop destinations. Betweenness: how often an airport lies "
                            "on the shortest connection between two other airports.")
    route_mode = st.radio("Routes", ["Key routes", "All", "None"], horizontal=True, key="route_mode",
                          help="Key routes: the routes that the most shortest trips depend on (edge betweenness). "
                               "Thicker line = more critical route.")
    n_key = st.slider("Number of key routes", 10, 300, 60, step=10, key="n_key",
                      disabled=route_mode != "Key routes")
    n_sel = st.slider("Routes drawn for a selected airport", 5, 100, 25, step=5, key="n_sel",
                      help="Its most critical routes get lines; all its destinations stay highlighted as dots.")
    engine = st.radio("Map engine", ["Standard", "WebGL"], horizontal=True, key="engine",
                      help="Standard works in any browser. WebGL is smoother but needs graphics acceleration "
                           "and online map tiles.")
    st.divider()
    st.selectbox("Airport", list(LABEL.values()), index=None, key="airport",
                 placeholder="Search, or click an airport on the map")
    st.multiselect("Close airports", list(LABEL.values()), key="closed",
                   placeholder="Pick airports to simulate a disruption")
    st.caption("Closures are simulated together: routes touching a closed airport disappear.")
    st.caption("App version 6")

sel = CODE.get(st.session_state.get("airport"))
closed = [CODE[x] for x in st.session_state.get("closed", [])]
res = scenario(closed) if closed else None
cut = set(res["cut"]) if res else set()

# ---------- map layers ----------
metric = ap.betweenness / ap.betweenness.max() if size_by == "Betweenness" else ap.degree / ap.degree.max()
pts = ap.assign(radius=3 + 22 * np.sqrt(metric),
                status=np.select([ap.iata.isin(closed), ap.iata.isin(cut), ap.iata == sel],
                                 ["Closed", "Cut off", "Selected"], "Open"))
if sel:
    nbrs = set(G[sel]); pts.loc[pts.iata.isin(nbrs) & (pts.status == "Open"), "status"] = "Destination"
COLOR = {"Open": NAVY + [230], "Closed": RED + [235], "Cut off": AMBER + [235],
         "Selected": MAGENTA + [255], "Destination": MAGENTA + [200]}
pts["color"] = pts.status.map(COLOR)
pts["rank_text"] = [f"#{d} by degree, #{b} by betweenness" for d, b in zip(pts.degree_rank, pts.betweenness_rank)]
pts = pts.sort_values("status", key=lambda s: s.map({"Open": 0}).fillna(1))  # highlighted on top
# send only what the map needs; NaN is invalid JSON and makes the whole map fail silently
pts = pts[["iata", "name", "city", "region", "degree", "rank_text", "lon", "lat", "radius", "color", "status"]].fillna("")

rts = rt.assign(slon=rt.src.map(coords.lon), slat=rt.src.map(coords.lat),
                dlon=rt.dst.map(coords.lon), dlat=rt.dst.map(coords.lat))
rts = rts[["src", "dst", "slon", "slat", "dlon", "dlat", "eb"]].dropna()
alive = ~(rts.src.isin(closed) | rts.dst.isin(closed))
REG = ap.set_index("iata").region
rreg_s, rreg_d = rts.src.map(REG), rts.dst.map(REG)
# draw only routes with both ends inside the view; cross-region lines can't be drawn cleanly
view_region = "Lower 48" if scope == "All US" else scope
in_view = (rreg_s == view_region) & (rreg_d == view_region)
view_routes = rts[alive & in_view]
if sel:                       # selected airport: only its most critical routes, no background
    background = rts.iloc[0:0]
    sel_all = rts[((rts.src == sel) | (rts.dst == sel)) & in_view]
    sel_routes = sel_all.nlargest(n_sel, "eb")
elif route_mode == "All":
    background = view_routes
elif route_mode == "Key routes":
    background = view_routes.nlargest(n_key, "eb")
else:
    background = rts.iloc[0:0]
if not sel:
    sel_all = sel_routes = rts.iloc[0:0]
broken = rts[~alive & in_view] if closed and not sel else rts.iloc[0:0]

# which airports get a text label
view_ap = ap if scope == "All US" else ap[ap.region == scope]
if scope == "Alaska":
    label_set = set(view_ap.nlargest(18, "betweenness").iata)
elif scope == "Hawaii/Pacific":
    label_set = set(view_ap.iata)
else:
    label_set = set(view_ap.nsmallest(30 if scope == "Lower 48" else 22, "degree_rank").iata)
if not sel and len(background):   # also label the ends of the routes being drawn
    label_set |= set(background.nlargest(40, "eb").src) | set(background.nlargest(40, "eb").dst)
if sel:
    label_set = {sel} | set(sel_routes.src) | set(sel_routes.dst)
label_set |= set(closed) | set(list(cut)[:40])

def thin_labels(codes, min_deg):
    """Keep the most important label when several airports sit almost on top of each other."""
    order = ap[ap.iata.isin(codes)].sort_values("degree", ascending=False)
    keep, placed = [], []
    for c, lo, la in zip(order.iata, order.lon, order.lat):
        if c == sel or all(abs(lo - x) > min_deg * 1.3 or abs(la - y) > min_deg for x, y in placed):
            keep.append(c); placed.append((lo, la))
    return set(keep)
label_set = thin_labels(label_set, {"All US": 1.1, "Lower 48": 0.8, "Alaska": 0.7, "Hawaii/Pacific": 0.12}[scope])
def hexa(c):  # [r,g,b,a] -> css rgba
    return f"rgba({c[0]},{c[1]},{c[2]},{c[3]/255:.2f})"

def segments(df):
    """One plotly line trace for many routes: coordinates separated by None."""
    lon, lat = [], []
    for a, b, c, d in zip(df.slon, df.slat, df.dlon, df.dlat):
        lon += [a, c, None]; lat += [b, d, None]
    return lon, lat

GEO = {"All US": dict(scope="usa", projection_type="albers usa"),
       "Lower 48": dict(scope="north america", projection_type="conic equal area",
                        projection_rotation=dict(lon=-96), fitbounds="locations"),
       "Alaska": dict(scope="north america", projection_type="conic equal area",
                      projection_rotation=dict(lon=-154), fitbounds="locations"),
       "Hawaii/Pacific": dict(scope="world", projection_type="mercator",
                              lonaxis_range=[-160.9, -154.4], lataxis_range=[18.6, 22.6])}

def add_routes(fig, df, rgb, alpha, widths):
    """Draw routes in three thickness classes by edge betweenness (thicker = more critical)."""
    import plotly.graph_objects as go
    if not len(df): return
    q = df.eb.rank(pct=True)
    for lo, hi, w in [(0, 1/3, widths[0]), (1/3, 2/3, widths[1]), (2/3, 1.01, widths[2])]:
        part = df[(q > lo) & (q <= hi)] if lo > 0 else df[q <= hi]
        if len(part):
            lon, lat = segments(part)
            fig.add_trace(go.Scattergeo(lon=lon, lat=lat, mode="lines", hoverinfo="skip",
                                        line=dict(width=w, color=f"rgba({rgb},{alpha})")))

def plotly_map():
    import plotly.graph_objects as go
    fig = go.Figure()
    states = {"All US": list(STATE_COLOR), "Alaska": ["AK"], "Hawaii/Pacific": ["HI"]}.get(
        scope, [x for x in STATE_COLOR if x not in ("AK", "HI")])   # keeps the map zoomed on the view
    steps = []
    for i, c in enumerate(CANDY):          # stepped scale: value i -> CANDY[i]
        steps += [[i / 6, c], [(i + 1) / 6, c]]
    fig.add_trace(go.Choropleth(locations=states, z=[STATE_COLOR[x] for x in states], locationmode="USA-states",
                                zmin=-0.5, zmax=5.5, colorscale=steps, showscale=False, hoverinfo="skip",
                                marker=dict(line=dict(color="white", width=1.6), opacity=1),
                                selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1))))
    if len(background):
        if route_mode == "All":
            add_routes(fig, background, "30,107,255", 0.15, (0.4, 0.6, 0.9))
        else:
            add_routes(fig, background, "30,107,255", 0.55, (1.0, 2.0, 3.6))
    if len(broken):
        lon, lat = segments(broken)
        fig.add_trace(go.Scattergeo(lon=lon, lat=lat, mode="lines", hoverinfo="skip",
                                    line=dict(width=0.9, color="rgba(255,59,48,0.38)")))
    if sel:
        add_routes(fig, sel_routes, "124,58,237", 0.8, (1.2, 2.2, 3.6))
    pv = pts if scope == "All US" else pts[pts.region == scope]
    dim = sel is not None
    colors = [hexa(c) if (not dim or st_ != "Open") else "rgba(30,107,255,0.25)"
              for c, st_ in zip(pv.color, pv.status)]
    fig.add_trace(go.Scattergeo(
        lon=pv.lon, lat=pv.lat, mode="markers", name="airports",
        customdata=np.stack([pv.iata, pv.name, pv.city, pv.region, pv.degree.astype(str), pv.rank_text], axis=1),
        marker=dict(size=np.where(pv.status.isin(["Closed", "Cut off"]), np.maximum(pv.radius * 0.85 + 4, 13),
                                  pv.radius * 0.85 + 4),
                    color=colors,
                    line=dict(width=np.where(pv.status.isin(["Closed", "Cut off"]), 2, 1.2),
                              color=[INK if x in ("Closed", "Cut off") else "white" for x in pv.status])),
        hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]} · %{customdata[3]}"
                      "<br>%{customdata[4]} destinations<br>%{customdata[5]}<extra></extra>"))
    lab = pv[pv.iata.isin(label_set)]
    fig.add_trace(go.Scattergeo(lon=lab.lon, lat=lab.lat, mode="text", hoverinfo="skip",
                                text=[f"<b>{c}</b>" if c == sel else c for c in lab.iata],
                                textposition="top right",
                                textfont=dict(size=[17 if c == sel else 12 for c in lab.iata], family=FONT,
                                              shadow="0 0 3px white, 0 0 3px white, 0 0 2px white",
                                              color=["#7C3AED" if c == sel else INK for c in lab.iata])))
    fig.update_geos(resolution=50, showland=True, landcolor="#F1F1EC", showocean=True, oceancolor="#A8DCFF",
                    showlakes=True, lakecolor="#A8DCFF", showsubunits=True, subunitcolor="#ffffff",
                    subunitwidth=1.6, showcountries=True, countrycolor="#ffffff", countrywidth=2,
                    showcoastlines=True, coastlinecolor="#4AA8E8", coastlinewidth=1.2,
                    bgcolor="rgba(0,0,0,0)", **GEO[scope])
    fig.update_layout(height=780, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", dragmode="pan", clickmode="event+select",
                      hoverlabel=dict(bgcolor="white", bordercolor="#7C3AED", font=dict(family=FONT, size=13, color=INK)))
    return fig

def deck_map():
    layers = []
    if len(background):
        layers.append(pdk.Layer("LineLayer", background, get_source_position=["slon", "slat"],
                                get_target_position=["dlon", "dlat"], get_color=ROUTE + [28], get_width=1))
    if len(broken):
        layers.append(pdk.Layer("LineLayer", broken, get_source_position=["slon", "slat"],
                                get_target_position=["dlon", "dlat"], get_color=RED + [60], get_width=1))
    if sel:
        layers.append(pdk.Layer("GreatCircleLayer", sel_routes, get_source_position=["slon", "slat"],
                                get_target_position=["dlon", "dlat"], get_source_color=MAGENTA + [230],
                                get_target_color=MAGENTA + [230], get_width=2.2))
    layers.append(pdk.Layer("ScatterplotLayer", pts, id="airports", pickable=True, get_position=["lon", "lat"],
                            get_radius="radius", radius_units="pixels", get_fill_color="color",
                            get_line_color=[255, 255, 255], line_width_min_pixels=0.6, stroked=True))
    return pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(**SCOPES[scope]), map_style="light",
                    tooltip={"html": "<b>{iata}</b> {name}<br/>{city} · {region}<br/>{degree} destinations<br/>{rank_text}",
                             "style": {"fontSize": "12px"}})

st.subheader("Which closures cut places off, and which only cause detours?")
if engine == "Standard":
    st.plotly_chart(plotly_map(), on_select="rerun", selection_mode="points", key="map_plotly",
                    config={"scrollZoom": True, "displayModeBar": False})
    if sel:
        shown = f"Showing {len(sel_routes)} of {sel}'s {len(sel_all)} routes in this view (its most critical ones). "
    elif len(background):
        shown = f"Showing {len(background)} of {len(view_routes)} routes in this view. "
    else:
        shown = ""
    st.caption(shown + "Drag to pan, scroll to zoom, click an airport to select it. In the All US view, Alaska and "
               "Hawaii appear as insets and only Lower 48 routes are drawn; switch the map view to see routes "
               "inside Alaska or Hawaii. Routes that leave the current view are listed in the airport table.")
else:
    st.pydeck_chart(deck_map(), height=780, on_select="rerun", selection_mode="single-object", key="map_deck")
st.markdown(
    "<div style='font-size:0.85rem;color:#4a5866'>"
    "<span style='color:#1E6BFF'>●</span> Airport (size = " + size_by.lower() + ") &nbsp; "
    "<span style='color:#7C3AED'>●</span> Selected airport and its destinations &nbsp; "
    "<span style='color:#FF3B30'>●</span> Closed &nbsp; "
    "<span style='color:#FF9500'>●</span> Cut off from the main network</div>", unsafe_allow_html=True)

# ---------- scenario results ----------
if res:
    st.markdown(f"#### Disruption scenario: {len(closed)} airport{'s' if len(closed) > 1 else ''} closed")
    c = st.columns(4)
    c[0].metric("Airports cut off", len(res["cut"]))
    c[1].metric("Trips no longer possible", f"{res['lost']:,}", f"{100*res['lost']/res['total']:.2f}% of airport pairs",
                delta_color="off")
    c[2].metric("Trips needing a detour", f"{res['det']:,}", f"{100*res['det']/res['total']:.2f}% of airport pairs",
                delta_color="off")
    c[3].metric("Extra connections per detour", f"{res['extra']:.2f}")
    if res["cut"]:
        cutdf = ap[ap.iata.isin(res["cut"])][["iata", "name", "city", "region"]]
        st.markdown("Cut off by region: " + ", ".join(f"**{r}** {n}" for r, n in cutdf.region.value_counts().items()))
        with st.expander(f"Show the {len(cutdf)} cut-off airports"):
            st.dataframe(cutdf, hide_index=True, width="stretch")
    st.caption("A trip is any pair of open airports that was connected before the closure. "
               "Detour = the shortest itinerary needs more connecting flights than before.")

# ---------- selected airport ----------
if sel:
    row = ap.set_index("iata").loc[sel]
    st.markdown(f"#### {sel} · {row['name']}")
    left, right = st.columns([3, 2])
    with left:
        c = st.columns(4)
        c[0].metric("Nonstop destinations", int(row.degree))
        c[1].metric("Degree rank", f"#{row.degree_rank}")
        c[2].metric("Betweenness rank", f"#{row.betweenness_rank}")
        reach = D0[idx[sel]]
        c[3].metric("Reachable with ≤1 connection", int(((reach > 0) & (reach <= 2)).sum()))
        effect = {"Loss of access": f"Closing {sel} alone would make **{int(row.trips_lost):,}** trips impossible "
                                    f"and cut off **{int(row.airports_cut_off)}** airport(s).",
                  "Detours only": f"Closing {sel} alone would cut nobody off, but **{int(row.trips_detoured):,}** "
                                  "trips would need extra connections.",
                  "No change": f"Closing {sel} alone would not affect travel between other airports."}
        st.markdown(effect[row.main_effect])
        cl = sc.set_index("iata").loc[sel, "cut_off_list"]
        if cl: st.caption("Would be cut off: " + cl.replace(" ", ", "))
        st.button(f"Close {sel} in the scenario", on_click=close_airport, args=(sel,), disabled=sel in closed)
    with right:
        nb = rt[(rt.src == sel) | (rt.dst == sel)].copy()
        nb["airport"] = np.where(nb.src == sel, nb.dst, nb.src)
        nb = nb.merge(ap[["iata", "city", "region", "degree"]], left_on="airport", right_on="iata")
        st.dataframe(nb[["airport", "city", "region", "degree", "airlines"]]
                     .rename(columns={"degree": "its destinations", "airlines": "airline codes"})
                     .sort_values("its destinations", ascending=False),
                     hide_index=True, width="stretch", height=240)

# ---------- reports ----------
st.divider()
t1, t2, t3, t4 = st.tabs(["Critical airports", "Single closures (Q1)", "Robustness (Level 1)", "About the data"])
with t1:
    st.markdown("Degree counts direct destinations; betweenness measures how often an airport is the bridge on "
                "the shortest path between others. The two disagree most for **gateway airports**: Anchorage has "
                "the highest betweenness in the country with only 34 destinations.")
    view_df = ap if scope == "All US" else ap[ap.region == scope]
    st.dataframe(view_df.sort_values("betweenness", ascending=False)
                 [["iata", "city", "region", "degree", "degree_rank", "betweenness", "betweenness_rank"]],
                 hide_index=True, width="stretch", height=320)
with t2:
    counts = sc.main_effect.value_counts()
    st.markdown(f"Closing one airport at a time: **{counts.get('Loss of access', 0)}** closures leave some "
                f"destinations unreachable, **{counts.get('Detours only', 0)}** only cause detours, and "
                f"**{counts.get('No change', 0)}** don't affect travel between other airports.")
    q1 = sc.merge(ap[["iata", "city", "region", "degree"]], on="iata")
    q1 = q1[q1.main_effect != "No change"].sort_values(["trips_lost", "trips_detoured"], ascending=False)
    st.dataframe(q1[["iata", "city", "region", "degree", "main_effect", "airports_cut_off", "trips_lost",
                     "pct_trips_lost", "trips_detoured", "mean_extra_connections"]],
                 hide_index=True, width="stretch", height=320)
    st.scatter_chart(q1, x="pct_trips_detoured", y="pct_trips_lost", color="region", size="degree",
                     x_label="% of trips needing a detour", y_label="% of trips no longer possible")
with t3:
    sc_choice = st.radio("Network", rob.scope.unique(), horizontal=True, key="rob_scope")
    curve = rob[rob.scope == sc_choice].pivot(index="airports_closed", columns="strategy",
                                              values="pct_in_largest_component")
    st.line_chart(curve, x_label="Airports closed (targets recomputed after each closure)",
                  y_label="% of airports in largest connected component",
                  color=["#FF9500", "#7C3AED", "#2EC27E"])
    st.markdown("Targeted closures fragment the network far faster than random ones. In the full network, "
                "closing Anchorage then Seattle cuts Alaska off, which is why betweenness-targeting looks so "
                "damaging; in the Lower 48 alone, degree and betweenness targeting perform about the same.")
with t4:
    st.markdown("""
**Source:** OpenFlights `routes.dat` (snapshot of June 2014) with airports from `airports.dat`, plus
`airports-extended.dat` for airports missing from it. Scheduled passenger routes only: no cargo carriers,
no frequencies or passenger counts.

**Cleaning:** nonstop domestic routes, airline duplicates and codeshares merged into one link per airport pair
(codeshare records are kept, since about 22% of pairs appear only as codeshares). Sightseeing tours
(Boulder City–Grand Canyon West, Grand Canyon–Page) and one cargo-only leg are excluded.

**Known gaps:** the Unalaska (DUT)–Anchorage route is missing, so the Dutch Harbor group and the
Boeing Field seaplane group appear disconnected from the start; they are not counted as "cut off" by closures.
Some small Alaskan routes have wrong airline names because two-letter airline codes were reused.
Results for remote airports should be checked against BTS T-100 data before being reported.
""")
