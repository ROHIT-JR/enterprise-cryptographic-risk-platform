FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates docker.io \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 ecdat \
    && useradd --uid 10001 --gid ecdat --create-home --shell /usr/sbin/nologin ecdat

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements.txt

COPY backend /app/backend
COPY scanners /app/scanners
COPY cbom_engine /app/cbom_engine
COPY knowledge_graph /app/knowledge_graph
COPY risk_engine /app/risk_engine
COPY sample_data /app/sample_data

RUN mkdir -p /app/scan-data && chown -R ecdat:ecdat /app

USER ecdat
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=3)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
