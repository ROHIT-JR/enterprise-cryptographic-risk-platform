import re
import types
from unittest import mock

import networkx as nx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.api.intelligence import get_blast_radius
from backend.app.models import (
    Asset,
    AssetRelationship,
    Organization,
    Project,
    RiskAnalysis,
    Scan,
    User,
)
from backend.app.models.base import Base
from backend.app.services.intelligence_service import IntelligenceService
from graph_analysis.networkx_layer import (
    DEFAULT_WEIGHTS,
    NetworkXGraphLayer,
    _validate_weights,
)
from knowledge_graph.models import GraphEdge, GraphNode, GraphPayload
from knowledge_graph.service import Neo4jGraphStore


@pytest.fixture(scope="module")
def db_session():
    """Create an in‑memory SQLite DB and populate minimal required rows."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(name="TestOrg")
    session.add(org)
    session.flush()
    proj = Project(name="TestProj", organization_id=org.id)
    session.add(proj)
    session.flush()
    scan = Scan(organization_id=org.id, project_id=proj.id, source_type="manual", target="local")
    session.add(scan)
    session.flush()

    asset1 = Asset(
        organization_id=org.id,
        project_id=proj.id,
        scan_id=scan.id,
        asset_type="library",
        name="TestApp1",
        location="/tmp/app1",
        evidence="test",
    )
    asset2 = Asset(
        organization_id=org.id,
        project_id=proj.id,
        scan_id=scan.id,
        asset_type="certificate",
        name="TestCert",
        location="/tmp/cert",
        evidence="test",
    )
    session.add_all([asset1, asset2])
    session.flush()

    rel = AssetRelationship(
        organization_id=org.id,
        project_id=proj.id,
        source_asset_id=asset1.id,
        target_asset_id=asset2.id,
        relationship_type="DEPENDS_ON",
    )
    session.add(rel)
    session.commit()

    yield session
    session.close()


def _mock_intelligence_service_dependencies(svc: IntelligenceService) -> None:
    """Mock downstream intelligence engines so analyze_project runs without external deps."""
    dummy = types.SimpleNamespace(
        assess=lambda *_, **__: types.SimpleNamespace(
            confidence=100,
            explanation="",
            risk_score=0.0,
            risk_severity="low",
            evidence_sources=[],
            reason="",
            hndl_risk="low",
            classification="none",
            score=0.0,
            severity="low",
            components={},
        )
    )
    svc.evidence = dummy
    svc.quantum = types.SimpleNamespace(
        assess=lambda *_: types.SimpleNamespace(
            quantum_vulnerable=False, score=0.0, classification="none", reason=""
        )
    )
    svc.hndl = types.SimpleNamespace(
        assess=lambda *_: types.SimpleNamespace(score=0.0, reason="", hndl_risk="low")
    )
    svc.business = types.SimpleNamespace(
        assess=lambda *_: types.SimpleNamespace(score=0.0, reason="")
    )
    svc.complexity = types.SimpleNamespace(
        assess=lambda *_: types.SimpleNamespace(score=0.0, reasons=[])
    )
    svc.final = types.SimpleNamespace(
        assess=lambda *_: types.SimpleNamespace(
            score=0.0, severity="low", explanation=[], components={}
        )
    )
    svc.evidence_fusion = types.SimpleNamespace(fuse=lambda _: {"confidence": 100})
    svc.mosca = types.SimpleNamespace()
    svc.advanced_ext = types.SimpleNamespace()
    svc.recommendations = dummy
    svc.roadmap = types.SimpleNamespace(generate=lambda **kwargs: [])


# -----------------------------------------------------------------------------
# Defect 1: Docker backend dependency & pyproject consistency (NetworkX + NumPy + SciPy)
# -----------------------------------------------------------------------------
def _scientific_pins(text: str) -> dict[str, str]:
    return dict(re.findall(r"(networkx|numpy|scipy)==([0-9][\w.]*)", text))


def test_networkx_and_scientific_dependencies_declared():
    # Pin *consistency* is what matters (Docker installs requirements.txt, the engines
    # declare pyproject.toml); a specific version would break on every Dependabot bump.
    with open("backend/requirements.txt", encoding="utf-8") as f:
        requirements = _scientific_pins(f.read())
    with open("pyproject.toml", encoding="utf-8") as f:
        pyproject = _scientific_pins(f.read())
    assert set(requirements) == {"networkx", "numpy", "scipy"}
    assert requirements == pyproject

    with open("backend/Dockerfile", encoding="utf-8") as f:
        dockerfile = f.read()
    assert "COPY graph_analysis /app/graph_analysis" in dockerfile

    with open("docker-compose.yml", encoding="utf-8") as f:
        compose = f.read()
    assert "./graph_analysis:/app/graph_analysis" in compose


def test_actual_pagerank_and_louvain_execution():
    """Verify actual PageRank, betweenness, and Louvain algorithms compute correctly."""
    G = nx.DiGraph()
    G.add_edges_from([("a", "b"), ("b", "c"), ("c", "a"), ("a", "c")])

    # Direct PageRank calculation (requires numpy/scipy in NetworkX 3.x)
    pr = nx.pagerank(G)
    assert len(pr) == 3
    assert pytest.approx(sum(pr.values())) == 1.0
    for val in pr.values():
        assert 0.0 < val < 1.0

    # Layer computation
    layer = NetworkXGraphLayer()
    metrics = layer.compute_metrics(G, project_id="p1", organization_id="o1")
    assert len(metrics) == 3
    for m in metrics.values():
        assert 0.0 <= m["pagerank_score"] <= 1.0
        assert 0.0 <= m["betweenness_centrality"] <= 1.0
        assert 0.0 <= m["degree_centrality"] <= 1.0
        assert 0.0 <= m["blast_radius"] <= 1.0


# -----------------------------------------------------------------------------
# Defect 2: Organization and Project isolation
# -----------------------------------------------------------------------------
def test_tenant_isolation_forwarding_in_service(db_session):
    svc = IntelligenceService()
    _mock_intelligence_service_dependencies(svc)

    project = db_session.query(Project).first()
    mock_layer = mock.Mock()
    mock_layer.fetch_payload.return_value = None
    svc.networkx_layer = mock_layer

    svc.analyze_project(db=db_session, project=project)

    mock_layer.fetch_payload.assert_called_once_with(
        project_id=project.id,
        organization_id=project.organization_id,
    )


def test_tenant_isolation_in_networkx_layer(monkeypatch):
    captured = {}

    class DummyStore:
        enabled = True

        def query(self, *, project_id=None, organization_id=None, limit=500):
            captured["project_id"] = project_id
            captured["organization_id"] = organization_id
            return GraphPayload(nodes=[], edges=[], source="neo4j")

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr("graph_analysis.networkx_layer.create_graph_store", lambda: DummyStore())
    layer = NetworkXGraphLayer()
    payload = layer.fetch_payload(project_id="proj123", organization_id="org456")
    assert payload is not None
    assert captured["project_id"] == "proj123"
    assert captured["organization_id"] == "org456"
    assert captured.get("closed") is True


def test_cross_organization_blast_radius_rejection(db_session):
    """Ensure assets belonging to another organization are never returned in blast-radius."""
    org1 = db_session.query(Organization).first()
    proj1 = db_session.query(Project).filter(Project.organization_id == org1.id).first()
    asset1 = db_session.query(Asset).filter(Asset.project_id == proj1.id).first()
    user1 = User(
        organization_id=org1.id,
        username="user1_sec",
        email="user1_sec@example.com",
        password_hash="hash",
        role="admin",
    )

    # Create separate foreign organization and asset
    org2 = Organization(name="ForeignOrg")
    db_session.add(org2)
    db_session.flush()
    proj2 = Project(name="ForeignProj", organization_id=org2.id)
    db_session.add(proj2)
    db_session.flush()
    scan2 = Scan(
        organization_id=org2.id,
        project_id=proj2.id,
        source_type="manual",
        target="local",
    )
    db_session.add(scan2)
    db_session.flush()
    foreign_asset = Asset(
        organization_id=org2.id,
        project_id=proj2.id,
        scan_id=scan2.id,
        asset_type="application",
        name="ForeignApp",
        location="/foreign",
        evidence="test",
    )
    db_session.add(foreign_asset)
    db_session.flush()

    # Inject foreign asset ID into asset1's analysis factors
    analysis = db_session.scalar(
        select(RiskAnalysis).where(RiskAnalysis.asset_id == asset1.id)
    )
    if not analysis:
        analysis = RiskAnalysis(
            organization_id=org1.id,
            project_id=proj1.id,
            asset_id=asset1.id,
            quantum_score=0,
            hndl_score=0,
            centrality_score=0,
            business_score=0,
            migration_complexity_score=0,
            evidence_confidence=100,
            final_score=0,
            severity="low",
            hndl_risk="low",
            quantum_classification="none",
            dependent_systems=0,
            factors={"dependent_ids": [foreign_asset.id]},
        )
        db_session.add(analysis)
    else:
        analysis.factors = {"dependent_ids": [foreign_asset.id]}
    db_session.commit()

    resp = get_blast_radius(asset_id=asset1.id, db=db_session, user=user1)
    node_ids = {node.id for node in resp.nodes}
    assert foreign_asset.id not in node_ids
    assert len(resp.edges) == 0


def test_blast_radius_forwards_organization_id(db_session, monkeypatch):
    """Verify get_blast_radius forwards authenticated organization_id to graph store."""
    org1 = db_session.query(Organization).first()
    proj1 = db_session.query(Project).filter(Project.organization_id == org1.id).first()
    asset1 = db_session.query(Asset).filter(Asset.project_id == proj1.id).first()
    user1 = User(
        organization_id=org1.id,
        username="user_fw",
        email="user_fw@example.com",
        password_hash="hash",
        role="admin",
    )

    captured = {}

    class FakeStore:
        def health(self):
            return True

        def dependency_metrics(self, *, project_id, organization_id=None):
            captured["project_id"] = project_id
            captured["organization_id"] = organization_id
            return {asset1.id: {"dependent_ids": []}}

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr(
        "backend.app.api.intelligence.create_graph_store", lambda: FakeStore()
    )
    get_blast_radius(asset_id=asset1.id, db=db_session, user=user1)
    assert captured["organization_id"] == org1.id
    assert captured["project_id"] == proj1.id
    assert captured.get("closed") is True


# -----------------------------------------------------------------------------
# Defect 3 & 7: Empty or partial Neo4j graphs, safe fallbacks & CentralityAssessment
# -----------------------------------------------------------------------------
def test_intelligence_service_fallback_neo4j_none(db_session):
    svc = IntelligenceService()
    _mock_intelligence_service_dependencies(svc)
    project = db_session.query(Project).first()

    mock_layer = mock.Mock()
    mock_layer.fetch_payload.return_value = None
    svc.networkx_layer = mock_layer

    analyses = svc.analyze_project(db=db_session, project=project)
    assert len(analyses) == 2
    for a in analyses:
        assert isinstance(a.centrality_score, float)
        assert 0.0 <= a.centrality_score <= 1.0


def test_intelligence_service_fallback_empty_payload(db_session):
    svc = IntelligenceService()
    _mock_intelligence_service_dependencies(svc)
    project = db_session.query(Project).first()

    mock_layer = mock.Mock()
    mock_layer.fetch_payload.return_value = GraphPayload(
        nodes=[], edges=[], source="neo4j"
    )
    svc.networkx_layer = mock_layer

    analyses = svc.analyze_project(db=db_session, project=project)
    assert len(analyses) == 2
    mock_layer.compute_metrics.assert_not_called()


def test_intelligence_service_fallback_empty_metrics(db_session):
    svc = IntelligenceService()
    _mock_intelligence_service_dependencies(svc)
    project = db_session.query(Project).first()

    mock_layer = mock.Mock()
    mock_layer.fetch_payload.return_value = GraphPayload(
        nodes=[GraphNode(id="dummy", label="D", type="asset")],
        edges=[],
        source="neo4j",
    )
    mock_layer.build_graph.return_value = nx.DiGraph()
    mock_layer.compute_metrics.return_value = {}
    svc.networkx_layer = mock_layer

    analyses = svc.analyze_project(db=db_session, project=project)
    assert len(analyses) == 2


def test_intelligence_service_partial_metrics_overlay(db_session):
    svc = IntelligenceService()
    _mock_intelligence_service_dependencies(svc)
    project = db_session.query(Project).first()
    assets = db_session.query(Asset).filter(Asset.project_id == project.id).all()
    assert len(assets) >= 2
    present_asset = assets[0]
    absent_asset = assets[1]

    mock_layer = mock.Mock()
    mock_layer.fetch_payload.return_value = GraphPayload(
        nodes=[GraphNode(id=present_asset.id, label="A", type="library")],
        edges=[],
        source="neo4j",
    )
    G = nx.DiGraph()
    G.add_node(present_asset.id)
    mock_layer.build_graph.return_value = G
    mock_layer.compute_metrics.return_value = {
        present_asset.id: {
            "degree_centrality": 0.85,
            "betweenness_centrality": 0.45,
            "pagerank_score": 0.65,
            "blast_radius": 0.72,
            "centrality_score": 0.72,
            "dependent_systems": 5,
            "dependent_ids": ["dep_1"],
        }
    }
    svc.networkx_layer = mock_layer

    analyses = svc.analyze_project(db=db_session, project=project)
    analysis_by_asset = {a.asset_id: a for a in analyses}

    assert present_asset.id in analysis_by_asset
    assert absent_asset.id in analysis_by_asset

    # Present asset receives NetworkX overlay
    assert analysis_by_asset[present_asset.id].centrality_score == 0.72
    assert analysis_by_asset[present_asset.id].dependent_systems == 5

    # Absent asset retains legacy calculation safely without KeyError
    assert isinstance(analysis_by_asset[absent_asset.id].centrality_score, float)
    assert 0.0 <= analysis_by_asset[absent_asset.id].centrality_score <= 1.0


def test_intelligence_service_calculation_exception_fallback(db_session):
    svc = IntelligenceService()
    _mock_intelligence_service_dependencies(svc)
    project = db_session.query(Project).first()

    mock_layer = mock.Mock()
    mock_layer.fetch_payload.return_value = GraphPayload(
        nodes=[GraphNode(id="a", label="A", type="asset")],
        edges=[],
        source="neo4j",
    )
    mock_layer.build_graph.side_effect = RuntimeError("NetworkX crash")
    svc.networkx_layer = mock_layer

    # Must complete without crashing
    analyses = svc.analyze_project(db=db_session, project=project)
    assert len(analyses) == 2


# -----------------------------------------------------------------------------
# Defect 4: Neo4j store closing in all paths & leak prevention
# -----------------------------------------------------------------------------
def test_fetch_payload_closes_store(monkeypatch):
    close_called = 0

    class DummyStore:
        enabled = True

        def query(self, *args, **kwargs):
            return GraphPayload(nodes=[], edges=[], source="neo4j")

        def close(self):
            nonlocal close_called
            close_called += 1

    monkeypatch.setattr("graph_analysis.networkx_layer.create_graph_store", lambda: DummyStore())
    layer = NetworkXGraphLayer()
    layer.fetch_payload("p1")
    assert close_called == 1


def test_fetch_payload_closes_store_on_exception(monkeypatch):
    close_called = 0

    class DummyStore:
        enabled = True

        def query(self, *args, **kwargs):
            raise RuntimeError("Database error")

        def close(self):
            nonlocal close_called
            close_called += 1

    monkeypatch.setattr("graph_analysis.networkx_layer.create_graph_store", lambda: DummyStore())
    layer = NetworkXGraphLayer()
    res = layer.fetch_payload("p1")
    assert res is None
    assert close_called == 1


def test_compute_metrics_closes_store(monkeypatch):
    close_called = 0

    class DummyStore:
        enabled = True

        def dependency_metrics(self, *args, **kwargs):
            return {}

        def close(self):
            nonlocal close_called
            close_called += 1

    monkeypatch.setattr("graph_analysis.networkx_layer.create_graph_store", lambda: DummyStore())
    layer = NetworkXGraphLayer()
    G = nx.DiGraph()
    G.add_node("n1")
    layer.compute_metrics(G, "p1")
    assert close_called == 1


def test_compute_metrics_closes_store_on_dep_error(monkeypatch):
    close_called = 0

    class DummyStore:
        enabled = True

        def dependency_metrics(self, *args, **kwargs):
            raise RuntimeError("Dependency query error")

        def close(self):
            nonlocal close_called
            close_called += 1

    monkeypatch.setattr("graph_analysis.networkx_layer.create_graph_store", lambda: DummyStore())
    layer = NetworkXGraphLayer()
    G = nx.DiGraph()
    G.add_node("n1")
    metrics = layer.compute_metrics(G, "p1")
    assert close_called == 1
    # Centralities are still computed even if dependency query failed!
    assert "n1" in metrics
    assert "degree_centrality" in metrics["n1"]


def test_write_back_closes_store(monkeypatch):
    close_called = 0

    class DummyStore:
        enabled = True

        def update_asset_metrics(self, *args, **kwargs):
            pass

        def close(self):
            nonlocal close_called
            close_called += 1

    monkeypatch.setattr("graph_analysis.networkx_layer.create_graph_store", lambda: DummyStore())
    layer = NetworkXGraphLayer()
    layer.write_back("p1", {"n1": {"degree_centrality": 0.5}}, organization_id="org1")
    assert close_called == 1


def test_write_back_closes_store_on_error(monkeypatch):
    close_called = 0

    class DummyStore:
        enabled = True

        def update_asset_metrics(self, *args, **kwargs):
            raise RuntimeError("Write-back failure")

        def close(self):
            nonlocal close_called
            close_called += 1

    monkeypatch.setattr("graph_analysis.networkx_layer.create_graph_store", lambda: DummyStore())
    layer = NetworkXGraphLayer()
    layer.write_back("p1", {"n1": {"degree_centrality": 0.5}}, organization_id="org1")
    assert close_called == 1


# -----------------------------------------------------------------------------
# Defect 5: Write-back invocation & safe public abstraction (zero driver leaks)
# -----------------------------------------------------------------------------
def test_write_back_invoked_once_and_non_fatal_on_failure(db_session):
    svc = IntelligenceService()
    _mock_intelligence_service_dependencies(svc)
    project = db_session.query(Project).first()
    asset = db_session.query(Asset).filter(Asset.project_id == project.id).first()

    mock_layer = mock.Mock()
    mock_layer.fetch_payload.return_value = GraphPayload(
        nodes=[GraphNode(id=asset.id, label="A", type="library")],
        edges=[],
        source="neo4j",
    )
    G = nx.DiGraph()
    G.add_node(asset.id)
    mock_layer.build_graph.return_value = G
    mock_layer.compute_metrics.return_value = {asset.id: {"centrality_score": 0.5}}
    mock_layer.write_back.side_effect = RuntimeError("Write-back crash")
    svc.networkx_layer = mock_layer

    # Should not raise exception
    analyses = svc.analyze_project(db=db_session, project=project)
    assert len(analyses) == 2
    mock_layer.write_back.assert_called_once_with(
        project_id=project.id,
        metrics={asset.id: {"centrality_score": 0.5}},
        organization_id=project.organization_id,
    )


def test_neo4j_graph_store_update_asset_metrics_whitelisting_and_scoping():
    fake_driver = mock.MagicMock()
    fake_session = mock.MagicMock()
    fake_driver.session.return_value.__enter__.return_value = fake_session

    with mock.patch("knowledge_graph.service.GraphDatabase.driver", return_value=fake_driver):
        store = Neo4jGraphStore(
            uri="bolt://localhost:7687", user="u", password="p", enabled=True
        )

        metrics = {
            "asset_123": {
                "degree_centrality": 0.45,
                "betweenness_centrality": 0.25,
                "pagerank_score": 0.35,
                "community_id": 2,
                "blast_radius": 0.5,
                "centrality_score": 0.5,
                "unauthorized_prop": "DROP DATABASE",
                "fake_score": 999,
            }
        }

        store.update_asset_metrics(
            project_id="proj_1",
            organization_id="org_1",
            metrics=metrics,
        )

    fake_session.run.assert_called_once()
    call_args = fake_session.run.call_args
    query = call_args[0][0]
    kwargs = call_args[1]

    # Parameterization and tenant scoping verified
    assert "MATCH (p:Project {id: $project_id, organization_id: $organization_id})" in query
    assert kwargs["project_id"] == "proj_1"
    assert kwargs["organization_id"] == "org_1"

    updates = kwargs["updates"]
    assert len(updates) == 1
    props = updates[0]["properties"]
    assert props["degreeCentrality"] == 0.45
    assert props["betweennessCentrality"] == 0.25
    assert props["pageRankScore"] == 0.35
    assert props["communityId"] == 2
    assert props["blastRadius"] == 0.5
    assert props["centralityScore"] == 0.5

    # Ensure unwhitelisted properties were completely excluded
    assert "unauthorized_prop" not in props
    assert "fake_score" not in props


def test_neo4j_graph_store_update_asset_metrics_requires_organization_id():
    fake_driver = mock.MagicMock()
    with mock.patch("knowledge_graph.service.GraphDatabase.driver", return_value=fake_driver):
        store = Neo4jGraphStore(
            uri="bolt://localhost:7687", user="u", password="p", enabled=True
        )
        with pytest.raises(ValueError, match="organization_id is required"):
            store.update_asset_metrics(
                project_id="p1",
                organization_id="",
                metrics={"a1": {"degree_centrality": 0.5}},
            )


def test_neo4j_graph_store_context_manager_no_real_driver_leak():
    fake_driver = mock.MagicMock()
    with mock.patch("knowledge_graph.service.GraphDatabase.driver", return_value=fake_driver):
        store = Neo4jGraphStore(
            uri="bolt://localhost:7687", user="u", password="p", enabled=True
        )
        with store as s:
            assert s is store
        fake_driver.close.assert_called_once()


# -----------------------------------------------------------------------------
# Defect 6: Project membership edges do not distort analytics
# -----------------------------------------------------------------------------
def test_project_membership_edges_excluded():
    layer = NetworkXGraphLayer()

    # Payload with Project node and Project -> Asset CONTAINS edges
    payload_with_project = GraphPayload(
        nodes=[
            GraphNode(
                id="project:p1",
                label="Project",
                type="project",
                properties={"name": "P1"},
            ),
            GraphNode(id="asset_a", label="A", type="application", properties={}),
            GraphNode(id="asset_b", label="B", type="library", properties={}),
        ],
        edges=[
            GraphEdge(id="e1", source="project:p1", target="asset_a", type="CONTAINS"),
            GraphEdge(id="e2", source="project:p1", target="asset_b", type="CONTAINS"),
            GraphEdge(id="e3", source="asset_a", target="asset_b", type="DEPENDS_ON"),
            GraphEdge(id="e4", source="asset_a", target="asset_b", type="UNKNOWN_TYPE"),
        ],
        source="neo4j",
    )

    G = layer.build_graph(payload_with_project)

    # Project node is completely excluded
    assert "project:p1" not in G
    assert "asset_a" in G
    assert "asset_b" in G

    # Membership edges and unknown relationship types are excluded
    assert not G.has_edge("project:p1", "asset_a")
    assert not G.has_edge("project:p1", "asset_b")
    assert G.has_edge("asset_a", "asset_b")
    assert G.number_of_edges() == 1

    # Centrality values on G match exactly a graph built without the project node
    payload_clean = GraphPayload(
        nodes=[
            GraphNode(id="asset_a", label="A", type="application", properties={}),
            GraphNode(id="asset_b", label="B", type="library", properties={}),
        ],
        edges=[
            GraphEdge(id="e3", source="asset_a", target="asset_b", type="DEPENDS_ON"),
        ],
        source="neo4j",
    )
    G_clean = layer.build_graph(payload_clean)

    metrics_with_proj = layer.compute_metrics(G, "p1")
    metrics_clean = layer.compute_metrics(G_clean, "p1")

    assert metrics_with_proj == metrics_clean


# -----------------------------------------------------------------------------
# Defect 8: Metric robustness, weights & clamping
# -----------------------------------------------------------------------------
def test_single_node_and_empty_graph():
    layer = NetworkXGraphLayer()
    empty_G = nx.DiGraph()
    assert layer.compute_metrics(empty_G, "p1") == {}

    single_G = nx.DiGraph()
    single_G.add_node("lone_node")
    res = layer.compute_metrics(single_G, "p1")
    assert "lone_node" in res
    assert 0.0 <= res["lone_node"]["blast_radius"] <= 1.0
    assert 0.0 <= res["lone_node"]["degree_centrality"] <= 1.0


def test_weight_validation_and_normalization():
    # Unknown key -> defaults
    w1 = _validate_weights({"unknown_key": 1.0})
    assert w1 == DEFAULT_WEIGHTS

    # Negative value -> defaults
    w2 = _validate_weights({"degree": -0.5, "betweenness": 0.5})
    assert w2 == DEFAULT_WEIGHTS

    # Zero sum -> defaults
    w3 = _validate_weights({"degree": 0.0, "betweenness": 0.0})
    assert w3 == DEFAULT_WEIGHTS

    # Valid custom weights normalized to sum 1.0
    w4 = _validate_weights(
        {"degree": 2.0, "betweenness": 2.0, "pagerank": 0.0, "dependency": 0.0}
    )
    assert pytest.approx(sum(w4.values())) == 1.0
    assert w4["degree"] == 0.5
    assert w4["betweenness"] == 0.5


def test_blast_radius_clamped():
    layer = NetworkXGraphLayer(
        weights={"degree": 1.0, "betweenness": 1.0, "pagerank": 1.0, "dependency": 1.0}
    )
    assert pytest.approx(sum(layer.weights.values())) == 1.0


def test_louvain_communities_handling(monkeypatch):
    layer = NetworkXGraphLayer()
    G = nx.DiGraph()
    G.add_edge("a", "b")

    # When louvain is absent
    def raise_import(*_, **__):
        raise ImportError

    monkeypatch.setattr(
        "networkx.algorithms.community.louvain_communities",
        raise_import,
        raising=False,
    )
    assert layer._community_assignments(G) == {}
