"""Build the neighborhood rankings and map.

Usage:
    python3 run.py                        # uses the sample data
    python3 run.py path/to/your_data.csv  # uses your own data (same columns as the sample)
"""

import sys
from pathlib import Path

from gasplan.data import load_neighborhoods
from gasplan.report import write_map_html, write_rankings_csv
from gasplan.score import score_neighborhoods

ROOT = Path(__file__).parent
SAMPLE = ROOT / "data" / "sample" / "neighborhoods.csv"


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else SAMPLE
    scored = score_neighborhoods(load_neighborhoods(source))

    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    write_rankings_csv(scored, out / "rankings.csv")
    write_map_html(scored, out / "map.html", sample_data=source == SAMPLE)

    print(f"Scored {len(scored)} neighborhoods from {source.name}\n")
    print(f"{'#':>2}  {'Neighborhood':<18} {'Priority':>8}  Equity")
    for rank, s in enumerate(scored[:10], start=1):
        print(f"{rank:>2}  {s.neighborhood.name:<18} {s.priority:>8.2f}  {'yes' if s.equity_flag else ''}")
    print(f"\nWrote {out / 'rankings.csv'}")
    print(f"Wrote {out / 'map.html'}  (open it in a browser)")


if __name__ == "__main__":
    main()
