# Targeted Analytics for Equitable Gas Decommissioning

A website and prototype for planning an equitable transition away from aging gas infrastructure,
so households that can't afford to electrify aren't left paying for it. The website maps Colorado's
electric and gas utility territories, where one utility provides both, and the Gas Planning Pilot
Program communities. A draft neighborhood ranking tool is in progress and not yet published.

Built for a CELI capstone (business pitch). The first target customer is a local government,
such as the City and County of Denver, selecting projects for the
[PUC Gas Planning Pilot Program](https://puc.colorado.gov/gas-planning-pilot-program).

> **Note:** `data/sample/neighborhoods.csv` holds made-up values for demonstration, labeled "Sample A" to "Sample T".
> They are not real neighborhood data, which is why the neighborhood map is kept off the published site for now.

## Run it

Needs Python 3.9 or newer. No extra packages are required.

```bash
python3 run.py
```

This writes:
- `site/`: **the public website**. Open `site/index.html` in a browser. It has two maps, built from
  the saved map data in `data/snapshots/`:
  1. Colorado electric and gas utility territories by ownership type, where one utility
     provides both, and optional county boundaries. Electric data is federal HIFLD data, gas
     data comes from Colorado GeoData, and county boundaries come from the U.S. Census Bureau.
  2. The five Gas Planning Pilot Program communities.

  See `docs/data-sources.md` for every source.
- `output/neighborhoods.html`: **draft, not published.** The same page plus the neighborhood
  priority map and ranked list, built from the sample data.
- `output/rankings.csv`: the neighborhood table with each factor score and cost estimate

To use your own data, make a CSV with the same columns as the sample and run
`python3 run.py path/to/file.csv`.

To preview the site the way GitHub Pages serves it:

```bash
python3 -m http.server 8000 --directory site
```

## Map data

The maps don't call any map servers when someone visits. `scripts/fetch_data.py` downloads each dataset
once and saves it in `data/snapshots/` (GeoJSON, one feature per line), with `manifest.json` recording
each source, its license, the source's last-edit date and when the copy was saved. `run.py` bundles the
snapshots into `site/data.js`.

```bash
python3 scripts/fetch_data.py
```

Every Monday, `.github/workflows/refresh-data.yml` reruns that script and opens a pull request if any
data changed, so territory changes can be reviewed before they reach the live site.

## Publishing

`.github/workflows/pages.yml` publishes the site to GitHub Pages on every push to `main`: it runs the
tests, runs `run.py`, checks that no draft content is included, and deploys the `site/` folder.

One-time setup on GitHub:
- **Settings > Pages > Build and deployment > Source: GitHub Actions**
- **Settings > Actions > General > Workflow permissions:** check "Allow GitHub Actions to create and
  approve pull requests" (needed for the weekly data refresh)

## License and data

The code is under the [MIT License](LICENSE). The map data is not covered by it; it comes from third parties
and keeps its own terms:

- Electric territories: HIFLD / Oak Ridge National Laboratory (public use), via the National Broadband Availability Map
- Gas territories: Colorado GeoData (State of Colorado, provided without warranty)
- Counties, city limits, roads, and the map background (state outlines, interstates, city names):
  U.S. Census Bureau TIGERweb (public domain)
- Pilot communities: Colorado PUC and Colorado Energy Office

The site shows each source's last-edit date and when its copy was saved. Territories are approximate and
are not official service territory maps; see the "Known data limitations" section on the site and
`docs/data-sources.md`.

## Run the tests

```bash
python3 -m unittest
```

## How the score works

Each factor is a percentile rank from 0 to 1 across the neighborhoods being compared:

| Factor | Higher when… | Data |
|---|---|---|
| Infrastructure age | Buildings are older (stand-in for pipe age) | `median_year_built` |
| Electrification momentum | More heat pump permits per home | `heat_pump_permits_5yr` |
| Grid readiness | More spare electric capacity per home | `grid_headroom_mw` |
| Equity need | More renters and low-income households | `pct_renter`, `pct_low_income` |

`readiness` is a weighted mix of the first three. `priority` blends readiness (60%) with
equity need (40%). You can change the weights at the top of `gasplan/score.py`.

## Project layout

```
web/index.html              page layout and text (draft-only parts marked NEIGHBORHOODS)
web/styles.css              styles
web/site.js                 the statewide utility map and the pilot communities map
web/neighborhoods.js        draft neighborhood map (never published)
data/snapshots/             saved map data and manifest.json
data/sample/                made-up neighborhood data for the draft
scripts/fetch_data.py       download and save the map data
gasplan/score.py            neighborhood scoring, weights and cost assumptions
gasplan/data.py             load the neighborhood CSV
gasplan/report.py           build site/ and the draft page from web/ and the saved data
run.py                      build everything
.github/workflows/pages.yml         publish the website to GitHub Pages
.github/workflows/refresh-data.yml  weekly data refresh pull request
docs/data-sources.md        each data source, who holds it, how to get it
```
