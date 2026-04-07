FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AINEWS_HOME=/app \
    AINEWS_LOG_FORMAT=json

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/data /app/output /app/output/site \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import sys, urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3); sys.exit(0)"

CMD ["uvicorn", "ainews.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
