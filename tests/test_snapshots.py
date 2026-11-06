"""Checks on the saved map data in data/snapshots/ (no network needed)."""

import json
import unittest
from pathlib import Path

SNAPSHOTS = Path(__file__).parent.parent / "data" / "snapshots"


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((SNAPSHOTS / "manifest.json").read_text())

    def test_manifest_matches_the_files(self):
        files = sorted(p.stem for p in SNAPSHOTS.glob("*.geojson"))
        self.assertEqual(files, sorted(self.manifest))

    def test_each_snapshot_is_valid_and_documented(self):
        for name, info in self.manifest.items():
            with self.subTest(name):
                data = json.loads((SNAPSHOTS / f"{name}.geojson").read_text())
                self.assertEqual(data["type"], "FeatureCollection")
                self.assertEqual(len(data["features"]), info["features"])
                self.assertGreater(info["features"], 0)
                for key in ["title", "publisher", "license", "item_url", "layer_url", "saved_on"]:
                    self.assertTrue(info.get(key), f"{name} manifest is missing {key}")
                for feature in data["features"]:
                    self.assertIn(feature["geometry"]["type"],
                                  ["Point", "Polygon", "MultiPolygon", "LineString", "MultiLineString"])

    def test_snapshots_cover_colorado(self):
        # Every coordinate should sit in the continental U.S. (the state outlines include all of Texas).
        # The national map data also covers Alaska and Hawaii, so it has its own test below.
        for name in [n for n in self.manifest if not n.startswith("us_")]:
            data = json.loads((SNAPSHOTS / f"{name}.geojson").read_text())
            text = json.dumps([f["geometry"]["coordinates"] for f in data["features"]])
            numbers = [float(n) for n in text.replace("[", " ").replace("]", " ").replace(",", " ").split()]
            lons, lats = numbers[0::2], numbers[1::2]
            with self.subTest(name):
                self.assertGreater(min(lons), -125)
                self.assertLess(max(lons), -90)
                self.assertGreater(min(lats), 24)
                self.assertLess(max(lats), 50)

    def test_wholesale_suppliers_are_left_out(self):
        data = json.loads((SNAPSHOTS / "electric.geojson").read_text())
        names = {f["properties"]["NAME"] for f in data["features"]}
        self.assertFalse([n for n in names if n.startswith(("WAPA", "DESERET"))])
        self.assertIn("PUBLIC SERVICE CO OF COLORADO", names)

    def test_national_overlap_has_known_utilities_in_the_right_groups(self):
        data = json.loads((SNAPSHOTS / "us_overlap.geojson").read_text())
        props = [f["properties"] for f in data["features"]]
        self.assertTrue(all(p["c"] in ("same", "parent", "uncertain", "different", "no_electric") for p in props))
        self.assertTrue(all(p["g"] for p in props))

        def groups(gas, electric):
            return {p["c"] for p in props if gas in p["g"] and electric in p["e"] and len(p["g"]) == 1 and len(p["e"]) == 1}

        self.assertEqual(groups("PACIFIC GAS & ELECTRIC CO", "PACIFIC GAS & ELECTRIC CO."), {"same"})
        self.assertEqual(groups("ATLANTA GAS LIGHT CO.", "GEORGIA POWER CO"), {"parent"})
        self.assertEqual(groups("SOUTHERN CALIFORNIA GAS COMPANY", "SOUTHERN CALIFORNIA EDISON CO"), {"different"})
        # City utilities stay "same" even where the data also draws a co-op over the town.
        springs = {p["c"] for p in props if "COLORADO SPRINGS UTILITIES" in p["g"]
                   and "CITY OF COLORADO SPRINGS - (CO)" in p["e"]}
        self.assertEqual(springs, {"same"})
        self.assertEqual(groups("MIDWEST ENERGY INC.", "MIDWEST ENERGY INC"), {"same"})
        # Names that look alike must not match.
        self.assertEqual(groups("ALABAMA GAS CORP", "ALABAMA POWER CO"), {"different"})
        self.assertEqual(groups("OAK RIDGE UTILITY DISTRICT", "CITY OF OAK RIDGE"), {"different"})
        self.assertEqual(groups("CHATTANOOGA GAS COMPANY", "CITY OF CHATTANOOGA - (TN)"), {"different"})

    def test_national_basemap_has_every_layer_and_state(self):
        data = json.loads((SNAPSHOTS / "us_basemap.geojson").read_text())
        kinds = {f["properties"]["k"] for f in data["features"]}
        self.assertEqual(kinds, {"land", "state", "state_label", "lake", "river", "road", "city"})
        states = [f["properties"]["n"] for f in data["features"] if f["properties"]["k"] == "state"]
        self.assertEqual(len(set(states)), 51)  # 50 states and D.C.
        cities = {f["properties"]["n"] for f in data["features"] if f["properties"]["k"] == "city"}
        self.assertIn("Denver", cities)

    def test_national_overlap_leaves_out_wholesale_suppliers_and_pipelines(self):
        data = json.loads((SNAPSHOTS / "us_overlap.geojson").read_text())
        electric = {n for f in data["features"] for n in f["properties"]["e"]}
        gas = {n for f in data["features"] for n in f["properties"]["g"]}
        self.assertFalse([n for n in electric if n.startswith(("WAPA", "DESERET", "BONNEVILLE", "TENNESSEE VALLEY AUTH"))])
        self.assertFalse([n for n in gas if n.startswith(("KINDER MORGAN", "FLORIDA GAS TRANSMISSION"))])


if __name__ == "__main__":
    unittest.main()
