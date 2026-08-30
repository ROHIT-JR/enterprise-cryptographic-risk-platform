from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

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

    def evaluate(self, data_lifetime: int, migration_time: int) -> Dict[str, Any]:
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
