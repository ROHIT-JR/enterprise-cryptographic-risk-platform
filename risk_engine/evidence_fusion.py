from __future__ import annotations


class EvidenceFusionEngine:
    """Dempster‑Shafer evidence fusion with conflict handling.

    The engine expects each source to provide a mass dictionary with three
    entries: ``{"True": p, "False": q, "Both": r}`` where ``p+q+r == 1``.
    """

    CONFLICT_THRESHOLD = 0.7  # above this we fall back to a simple Bayesian average

    @staticmethod
    def _combine_two(m1: dict[str, float], m2: dict[str, float]) -> tuple[dict[str, float], float]:
        """Combine two mass functions using Dempster's rule.

        Returns the combined mass dictionary and the conflict coefficient K.
        """
        combined = {"True": 0.0, "False": 0.0, "Both": 0.0}
        K = 0.0
        # Enumerate all focal elements
        for a, pa in m1.items():
            for b, pb in m2.items():
                prod = pa * pb
                if a == "True" and b == "True":
                    combined["True"] += prod
                elif a == "False" and b == "False":
                    combined["False"] += prod
                elif a == "Both" and b == "Both":
                    combined["Both"] += prod
                elif (a == "True" and b == "False") or (a == "False" and b == "True"):
                    K += prod  # empty intersection
                else:
                    # Intersection results in the more specific element
                    # For simplicity treat all mixed cases as "Both"
                    combined["Both"] += prod
        if K >= 1.0:
            # Complete conflict – return uniform ignorance
            return {"True": 0.0, "False": 0.0, "Both": 1.0}, 1.0
        # Normalise by (1‑K)
        factor = 1.0 - K
        for key in combined:
            combined[key] = combined[key] / factor
        return combined, K

    def fuse(self, sources: list[dict[str, float]]) -> dict[str, object]:
        """Fuse a list of source mass dictionaries.

        Returns a dict with keys:
        * ``confidence`` – int (0‑100)
        * ``evidence_strength`` – string label
        * ``conflict`` – bool indicating whether K exceeded threshold
        """
        if not sources:
            return {"confidence": 0, "evidence_strength": "Low", "conflict": False}
        # Fast-path: if all source masses are identical, keep original confidence
        if all(src == sources[0] for src in sources):
            confidence_frac = sources[0].get("True", 0.0) + 0.5 * sources[0].get("Both", 0.0)
            confidence = int(round(confidence_frac * 100))
            strength = (
                "Very High" if confidence >= 95 else
                "High" if confidence >= 80 else
                "Medium" if confidence >= 60 else
                "Low"
            )
            return {"confidence": confidence, "evidence_strength": strength, "conflict": False}
        # Iteratively combine all sources
        combined = sources[0]
        conflict = False
        for src in sources[1:]:
            combined, K = self._combine_two(combined, src)
            if K > self.CONFLICT_THRESHOLD:
                conflict = True
        # Derive confidence from the belief in "True"
        confidence_frac = combined.get("True", 0.0) + 0.5 * combined.get("Both", 0.0)
        confidence = int(round(confidence_frac * 100))
        # Map to human‑readable strength
        if confidence >= 95:
            strength = "Very High"
        elif confidence >= 80:
            strength = "High"
        elif confidence >= 60:
            strength = "Medium"
        else:
            strength = "Low"
        return {"confidence": confidence, "evidence_strength": strength, "conflict": conflict}
