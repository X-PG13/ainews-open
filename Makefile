PYTHON ?= python3

.PHONY: ingest extract enrich digest pipeline publish publications refresh-publications housekeeping monitoring-up monitoring-down lint build sbom check serve test coverage smoke

ingest:
	$(PYTHON) -m ainews ingest

enrich:
	$(PYTHON) -m ainews enrich --limit 20

extract:
	$(PYTHON) -m ainews extract --limit 20

digest:
	$(PYTHON) -m ainews print-digest --use-llm --persist

pipeline:
	$(PYTHON) -m ainews run-pipeline --use-llm --persist --export

publish:
	$(PYTHON) -m ainews publish --use-llm --persist --export --target static_site

publications:
	$(PYTHON) -m ainews list-publications --limit 20

refresh-publications:
	$(PYTHON) -m ainews refresh-publications --target wechat --limit 20

housekeeping:
	$(PYTHON) -m ainews prune-source-runtime-history --retention-days 45

monitoring-up:
	docker compose --profile monitoring up --build -d

monitoring-down:
	docker compose --profile monitoring down

lint:
	$(PYTHON) -m ruff check src tests

build:
	$(PYTHON) -m build

sbom:
	PYTHON_BIN="$$( $(PYTHON) -c 'import sys; print(sys.executable)' )"; \
	$(PYTHON) -m cyclonedx_py environment "$$PYTHON_BIN" --pyproject pyproject.toml --mc-type application --output-reproducible --of JSON -o sbom.json

check: lint test build

serve:
	$(PYTHON) -m uvicorn ainews.api:create_app --factory --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m unittest discover -s tests -v

coverage:
	$(PYTHON) -m coverage run -m unittest discover -s tests -v
	$(PYTHON) -m coverage report

smoke:
	@AINEWS_HOME="$(CURDIR)/.ainews-smoke" $(PYTHON) -m uvicorn ainews.api:create_app --factory --host 127.0.0.1 --port 8001 >/tmp/ainews-smoke.log 2>&1 & \
	PID=$$!; \
	trap 'kill $$PID >/dev/null 2>&1 || true' EXIT; \
	for attempt in $$(seq 1 30); do \
		if curl -fsS http://127.0.0.1:8001/health >/tmp/ainews-smoke-health.json; then \
			break; \
		fi; \
		sleep 1; \
	done; \
	$(PYTHON) -c 'import json; payload=json.load(open("/tmp/ainews-smoke-health.json", "r", encoding="utf-8")); assert payload["ready"] is True'
