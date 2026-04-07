PYTHON ?= python3

.PHONY: ingest extract enrich digest pipeline publish publications refresh-publications lint build check serve test

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

lint:
	$(PYTHON) -m ruff check src tests

build:
	$(PYTHON) -m build

check: lint test build

serve:
	$(PYTHON) -m uvicorn ainews.api:create_app --factory --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m unittest discover -s tests -v
