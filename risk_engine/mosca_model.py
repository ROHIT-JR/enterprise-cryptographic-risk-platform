from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any


class MoscaModel:
    """Mosca quantum‑readiness model.

    Implements the inequality ``X + Y > Z`` where:
    * X – data lifetime (years)
    * Y – migration time (years)
    * Z – estimated quantum arrival year (relative to current year) or a timeline value
    The model reads a configuration file ``config/quantum_timeline.json`` for the
    quantum timeline and an optional confidence level.
    """

    CONFIG_PATH = Path("config/quantum_timeline.json")

    def __init__(self) -> None:
        # Load configuration lazily – if missing, use safe defaults
        if self.CONFIG_PATH.is_file():
            try:
                cfg = json.loads(self.CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}
        else:
            cfg = {}
        # Expected keys: "quantum_arrival_year" (int) and "confidence" (str)
        self.quantum_year: int = int(cfg.get("quantum_arrival_year", 2035))
        self.confidence: str = str(cfg.get("confidence", "Medium")).lower()

    @staticmethod
    def _adjust_threshold(base: int, confidence: str) -> float:
        """Adjust the quantum timeline based on confidence.

        * High   – assume earlier arrival (‑5 %)
        * Low    – assume later arrival (+5 %)
        * Medium – no adjustment
        """
        if confidence == "high":
            return base * 0.95
        if confidence == "low":
            return base * 1.05
        return float(base)

    def evaluate(self, data_lifetime: int, migration_time: int) -> dict[str, Any]:
        """Calculate Mosca risk.

        Returns a dictionary compatible with the Phase‑4 specification.
        """
        lhs = data_lifetime + migration_time
        threshold = self._adjust_threshold(self.quantum_year, self.confidence)
        if lhs > threshold:
            deadline_risk = "Critical"
            explanation = "Migration must begin immediately"
        else:
            deadline_risk = "Low"
            explanation = "Current schedule meets quantum timeline"
        formula = f"{data_lifetime} + {migration_time} > {int(threshold)}"
        return {
            "deadline_risk": deadline_risk,
            "formula": formula,
            "explanation": explanation,
        }

    def simulate(
        self,
        data_lifetime: float,
        migration_time: float,
        quantum_arrival_year: int | None = None,
        current_year: int | None = None,
    ) -> dict[str, Any]:
        """Evaluate the Mosca inequality against real calendar years.

        Used by the interactive Mosca timeline (dashboard "what-if" sliders),
        where X + Y (years of required protection) is compared against Z
        (years remaining until the estimated quantum arrival year).
        """
        year_now = current_year if current_year is not None else datetime.date.today().year
        arrival_year = (
            quantum_arrival_year if quantum_arrival_year is not None else self.quantum_year
        )
        years_until_quantum = max(arrival_year - year_now, 1)
        lhs = data_lifetime + migration_time
        verdict = "critical" if lhs > years_until_quantum else "safe"
        return {
            "data_lifetime": data_lifetime,
            "migration_time": migration_time,
            "current_year": year_now,
            "quantum_arrival_year": arrival_year,
            "years_until_quantum": years_until_quantum,
            "lhs": lhs,
            "verdict": verdict,
            "formula": f"{data_lifetime} + {migration_time} > {years_until_quantum}",
        }
