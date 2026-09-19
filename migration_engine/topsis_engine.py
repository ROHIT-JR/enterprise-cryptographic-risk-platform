"""TOPSIS multi-criteria decision analysis solver.

Operates purely on a numeric matrix without any pre-filtering. 
Security level has been removed as a TOPSIS weight because it is now 
a hard constraint evaluated prior to the solver.
"""

from __future__ import annotations

import logging

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Default criteria weights — sum to 1.0. Note security_level is removed.
DEFAULT_TOPSIS_WEIGHTS: dict[str, float] = {
    "performance_rank": 0.20,
    "public_key_bytes": 0.15,
    "sig_ct_size": 0.15,
    "maturity": 0.15,
    "compatibility": 0.20,
    "migration_complexity": 0.15,
}

# Benefit (True = maximize) or Cost (False = minimize)
CRITERIA_TYPES: dict[str, bool] = {
    "performance_rank": True,
    "public_key_bytes": False,
    "sig_ct_size": False,
    "maturity": True,
    "compatibility": True,
    "migration_complexity": True, # Note: redefined as ease of migration, so higher=better
}

CRITERIA_ORDER = list(DEFAULT_TOPSIS_WEIGHTS.keys())


class TOPSISResult(BaseModel):
    name: str
    closeness: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)
    scores: dict[str, float]
    distance_positive: float = Field(ge=0.0)
    distance_negative: float = Field(ge=0.0)


class TOPSISSolution(BaseModel):
    rankings: list[TOPSISResult]
    criteria: list[str]
    weights: dict[str, float]
    criteria_types: dict[str, str]
    ideal: dict[str, float]
    anti_ideal: dict[str, float]
    algorithm: str = "TOPSIS"
    version: str = "1.0.0"


def validate_weights(weights: dict[str, float] | None) -> dict[str, float]:
    if not weights:
        return dict(DEFAULT_TOPSIS_WEIGHTS)
    allowed = set(DEFAULT_TOPSIS_WEIGHTS.keys())
    if not set(weights.keys()).issubset(allowed):
        logger.warning("Unknown TOPSIS weight keys in %s; using defaults", weights)
        return dict(DEFAULT_TOPSIS_WEIGHTS)
    if any(v < 0 for v in weights.values()):
        logger.warning("Negative TOPSIS weights in %s; using defaults", weights)
        return dict(DEFAULT_TOPSIS_WEIGHTS)
    total = sum(weights.get(k, 0.0) for k in allowed)
    if total <= 0:
        logger.warning("Zero-sum TOPSIS weights; using defaults")
        return dict(DEFAULT_TOPSIS_WEIGHTS)
    return {k: weights.get(k, 0.0) / total for k in allowed}


def solve(
    alternatives: list[str],
    matrix: list[list[float]],
    weights: dict[str, float] | None = None,
    criteria_types: dict[str, bool] | None = None,
) -> TOPSISSolution:
    n = len(alternatives)
    w = validate_weights(weights)
    ct = criteria_types if criteria_types else dict(CRITERIA_TYPES)

    if n == 0:
        return TOPSISSolution(
            rankings=[],
            criteria=CRITERIA_ORDER,
            weights=w,
            criteria_types={k: ("benefit" if v else "cost") for k, v in ct.items()},
            ideal={},
            anti_ideal={},
        )

    m = len(CRITERIA_ORDER)
    if n == 1:
        scores = {CRITERIA_ORDER[j]: float(matrix[0][j]) for j in range(m)}
        return TOPSISSolution(
            rankings=[
                TOPSISResult(
                    name=alternatives[0],
                    closeness=1.0,
                    rank=1,
                    scores=scores,
                    distance_positive=0.0,
                    distance_negative=0.0,
                )
            ],
            criteria=CRITERIA_ORDER,
            weights=w,
            criteria_types={k: ("benefit" if v else "cost") for k, v in ct.items()},
            ideal=scores,
            anti_ideal=scores,
        )

    raw = np.array(matrix, dtype=np.float64)
    col_norms = np.sqrt((raw ** 2).sum(axis=0))
    col_norms[col_norms == 0] = 1.0
    normalised = raw / col_norms

    weight_vec = np.array([w[k] for k in CRITERIA_ORDER], dtype=np.float64)
    weighted = normalised * weight_vec

    ideal = np.empty(m, dtype=np.float64)
    anti_ideal = np.empty(m, dtype=np.float64)
    for j, crit in enumerate(CRITERIA_ORDER):
        if ct.get(crit, True):
            ideal[j] = weighted[:, j].max()
            anti_ideal[j] = weighted[:, j].min()
        else:
            ideal[j] = weighted[:, j].min()
            anti_ideal[j] = weighted[:, j].max()

    d_pos = np.sqrt(((weighted - ideal) ** 2).sum(axis=1))
    d_neg = np.sqrt(((weighted - anti_ideal) ** 2).sum(axis=1))

    denominator = d_pos + d_neg
    denominator[denominator == 0] = 1.0
    closeness = d_neg / denominator

    ranked_indices = np.argsort(-closeness)
    results = []
    for rank_pos, idx in enumerate(ranked_indices):
        results.append(
            TOPSISResult(
                name=alternatives[idx],
                closeness=round(float(np.clip(closeness[idx], 0.0, 1.0)), 6),
                rank=rank_pos + 1,
                scores={CRITERIA_ORDER[j]: round(float(weighted[idx, j]), 6) for j in range(m)},
                distance_positive=round(float(d_pos[idx]), 6),
                distance_negative=round(float(d_neg[idx]), 6),
            )
        )

    return TOPSISSolution(
        rankings=results,
        criteria=CRITERIA_ORDER,
        weights=w,
        criteria_types={k: ("benefit" if v else "cost") for k, v in ct.items()},
        ideal={CRITERIA_ORDER[j]: round(float(ideal[j]), 6) for j in range(m)},
        anti_ideal={CRITERIA_ORDER[j]: round(float(anti_ideal[j]), 6) for j in range(m)},
    )
