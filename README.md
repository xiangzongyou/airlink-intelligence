# AirLink Intelligence

**Robustness, accessibility, and recovery in the US airport network**
CAP 6318 team project · Trung Hieu Le, Zongyou Xiang, Sri Nikhil Jemili

🌐 **Live website:** https://YOUR-USERNAME.github.io/airlink-intelligence/

## What this project asks

Which airport closures mainly cause detours, and which leave destinations unreachable? Can a closure look minor
nationwide but be severe for one region? We model the US domestic airline network (OpenFlights, June 2014:
605 airports, 2,883 nonstop routes) and simulate airport closures.

## Findings so far

- **Level 1 – critical airports.** Degree and betweenness disagree most for gateway airports: Anchorage has the
  highest betweenness in the country with only 34 destinations. Targeted closures fragment the network far faster
  than random ones.
- **Q1 – detours vs. loss of access.** Closing airports one at a time: 64 closures leave some destinations
  unreachable, 66 only cause detours, 475 change nothing for other airports.
- **Q2 / Level 2 – regions.** Louvain community detection finds 13 communities (modularity Q = 0.385). In the
  Lower 48 they follow airline hub networks; in Alaska they follow geography. Some closures are small nationally
  but severe regionally: closing Ketchikan loses 3.7% of US trips but cuts off 39% of Southeast Alaska's airports.

## What's in this repository

| Path | What it is |
|---|---|
| `index.html` | The interactive website (single file; open it in any browser, or via GitHub Pages) |
| `airlink_app/` | The same demo as a Python/Streamlit app |
| `analysis/` | Analysis scripts, figures and result tables (Steps 0–3) |

## Running things yourself

**Website:** just open `index.html` in a browser (needs internet for the map library and font).

**Streamlit app** (Python 3.9+):
```
cd airlink_app
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

**Analysis** (run in order; each script works from any folder):
```
python3 analysis/download_openflights.py     # step 0: get the OpenFlights data
python3 analysis/step1_filter.py             # step 1: filter routes, check data gaps, build the network
python3 analysis/step1_missing.py
python3 analysis/step1_build.py
python3 analysis/step2_level1.py             # step 2: centrality and robustness (about a minute)
python3 analysis/step2b_lower48.py
python3 analysis/step2c_figures.py
python3 analysis/step3_communities.py        # step 3: communities and regional impact (Q2)
python3 analysis/step3_airlines_regional.py
python3 analysis/step3_figure.py
```

## Data, limitations and credits

- Route and airport data: [OpenFlights](https://github.com/jpatokal/openflights) (snapshot of June 2014).
  Passenger routes only; no frequencies or passenger counts. Some small Alaskan routes are missing
  (for example Unalaska–Anchorage), and some small-carrier airline names are unreliable.
- Map outlines: `us-atlas` and `world-atlas` (derived from US Census and Natural Earth data). Charts and maps: D3.
- Next steps: backup airport pairs (Q3), reopening order after a disruption (Q4), and validation with BTS T-100 data.
