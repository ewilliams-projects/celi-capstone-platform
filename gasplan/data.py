"""Load neighborhood indicator data.

Every source is read into the same `Neighborhood` record, so swapping the
sample CSV for real data (permits, assessor records, Census ACS, Xcel hosting
capacity) only means producing a CSV with these columns.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Neighborhood:
    name: str
    lat: float
    lon: float
    housing_units: int
    median_year_built: int    # stand-in for gas pipe age until Xcel data is available
    pct_renter: float         # 0-1, share of renter-occupied homes
    pct_low_income: float     # 0-1, share of households with high energy burden risk
    heat_pump_permits_5yr: int  # electrification permits issued in the last 5 years
    grid_headroom_mw: float   # spare distribution capacity (Xcel hosting capacity map)
    gas_main_miles: float     # estimated miles of gas main serving the area


def load_neighborhoods(path: Path) -> List[Neighborhood]:
    with open(path, newline="") as f:
        return [
            Neighborhood(
                name=row["neighborhood"],
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                housing_units=int(row["housing_units"]),
                median_year_built=int(row["median_year_built"]),
                pct_renter=float(row["pct_renter"]),
                pct_low_income=float(row["pct_low_income"]),
                heat_pump_permits_5yr=int(row["heat_pump_permits_5yr"]),
                grid_headroom_mw=float(row["grid_headroom_mw"]),
                gas_main_miles=float(row["gas_main_miles"]),
            )
            for row in csv.DictReader(f)
        ]
