# AirLink Intelligence

**Robustness, accessibility, and recovery in the US airport network**
CAP 6318 team project · Trung Hieu Le, Zongyou Xiang, Sri Nikhil Jemili

🌐 **Live website:** https://xiangzongyou.com/airlink-intelligence/

## What this project asks

Which airport closures mainly cause detours, and which leave destinations unreachable? Can a closure look minor
nationwide but be severe for one region? How many travelers does a closure affect? We model the US domestic airline
network in 2014 and simulate airport closures, using three public data sources.

## Data sources

| Source | What it contains | How we use it |
|---|---|---|
| [OpenFlights](https://github.com/jpatokal/openflights) `routes.dat` (June 2014 snapshot), `airports.dat`, `airports-extended.dat` | Nonstop routes with the airlines that fly them; airport names, locations and elevations | The network: 605 airports and 2,883 routes. All network results and the website map |
| [BTS T-100 Domestic Segment](https://www.transtats.bts.gov/DataIndex.asp), all carriers, 2014 | Passengers, seats and flights on every nonstop route, every month | Checks the network against official route counts |
| [BTS Airline Origin and Destination Survey (DB1B)](https://www.transtats.bts.gov/DataIndex.asp), Market table, April–June 2014 | A 10% sample of domestic tickets: each traveler's origin, destination and connecting airports | Traveler counts on the website |

## Findings so far

- **Critical airports.** Degree and betweenness disagree most for gateway airports: Anchorage has the highest
  betweenness in the country with only 34 destinations. Targeted closures fragment the network far faster than random
  ones (after 10 closures the largest connected part keeps 96% of airports for random closures, 80% by degree, 51% by
  betweenness).
- **Detours vs. loss of access.** Closing airports one at a time: 64 closures leave some destinations unreachable,
  66 only cause detours, 475 change nothing for other airports.
- **Regions.** Louvain community detection finds 13 communities (modularity Q = 0.385). In the Lower 48 they follow
  airline hub networks; in Alaska they follow geography. Some closures are small nationally but severe regionally:
  closing Ketchikan loses 3.7% of US trips but cuts off 39% of Southeast Alaska's airports.
- **The network checks out.** 98.9% of our OpenFlights routes (2,851 of 2,883) appear in 2014 T-100, and 97.5% of
  T-100 passengers fly routes in our network.
- **Travelers.** DB1B shows about 1.31 million domestic air trips a day in spring 2014: 67% nonstop, 31% with one
  connection, 2% with two or more. Hubs carry many people who never leave the airport: 58% of travelers using
  Charlotte and 49% using Atlanta only change planes there. Closing Atlanta alone leaves about 73,500 travelers a day
  unable to travel and 65,300 more forced to reroute.
- **Backup airport pairs** (side result). 23 pairs where closing either airport alone keeps everyone connected but
  closing both cuts someone off; most are small Alaska communities, and T-100 shows most Alaska cases are OpenFlights
  gaps. Two Lower 48 cases hold up fully: Cincinnati + Lunken (Morristown, NJ) and San Diego + Burbank (Imperial, CA).

## What's in this repository

| Path | What it is |
|---|---|
| `index.html` | The interactive website (one file; open it in any browser, or via GitHub Pages) |
| `airlink_app/` | The same demo as a Python/Streamlit app |
| `analysis/` | Analysis scripts, figures and result tables (steps 0–6) |

## Running things yourself

**Website:** open `index.html` in a browser (needs internet for the map library and font).

**Streamlit app** (Python 3.9+):
```
cd airlink_app
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

**Analysis** (Python 3.9+; run in order; each script works from any folder):
```
python3 -m pip install pandas numpy networkx scipy matplotlib scikit-learn adjustText
```
```
python3 analysis/download_openflights.py     # step 0: get the OpenFlights data
python3 analysis/step1_filter.py             # step 1: filter routes, check data gaps, build the network
python3 analysis/step1_missing.py
python3 analysis/step1_build.py
python3 analysis/step2_level1.py             # step 2: centrality and robustness (about a minute)
python3 analysis/step2b_lower48.py
python3 analysis/step2c_figures.py
python3 analysis/step3_communities.py        # step 3: communities and regional impact
python3 analysis/step3_airlines_regional.py
python3 analysis/step3_figure.py
python3 analysis/step4_backup_pairs.py       # step 4: backup airport pairs (1-2 minutes)
python3 analysis/step5_t100_check.py         # step 5: check the network against BTS T-100 (zip included)
python3 analysis/step6_db1b_trips.py         # step 6: real trips from DB1B (download the zip first, see below)
```

### Data you download yourself

Both BTS tables come from https://www.transtats.bts.gov/DataIndex.asp. Put the downloaded zip, unrenamed, in `analysis/`.

- **T-100** (already included as `analysis/T_T100D_SEGMENT_ALL_CARRIER_*.zip`, 5 MB): Air Carrier Statistics
  (Form 41 Traffic) – All Carriers → T-100 Domestic Segment (All Carriers) → Download. Year 2014, all months. Fields:
  DEPARTURES_SCHEDULED, DEPARTURES_PERFORMED, SEATS, PASSENGERS, DISTANCE, UNIQUE_CARRIER, UNIQUE_CARRIER_NAME,
  ORIGIN_AIRPORT_ID, ORIGIN, ORIGIN_CITY_NAME, ORIGIN_STATE_ABR, DEST_AIRPORT_ID, DEST, DEST_CITY_NAME, DEST_STATE_ABR,
  YEAR, MONTH, CLASS.
- **DB1B** (not included: about 93 MB zipped, 1.6 GB unzipped): Airline Origin and Destination Survey (DB1B) →
  DB1BMarket → Download. Year 2014, Quarter 2. The prezipped file with all fields works; the script reads only
  Origin, Dest, AirportGroup and Passengers. Its output, `analysis/db1b_itineraries_2014q2.csv`, is included, so
  everything else runs without the zip.

## Limitations

- Everything describes 2014; air travel is higher today and some routes have changed. Routes that began after June
  2014, such as Dallas Love Field's long-distance flights from October, are not in the network.
- OpenFlights lacks a few real routes, such as Unalaska–Anchorage, and some small-carrier airline names are
  unreliable. Codeshare records are kept and merged into one link per airport pair.
- The website's traveler counts assume rerouted travelers find seats; flight capacity is not modeled.

## Credits

Route and airport data: OpenFlights. Passenger and ticket data: U.S. Bureau of Transportation Statistics (T-100,
DB1B). Map outlines: `us-atlas` and `world-atlas` (derived from US Census and Natural Earth data). Charts and maps: D3.
