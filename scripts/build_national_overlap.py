"""Build the national map of where gas and electric utility territories overlap, and who runs them.

Usage:
    pip install shapely        # needed only for this script; the website and tests don't use it
    python3 scripts/build_national_overlap.py

Writes data/snapshots/us_overlap.geojson and us_states.geojson and their manifest entries. Unlike
fetch_data.py this doesn't run weekly: both national sources are frozen copies of HIFLD Open, which shut
down in 2025, and overlaying the whole country takes a few minutes. Rerun it if Colorado's gas data changes
in a way that matters, or if the company ownership tables below need updating.

Each output shape is one combination of gas and electric utilities, sorted into a class:
    same       one company provides both
    parent     separate companies with the same parent
    uncertain  same or parent, but the data also lists another utility there
    different  gas and electric come from unrelated companies
    no_electric  gas territory where the data lists no retail electric utility
Land with no shape has no gas territory in the data.
"""

import json
import math
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

import shapely
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.strtree import STRtree

SNAPSHOTS = Path(__file__).resolve().parent.parent / "data" / "snapshots"

ELECTRIC_LAYER = ("https://services3.arcgis.com/OYP7N6mAJJCyH6hd/arcgis/rest/services/"
                  "Electric_Retail_Service_Territories_HIFLD/FeatureServer/0")
ELECTRIC_ITEM = "https://www.arcgis.com/home/item.html?id=597555ce8e4a4892a030784a7c657fdd"
# An ArcGIS Online copy of HIFLD's national gas layer, published February 2021. HIFLD's own site is gone.
GAS_LAYER = ("https://services5.arcgis.com/HDRa0B57OVrv2E1q/arcgis/rest/services/"
             "Natural_Gas_Local_Distribution_Company_Service_Territories/FeatureServer/0")
GAS_ITEM = "https://www.arcgis.com/home/item.html?id=b3c5fcdbf67c4cf2a2a660a859f7a3d2"
STATES_LAYER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/0"

DOWNLOAD_TOLERANCE = "0.002"  # degrees, about 200 m
OUTPUT_TOLERANCE = 0.008      # degrees, about 800 m: the national map doesn't need more, and it keeps the file small
GRID = 0.0002                 # snap overlay results to about 20 m so slightly misaligned borders don't fail
MIN_SQ_MI = 0.1

# Not retail utilities: federal and regional wholesale suppliers and power agencies, drawn across their
# customers' territories, plus a transit agency. Compare the same filter for Colorado in fetch_data.py.
NOT_RETAIL_ELECTRIC = re.compile(
    r"^WAPA|BONNEVILLE POWER|^TENNESSEE VALLEY AUTHORITY|^DESERET|^BASIN ELECTRIC POWER|^WOLVERINE POWER SUPPLY|"
    r"^WPPI|^EAST KENTUCKY POWER|^SAM RAYBURN|^SOUTH TEXAS ELECTRIC COOP|^BADGER POWER|^NORTH CAROLINA EASTERN M|"
    r"^OHIO VALLEY ELECTRIC|^MASSACHUSETTS BAY TRANS|^TUOLUMNE COUNTY PUB POWER")
NOT_US = {"AB", "BC", "PR", "VI", "GU", "AS", "MP"}
# Interstate pipelines and producers with a handful of direct customers, not local gas systems. Kinder
# Morgan's record alone covers about 65,000 square miles and 101 customers.
NOT_DISTRIBUTION_GAS = re.compile(
    r"^KINDER MORGAN|^FLORIDA GAS TRANSMISSION|^AMERICAN MIDSTREAM|^TUSCARORA|^PHILLIPS T W|^PANTHER NATURAL|^SWISSVALE")

# Who owns what. Neither source is reliable on this: 94% of the gas records have no holding company and
# many have changed hands since the data was collected (for example AGL is now Southern Company Gas,
# SCANA is now Dominion, Vectren is now CenterPoint). So this is a table written and checked by hand,
# using ownership as of 2026. Each row: company, parent, gas name pattern, electric name pattern.
COMPANIES = [
    ("Xcel Energy (Colorado)", "Xcel Energy", r"PUBLIC SERVICE CO OF COLORADO", r"^PUBLIC SERVICE CO OF COLORADO"),
    ("Xcel Energy (Northern States Power)", "Xcel Energy", r"NORTHERN STATES POWER", r"^NORTHERN STATES POWER"),
    ("Xcel Energy (Southwestern Public Service)", "Xcel Energy", None, r"^SOUTHWESTERN PUBLIC SERVICE"),
    ("Duke Energy Ohio", "Duke Energy", r"^DUKE ENERGY OHIO", r"^DUKE ENERGY OHIO"),
    ("Duke Energy Kentucky", "Duke Energy", r"^DUKE ENERGY KENTUCKY", r"^DUKE ENERGY KENTUCKY"),
    ("Duke Energy Carolinas and Progress", "Duke Energy", None, r"^DUKE ENERGY (CAROLINAS|PROGRESS)"),
    ("Duke Energy Indiana", "Duke Energy", None, r"^DUKE ENERGY INDIANA"),
    ("Duke Energy Florida", "Duke Energy", None, r"^DUKE ENERGY FLORIDA"),
    ("Piedmont Natural Gas", "Duke Energy", r"^PIEDMONT NATURAL GAS", None),
    ("Dominion Energy South Carolina", "Dominion Energy", r"^SOUTH CAROLINA ELECTRIC & GAS", r"^(DOMINION ENERGY SOUTH CAROLINA|SOUTH CAROLINA ELECTRIC)"),
    ("Georgia Power", "Southern Company", None, r"^GEORGIA POWER"),
    ("Alabama Power", "Southern Company", None, r"^ALABAMA POWER"),
    ("Mississippi Power", "Southern Company", None, r"^MISSISSIPPI POWER"),
    ("Southern Company Gas", "Southern Company", r"^(ATLANTA GAS LIGHT|NICOR|VIRGINIA NATURAL GAS|CHATTANOOGA GAS)", None),
    ("CenterPoint Energy Houston Electric", "CenterPoint Energy", None, r"^CENTERPOINT ENERGY"),
    ("CenterPoint Energy gas", "CenterPoint Energy", r"^CENTERPOINT ENERGY|^INDIANA GAS AND ELECTRIC|^VECTREN", None),
    ("CenterPoint Energy Indiana South", "CenterPoint Energy", r"^SOUTHERN INDIANA GAS", r"^SOUTHERN INDIANA GAS"),
    ("Ameren Illinois", "Ameren", r"^AMEREN ILLINOIS", r"^AMEREN ILLINOIS"),
    ("Ameren Missouri", "Ameren", r"^(UNION ELECTRIC|AMEREN MISSOURI)", r"^UNION ELECTRIC"),
    ("NIPSCO", "NiSource", r"^NORTHERN INDIANA PUB", r"^NORTHERN INDIANA PUB"),
    ("We Energies (Wisconsin Electric)", "WEC Energy Group", r"^WISCONSIN ELECTRIC POWER", r"^WISCONSIN ELECTRIC POWER"),
    ("We Energies (Wisconsin Gas)", "WEC Energy Group", r"^WISCONSIN GAS", None),
    ("Wisconsin Public Service", "WEC Energy Group", r"^WISCONSIN PUB", r"^WISCONSIN PUBLIC SERVICE"),
    ("Upper Michigan Energy Resources", "WEC Energy Group", None, r"^UPPER MICHIGAN ENERGY"),
    ("WEC gas utilities", "WEC Energy Group", r"^(PEOPLES GAS LT|NORTH SHORE GAS|MINNESOTA ENERGY RESOURCES|MICHIGAN GAS UTILITIES)", None),
    ("Alliant Energy (Interstate Power and Light)", "Alliant Energy", r"^INTERSTATE PWR", r"^INTERSTATE POWER AND LIGHT"),
    ("Alliant Energy (Wisconsin Power and Light)", "Alliant Energy", r"^WISCONSIN POWER AND LIGHT", r"^WISCONSIN POWER & LIGHT"),
    ("MidAmerican Energy", "Berkshire Hathaway Energy", r"^MIDAMERICAN", r"^MIDAMERICAN"),
    ("NV Energy (Sierra Pacific)", "Berkshire Hathaway Energy", r"^NV ENERGY", r"^SIERRA PACIFIC POWER"),
    ("DTE Electric", "DTE Energy", None, r"^DTE ELECTRIC"),
    ("DTE Gas", "DTE Energy", r"^DTE GAS", None),
    ("Consumers Energy", "CMS Energy", r"^CONSUMERS ENERGY", r"^CONSUMERS ENERGY"),
    ("Pacific Gas & Electric", "PG&E Corporation", r"^PACIFIC GAS & ELECTRIC", r"^PACIFIC GAS & ELECTRIC"),
    ("San Diego Gas & Electric", "Sempra", r"^SAN DIEGO GAS", r"^SAN DIEGO GAS"),
    ("Southern California Gas", "Sempra", r"^SOUTHERN CALIFORNIA GAS", None),
    ("Avista", "Avista", r"^AVISTA", r"^AVISTA"),
    ("Puget Sound Energy", "Puget Sound Energy", r"^PUGET SOUND ENERGY", r"^PUGET SOUND ENERGY"),
    ("NorthWestern Energy", "NorthWestern", r"^NORTHWESTERN ENERGY", r"^NORTHWESTERN ENERGY"),
    ("Montana-Dakota Utilities", "MDU Resources", r"^MONTANA-DAKOTA", r"^MONTANA-DAKOTA"),
    ("Black Hills gas", "Black Hills Corporation", r"^BLACK HILLS ENERGY", None),
    ("Black Hills electric", "Black Hills Corporation", None, r"^(BLACK HILLS (COLORADO ELECTRIC|POWER)|CHEYENNE LIGHT)"),
    ("Madison Gas & Electric", "MGE Energy", r"^MADISON GAS", r"^MADISON GAS"),
    ("Superior Water, Light & Power", "ALLETE", r"^SUPERIOR WATER", r"^SUPERIOR WATER"),
    ("Consolidated Edison of New York", "Consolidated Edison", r"^CONSOLIDATED EDISON", r"^CONSOLIDATED EDISON"),
    ("Orange & Rockland", "Consolidated Edison", r"^ORANGE AND ROCKLAND", r"^(ORANGE & ROCKLAND|ROCKLAND ELECTRIC)"),
    ("Pike County Light & Power", "Corning Natural Gas", r"^PIKE CTY", r"^PIKE COUNTY LIGHT"),
    ("Niagara Mohawk (National Grid)", "National Grid", r"^NIAGARA MOHAWK", r"^NIAGARA MOHAWK"),
    ("Massachusetts Electric (National Grid)", "National Grid", None, r"^(MASSACHUSETTS ELECTRIC|NANTUCKET ELECTRIC)"),
    ("National Grid gas", "National Grid", r"^(NATIONAL GRID|BOSTON GAS|BROOKLYN UNION|KEYSPAN)", None),
    ("Eversource electric", "Eversource Energy", None, r"^(NSTAR ELECTRIC|CONNECTICUT LIGHT & POWER|PUBLIC SERVICE CO OF NH|PUBLIC SERVICE CO OF NEW HAMPSHIRE)"),
    ("Eversource gas", "Eversource Energy", r"^(NSTAR GAS|YANKEE GAS|COLUMBIA GAS OF MASSACHUSETTS)", None),
    ("NYSEG", "Avangrid", r"^NYS ELECTRIC", r"^NEW YORK STATE ELECTRIC"),
    ("Rochester Gas & Electric", "Avangrid", r"^ROCHESTER GAS", r"^ROCHESTER GAS"),
    ("Avangrid electric", "Avangrid", None, r"^(CENTRAL MAINE POWER|UNITED ILLUMINATING)"),
    ("Avangrid gas", "Avangrid", r"^(SOUTHERN CONNECTICUT GAS|CONNETICUT NATURAL GAS|CONNECTICUT NATURAL GAS|BERKSHIRE GAS|MAINE NATURAL GAS)", None),
    ("Fitchburg Gas & Electric", "Unitil", r"^FITCHBURG GAS", r"^FITCHBURG GAS"),
    ("Unitil Energy Systems", "Unitil", None, r"^UNITIL ENERGY"),
    ("Northern Utilities", "Unitil", r"^NORTHERN UTILITIES", None),
    ("PSE&G", "PSEG", r"^PUBLIC SERVICE ELEC", r"^PUBLIC SERVICE ELEC"),
    ("Baltimore Gas & Electric", "Exelon", r"^BALTIMORE GAS", r"^BALTIMORE GAS"),
    ("PECO", "Exelon", r"^PECO", r"^PECO"),
    ("Delmarva Power", "Exelon", r"^DELMARVA", r"^DELMARVA"),
    ("Louisville Gas & Electric", "PPL", r"^LOUISVILLE GAS", r"^LOUISVILLE GAS"),
    ("Kentucky Utilities", "PPL", None, r"^KENTUCKY UTILITIES"),
    ("Rhode Island Energy", "PPL", r"^NARRAGANSETT", r"NARRAGANSETT ELECTRIC"),
    ("UGI Utilities", "UGI", r"^(UGI|PPL GAS UTILITIES)", r"^UGI UTILITIES"),
    ("Tampa Electric", "Emera", None, r"^TAMPA ELECTRIC"),
    ("Peoples Gas System", "Emera", r"^PEOPLES GAS SYSTEMS", None),
    ("Tucson Electric Power", "Fortis", None, r"^TUCSON ELECTRIC"),
    ("UNS Electric", "Fortis", None, r"^UNS ELECTRIC"),
    ("UNS Gas", "Fortis", r"^UNISOURCE ENERGY", None),
    ("Central Hudson", "Fortis", r"^CENTRAL HUDSON", r"^CENTRAL HUDSON"),
    ("Liberty (New Hampshire) gas", "Algonquin Power & Utilities", r"^LIBERTY UTILITIES \(ENERGYNORTH", None),
    ("Liberty (New Hampshire) electric", "Algonquin Power & Utilities", None, r"^LIBERTY UTILITIES \(GRANITE STATE"),
    ("Liberty (Empire District) electric", "Algonquin Power & Utilities", None, r"^EMPIRE DISTRICT"),
    ("Liberty (Empire District) gas", "Algonquin Power & Utilities", r"^EMPIRE (DISTRICT|GAS)", None),
    ("Entergy Louisiana", "Entergy", r"^ENTERGY - GULF STATES", r"^ENTERGY LOUISIANA"),
    ("Entergy New Orleans", "Entergy", r"^ENTERGY NEW ORLEANS", r"^ENTERGY NEW ORLEANS"),
    ("Green Mountain Power", "Energir", None, r"^GREEN MOUNTAIN POWER"),
    ("Vermont Gas", "Energir", r"^VERMONT GAS", None),
    ("Florida Public Utilities", "Chesapeake Utilities", r"^FLORIDA PUBLIC UTILITIES", r"^FLORIDA PUBLIC UTILITIES"),
    ("Mt. Carmel Public Utility", "Mt. Carmel Public Utility", r"^MOUNT CARMEL PUB", r"^MT CARMEL PUBLIC"),
    ("Barrow Utilities & Electric Coop", "Barrow Utilities & Electric Coop", r"^BARROW UTILITY", r"^BARROW UTILS"),
    ("Midwest Energy", "Midwest Energy", r"^MIDWEST ENERGY", r"^MIDWEST ENERGY"),
    ("Navajo Tribal Utility Authority", "Navajo Tribal Utility Authority", r"^NAVAJO TRIBAL", r"^NAVAJO TRIBAL"),
    ("Lower Valley Energy", "Lower Valley Energy", r"^LOWER VALLEY ENERGY", r"^LOWER VALLEY ENERGY"),
    ("Presque Isle Electric & Gas Coop", "Presque Isle Electric & Gas Coop", r"^PRESQUE ISLE", r"^PRESQUE ISLE"),
    ("Rock Energy Cooperative", "Rock Energy Cooperative", r"^ROCK ENERGY", r"^ROCK ENERGY"),
    ("Duncan Valley Electric Coop", "Duncan Valley Electric Coop", r"^DUNCAN VALLEY", r"^DUNCAN VALLEY"),
    ("Graham County Electric Coop", "Graham County Electric Coop", None, r"^GRAHAM COUNTY ELECTRIC"),
    ("Graham County Utilities", "Graham County Electric Coop", r"^GRAHAM COUNTY UTILITIES", None),
    ("Holyoke Gas & Electric", "City of Holyoke", r"^HOLYOKE GAS", r"^CITY OF HOLYOKE"),
    ("City Utilities of Springfield", "City of Springfield, Missouri", r"^SPRINGFIELD CITY UTIL", r"^CITY UTILITIES OF SPRINGFIELD"),
    ("Greenwood Commissioners of Public Works", "City of Greenwood, South Carolina", r"^GREENWOOD COMM", r"^GREENWOOD CPW"),
]
PARENTS = {name: parent for name, parent, _, _ in COMPANIES}

# Local public utilities: matched when their place names and state agree, e.g. electric "CITY OF TRINIDAD -
# (CO)" and gas "TRINIDAD, CITY OF". These words end the place name.
PUBLIC_WORDS = re.compile(
    r"\b(MUNICIPAL|MUNI|MUN|NATURAL|NAT|GAS|SYSTEM|SYS|DEPARTMENT|DEPT|DEP|UTILITY|UTILITIES|UTILITES|UTIL|BOARD|"
    r"COMMISSION|COMM|ENERGY|PUBLIC|PUB|WORKS|WTR|WATER|LIGHT|LT|ELECTRIC|ELEC|POWER|PWR|DIVISION|DIV|AUTHORITY|"
    r"COMPANY|CO|CORPORATION|CORP|REGIONAL|COUNTY)\b.*$")
PLACE_ALIASES = {"FORD MEADE": "FORT MEADE", "FT PIERCE": "FORT PIERCE", "LENOIR CITY": "LENOIR",
                 "MT PLEASANT": "MOUNT PLEASANT", "HENDERSON CITY": "HENDERSON", "PARIS-HENRY": "PARIS"}
# Same place name but separate organizations: these gas districts aren't the local electric departments.
PUBLIC_EXCEPTIONS = {("OAK RIDGE", "TN"), ("SEVIER", "TN")}
# "Stuart Gas Co" and the like may be private companies that only share a town's name, so they don't match.
PRIVATE_STYLE = re.compile(r"^(?!.*\bMUN\b).*\b(GAS|NATURAL GAS) (CO|COMPANY|CORP)\b")


def place_of(name):
    name = name.upper().replace(".", "")
    name = re.sub(r"\s*-?\s*\([A-Z]{2}\)\s*$", "", name)
    name = re.sub(r"^(CITY|TOWN|VILLAGE|BOROUGH) OF ", "", name)
    name = re.sub(r",\s*(CITY|TOWN|VILLAGE|BOROUGH) OF\b.*$", "", name)
    name = PUBLIC_WORDS.sub("", name).strip(" ,-&")
    return PLACE_ALIASES.get(name, name)


def company(name, service):
    """The name of the company in COMPANIES that this record belongs to, or None."""
    for row in COMPANIES:
        pattern = row[2] if service == "gas" else row[3]
        if pattern and re.search(pattern, name):
            return row[0]
    return None


def public_utility(props, service):
    """A key like 'PUBLIC TRINIDAD CO' for records that look like a local public utility, or None."""
    name, kind = props["NAME"], (props.get("TYPE") or "").upper()
    if company(name, service):  # e.g. Chattanooga Gas is Southern Company's, not the city's
        return None
    if service == "gas":
        if PRIVATE_STYLE.search(name):
            return None
        # The gas TYPE field is unreliable in both directions, so a place name in a utility's name also counts.
        if kind not in ("MUNICIPAL", "OTHER") and not re.search(
                r"(CITY|TOWN|VILLAGE|BOROUGH) OF|GAS (SYSTEM|DEPT|DEPARTMENT)|WATER WORKS|ENERGY AUTHORITY|^WILSON ENERGY", name):
            return None
    elif kind in ("INVESTOR OWNED", "COOPERATIVE", "FEDERAL"):
        return None
    elif not re.search(r"^(CITY|TOWN|VILLAGE|BOROUGH) OF|UTILIT|BOARD|COMM\b|ELECTRIC GAS|POWER & LIGHT|AUTHORITY|COUNTY|-\s*\([A-Z]{2}\)$", name):
        return None
    place = place_of(name)
    state = props.get("STATE")
    tag = re.search(r"\(([A-Z]{2})\)\s*$", name)
    state = tag.group(1) if tag else state
    if not place or (place, state) in PUBLIC_EXCEPTIONS:
        return None
    return f"PUBLIC {place} {state}"


def relation(gas, electric):
    """'same', 'parent', or None for a gas record and an electric record."""
    if gas["company"] and electric["company"]:
        if gas["company"] == electric["company"]:
            return "same"
        if PARENTS[gas["company"]] == PARENTS[electric["company"]]:
            return "parent"
    if gas["public"] and gas["public"] == electric["public"]:
        return "same"
    return None


def get_json(url, params):
    request = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                     headers={"User-Agent": "celi-capstone-platform data build"})
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.load(response)
    if "error" in data:
        raise RuntimeError(f"{url}: {data['error']}")
    return data


def download(layer, fields, where="1=1", tolerance=DOWNLOAD_TOLERANCE, order="OBJECTID"):
    features, offset = [], 0
    while True:
        data = get_json(layer + "/query", {
            "where": where, "outFields": fields, "outSR": "4326", "f": "geojson", "orderByFields": order,
            "maxAllowableOffset": tolerance, "geometryPrecision": "4", "resultOffset": offset,
            "resultRecordCount": 200})
        page = data.get("features") or []
        features += [f for f in page if f.get("geometry")]
        offset += len(page)
        print(f"  {layer.split('/services/')[1][:40]:<42}{offset}", flush=True)
        if len(page) < 200 and not data.get("exceededTransferLimit"):
            return features


def sq_mi(geom):
    """Approximate area in square miles, close enough for filtering and rounded summaries."""
    return 0.0 if geom.is_empty else geom.area * 69.0 ** 2 * math.cos(math.radians(geom.centroid.y))


def polygon_parts(geom):
    return [p for g in shapely.get_parts(geom) if isinstance(g, (Polygon, MultiPolygon))
            for p in shapely.get_parts(g)]


def polygons_only(geom):
    """Just the polygons from an overlay result (which can include stray lines and points), repaired if needed."""
    if geom.is_empty:
        return None
    flat = polygon_parts(geom)
    if not flat:
        return None
    result = MultiPolygon(flat)
    if result.is_valid:
        return result
    repaired = polygon_parts(shapely.make_valid(result))
    result = MultiPolygon(repaired)
    return result if result.is_valid else shapely.buffer(result, 0)


def clean(geometry):
    # Round first and repair afterward: GEOS can fail when snapping some source shapes to a grid.
    geom = polygons_only(shapely.make_valid(shapely.set_precision(shape(geometry), GRID, mode="pointwise")))
    return polygons_only(shapely.buffer(geom, 0)) if geom else None


def load_records():
    print("Downloading the national layers...")
    electric, gas = [], []
    for f in download(ELECTRIC_LAYER, "NAME,STATE,TYPE,CUSTOMERS"):
        p = f["properties"]
        p["NAME"] = (p["NAME"] or "").replace("\xa0", " ").strip()
        if p["STATE"] in NOT_US or NOT_RETAIL_ELECTRIC.search(p["NAME"]):
            continue
        geom = clean(f["geometry"])
        if geom:
            electric.append({"name": p["NAME"], "geom": geom, "company": company(p["NAME"], "electric"),
                             "public": public_utility(p, "electric")})
    # Colorado's own gas layer is newer than the national copy, and it's what the statewide map uses.
    colorado = json.loads((SNAPSHOTS / "gas.geojson").read_text())["features"]
    national = [f for f in download(GAS_LAYER, "NAME,STATE,TYPE,TOTAL_CUST") if f["properties"]["STATE"] != "CO"]
    for f in national + [{**f, "properties": {**f["properties"], "STATE": "CO"}} for f in colorado]:
        p = f["properties"]
        p["NAME"] = (p["NAME"] or "").strip()
        if NOT_DISTRIBUTION_GAS.search(p["NAME"]):
            continue
        geom = clean(f["geometry"])
        if geom:
            gas.append({"name": p["NAME"], "geom": geom, "company": company(p["NAME"], "gas"),
                        "public": public_utility(p, "gas")})
    print(f"Kept {len(electric)} electric and {len(gas)} gas records")
    return electric, gas


def is_sliver(geom):
    """Long thin leftovers along borders that nearly line up. They aren't real overlaps."""
    area = sq_mi(geom)
    if area < MIN_SQ_MI:
        return True
    perimeter = geom.length * 69.0 * math.cos(math.radians(geom.centroid.y))
    return area < 10 and 4 * math.pi * area / max(perimeter ** 2, 1e-9) < 0.04


def split(cells, new):
    """Split each (geometry, claim indexes) cell by one more territory."""
    out = []
    for geom, held in cells:
        try:
            parts = cut(geom, new["geom"])
        except shapely.errors.GEOSException:
            # A rare shape that GEOS can't handle: count it after a tiny cleanup, and say so if that fails too.
            try:
                parts = cut(shapely.buffer(geom, 0), shapely.buffer(new["geom"], 0))
            except shapely.errors.GEOSException:
                try:
                    parts = cut(shapely.buffer(geom, 1e-5), shapely.buffer(new["geom"], 1e-5))
                except shapely.errors.GEOSException:
                    print(f"  could not split by {new['name']} near {geom.centroid.coords[0]}", flush=True)
                    parts = None
        if parts is None:
            out.append((geom, held))
            continue
        inside, outside = parts
        if inside and not is_sliver(inside):
            out.append((inside, held | {new["index"]}))
            if outside and not is_sliver(outside):
                out.append((outside, held))
        else:
            out.append((geom, held))
    return out


def cut(geom, other):
    """(the part of geom inside other, the part outside), or None if they don't touch."""
    if not shapely.intersects(geom, other):
        return None
    return (polygons_only(shapely.intersection(geom, other, grid_size=GRID)),
            polygons_only(shapely.difference(geom, other, grid_size=GRID)))


def overlay(electric, gas):
    """Cut the country's gas territories into pieces that each have one exact set of utilities.

    Gas territories are processed one at a time. Anything an earlier one already covered is removed first,
    so each place appears once, and the later territory still counts because it's split in as a claim.
    """
    for i, g in enumerate(gas):
        g["index"] = i
    for i, e in enumerate(electric):
        e["index"] = i
    gas_tree = STRtree([g["geom"] for g in gas])
    electric_tree = STRtree([e["geom"] for e in electric])
    pieces = defaultdict(list)
    for n, g in enumerate(gas):
        if n % 100 == 0:
            print(f"  overlay {n}/{len(gas)}", flush=True)
        region = g["geom"]
        others = [gas[i] for i in gas_tree.query(g["geom"], predicate="intersects") if i != n]
        earlier = [o["geom"] for o in others if o["index"] < n]
        if earlier:
            region = polygons_only(shapely.difference(
                region, shapely.union_all(earlier, grid_size=GRID), grid_size=GRID))
            if not region:
                continue
        cells = [(region, frozenset())]
        for other in others:
            if other["index"] > n and other["name"] != g["name"]:
                cells = split(cells, other)
        gas_cells = cells
        for geom, gas_claims in gas_cells:
            sets = [(geom, frozenset())]
            for i in electric_tree.query(geom, predicate="intersects"):
                sets = split(sets, electric[i])
            for piece, electric_claims in sets:
                if sq_mi(piece) >= MIN_SQ_MI:
                    all_gas = tuple(sorted({g["index"], *gas_claims}))
                    pieces[(all_gas, tuple(sorted(electric_claims)))].append(piece)
    return pieces


def classify(gas_records, electric_records):
    """The class of a place with these utilities, plus the company or parent that provides both."""
    if not electric_records:
        return "no_electric", None
    best = None
    for g in gas_records:
        for e in electric_records:
            found = relation(g, e)
            if found == "same" or (found == "parent" and best is None):
                best = (found, g, e)
            if found == "same":
                break
    if not best:
        return "different", None
    kind, g, e = best
    if g["public"] and g["public"] == e["public"]:
        # Local public utilities serve their own town, and the data draws co-ops straight over towns,
        # so another listed utility doesn't make these uncertain (the same rule as the Colorado map).
        return "same", re.sub(r"\s*-?\s*\([A-Z]{2}\)\s*$", "", e["name"]).title().replace(" Of ", " of ")
    related = {g["name"], e["name"]}
    others = [r for r in gas_records if relation(r, e) is None and r["name"] not in related] + \
             [r for r in electric_records if relation(g, r) is None and r["name"] not in related]
    label = g["company"] if kind == "same" else PARENTS[g["company"]]
    return ("uncertain" if others else kind), label


def round_coords(value):
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], (int, float)):
            return [round(value[0], 3), round(value[1], 3)]
        return [round_coords(v) for v in value]
    return value


def to_feature(geom, props):
    return {"type": "Feature", "properties": props, "geometry": {
        "type": mapping(geom)["type"], "coordinates": round_coords(mapping(geom)["coordinates"])}}


def save(name, features):
    lines = [json.dumps(f, separators=(",", ":"), sort_keys=True) for f in features]
    (SNAPSHOTS / f"{name}.geojson").write_text('{"type":"FeatureCollection","features":[\n' + ",\n".join(lines) + "\n]}\n")


def main():
    electric, gas = load_records()
    pieces = overlay(electric, gas)

    print("Downloading state outlines...")
    state_features = download(STATES_LAYER, "STUSAB,BASENAME", where="STATE<'60'", tolerance="0.01", order="STATE")
    states = {}
    outlines = []
    for f in state_features:
        geom = polygons_only(shapely.make_valid(shape(f["geometry"])))
        # Alaska's far Aleutians cross the 180th meridian and would draw across the whole map.
        geom = polygons_only(shapely.clip_by_rect(geom, -180, 15, -60, 75))
        states[f["properties"]["STUSAB"]] = geom
        outlines.append(to_feature(geom, {"STUSAB": f["properties"]["STUSAB"], "NAME": f["properties"]["BASENAME"]}))
    save("us_states", sorted(outlines, key=lambda f: f["properties"]["STUSAB"]))
    state_codes = list(states)
    state_tree = STRtree([states[s] for s in state_codes])

    features = []
    by_state = defaultdict(lambda: defaultdict(float))
    totals = defaultdict(float)
    for (gas_ids, electric_ids), parts in pieces.items():
        gas_records = [gas[i] for i in gas_ids]
        electric_records = [electric[i] for i in electric_ids]
        kind, provider = classify(gas_records, electric_records)
        geom = polygons_only(shapely.union_all(parts, grid_size=GRID))
        if not geom:
            continue
        for i in state_tree.query(geom, predicate="intersects"):
            inside = shapely.intersection(geom, states[state_codes[i]], grid_size=GRID)
            by_state[state_codes[i]][kind] += sq_mi(inside)
        small = polygons_only(shapely.make_valid(shapely.simplify(geom, OUTPUT_TOLERANCE))) or geom
        area = sq_mi(geom)
        totals[kind] += area
        props = {"c": kind, "g": sorted({r["name"] for r in gas_records}),
                 "e": sorted({r["name"] for r in electric_records}), "sqmi": round(area, 1)}
        if provider:
            props["by"] = provider
        features.append(to_feature(small, props))
    features.sort(key=lambda f: (f["properties"]["c"], f["properties"]["g"], f["properties"]["e"]))
    save("us_overlap", features)

    manifest_path = SNAPSHOTS / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    today = date.today().isoformat()
    manifest["us_states"] = {
        "title": "U.S. state outlines (national map background)", "publisher": "U.S. Census Bureau TIGERweb",
        "license": "Public domain", "item_url": "https://tigerweb.geo.census.gov/", "layer_url": STATES_LAYER,
        "features": len(outlines), "source_last_edited": None, "saved_on": today}
    manifest["us_overlap"] = {
        "title": "Where gas and electric utility territories overlap across the U.S. (computed)",
        "publisher": "Computed from HIFLD data (Oak Ridge National Laboratory; DHS) and Colorado GeoData",
        "license": "Public use; provided without warranty",
        "item_url": GAS_ITEM, "layer_url": GAS_LAYER,
        "electric_item_url": ELECTRIC_ITEM, "electric_layer_url": ELECTRIC_LAYER,
        "features": len(features), "source_last_edited": None, "saved_on": today,
        "sq_mi_by_class": {k: round(v) for k, v in sorted(totals.items())},
        "sq_mi_by_state": {s: {k: round(v) for k, v in sorted(by_state[s].items())} for s in sorted(by_state)}}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    size = (SNAPSHOTS / "us_overlap.geojson").stat().st_size / 1e6
    print(f"Wrote {len(features)} shapes ({size:.1f} MB)")
    print({k: round(v) for k, v in totals.items()})


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"National overlap build failed: {error}", file=sys.stderr)
        raise
