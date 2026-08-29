from backend.app.config import Settings


def test_settings_accept_local_connection_variable_names(monkeypatch):
    for name in (
        "ECDAT_DATABASE_URL",
        "ECDAT_NEO4J_URI",
        "ECDAT_NEO4J_USER",
        "ECDAT_NEO4J_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@postgres:5432/ecdat")
    monkeypatch.setenv("NEO4J_URI", "bolt://neo4j:7687")
    monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "password")

    settings = Settings(_env_file=None)

    assert settings.database_url.endswith("@postgres:5432/ecdat")
    assert settings.neo4j_uri == "bolt://neo4j:7687"
    assert settings.neo4j_user == "neo4j"
    assert settings.neo4j_password == "password"
