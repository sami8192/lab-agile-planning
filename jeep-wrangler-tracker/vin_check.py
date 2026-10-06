#!/usr/bin/env python3
"""Vet Jeep Wrangler VINs using free, official data, and print history-report links.

Usage:
    python3 vin_check.py 1C4AJWAG5FL000000 [VIN ...]
    python3 vin_check.py --json tracker-export.json     # export from the tracker page

What it does (stdlib only, no keys needed):
  * validates the VIN check digit (catches typos and fake VINs)
  * decodes year/model/engine/plant via NHTSA vPIC
  * lists NHTSA recall campaigns for that year/make/model
  * flags the model year against the tracker's avoid/caution list
  * prints ready-made links for CarFax, AutoCheck, NICB VINCheck and NHTSA's
    per-VIN open-recall lookup

What it deliberately does NOT do: fetch CarFax/AutoCheck reports. Those are paid
services with no public consumer API, and scraping them breaks their terms.
Options for getting the report itself:
  * buy one report per finalist on carfax.com / autocheck.com (a few dollars each)
  * many dealer listings embed a free CarFax link ("Show me the CARFAX"); paste it
    into the tracker's URL field
  * ask the seller for the report (dealers have to provide one on request)
  * a paid VIN-history API under your own account, if you want automation
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

AVOID = {1997, 1998, 2001, 2007, 2008, 2012, 2019}
CAUTION = {1999, 2000, 2002, 2009, 2010, 2011, 2013, 2014}

TRANS = {**{str(d): d for d in range(10)},
         **dict(zip("ABCDEFGH", range(1, 9))), **dict(zip("JKLMN", range(1, 6))),
         "P": 7, "R": 9, **dict(zip("STUVWXYZ", range(2, 10)))}
WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def valid_vin(vin):
    if len(vin) != 17 or any(c in vin for c in "IOQ") or any(c not in TRANS for c in vin):
        return False
    total = sum(TRANS[c] * w for c, w in zip(vin, WEIGHTS))
    check = "X" if total % 11 == 10 else str(total % 11)
    return vin[8] == check


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wrangler-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def decode(vin):
    d = get(f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json")
    return d["Results"][0]


def recalls(year, make, model):
    q = urllib.parse.urlencode({"make": make, "model": model, "modelYear": year})
    try:
        return get(f"https://api.nhtsa.gov/recalls/recallsByVehicle?{q}").get("results", [])
    except urllib.error.HTTPError:
        return []


def verdict(year, model):
    y = int(year)
    # 2018 is ambiguous: JK final year vs. first-gen JL ("Wrangler" body class differs by model string)
    if y == 2018 and "JL" in model.upper():
        return "AVOID (first-year JL)"
    if y in AVOID:
        return "AVOID"
    if y in CAUTION:
        return "CAUTION"
    return "OK (target year)"


def report(vin):
    vin = vin.strip().upper()
    print("=" * 72)
    print("VIN", vin)
    if not valid_vin(vin):
        print("  !! Invalid VIN (bad length, characters or check digit): ask the seller to re-send it.")
        return
    try:
        r = decode(vin)
    except Exception as e:  # network or API trouble
        print("  could not reach NHTSA vPIC:", e)
        return
    year, make, model = r.get("ModelYear", ""), r.get("Make", ""), r.get("Model", "")
    print(f"  {year} {make} {model} {r.get('Trim', '')}  |  {r.get('BodyClass', '')}")
    print(f"  Engine: {r.get('DisplacementL', '?')}L {r.get('EngineCylinders', '?')}cyl  |  "
          f"Plant: {r.get('PlantCity', '?')}, {r.get('PlantCountry', '')}  |  Drive: {r.get('DriveType', '?')}")
    if r.get("ErrorCode", "0") not in ("0", ""):
        print("  vPIC notes:", r.get("ErrorText"))
    if make.upper() != "JEEP" or "WRANGLER" not in model.upper():
        print("  !! Not a Jeep Wrangler per the VIN. Is the listing accurate?")
    print("  Model-year verdict:", verdict(year, model))

    rc = recalls(year, make, model)
    print(f"  NHTSA recall campaigns for {year} {model}: {len(rc)}")
    for c in rc[:12]:
        print(f"    - {c.get('NHTSACampaignNumber')}: {c.get('Component')} ({c.get('ReportReceivedDate')})")
    print("  (Campaign list is per model-year. Whether THIS VIN is still open needs the lookup below.)")

    print("  Open-recall check (VIN):  https://www.nhtsa.gov/recalls?vin=" + vin)
    print("  Mopar recall check:       https://www.mopar.com/en-us/my-vehicle/recalls.html")
    print("  Theft/total-loss (free):  https://www.nicb.org/vincheck")
    print("  CarFax:                   https://www.carfax.com/vehicle/" + vin)
    print("  AutoCheck:                https://www.autocheck.com/vehiclehistory/search-by-vin?vin=" + vin)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    if argv[1] == "--json":
        with open(argv[2]) as f:
            vins = [x["vin"] for x in json.load(f) if x.get("vin")]
        if not vins:
            print("No VINs in that file yet. Add them to listings in the tracker, then re-export.")
            return 0
    else:
        vins = argv[1:]
    for v in vins:
        report(v)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
