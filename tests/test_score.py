import unittest
from pathlib import Path

from gasplan.data import Neighborhood, load_neighborhoods
from gasplan.score import score_neighborhoods

SAMPLE = Path(__file__).parent.parent / "data" / "sample" / "neighborhoods.csv"


def make(name, year=1950, renter=0.5, low_income=0.3, permits=50, headroom=5.0):
    return Neighborhood(name, 39.7, -104.9, 1000, year, renter, low_income, permits, headroom, 10)


class ScoreTests(unittest.TestCase):
    def test_sample_data_loads_and_scores(self):
        scored = score_neighborhoods(load_neighborhoods(SAMPLE))
        self.assertEqual(len(scored), 20)
        priorities = [s.priority for s in scored]
        self.assertEqual(priorities, sorted(priorities, reverse=True))
        for s in scored:
            self.assertTrue(0 <= s.priority <= 1)

    def test_older_buildings_rank_higher_when_all_else_equal(self):
        scored = score_neighborhoods([make("New", year=2000), make("Old", year=1920)])
        self.assertEqual(scored[0].neighborhood.name, "Old")

    def test_equity_need_raises_priority(self):
        scored = score_neighborhoods([make("Affluent", renter=0.2, low_income=0.1),
                                      make("Burdened", renter=0.8, low_income=0.6)])
        self.assertEqual(scored[0].neighborhood.name, "Burdened")
        self.assertTrue(scored[0].equity_flag)
        self.assertFalse(scored[1].equity_flag)

    def test_identical_neighborhoods_do_not_divide_by_zero(self):
        scored = score_neighborhoods([make("A"), make("B")])
        self.assertAlmostEqual(scored[0].priority, scored[1].priority)


if __name__ == "__main__":
    unittest.main()
