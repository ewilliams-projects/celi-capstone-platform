"""Score and rank neighborhoods as candidates for neighborhood-scale electrification.

Four factors, each a percentile rank (0-1) across the neighborhoods being compared,
so one extreme neighborhood doesn't squash everyone else's scores:

- infrastructure_age:  older buildings -> older gas mains -> replacement coming due
- momentum:            electrification permits per home -> gas customers already leaving
- grid_readiness:      spare electric capacity per home -> fewer grid upgrades needed
- equity_need:         renters and low-income households -> most at risk of being
                       left paying for stranded gas infrastructure

The final priority blends a "readiness" score with equity need, so equity
neighborhoods rise to the top when they are otherwise viable.
"""

from dataclasses import dataclass
from typing import Dict, List

from gasplan.data import Neighborhood

# Weights are a starting point to discuss with your mentor and peer pod.
READINESS_WEIGHTS = {"infrastructure_age": 0.4, "momentum": 0.3, "grid_readiness": 0.3}
EQUITY_WEIGHT = 0.4          # share of the final score driven by equity need
EQUITY_FLAG_THRESHOLD = 0.7  # top ~30% by equity need are flagged as equity neighborhoods

# Placeholder cost assumptions: replace with sourced figures (e.g. Xcel PUC filings, RMI).
GAS_MAIN_COST_PER_MILE = 2_500_000
ELECTRIFICATION_COST_PER_HOME = 20_000


@dataclass
class ScoredNeighborhood:
    neighborhood: Neighborhood
    factors: Dict[str, float]
    readiness: float
    priority: float
    equity_flag: bool
    gas_replacement_cost: float
    electrification_cost: float

    @property
    def avoided_cost_ratio(self) -> float:
        """Gas replacement dollars avoided per dollar spent electrifying homes."""
        return self.gas_replacement_cost / self.electrification_cost


def _percentile(values: List[float]) -> List[float]:
    """Rank each value from 0 (lowest) to 1 (highest); ties share the average rank."""
    n = len(values)
    if n == 1:
        return [0.5]
    return [
        (sum(o < v for o in values) + (sum(o == v for o in values) - 1) / 2) / (n - 1)
        for v in values
    ]


def score_neighborhoods(neighborhoods: List[Neighborhood]) -> List[ScoredNeighborhood]:
    """Return neighborhoods sorted from highest to lowest priority."""
    # Older median year built -> higher score, so negate before scaling.
    age = _percentile([-n.median_year_built for n in neighborhoods])
    momentum = _percentile([n.heat_pump_permits_5yr / n.housing_units for n in neighborhoods])
    grid = _percentile([n.grid_headroom_mw / n.housing_units for n in neighborhoods])
    equity = _percentile([(n.pct_renter + n.pct_low_income) / 2 for n in neighborhoods])

    scored = []
    for i, n in enumerate(neighborhoods):
        factors = {
            "infrastructure_age": age[i],
            "momentum": momentum[i],
            "grid_readiness": grid[i],
            "equity_need": equity[i],
        }
        readiness = sum(READINESS_WEIGHTS[k] * factors[k] for k in READINESS_WEIGHTS)
        priority = (1 - EQUITY_WEIGHT) * readiness + EQUITY_WEIGHT * factors["equity_need"]
        scored.append(
            ScoredNeighborhood(
                neighborhood=n,
                factors=factors,
                readiness=readiness,
                priority=priority,
                equity_flag=factors["equity_need"] >= EQUITY_FLAG_THRESHOLD,
                gas_replacement_cost=n.gas_main_miles * GAS_MAIN_COST_PER_MILE,
                electrification_cost=n.housing_units * ELECTRIFICATION_COST_PER_HOME,
            )
        )
    return sorted(scored, key=lambda s: s.priority, reverse=True)
