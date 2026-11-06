"""Build the background for the national overlap map: land, water, roads and place names.

Usage:
    pip install shapely        # needed only for this script; the website and tests don't use it
    python3 scripts/build_us_basemap.py

Writes data/snapshots/us_basemap.geojson and its manifest entry. Run by hand, not weekly: this is reference
geography that rarely changes. Everything is public domain and saved with the site, so the map needs no
third-party tile service (see "Map background" in docs/data-sources.md).

Each feature has a "k" property saying what it is: land (Canada, Mexico and nearby), state, lake, river, road,
city or state_label.
"""

import json
import re
import urllib.request
from datetime import date
from pathlib import Path

import shapely
from shapely.geometry import box, mapping, shape

SNAPSHOTS = Path(__file__).resolve().parent.parent / "data" / "snapshots"
# A fixed release, so a rebuild only changes when this does.
NATURAL_EARTH = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/"

# Everything the map can show. Stops before the 180th meridian, as us_states does, so Alaska doesn't wrap.
FRAME = box(-180, 14, -50, 75)
TOLERANCE = 0.008   # degrees, about 800 m, the same as the overlap shapes
MAX_LAKE_RANK = 5   # Natural Earth's scalerank: lower is more prominent
MAX_RIVER_RANK = 5
MAX_CITY_RANK = 8


def get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "celi-capstone-platform data build"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def natural_earth(name):
    print(f"  {name}", flush=True)
    return get_json(f"{NATURAL_EARTH}{name}.geojson")["features"]


def round_coords(value):
    if value and isinstance(value[0], (int, float)):
        return [round(value[0], 3), round(value[1], 3)]
    return [round_coords(v) for v in value]


def feature(geom, **props):
    shape_json = mapping(geom)
    return {"type": "Feature", "properties": props,
            "geometry": {"type": shape_json["type"], "coordinates": round_coords(shape_json["coordinates"])}}


def fit(raw, tolerance=TOLERANCE):
    """Valid geometry, cut to the frame and simplified, or None if nothing is left."""
    geom = shapely.make_valid(shape(raw))
    geom = shapely.simplify(shapely.intersection(geom, FRAME), tolerance)
    return None if geom.is_empty else geom


def polygons(geom):
    parts = [p for g in shapely.get_parts(geom) if g.geom_type in ("Polygon", "MultiPolygon")
             for p in shapely.get_parts(g)]
    return shapely.multipolygons(parts) if parts else None


def lines(geom):
    parts = [p for g in shapely.get_parts(geom) if g.geom_type in ("LineString", "MultiLineString")
             for p in shapely.get_parts(g)]
    return shapely.multilinestrings(parts) if parts else None


def main():
    print("Downloading Natural Earth...")
    out = []
    for f in natural_earth("ne_50m_admin_0_countries"):
        if f["properties"]["ADM0_A3"] != "USA":
            geom = fit(f["geometry"], 0.02)
            geom = polygons(geom) if geom else None
            if geom:
                out.append(feature(geom, k="land"))
    for f in natural_earth("ne_10m_admin_1_states_provinces"):
        if f["properties"]["adm0_a3"] == "USA":
            geom = polygons(fit(f["geometry"]))
            out.append(feature(geom, k="state", n=f["properties"]["postal"]))
            # Label the biggest piece: otherwise Michigan or Hawaii could land between islands.
            biggest = max(shapely.get_parts(geom), key=lambda p: p.area)
            out.append(feature(biggest.representative_point(), k="state_label", n=f["properties"]["postal"]))
    for f in natural_earth("ne_10m_lakes"):
        if f["properties"]["scalerank"] <= MAX_LAKE_RANK:
            geom = fit(f["geometry"])
            geom = polygons(geom) if geom else None
            if geom:
                out.append(feature(geom, k="lake"))
    rivers = []
    for f in natural_earth("ne_10m_rivers_lake_centerlines"):
        if (f["properties"]["scalerank"] or 99) <= MAX_RIVER_RANK:
            geom = fit(f["geometry"])
            geom = lines(geom) if geom else None
            if geom:
                rivers.append(geom)
    out.append(feature(lines(shapely.line_merge(shapely.union_all(rivers))), k="river"))
    for f in natural_earth("ne_10m_populated_places_simple"):
        p = f["properties"]
        if p["adm0_a3"] == "USA" and p["scalerank"] <= MAX_CITY_RANK:
            out.append(feature(shape(f["geometry"]), k="city", n=re.sub(r"\s+", " ", p["name"]), r=p["scalerank"]))

    roads = [fit(f["geometry"]) for f in natural_earth("ne_10m_roads")
             if f["properties"]["sov_a3"] == "USA" and f["properties"]["level"] == "Interstate"]
    out.append(feature(lines(shapely.line_merge(shapely.union_all([r for r in roads if r]))), k="road"))

    lines_out = [json.dumps(f, separators=(",", ":"), sort_keys=True) for f in out]
    path = SNAPSHOTS / "us_basemap.geojson"
    path.write_text('{"type":"FeatureCollection","features":[\n' + ",\n".join(lines_out) + "\n]}\n")

    manifest_path = SNAPSHOTS / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["us_basemap"] = {
        "title": "National map background: land, water, place names and interstates",
        "publisher": "Natural Earth", "license": "Public domain",
        "item_url": "https://www.naturalearthdata.com/", "layer_url": NATURAL_EARTH,
        "features": len(out), "source_last_edited": None,
        "saved_on": date.today().isoformat()}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {len(out)} features ({path.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
