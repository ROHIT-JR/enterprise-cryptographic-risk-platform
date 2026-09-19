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
COPY sample_data /app/sample_data
COPY alembic.ini /app/alembic.ini
COPY backend/migrations /app/backend/migrations

RUN mkdir -p /app/scan-data && chown -R ecdat:ecdat /app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/full', timeout=3)"

FROM base AS development

USER ecdat
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production

USER ecdat
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
