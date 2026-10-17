# Data sources

The biggest risk to this project is getting the data. Each column the tool uses is listed
with who holds the data and how to get it. The prototype runs today on sample values.

| Tool input (CSV column) | What it stands for | Who holds it | Access | Status |
|---|---|---|---|---|
| `median_year_built` | Gas pipe age (stand-in) | Denver Assessor (parcels), Census ACS | Public | Use as a proxy for now |
| *(future)* pipe install year | Real gas main age | Xcel Energy | Not shared (security concerns) | Upgrade once a PUC data-sharing rule exists |
| *(future)* replacement schedule | When mains are due for replacement | Xcel, filed at the PUC | May be marked highly confidential | Ask mentor / PUC staff |
| `heat_pump_permits_5yr` | How fast homes are electrifying | City and County of Denver building permits | Public; the city already shares it with Xcel | Next to collect |
| `grid_headroom_mw` | Spare electric capacity | Xcel hosting capacity map | Public online | Next to collect |
| `pct_renter` | Renter share | Census ACS (table B25003) | Public | Next to collect |
| `pct_low_income` | Energy burden risk | Census ACS income data, DOE LEAD tool | Public | Next to collect |
| `gas_main_miles` | Size of the gas system to replace | Xcel (estimate from street miles until then) | Not shared | Estimate |
| `lat`, `lon` | Neighborhood location | Denver statistical neighborhoods | Public | Approximate centers in the sample |
| Electric service territories | Where Xcel provides electricity | Federal HIFLD data (Oak Ridge National Laboratory, 2023), [copy kept by the National Broadband Availability Map](https://www.arcgis.com/home/item.html?id=597555ce8e4a4892a030784a7c657fdd) | Public use | On the statewide map |
| Gas service territories | Where Xcel provides gas | [Colorado GeoData](https://geodata.colorado.gov/datasets/47935f56eddd4d1781328c60c8517c96_0/explore) | Public | On the statewide map |

## Policy context

- [PUC Gas Planning Pilot Program](https://puc.colorado.gov/gas-planning-pilot-program): neighborhood-scale
  alternatives to gas pipe replacement in 5 communities. Denver is just starting to pick projects.

## Cost assumptions

`gasplan/score.py` uses placeholder costs (`GAS_MAIN_COST_PER_MILE`, `ELECTRIFICATION_COST_PER_HOME`).
Replace them with sourced figures, for example from Xcel PUC filings or RMI analysis, before using
the results in the pitch.

## Why not the CDOT electric boundaries?

The [CDOT Utilities Boundaries](https://geodata.colorado.gov/datasets/cdot::utilities-boundaries/explore) layer
contradicts itself: its license says use is limited to people named in a Master Service Agreement with
Platts (S&P Global), while its description says there are no restrictions. The federal HIFLD layer has no
such restriction. HIFLD Open shut down in 2025, so the copy used here is a snapshot that won't be updated.
