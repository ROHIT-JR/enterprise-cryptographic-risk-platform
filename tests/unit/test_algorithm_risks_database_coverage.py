"""Covers issue #40: expand the quantum-risk database beyond the original 9
entries so common hash/MAC algorithms don't silently fall back to "unknown".

Note: mosca_model.py's alleged "missing closing brace" syntax error (also
reported in issue #40) does not exist on this branch - ast.parse() and a
live MoscaModel().evaluate() call both succeed. See test_mosca_parses_and_
evaluates_without_error below, which pins that down as a regression guard
rather than leaving it undocumented.
"""

import ast
from pathlib import Path

import pytest

from risk_engine.mosca_model import MoscaModel
from risk_engine.quantum_risk import QuantumRiskEngine


def test_mosca_parses_and_evaluates_without_error():
    source = Path("risk_engine/mosca_model.py").read_text(encoding="utf-8")
    ast.parse(source)  # raises SyntaxError if the file is malformed

    model = MoscaModel()
    result = model.evaluate(data_lifetime=20, migration_time=3)
    assert set(result) == {"deadline_risk", "formula", "explanation"}


@pytest.mark.parametrize(
    ("algorithm", "expected_classification"),
    [
        ("SHA-384", "low"),
        ("SHA-512", "low"),
        ("SHA-3", "low"),
        ("HMAC", "low"),
    ],
)
def test_previously_unmapped_algorithms_now_have_a_real_classification(
    algorithm, expected_classification
):
    assessment = QuantumRiskEngine().assess(algorithm)
    assert assessment.classification == expected_classification
    assert assessment.classification != "unknown"


def test_sha512_is_scored_lower_risk_than_sha384_which_is_lower_than_sha256():
    engine = QuantumRiskEngine()
    sha256 = engine.assess("SHA-256")
    sha384 = engine.assess("SHA-384")
    sha512 = engine.assess("SHA-512")
    assert sha512.score <= sha384.score <= sha256.score


def test_algorithm_risks_database_has_at_least_thirteen_entries():
    # 9 original + SHA-384/512/3/HMAC = 13 on this branch alone. PR #61 adds
    # RC4/MD5/DES/3DES/SHA-1 independently (5 more, 18 once both merge) -
    # this just guards that this branch's own additions landed.
    engine = QuantumRiskEngine()
    assert len(engine.database) >= 13
