import json
import tempfile
import unittest
from pathlib import Path

from gasplan.data import load_neighborhoods
from gasplan.report import build_draft, build_site
from gasplan.score import score_neighborhoods

SAMPLE = Path(__file__).parent.parent / "data" / "sample" / "neighborhoods.csv"


def read_snapshots(data_js: Path) -> dict:
    text = data_js.read_text()
    start = text.index("window.SNAPSHOTS = ") + len("window.SNAPSHOTS = ")
    return json.loads(text[start:].rstrip().rstrip(";"))


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp())
        build_site(cls.dir)
        cls.html = (cls.dir / "index.html").read_text()

    def test_site_has_only_public_files(self):
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()),
                         ["data.js", "index.html", "site.js", "styles.css"])

    def test_site_page_leaves_out_the_neighborhood_draft(self):
        self.assertIn('id="statemap"', self.html)
        self.assertIn('id="pilotmap"', self.html)
        self.assertNotIn('id="map"', self.html)
        self.assertNotIn("NEIGHBORHOODS", self.html)
        self.assertNotIn("neighborhoods.js", self.html)
        self.assertNotIn("Sample data", self.html)
        self.assertNotIn("__", self.html)  # no unfilled placeholders

    def test_site_page_structure_and_credits(self):
        self.assertEqual(self.html.count("<main"), 1)
        self.assertIn("Background: U.S. Census Bureau", (self.dir / "site.js").read_text())
        self.assertNotIn("arcgisonline.com", self.html)  # no third-party tile service
        self.assertIn('integrity="sha384-', self.html)
        # Scripts load in order: data first, then the maps that read it.
        self.assertLess(self.html.index('src="data.js"'), self.html.index('src="site.js"'))

    def test_site_makes_no_live_data_requests(self):
        site_js = (self.dir / "site.js").read_text()
        self.assertNotIn("fetch(", site_js)
        self.assertNotIn("arcgis/rest/services", site_js)

    def test_data_js_holds_every_dataset_the_maps_use(self):
        snapshots = read_snapshots(self.dir / "data.js")
        site_js = (self.dir / "site.js").read_text()
        for name in ["electric", "gas", "counties", "states", "interstates", "cities",
                     "pilot_places", "pilot_roads_primary", "pilot_roads_secondary"]:
            self.assertIn(f"'{name}'", site_js)
            self.assertEqual(snapshots[name]["type"], "FeatureCollection")
            self.assertTrue(snapshots[name]["features"], name)
        self.assertIn("manifest", snapshots)


class DraftTests(unittest.TestCase):
    def test_draft_page_keeps_the_neighborhood_map(self):
        dest = Path(tempfile.mkdtemp())
        build_draft(score_neighborhoods(load_neighborhoods(SAMPLE)), dest, sample_data=True)
        html = (dest / "neighborhoods.html").read_text()
        self.assertIn('id="map"', html)
        self.assertIn("Sample data for demonstration only", html)
        self.assertNotIn("__", html)
        self.assertIn("const DATA = ", (dest / "neighborhood-data.js").read_text())
        self.assertTrue((dest / "neighborhoods.js").exists())


if __name__ == "__main__":
    unittest.main()
