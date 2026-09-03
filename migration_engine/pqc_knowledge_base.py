"""PQC algorithm knowledge base with NIST standardization provenance.

Includes 18 candidates from FIPS 203, 204, and 205.
Uses objectively verifiable ordinal scores and artifact sizes instead of 
arbitrary performance/memory metrics. Security levels are used as hard 
eligibility constraints.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PQCCandidate(BaseModel):
    """A single post-quantum candidate algorithm with provenance."""

    name: str
    function: str  # key_establishment | digital_signature
    nist_level: int = Field(ge=1, le=5)
    public_key_bytes: int = Field(ge=0)
    sig_or_ct_bytes: int = Field(ge=0)
    performance_rank: int = Field(ge=1)  # Ordinal rank (higher is better/faster)
    maturity: float = Field(ge=0.0, le=1.0)
    compatibility: float = Field(ge=0.0, le=1.0)
    migration_complexity: float = Field(ge=0.0, le=1.0)  # 0.0=hard, 1.0=easy (benefit)
    source: str
    family: str
    notes: str = ""


_CANDIDATES: list[dict[str, Any]] = [
    # --- ML-KEM (FIPS 203) ---
    {
        "name": "ML-KEM-512",
        "function": "key_establishment",
        "nist_level": 1,
        "public_key_bytes": 800,
        "sig_or_ct_bytes": 768,
        "performance_rank": 3,
        "maturity": 1.0,
        "compatibility": 0.85,
        "migration_complexity": 0.8,
        "source": "FIPS 203",
        "family": "ML-KEM",
    },
    {
        "name": "ML-KEM-768",
        "function": "key_establishment",
        "nist_level": 3,
        "public_key_bytes": 1184,
        "sig_or_ct_bytes": 1088,
        "performance_rank": 2,
        "maturity": 1.0,
        "compatibility": 0.90,
        "migration_complexity": 0.7,
        "source": "FIPS 203",
        "family": "ML-KEM",
    },
    {
        "name": "ML-KEM-1024",
        "function": "key_establishment",
        "nist_level": 5,
        "public_key_bytes": 1568,
        "sig_or_ct_bytes": 1568,
        "performance_rank": 1,
        "maturity": 1.0,
        "compatibility": 0.80,
        "migration_complexity": 0.6,
        "source": "FIPS 203",
        "family": "ML-KEM",
    },
    # --- ML-DSA (FIPS 204) ---
    {
        "name": "ML-DSA-44",
        "function": "digital_signature",
        "nist_level": 2,
        "public_key_bytes": 1312,
        "sig_or_ct_bytes": 2420,
        "performance_rank": 3,
        "maturity": 1.0,
        "compatibility": 0.85,
        "migration_complexity": 0.7,
        "source": "FIPS 204",
        "family": "ML-DSA",
    },
    {
        "name": "ML-DSA-65",
        "function": "digital_signature",
        "nist_level": 3,
        "public_key_bytes": 1952,
        "sig_or_ct_bytes": 3309,
        "performance_rank": 2,
        "maturity": 1.0,
        "compatibility": 0.90,
        "migration_complexity": 0.6,
        "source": "FIPS 204",
        "family": "ML-DSA",
    },
    {
        "name": "ML-DSA-87",
        "function": "digital_signature",
        "nist_level": 5,
        "public_key_bytes": 2592,
        "sig_or_ct_bytes": 4627,
        "performance_rank": 1,
        "maturity": 1.0,
        "compatibility": 0.80,
        "migration_complexity": 0.5,
        "source": "FIPS 204",
        "family": "ML-DSA",
    },
]

# --- SLH-DSA (FIPS 205) --- 12 Parameter Sets
for variant in ["SHA2", "SHAKE"]:
    for level, s_f, pk, sig, pr, notes in [
        (1, "s", 32, 7856, 2, "Small signature, slower"),
        (1, "f", 32, 17088, 5, "Fast signature, larger"),
        (3, "s", 48, 16224, 1, "Small signature, slower"),
        (3, "f", 48, 35664, 4, "Fast signature, larger"),
        (5, "s", 64, 29792, 1, "Small signature, slower"),
        (5, "f", 64, 49856, 3, "Fast signature, larger"),
    ]:
        _CANDIDATES.append({
            "name": f"SLH-DSA-{variant}-{(128 if level==1 else 192 if level==3 else 256)}{s_f}",
            "function": "digital_signature",
            "nist_level": level,
            "public_key_bytes": pk,
            "sig_or_ct_bytes": sig,
            "performance_rank": pr,
            "maturity": 1.0,
            "compatibility": 0.60,
            "migration_complexity": 0.4,
            "source": "FIPS 205",
            "family": "SLH-DSA",
            "notes": f"Hash-based {variant} variant. {notes}",
        })

class PQCKnowledgeBase:
    """Registry of NIST-standardized PQC algorithms."""

    def __init__(self) -> None:
        self._candidates = [PQCCandidate(**entry) for entry in _CANDIDATES]

    @property
    def all_candidates(self) -> list[PQCCandidate]:
        return list(self._candidates)

    def candidates_for_function(self, function: str) -> list[PQCCandidate]:
        return [c for c in self._candidates if c.function == function]

    def candidates_by_family(self, family: str) -> list[PQCCandidate]:
        return [c for c in self._candidates if c.family == family]

    def get(self, name: str) -> PQCCandidate | None:
        for candidate in self._candidates:
            if candidate.name == name:
                return candidate
        return None
