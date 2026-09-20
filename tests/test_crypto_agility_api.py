import pytest
from sqlalchemy import select

from backend.app.api.intelligence import get_crypto_agility_score
from backend.app.database import SessionLocal
from backend.app.models import Organization, User
from backend.app.seed import seed_securebank_demo


@pytest.fixture()
def seeded():
    with SessionLocal() as db:
        seed_securebank_demo(db)
        organization = db.scalar(select(Organization).where(Organization.name == "SecureBank"))
        admin = db.scalar(select(User).where(User.username == "securebank-admin"))
        assert organization is not None and admin is not None
        yield db, admin


def test_agility_score_is_computed_from_real_seeded_evidence(seeded):
    db, admin = seeded
    result = get_crypto_agility_score(project_id=None, db=db, user=admin)

    assert 0 <= result.score <= 100
    assert result.band in {"crypto-rigid", "crypto-aware", "crypto-ready", "crypto-agile"}
    assert len(result.factors) == 5
    assert {factor.factor for factor in result.factors} == {
        "abstraction_layer_usage",
        "algorithm_hardcoding",
        "dependency_coupling",
        "key_management_flexibility",
        "protocol_version_support",
    }
    assert len(result.recommendations) <= 3


def test_agility_factor_weights_sum_to_one(seeded):
    db, admin = seeded
    result = get_crypto_agility_score(project_id=None, db=db, user=admin)

    assert sum(factor.weight for factor in result.factors) == pytest.approx(1.0)


def test_protocol_support_reflects_the_seeded_tls_versions(seeded):
    db, admin = seeded
    result = get_crypto_agility_score(project_id=None, db=db, user=admin)

    protocol = next(f for f in result.factors if f.factor == "protocol_version_support")
    # SecureBank's demo estate discovers TLS 1.2 and TLS 1.3 across its services.
    assert "TLS 1.2" in protocol.explanation
    assert "TLS 1.3" in protocol.explanation
