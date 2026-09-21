# ruff: noqa: E501  (long lines here are documentation prose, which reads worse when wrapped)
"""Render the generated blocks of docs/architecture.md from the code they describe.

Two diagrams are generated rather than hand-drawn so they cannot drift:

* the database ER diagram, from the SQLAlchemy models, and
* the TOPSIS worked example, from the real solver and the PQC knowledge base.

A test fails if the committed blocks differ from this script's output.

    python scripts/generate_docs.py           # print the blocks
    python scripts/generate_docs.py --write   # refresh docs/architecture.md in place
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("ECDAT_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("ECDAT_NEO4J_ENABLED", "false")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import backend.app.models  # noqa: E402,F401  (registers every table on Base.metadata)
from backend.app.models.base import Base  # noqa: E402

ARCHITECTURE = ROOT / "docs" / "architecture.md"
API_GUIDE = ROOT / "docs" / "api-guide.md"
DEVELOPMENT = ROOT / "docs" / "development.md"

# Columns worth showing next to the keys. Everything else (timestamps, blobs, secrets such as
# password and token hashes) is left out to keep the diagram readable. Each name is checked
# against the model, so a renamed column fails loudly instead of silently disappearing.
NOTABLE: dict[str, list[str]] = {
    "organizations": ["name", "industry"],
    "users": ["username", "email", "role", "is_active"],
    "refresh_tokens": ["expires_at", "revoked_at"],
    "audit_logs": ["action", "timestamp"],
    "projects": ["name", "criticality"],
    "scans": ["source_type", "target", "status", "progress"],
    "assets": ["asset_type", "name", "algorithm", "lifecycle_state", "governance_status"],
    "asset_relationships": ["relationship_type"],
    "business_context": ["criticality", "data_lifetime_years", "data_sensitivity"],
    "risk_findings": ["score", "severity"],
    "risk_analysis": ["quantum_score", "hndl_score", "centrality_score", "final_score", "severity"],
    "migration_plan": ["recommended_algorithm", "wave", "complexity", "priority_score"],
    "crypto_lifecycle_events": ["previous_state", "new_state", "source", "migration_wave"],
}

# organization_id and project_id are copied onto every domain table for tenant isolation. Drawing
# every one of those edges would bury the real structure, so they are drawn only where they are
# the table's genuine parent. The columns still appear (marked FK) inside each entity.
ORGANIZATION_EDGES = {"projects", "users", "audit_logs"}
PROJECT_EDGES = {"scans", "assets"}

_TYPES = {
    "String": "string",
    "Text": "text",
    "Integer": "int",
    "Float": "float",
    "Boolean": "bool",
    "DateTime": "datetime",
    "JSON": "json",
}


def _type_name(column) -> str:
    return _TYPES.get(type(column.type).__name__, "string")


def _entity(table) -> list[str]:
    columns = {column.name: column for column in table.columns}
    unknown = [name for name in NOTABLE.get(table.name, []) if name not in columns]
    if unknown:
        raise KeyError(f"{table.name}: NOTABLE lists columns that do not exist: {unknown}")
    lines = [f"    {table.name.upper()} {{"]
    for column in table.columns:
        if column.primary_key:
            lines.append(f"        {_type_name(column)} {column.name} PK")
    for column in table.columns:
        if column.foreign_keys:
            lines.append(f"        {_type_name(column)} {column.name} FK")
    for name in NOTABLE.get(table.name, []):
        lines.append(f"        {_type_name(columns[name])} {name}")
    lines.append("    }")
    return lines


def _relationships(tables) -> list[str]:
    lines = []
    for table in tables:
        for column in table.columns:
            for foreign_key in column.foreign_keys:
                parent = foreign_key.column.table.name
                if parent == "organizations" and table.name not in ORGANIZATION_EDGES:
                    continue
                if parent == "projects" and table.name not in PROJECT_EDGES:
                    continue
                parent_side = "|o" if column.nullable else "||"  # optional vs required parent
                child_side = "o|" if column.unique else "o{"  # at most one vs many children
                edge = f"{parent.upper()} {parent_side}--{child_side} {table.name.upper()}"
                lines.append(f'    {edge} : "{column.name}"')
    return lines


def render_er() -> str:
    tables = sorted(Base.metadata.sorted_tables, key=lambda table: table.name)
    lines = ["```mermaid", "erDiagram"]
    lines += _relationships(tables)
    for table in tables:
        lines += _entity(table)
    lines.append("```")
    return "\n".join(lines)


CRITERIA_LABELS = {
    "performance_rank": "performance rank",
    "public_key_bytes": "public key (B)",
    "sig_ct_size": "ciphertext (B)",
    "maturity": "maturity",
    "compatibility": "compatibility",
    "migration_complexity": "ease of migration",
}


def _row(cells) -> str:
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def _table(header, rows, align_right_from=1) -> list[str]:
    left = min(align_right_from, len(header))  # columns from here on are right-aligned
    align = ["---"] * left + ["---:"] * (len(header) - left)
    return [_row(header), _row(align), *(_row(row) for row in rows)]


def _solve(required_level: int):
    from migration_engine.pqc_knowledge_base import PQCKnowledgeBase
    from migration_engine.topsis_engine import solve

    candidates = [
        c
        for c in PQCKnowledgeBase().candidates_for_function("key_establishment")
        if c.nist_level >= required_level
    ]
    matrix = [
        [
            c.performance_rank,
            c.public_key_bytes,
            c.sig_or_ct_bytes,
            c.maturity,
            c.compatibility,
            c.migration_complexity,
        ]
        for c in candidates
    ]
    return candidates, matrix, solve([c.name for c in candidates], matrix)


def render_topsis() -> str:
    from migration_engine.topsis_engine import CRITERIA_ORDER, CRITERIA_TYPES

    candidates, matrix, solution = _solve(required_level=1)
    weights = solution.weights
    header = ["Candidate", *(CRITERIA_LABELS[c] for c in CRITERIA_ORDER)]
    out = ["**Step 1: the decision matrix** (raw values from the knowledge base)", ""]
    out += _table(
        header,
        [[c.name, *row] for c, row in zip(candidates, matrix, strict=True)],
    )
    out += [
        "",
        "Weights: "
        + ", ".join(
            f"{CRITERIA_LABELS[c]} {weights[c]:.2f} ({'benefit' if CRITERIA_TYPES[c] else 'cost'})"
            for c in CRITERIA_ORDER
        ),
    ]
    ranked = {r.name: r for r in solution.rankings}
    out += [
        "",
        "**Step 2: normalize and weight, then find the ideal and anti-ideal solutions**",
        "",
    ]
    rows = [
        [c.name, *(f"{ranked[c.name].scores[k]:.4f}" for k in CRITERIA_ORDER)] for c in candidates
    ]
    rows.append(["**Ideal (best)**", *(f"{solution.ideal[k]:.4f}" for k in CRITERIA_ORDER)])
    rows.append(
        ["**Anti-ideal (worst)**", *(f"{solution.anti_ideal[k]:.4f}" for k in CRITERIA_ORDER)]
    )
    out += _table(header, rows)
    out += [
        "",
        "**Step 3: distance to each, and the closeness coefficient** `C = D− / (D+ + D−)`",
        "",
    ]
    out += _table(
        ["Rank", "Candidate", "D+ (to ideal)", "D− (to anti-ideal)", "Closeness C"],
        [
            [
                r.rank,
                r.name,
                f"{r.distance_positive:.4f}",
                f"{r.distance_negative:.4f}",
                f"{r.closeness:.4f}",
            ]
            for r in solution.rankings
        ],
        align_right_from=2,
    )
    out += [
        "",
        "**The same decision with a stricter security floor** (`required_security_level = 3`)",
        "",
    ]
    _, _, strict = _solve(required_level=3)
    out += _table(
        ["Rank", "Candidate", "Closeness C"],
        [[r.rank, r.name, f"{r.closeness:.4f}"] for r in strict.rankings],
        align_right_from=2,
    )
    return "\n".join(out)


def render_endpoint_map() -> str:
    """One table per feature area, read from the live OpenAPI spec (never hand-edited)."""
    from backend.app.auth.permissions import ROLE_PERMISSIONS, Permission
    from backend.app.main import app
    from backend.app.openapi_docs import OPENAPI_TAGS

    spec = app.openapi()
    role_order = ["viewer", "auditor", "security_analyst", "administrator"]

    def needs(operation) -> str:
        minimum = operation.get("x-minimum-role")
        if minimum:  # enforced inside a service, so it is declared explicitly
            return f"`{minimum}` and above"
        security = operation.get("security")
        if not security:
            return "Nothing (public)"
        scopes = security[0].get("HTTPBearer") or []
        if not scopes:
            return "Any signed-in user"
        allowed = [
            role.value
            for role in ROLE_PERMISSIONS
            if all(Permission(scope) in ROLE_PERMISSIONS[role] for scope in scopes)
        ]
        allowed.sort(key=role_order.index)
        return ", ".join(f"`{name}`" for name in allowed[:1]) + (
            " and above" if len(allowed) > 1 else ""
        )

    def first_sentence(text: str) -> str:
        paragraph = " ".join((text or "").split("\n\n")[0].split())
        head, dot, _ = paragraph.partition(". ")
        return (head + dot.strip()) if dot else paragraph

    grouped: dict[str, list[tuple[str, str, str, str]]] = {tag["name"]: [] for tag in OPENAPI_TAGS}
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            tag = operation["tags"][0]
            if tag == "Compatibility" or not (
                path.startswith("/api/v1") or path.startswith("/health")
            ):
                continue
            grouped[tag].append(
                (path, method.upper(), first_sentence(operation["description"]), needs(operation))
            )

    out = []
    for tag in OPENAPI_TAGS:
        rows = sorted(grouped[tag["name"]])
        if not rows:
            continue
        out += [f"#### {tag['name']}", "", tag["description"], ""]
        out += _table(
            ["Endpoint", "What it does", "Needs"],
            [[f"`{m} {path}`", what, need] for path, m, what, need in rows],
            align_right_from=3,
        )
        out.append("")
    legacy = sorted(
        {
            path
            for path, item in spec["paths"].items()
            for op in item.values()
            if op["tags"][0] == "Compatibility"
        }
    )
    out += [
        "#### Compatibility aliases",
        "",
        "Unversioned paths kept for older clients: " + ", ".join(f"`{p}`" for p in legacy) + ".",
    ]
    return "\n".join(out)


def render_role_matrix() -> str:
    from backend.app.auth.permissions import ROLE_PERMISSIONS, Permission, Role

    roles = [Role.VIEWER, Role.AUDITOR, Role.SECURITY_ANALYST, Role.ADMINISTRATOR]
    meaning = {
        Permission.VIEW_DASHBOARD: "Dashboards, benchmarks, verification, compliance",
        Permission.VIEW_SCANS: "Read scans and inventory",
        Permission.RUN_SCANS: "Start scans, create projects, run benchmarks",
        Permission.ANALYZE_RISKS: "Set business context for an asset",
        Permission.CREATE_MIGRATION_PLANS: "Create migration plans",
        Permission.VIEW_REPORTS: "Read the audit trail and reports",
        Permission.EXPORT_FINDINGS: "Export reports and the CBOM",
        Permission.MANAGE_USERS: "List and create users",
        Permission.CONFIGURE_ORGANIZATION: "Change organization settings",
    }
    missing = set(Permission) - set(meaning)
    if missing:
        raise KeyError(f"role matrix has no description for: {sorted(p.value for p in missing)}")
    from backend.app.main import app

    required: set[str] = set()  # permissions that at least one v1 endpoint actually enforces
    for item in app.openapi()["paths"].values():
        for operation in item.values():
            for requirement in operation.get("security") or []:
                required.update(requirement.get("HTTPBearer", []))

    def grants(permission) -> str:
        note = "" if permission.value in required else " *(no endpoint requires it yet)*"
        return meaning[permission] + note

    rows = [
        [f"`{permission.value}`", grants(permission)]
        + ["yes" if permission in ROLE_PERMISSIONS[role] else "" for role in roles]
        for permission in Permission
    ]
    return "\n".join(
        _table(
            ["Permission", "Grants", *(f"`{role.value}`" for role in roles)],
            rows,
            align_right_from=99,
        )
    )


# What each application setting does. Every field of Settings must appear here, so adding a
# setting without documenting it fails the docs test.
SETTING_DOCS = {
    "app_name": "Title shown in the API documentation.",
    "environment": "`production` enables startup checks (a strong secret key, no wildcard CORS) and HSTS.",
    "debug": "Reserved. Currently has no effect.",
    "api_prefix": "URL prefix of the versioned API.",
    "database_url": "SQLAlchemy URL. SQLite for local use, `postgresql+psycopg://...` for the stack.",
    "cors_origins": "Comma-separated browser origins allowed to call the API (exact match; `*` is refused in production).",
    "scan_storage_path": "Where uploaded archives are unpacked during a scan.",
    "max_upload_bytes": "Largest accepted repository upload (compressed).",
    "max_archive_files": "Most files a repository archive may contain.",
    "max_archive_uncompressed_bytes": "Most bytes a repository archive may expand to (zip-bomb guard).",
    "scanner_timeout_seconds": "Time budget for one scanner run.",
    "tls_connect_timeout_seconds": "Connect timeout for TLS endpoint scans.",
    "tls_allow_private_targets": "Allow TLS scans of private and loopback addresses. Off by default to prevent SSRF.",
    "docker_enabled": "Enable the Docker image scanner (needs access to the Docker socket).",
    "neo4j_enabled": "Project the graph into Neo4j. When off, the graph is served from the database.",
    "neo4j_uri": "Neo4j Bolt endpoint.",
    "neo4j_user": "Neo4j user.",
    "neo4j_password": "Neo4j password.",
    "seed_demo": "Load the SecureBank demo organization on startup (once).",
    "secret_key": "Signs JWTs. Must be a random value of 32+ characters in production.",
    "jwt_issuer": "`iss` claim of issued tokens.",
    "jwt_audience": "`aud` claim of issued tokens.",
    "access_token_minutes": "Access token lifetime.",
    "refresh_token_days": "Refresh token lifetime.",
    "rate_limit_per_minute": "Requests per minute allowed from one client before `429`.",
    "demo_password": "Password given to the seeded demo users.",
    "log_level": "Python logging level.",
}
SECRET_SETTINGS = {"secret_key", "demo_password", "neo4j_password"}


def render_settings() -> str:
    from backend.app.config import Settings

    missing = set(Settings.model_fields) - set(SETTING_DOCS)
    stale = set(SETTING_DOCS) - set(Settings.model_fields)
    if missing or stale:
        raise KeyError(
            f"SETTING_DOCS out of date: missing {sorted(missing)}, stale {sorted(stale)}"
        )

    def names(field_name: str, field) -> str:
        alias = field.validation_alias
        choices = alias.choices if alias is not None else [f"ECDAT_{field_name.upper()}"]
        return ", ".join(f"`{choice}`" for choice in choices)

    def default(field_name: str, field) -> str:
        if field_name in SECRET_SETTINGS:
            return "set in `.env`"
        value = field.get_default(call_default_factory=True)
        if isinstance(value, list):
            value = ",".join(value)
        if value in ("", None):
            return "empty"
        return f"`{value}`"

    rows = [
        [names(name, field), default(name, field), SETTING_DOCS[name]]
        for name, field in Settings.model_fields.items()
    ]
    return "\n".join(_table(["Variable", "Default", "Purpose"], rows, align_right_from=3))


# name -> (document that holds the block, renderer)
BLOCKS = {
    "er-diagram": (ARCHITECTURE, render_er),
    "topsis-example": (ARCHITECTURE, render_topsis),
    "endpoint-map": (API_GUIDE, render_endpoint_map),
    "role-matrix": (API_GUIDE, render_role_matrix),
    "settings": (DEVELOPMENT, render_settings),
}


def markers(name: str) -> tuple[str, str]:
    return f"<!-- {name}:start -->", f"<!-- {name}:end -->"


def render_all() -> dict[str, str]:
    return {name: render() for name, (_, render) in BLOCKS.items()}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # blocks contain non-ASCII (e.g. a minus sign)
    blocks = render_all()
    if "--write" not in sys.argv:
        for name, block in blocks.items():
            print(f"### {name}\n{block}\n")
        return
    texts: dict[Path, str] = {}
    for name, block in blocks.items():
        doc = BLOCKS[name][0]
        text = texts.setdefault(doc, doc.read_text(encoding="utf-8"))
        start, end = markers(name)
        pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
        if not pattern.search(text):
            raise SystemExit(f"{doc}: missing {start} ... {end} markers")
        texts[doc] = pattern.sub(lambda _, b=block, s=start, e=end: f"{s}\n{b}\n{e}", text)
    for doc, text in texts.items():
        doc.write_text(text, encoding="utf-8")
        print(f"updated {doc.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
