FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/data /app/output /app/output/site \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "ainews.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
