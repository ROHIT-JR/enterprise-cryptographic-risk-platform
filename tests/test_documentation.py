"""The documentation is part of the product: it must not drift from the code it describes.

Some blocks are generated (run `python scripts/generate_docs.py --write` to refresh them); the rest
is checked for broken links, malformed diagrams, endpoints that do not exist, and credentials.
"""

import importlib.util
import re
from pathlib import Path

import pytest

from backend.app.config import Settings
from backend.app.main import app

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MARKDOWN = [ROOT / "README.md", *sorted(DOCS.glob("*.md"))]
API_GUIDE = DOCS / "api-guide.md"


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_docs", ROOT / "scripts" / "generate_docs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator():
    return _load_generator()


# --- generated blocks ---------------------------------------------------------------------------
def test_generated_blocks_are_up_to_date(generator):
    stale = []
    for name, (document, render) in generator.BLOCKS.items():
        start, end = generator.markers(name)
        text = document.read_text(encoding="utf-8")
        found = re.search(re.escape(start) + r"\n(.*?)\n" + re.escape(end), text, re.DOTALL)
        assert found, f"{document.name} is missing the {name!r} markers"
        if found.group(1).strip() != render().strip():
            stale.append(f"{document.name}: {name}")
    assert not stale, "stale generated docs (run: python scripts/generate_docs.py --write): " + (
        ", ".join(stale)
    )


def test_er_diagram_lists_every_table_and_no_stale_one(generator):
    from backend.app.models.base import Base

    block = generator.render_er()
    entities = set(re.findall(r"^    ([A-Z_]+) \{$", block, re.MULTILINE))
    assert entities == {name.upper() for name in Base.metadata.tables}


def test_topsis_example_matches_the_real_recommender(generator):
    """The worked example and the recommender must agree on the winner and its score."""
    from migration_engine.pqc_recommendation import PQCRecommendationInput
    from migration_engine.topsis_recommendation import TOPSISRecommendationEngine

    asset = PQCRecommendationInput(
        asset="gateway", current_algorithm="RSA-2048", use_case="key_exchange"
    )
    ranked = TOPSISRecommendationEngine().recommend(asset).recommendations[0].candidates
    text = generator.render_topsis()
    assert f"| 1 | {ranked[0].algorithm} |" in text
    assert f"{ranked[0].closeness_coefficient:.4f}" in text


def test_every_setting_is_documented(generator):
    documented = set(generator.SETTING_DOCS)
    assert documented == set(Settings.model_fields), "add a purpose line for the new setting"


# --- diagrams -----------------------------------------------------------------------------------
def _diagrams():
    for path in MARKDOWN:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"```mermaid\n(.*?)```", text, re.DOTALL):
            line = text[: match.start()].count("\n") + 1
            yield pytest.param(match.group(1), id=f"{path.name}:{line}")


@pytest.mark.parametrize("code", _diagrams())
def test_mermaid_diagrams_are_structurally_sound(code):
    """A cheap guard; diagrams are also rendered with the real Mermaid parser in review."""
    lines = [
        line for line in code.splitlines() if line.strip() and not line.strip().startswith("%%")
    ]
    assert re.match(r"(flowchart|graph|sequenceDiagram|erDiagram)\b", lines[0]), lines[0]
    if lines[0].startswith(("flowchart", "graph")):
        opened = sum(1 for line in lines if line.strip().startswith("subgraph "))
        closed = sum(1 for line in lines if line.strip() == "end")
        assert opened == closed, "unbalanced subgraph/end"
    assert code.count("[") == code.count("]"), "unbalanced brackets"
    assert code.count('"') % 2 == 0, "unbalanced quotes"


# --- links --------------------------------------------------------------------------------------
def _slug(heading: str) -> str:
    """GitHub's heading anchor: lowercase, drop punctuation, spaces to hyphens."""
    heading = re.sub(r"[`*_]", "", heading.strip().lower())
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading))


def _anchors(path: Path) -> set[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    return {_slug(m.group(1)) for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, re.MULTILINE)}


def _links(path: Path):
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", "", text)
    for match in re.finditer(r"\[[^\]]+\]\(([^)\s]+)\)", text):
        target = match.group(1)
        if not target.startswith(("http://", "https://", "mailto:")):
            yield target


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: p.name)
def test_relative_links_and_anchors_resolve(path):
    problems = []
    for target in _links(path):
        file_part, _, anchor = target.partition("#")
        destination = (path.parent / file_part).resolve() if file_part else path
        if not destination.exists():
            problems.append(f"{target}: no such file")
        elif anchor and destination.suffix == ".md" and anchor not in _anchors(destination):
            problems.append(f"{target}: no heading '#{anchor}' in {destination.name}")
    assert not problems, f"{path.name}: " + "; ".join(problems)


# --- the guide only mentions endpoints that exist ------------------------------------------------
def _spec_patterns():
    patterns = []
    for path, item in app.openapi()["paths"].items():
        regex = re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(path))
        for method in item:
            patterns.append((method.upper(), re.compile(f"^{regex}$")))
    return patterns


def _exists(method: str | None, path: str, patterns) -> bool:
    path = re.sub(r"<[^>]+>|\$[A-Z_]+", "x", path)  # a placeholder or shell variable is any segment
    candidates = [path, f"/api/v1{path}"]
    return any(
        regex.match(candidate) and (method is None or method == m)
        for candidate in candidates
        for m, regex in patterns
    )


def test_api_guide_only_mentions_real_endpoints():
    text = API_GUIDE.read_text(encoding="utf-8")
    text = re.sub(
        r"<!-- endpoint-map:start -->.*?<!-- endpoint-map:end -->", "", text, flags=re.DOTALL
    )
    patterns = _spec_patterns()
    missing = []
    for method, path in re.findall(r"`(GET|POST|PUT|DELETE) (/[^\s`?]*)`", text):
        if not _exists(method, path, patterns):
            missing.append(f"{method} {path}")
    for path in re.findall(r"\$BASE(/[^\s\"'?\\]+)", text):
        if not _exists(None, path.rstrip(".,)"), patterns):
            missing.append(f"$BASE{path}")
    assert not missing, "the API guide mentions endpoints that do not exist: " + ", ".join(
        sorted(set(missing))
    )


# --- no credentials in the docs -----------------------------------------------------------------
def test_new_docs_contain_no_credential_shaped_literals():
    """Examples read the demo password from the environment; a literal trips secret scanning."""
    demo_password = Settings.model_fields["demo_password"].default
    for name in ("api-guide.md", "development.md", "architecture.md", "scanner-development.md"):
        text = (DOCS / name).read_text(encoding="utf-8")
        assert demo_password not in text, f"docs/{name} contains the demo password"
        assert "eyJ" not in text, f"docs/{name} contains something shaped like a JWT"
