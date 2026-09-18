from __future__ import annotations

from typing import Any


class AdvancedRiskExtension:
    """Wraps the existing FinalRiskEngine output and enriches it.

    The extension does **not** replace the FinalRiskEngine – it consumes the
    ``final`` result produced by ``FinalRiskEngine.assess`` and adds the
    Mosca quantum‑readiness score and the evidence‑fusion confidence.
    """

    MODEL_NAME = "AdvancedRiskExtension"
    VERSION = "1.0.0"

    def enhance(
        self, final_result: dict[str, Any], mosca: dict[str, Any], evidence: dict[str, Any]
    ) -> dict[str, Any]:
        """Combine the three pieces into a single enriched payload.

        Parameters
        ----------
        final_result:
            Output from ``FinalRiskEngine.assess`` – must contain at least a
            ``score`` and ``severity`` field.
        mosca:
            Dictionary returned by :class:`risk_engine.mosca_model.MoscaModel`
            (must contain ``deadline_risk``, ``formula`` and ``explanation``).
        evidence:
            Dictionary returned by :class:`risk_engine.evidence_fusion.EvidenceFusionEngine`
            (must contain ``confidence`` and ``evidence_strength``).
        """
        # Build a result dictionary that mirrors the existing API payload but
        # adds the new fields.  ``parameters`` records the inputs used for
        # reproducibility.
        result = {
            "model": self.MODEL_NAME,
            "version": self.VERSION,
            "parameters": {
                "mosca_deadline_risk": mosca.get("deadline_risk"),
                "mosca_formula": mosca.get("formula"),
                "mosca_explanation": mosca.get("explanation"),
                "evidence_confidence": evidence.get("confidence"),
                "evidence_strength": evidence.get("evidence_strength"),
                "conflict": evidence.get("conflict"),
            },
            "result": {
                **final_result,
                "mosca_deadline_risk": mosca.get("deadline_risk"),
                "mosca_formula": mosca.get("formula"),
                "mosca_explanation": mosca.get("explanation"),
                "evidence_confidence": evidence.get("confidence"),
                "evidence_strength": evidence.get("evidence_strength"),
                "evidence_conflict": evidence.get("conflict"),
            },
        }
        return result
