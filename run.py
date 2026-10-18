"""Build the website and the draft neighborhood page.

Usage:
    python3 run.py                        # neighborhood draft uses the sample data
    python3 run.py path/to/your_data.csv  # neighborhood draft uses your own data (same columns as the sample)

Writes:
    site/                       the public website published to GitHub Pages (index.html, styles.css,
                                site.js, data.js), built from web/ and the saved map data in data/snapshots/
    output/neighborhoods.html   draft page with the neighborhood priority map (not published)
    output/rankings.csv         neighborhood rankings

To refresh the saved map data first:  python3 scripts/fetch_data.py
"""

import sys
from pathlib import Path

from gasplan.data import load_neighborhoods
from gasplan.report import build_draft, build_site, write_rankings_csv
from gasplan.score import score_neighborhoods

ROOT = Path(__file__).parent
SAMPLE = ROOT / "data" / "sample" / "neighborhoods.csv"


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else SAMPLE
    scored = score_neighborhoods(load_neighborhoods(source))

    site = ROOT / "site"
    build_site(site)

    out = ROOT / "output"
    build_draft(scored, out, sample_data=source == SAMPLE)
    write_rankings_csv(scored, out / "rankings.csv")

    print(f"Scored {len(scored)} neighborhoods from {source.name}\n")
    print(f"{'#':>2}  {'Neighborhood':<18} {'Priority':>8}  Equity")
    for rank, s in enumerate(scored[:10], start=1):
        print(f"{rank:>2}  {s.neighborhood.name:<18} {s.priority:>8.2f}  {'yes' if s.equity_flag else ''}")
    print(f"\nWrote {site}/  (the public website: open index.html)")
    print(f"Wrote {out / 'neighborhoods.html'}  (draft with the neighborhood map, not published)")
    print(f"Wrote {out / 'rankings.csv'}")


if __name__ == "__main__":
    main()
