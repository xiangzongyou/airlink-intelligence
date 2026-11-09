# AirLink Intelligence: interactive demo

Interactive map of the US domestic airport network (OpenFlights, June 2014) for the CAP 6318 project.

## Run it
```
pip install -r requirements.txt
python build_data.py      # downloads OpenFlights and precomputes results (~1-2 min, once)
streamlit run app.py      # opens http://localhost:8501
```
`app_data/` is already included, so you can skip `build_data.py` unless you change the cleaning rules.

## What you can do
- Click an airport (or search in the sidebar) to see its nonstop routes, rankings, and what closing it would do.
- Add airports to "Close airports" to simulate a disruption: closed airports turn red, airports that lose
  all connection to the main network turn amber, and the panel reports trips lost vs. trips needing detours.
- Switch the map between All US, Lower 48, Alaska, and Hawaii; size airports by degree or betweenness.
- Tabs at the bottom: critical-airport rankings, single-closure impact table (Q1), robustness curves (Level 1),
  and data notes.

## Definitions
- **Trip**: any pair of open airports that could reach each other before the closure.
- **Lost**: no itinerary exists anymore. **Detour**: the shortest itinerary needs more connecting flights.
- **Cut off**: the airport is no longer in the largest connected part of the network.

## Sharing it online
Push this folder to the team GitHub repo and deploy for free at https://share.streamlit.io (pick `app.py`).
