"""Step 0: download the OpenFlights files (June 2014 snapshot) into analysis/data/."""
import os, urllib.request
os.chdir(os.path.dirname(os.path.abspath(__file__))); os.makedirs("data", exist_ok=True)
BASE = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/"
for f in ["routes.dat", "airports.dat", "airports-extended.dat", "airlines.dat"]:
    print("downloading", f); urllib.request.urlretrieve(BASE + f, os.path.join("data", f))
print("done")
