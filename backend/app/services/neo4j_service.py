from backend.app.config import Settings, get_settings
from knowledge_graph import Neo4jGraphStore


def create_graph_store(settings: Settings | None = None) -> Neo4jGraphStore:
    config = settings or get_settings()
    return Neo4jGraphStore(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password,
        enabled=config.neo4j_enabled,
    )


__all__ = ["Neo4jGraphStore", "create_graph_store"]
