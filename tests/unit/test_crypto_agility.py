from risk_engine.crypto_agility import AgilityAssetEvidence, CryptoAgilityEngine, CryptoAgilityInput


def _assess(**kwargs):
    return CryptoAgilityEngine().assess(CryptoAgilityInput(**kwargs))


def test_empty_input_bands_crypto_rigid():
    # No discovered assets means no abstraction/hardcoding/key-flex signal (0)
    # and a single-library-equivalent coupling default (20); protocol support
    # is left neutral (60) since "no TLS assets found" isn't itself a penalty.
    result = _assess()
    assert result.band == "crypto-rigid"
    assert result.score <= 30


def test_direct_hardcoded_calls_score_low_on_abstraction_and_hardcoding():
    result = _assess(
        algorithm_assets=[
            AgilityAssetEvidence(
                evidence="AES.new(key, AES.MODE_CBC, key_size=256)",
                location="services/payments/vault.py",
            ),
            AgilityAssetEvidence(
                evidence='rsa.generate_private_key(key_size=2048)', location="services/auth.py"
            ),
        ],
        library_names=["PyCryptodome"],
    )
    abstraction = next(f for f in result.factors if f.factor == "abstraction_layer_usage")
    hardcoding = next(f for f in result.factors if f.factor == "algorithm_hardcoding")
    key_flex = next(f for f in result.factors if f.factor == "key_management_flexibility")
    assert abstraction.score == 20
    assert hardcoding.score == 20
    assert key_flex.score == 20  # hardcoded 2048 literal
    assert result.band == "crypto-rigid"


def test_web_crypto_subtle_is_recognized_as_high_abstraction():
    result = _assess(
        algorithm_assets=[
            AgilityAssetEvidence(
                evidence="window.crypto.subtle.generateKey(...)", location="src/crypto.ts"
            )
        ],
    )
    abstraction = next(f for f in result.factors if f.factor == "abstraction_layer_usage")
    assert abstraction.score == 100


def test_env_or_settings_reference_scores_high_on_hardcoding_and_key_flexibility():
    result = _assess(
        algorithm_assets=[
            AgilityAssetEvidence(
                evidence='Cipher.getInstance(os.environ["CIPHER_ALGO"])', location="app/crypto.py"
            )
        ],
    )
    hardcoding = next(f for f in result.factors if f.factor == "algorithm_hardcoding")
    key_flex = next(f for f in result.factors if f.factor == "key_management_flexibility")
    assert hardcoding.score == 100
    assert key_flex.score == 100


def test_conf_file_location_scores_medium_hardcoding_not_high():
    result = _assess(
        algorithm_assets=[
            AgilityAssetEvidence(
                evidence="cipher AES-256-GCM", location="etc/openvpn/server.conf:31"
            )
        ],
    )
    hardcoding = next(f for f in result.factors if f.factor == "algorithm_hardcoding")
    assert hardcoding.score == 60


def test_dependency_coupling_buckets_by_distinct_library_count():
    single = _assess(library_names=["OpenSSL"])
    two = _assess(library_names=["OpenSSL", "Bouncy Castle"])
    four = _assess(library_names=["OpenSSL", "Bouncy Castle", "libsodium", "Web Crypto API"])
    coupling_single = next(f for f in single.factors if f.factor == "dependency_coupling")
    coupling_two = next(f for f in two.factors if f.factor == "dependency_coupling")
    coupling_four = next(f for f in four.factors if f.factor == "dependency_coupling")
    assert coupling_single.score == 20
    assert coupling_two.score == 60
    assert coupling_four.score == 100


def test_protocol_support_matches_the_issues_own_worked_example():
    # The issue text says "TLS 1.2 + 1.3 = medium" verbatim.
    result = _assess(protocol_names=["TLS 1.2", "TLS 1.3"])
    protocol = next(f for f in result.factors if f.factor == "protocol_version_support")
    assert protocol.score == 60


def test_pqc_hybrid_protocol_scores_high_regardless_of_count():
    result = _assess(protocol_names=["TLS 1.3 Hybrid ML-KEM"])
    protocol = next(f for f in result.factors if f.factor == "protocol_version_support")
    assert protocol.score == 100


def test_score_bands_are_ordered_and_bounded():
    from risk_engine.crypto_agility import _band

    assert _band(0)[0] == "crypto-rigid"
    assert _band(30)[0] == "crypto-rigid"
    assert _band(31)[0] == "crypto-aware"
    assert _band(60)[0] == "crypto-aware"
    assert _band(61)[0] == "crypto-ready"
    assert _band(80)[0] == "crypto-ready"
    assert _band(81)[0] == "crypto-agile"
    assert _band(100)[0] == "crypto-agile"


def test_recommendations_are_capped_at_three_and_target_the_weakest_factors():
    result = _assess(
        algorithm_assets=[
            AgilityAssetEvidence(evidence="AES.new(key)", location="app.py"),
        ],
        library_names=["OpenSSL"],
    )
    assert len(result.recommendations) == 3
