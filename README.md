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
- `site/index.html`: **the public website** (open it in a browser). It has two maps, loaded live
  (needs an internet connection):
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

## Publishing

`.github/workflows/pages.yml` publishes `site/index.html` to GitHub Pages on every push to `main`:
it runs the tests, runs `run.py`, and deploys the `site/` folder. One-time setup on GitHub:
**Settings > Pages > Build and deployment > Source: GitHub Actions**.

## License and data

The code is under the [MIT License](LICENSE). The map data and basemap are not covered by it; they come from
third parties and keep their own terms:

- Electric territories: HIFLD / Oak Ridge National Laboratory (public use), via the National Broadband Availability Map
- Gas territories: Colorado GeoData (State of Colorado, provided without warranty)
- Counties, city limits and roads: U.S. Census Bureau TIGERweb (public domain)
- Pilot communities: Colorado PUC and Colorado Energy Office
- Basemap: Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community

The site loads this data live, so it shows each source's last-update date. Territories are approximate and
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
gasplan/data.py     load the neighborhood CSV
gasplan/score.py    scoring, weights and cost assumptions
gasplan/report.py   write the website, the draft page and the rankings CSV
run.py              build everything
.github/workflows/pages.yml  publish the website to GitHub Pages
docs/data-sources.md  each data source, who holds it, how to get it
```
