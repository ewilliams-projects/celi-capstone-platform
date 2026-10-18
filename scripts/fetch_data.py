"""Download the map data the website shows and save it to data/snapshots/.

Usage:
    python3 scripts/fetch_data.py

Each dataset is saved as GeoJSON with one feature per line, so a change in the source data shows up as
a readable change in a pull request. data/snapshots/manifest.json records where each dataset came from,
its license, the source's own last-edit date (when the service reports one) and the date it was saved
here. A dataset's "saved_on" date only changes when its contents change.

Runs weekly in GitHub Actions (.github/workflows/refresh-data.yml), which opens a pull request when
anything changed. Standard library only.
"""

import json
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

SNAPSHOTS = Path(__file__).resolve().parent.parent / "data" / "snapshots"

HIFLD_ELECTRIC = ("https://services3.arcgis.com/OYP7N6mAJJCyH6hd/arcgis/rest/services/"
                  "Electric_Retail_Service_Territories_HIFLD/FeatureServer/0")
CO_GAS = ("https://services3.arcgis.com/DgjqnJA1rgO92Soi/arcgis/rest/services/"
          "Gas_Utility_Service_Territories/FeatureServer/0")
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"

# Colorado's border is (almost exactly) a box of latitude and longitude lines: west, south, east, north.
COLORADO_BBOX = "-109.0603,36.9924,-102.0415,41.0034"
PILOT_FRAME = "-106.3,39.35,-104.5,40.15"
MAP_CITIES = ["Denver", "Colorado Springs", "Fort Collins", "Pueblo", "Grand Junction", "Boulder", "Greeley",
              "Durango", "Alamosa", "Steamboat Springs", "Glenwood Springs", "Sterling", "Lamar", "Trinidad",
              "Gunnison", "Montrose"]
PILOT_COMMUNITIES = ["Boulder", "Denver", "Golden", "Winter Park", "Breckenridge"]

CENSUS = {"publisher": "U.S. Census Bureau TIGERweb", "license": "Public domain",
          "item_url": "https://tigerweb.geo.census.gov/"}


def envelope(bbox):
    return {"geometry": bbox, "geometryType": "esriGeometryEnvelope", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects"}


def in_list(field, values):
    return f"{field} IN (" + ",".join("'" + v.replace("'", "''") + "'" for v in values) + ")"


# Each dataset: the service layer, the query, and how it's credited. Simplification tolerances
# (maxAllowableOffset, in degrees) match what the maps need: about 50 m for territories.
DATASETS = {
    "electric": {
        "title": "Electric Retail Service Territories (HIFLD, Oak Ridge National Laboratory)",
        "publisher": "National Broadband Availability Map copy of HIFLD data", "license": "Public use",
        "item_url": "https://www.arcgis.com/home/item.html?id=597555ce8e4a4892a030784a7c657fdd",
        "layer": HIFLD_ELECTRIC,
        # WAPA and Deseret sell wholesale power to utilities, not to homes; see docs/data-sources.md.
        "params": {"where": "NAME NOT LIKE 'WAPA%' AND NAME NOT LIKE 'DESERET%'",
                   "outFields": "NAME,TYPE,CUSTOMERS,HOLDING_CO", "geometryPrecision": "5",
                   "maxAllowableOffset": "0.0005", **envelope(COLORADO_BBOX)},
    },
    "gas": {
        "title": "Gas Utility Service Territories (Colorado GeoData)",
        "publisher": "State of Colorado", "license": "Public; provided without warranty",
        "item_url": "https://geodata.colorado.gov/datasets/47935f56eddd4d1781328c60c8517c96_0/explore",
        "layer": CO_GAS,
        "params": {"where": "1=1", "outFields": "NAME,HOLDINGCO,TYPE,TOTAL_CUST", "geometryPrecision": "5",
                   "maxAllowableOffset": "0.0005"},
    },
    "counties": {
        "title": "Colorado counties", **CENSUS, "layer": TIGERWEB + "State_County/MapServer/1",
        "params": {"where": "STATE='08'", "outFields": "BASENAME", "geometryPrecision": "5",
                   "maxAllowableOffset": "0.0005"},
    },
    "states": {
        "title": "State outlines (map background)", **CENSUS, "layer": TIGERWEB + "State_County/MapServer/0",
        "params": {"where": "1=1", "outFields": "STUSAB", "geometryPrecision": "4", "maxAllowableOffset": "0.01",
                   **envelope("-112,35,-99,43")},
    },
    "interstates": {
        "title": "Interstates in Colorado (map background)", **CENSUS,
        "layer": TIGERWEB + "Transportation/MapServer/1",
        "params": {"where": "1=1", "outFields": "MTFCC", "geometryPrecision": "4", "maxAllowableOffset": "0.002",
                   **envelope(COLORADO_BBOX)},
    },
    "cities": {
        "title": "City names shown on the statewide map", **CENSUS,
        "layer": TIGERWEB + "Places_CouSub_ConCity_SubMCD/MapServer/4",
        "params": {"where": "STATE='08' AND " + in_list("BASENAME", MAP_CITIES), "outFields": "BASENAME",
                   "geometryPrecision": "4", "maxAllowableOffset": "0.005"},
    },
    "pilot_places": {
        "title": "Gas Planning Pilot Program communities (city limits)", **CENSUS,
        "layer": TIGERWEB + "Places_CouSub_ConCity_SubMCD/MapServer/4",
        "params": {"where": "STATE='08' AND " + in_list("BASENAME", PILOT_COMMUNITIES), "outFields": "BASENAME",
                   "geometryPrecision": "5", "maxAllowableOffset": "0.0005"},
    },
    "pilot_roads_primary": {
        "title": "Interstates around the pilot communities", **CENSUS,
        "layer": TIGERWEB + "Transportation/MapServer/1",
        "params": {"where": "1=1", "outFields": "MTFCC", "geometryPrecision": "4", "maxAllowableOffset": "0.001",
                   **envelope(PILOT_FRAME)},
    },
    "pilot_roads_secondary": {
        "title": "State and US highways around the pilot communities", **CENSUS,
        "layer": TIGERWEB + "Transportation/MapServer/4",
        "params": {"where": "1=1", "outFields": "MTFCC", "geometryPrecision": "4", "maxAllowableOffset": "0.001",
                   **envelope(PILOT_FRAME)},
    },
}


def get_json(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "celi-capstone-platform data refresh"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.load(response)
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"{url}: {data['error']}")
    return data


def fetch_features(dataset):
    params = {"outSR": "4326", "f": "geojson", "orderByFields": "OBJECTID", **dataset["params"]}
    data = get_json(dataset["layer"] + "/query", params)
    if data.get("exceededTransferLimit") or (data.get("properties") or {}).get("exceededTransferLimit"):
        raise RuntimeError(f"{dataset['layer']}: more features than one request returns; add paging")
    features = data.get("features") or []
    if not features:
        raise RuntimeError(f"{dataset['layer']}: no features returned")
    # Keep only geometry and the requested properties, so the files hold nothing unexpected.
    return [{"type": "Feature", "properties": f.get("properties") or {}, "geometry": f["geometry"]}
            for f in features]


def source_last_edited(layer_url):
    info = get_json(layer_url, {"f": "json"})
    edited = (info.get("editingInfo") or {}).get("lastEditDate")
    if not edited:
        return None
    return datetime.fromtimestamp(edited / 1000, tz=timezone.utc).date().isoformat()


def to_geojson_text(features):
    lines = [json.dumps(f, separators=(",", ":"), sort_keys=True) for f in features]
    return '{"type":"FeatureCollection","features":[\n' + ",\n".join(lines) + "\n]}\n"


def main():
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    manifest_path = SNAPSHOTS / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest = {}
    for name, dataset in DATASETS.items():
        features = fetch_features(dataset)
        text = to_geojson_text(features)
        path = SNAPSHOTS / f"{name}.geojson"
        changed = not path.exists() or path.read_text() != text
        if changed:
            path.write_text(text)
        manifest[name] = {
            "title": dataset["title"],
            "publisher": dataset["publisher"],
            "license": dataset["license"],
            "item_url": dataset["item_url"],
            "layer_url": dataset["layer"],
            "features": len(features),
            "source_last_edited": source_last_edited(dataset["layer"]),
            "saved_on": date.today().isoformat() if changed else old.get(name, {}).get("saved_on"),
        }
        print(f"{name:<22} {len(features):>4} features  {'updated' if changed else 'unchanged'}")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # one failed source must not leave a half-updated snapshot unnoticed
        print(f"Data refresh failed: {error}", file=sys.stderr)
        sys.exit(1)
