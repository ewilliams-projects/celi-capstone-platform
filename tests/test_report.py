import tempfile
import unittest
from pathlib import Path

from gasplan.data import load_neighborhoods
from gasplan.report import write_map_html, write_site_html
from gasplan.score import score_neighborhoods

SAMPLE = Path(__file__).parent.parent / "data" / "sample" / "neighborhoods.csv"


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_site_page_leaves_out_the_neighborhood_draft(self):
        path = self.dir / "index.html"
        write_site_html(path)
        html = path.read_text()
        self.assertIn('id="statemap"', html)
        self.assertIn('id="pilotmap"', html)
        self.assertNotIn('id="map"', html)
        self.assertNotIn("NEIGHBORHOODS", html)
        self.assertNotIn("Sample data", html)
        self.assertNotIn("Sample A", html)
        # Page structure and required credits
        self.assertEqual(html.count("<main"), 1)
        self.assertIn("Background: U.S. Census Bureau", html)
        self.assertNotIn("arcgisonline.com", html)  # no third-party tile service
        self.assertIn('integrity="sha384-', html)
        self.assertNotIn("__", html.replace("__proto__", ""))  # no unfilled placeholders

    def test_draft_page_keeps_the_neighborhood_map(self):
        path = self.dir / "neighborhoods.html"
        write_map_html(score_neighborhoods(load_neighborhoods(SAMPLE)), path, sample_data=True)
        html = path.read_text()
        self.assertIn('id="map"', html)
        self.assertIn("Sample data for demonstration only", html)
        self.assertNotIn("__DATA__", html)


if __name__ == "__main__":
    unittest.main()
