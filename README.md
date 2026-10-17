# Targeted Analytics for Equitable Gas Decommissioning

A prototype that ranks neighborhoods as candidates for neighborhood-scale electrification,
putting equity neighborhoods first, so households that can't afford to electrify aren't
left paying for aging gas infrastructure.

Built for a CELI capstone (business pitch). The first target customer is a local government,
such as the City and County of Denver, selecting projects for the
[PUC Gas Planning Pilot Program](https://puc.colorado.gov/gas-planning-pilot-program).

> **Note:** `data/sample/neighborhoods.csv` holds made-up values for demonstration. They are not real Denver data.

## Run it

Needs Python 3.9 or newer. No extra packages are required.

```bash
python3 run.py
```

This prints the top 10 neighborhoods and writes:
- `output/map.html`: two interactive maps (open it in a browser):
  1. Colorado electric and gas utility service territories, loaded live (needs an internet
     connection), with Xcel Energy highlighted. Electric data is federal HIFLD data, and gas
     data comes from Colorado GeoData. See `docs/data-sources.md`.
  2. Neighborhood priorities with a ranked list
- `output/rankings.csv`: the full table with each factor score and cost estimate

To use your own data, make a CSV with the same columns as the sample and run
`python3 run.py path/to/file.csv`.

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
gasplan/report.py   write the rankings CSV and the map
run.py              run everything
docs/data-sources.md  each data source, who holds it, how to get it
```
