FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# `upgrade` pulls in Debian security fixes published since the base image was built.
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install --no-install-recommends -y ca-certificates docker.io \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 ecdat \
    && useradd --uid 10001 --gid ecdat --create-home --shell /usr/sbin/nologin ecdat

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip setuptools \
    && python -m pip install -r /tmp/requirements.txt

COPY backend /app/backend
COPY scanners /app/scanners
COPY cbom_engine /app/cbom_engine
COPY knowledge_graph /app/knowledge_graph
COPY risk_engine /app/risk_engine
COPY migration_engine /app/migration_engine
COPY graph_analysis /app/graph_analysis
COPY lifecycle_engine /app/lifecycle_engine
COPY benchmarks /app/benchmarks
COPY config /app/config
COPY alembic.ini /app/alembic.ini
COPY backend/migrations /app/backend/migrations

RUN mkdir -p /app/scan-data && chown -R ecdat:ecdat /app && chmod +x /app/backend/start.sh

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/full', timeout=3)"

FROM base AS development

# git is needed to pip-install ecdat-x-demo-seed's git+https source below; the
# production stage never installs requirements-dev.txt, so it never needs git
# and never bundles the demo-seed package or the synthetic data it carries.
RUN apt-get update && apt-get install --no-install-recommends -y git && rm -rf /var/lib/apt/lists/*
COPY backend/requirements-dev.txt /tmp/requirements-dev.txt
RUN python -m pip install -r /tmp/requirements-dev.txt

USER ecdat
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production

# Packaging tools are not needed at runtime; their vendored dependencies (e.g. msgpack,
# setuptools' bundled copies) otherwise show up as image vulnerabilities.
RUN python -m pip uninstall -y pip setuptools

USER ecdat
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
