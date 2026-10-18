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
| Same-utility areas | Where one utility provides both electricity and gas | Computed in the browser from the two layers above | Public | On the statewide map |
| County boundaries | Map reference (county names show when zoomed in) | [U.S. Census Bureau TIGERweb](https://tigerweb.geo.census.gov/) | Public domain | On the statewide map |
| Gas service territories | Where Xcel provides gas | [Colorado GeoData](https://geodata.colorado.gov/datasets/47935f56eddd4d1781328c60c8517c96_0/explore) | Public | On the statewide map |

## Policy context

- [PUC Gas Planning Pilot Program](https://puc.colorado.gov/gas-planning-pilot-program): neighborhood-scale
  alternatives to gas pipe replacement under HB 24-1370. The PUC approved five pilot communities in Decision
  C25-0482 (June 2025): Boulder, Denver, Golden, Winter Park and Breckenridge, all partnering with Xcel. First
  projects (or an explanation) are due June 1, 2027. Xcel's June 1, 2026 status report (proceeding 25M-0269G) lists 16
  potential projects: 7 in Breckenridge, 3 in Winter Park, and 2 each in Denver, Golden and Boulder
  ([Colorado Energy Office](https://energyoffice.colorado.gov/gas-planning-pilot-communities)). The law covers local
  governments in Xcel's natural gas service territory, which is why Winter Park qualifies. The pilot map uses Census TIGERweb city limits for these five, and faint
  TIGERweb primary and secondary roads (no basemap place names, so labels aren't doubled).
  In Winter Park, Xcel provides gas but Mountain Parks Electric provides electricity.

## Cost assumptions

`gasplan/score.py` uses placeholder costs (`GAS_MAIN_COST_PER_MILE`, `ELECTRIFICATION_COST_PER_HOME`).
Replace them with sourced figures, for example from Xcel PUC filings or RMI analysis, before using
the results in the pitch.

## Why not the CDOT electric boundaries?

The [CDOT Utilities Boundaries](https://geodata.colorado.gov/datasets/cdot::utilities-boundaries/explore) layer
contradicts itself: its license says use is limited to people named in a Master Service Agreement with
Platts (S&P Global), while its description says there are no restrictions. The federal HIFLD layer has no
such restriction. HIFLD Open shut down in 2025, so the copy used here is a snapshot that won't be updated.

## How same-utility areas are found

`gasplan/report.py` matches companies across the two layers, since their names are spelled differently
(e.g. electric "CITY OF TRINIDAD - (CO)" and gas "TRINIDAD, CITY OF"), then intersects each matched pair
of territories with Turf.js. Matches: Xcel Energy, Black Hills (Black Hills Colorado Electric and Black
Hills Energy gas share a parent company, Black Hills Corporation), and the cities of Colorado Springs, Trinidad, Fort Morgan and
Center. Areas are approximate because the shapes are simplified for faster loading.

Where the data also lists another electric or gas utility over a same-utility area, that part is shown
as **uncertain** (pale, dashed outline) and its popup names the other utility. For example, the electric
data puts both Xcel and Holy Cross Energy over Silt; Holy Cross is reported to serve Silt (for example,
[KMTS, 2015](https://www.kmts.com/news/holy-cross-energy-outage-affects-nearly-200-consumers-and-kmts)), with Xcel
supplying Holy Cross wholesale ([Holy Cross Energy](https://www.holycross.com/wp-content/uploads/2018/06/HCE_CO2_2015-1.pdf)). About 1,640 of Xcel's ~7,100 sq mi same-utility area is uncertain,
mostly where Poudre Valley REA, United Power, Mountain Parks Electric or Estes Park overlap it.
City-owned utilities (Colorado Springs, Trinidad, Fort Morgan, Center) are exempt, because the source
data draws co-op territories straight over towns.

## Map cleanup and known data problems

The statewide map leaves out WAPA (Western Area Power Administration) and Deseret Generation &
Transmission. They sell wholesale power to utilities, not to homes, but the federal layer draws them
across most of Colorado underneath the retail utilities. Shapes are simplified to about 50 m and cut
at the Colorado border.

Some overlaps between electric territories remain in the source data and aren't fixed here:
- Town of Oak Creek's territory (about 655 customers) is drawn over roughly 2,300 sq mi of Yampa Valley
  Electric's area, which looks like a data error.
- Southwestern Electric Coop (NM) and Tri-County Electric Coop (OK) extend thousands of square miles
  into southeast Colorado, overlapping San Isabel and Southeast Colorado Power.
- Xcel overlaps neighboring co-ops in places (about 1,600 sq mi with Poudre Valley REA; about 210 sq mi
  with Grand Valley Power). Some service areas really are interleaved more finely than this data shows.
For exact service territories, use the Colorado PUC's certificated territory maps.

## Map background

The maps don't use a third-party tile service. The background is drawn from U.S. Census Bureau TIGERweb data
(public domain): state outlines, interstates, and a short list of Colorado city names, so there are no API keys
or tile terms to manage. An earlier version used Esri's World Light Gray Canvas tiles without a key; Esri lists
that service as in mature support and its terms likely expect an ArcGIS account for public sites, so it was
replaced. Trade-off: no street, water or terrain detail when zoomed in.
