PY ?= .venv/bin/python
DEMO_DATE = 2026-01-01T00:00:00Z

.PHONY: install test demo fixtures

install:
	python3.11 -m venv .venv
	.venv/bin/pip install -e '.[test]'

test:
	$(PY) -m pytest -q

fixtures:
	$(PY) scripts/make_fixtures.py

demo:
	@test -f fixtures/demo_response.json || { echo "fixtures/demo_response.json is missing; create it with scripts/run_live.sh"; exit 1; }
	@mkdir -p out
	$(PY) -m redline.cli review fixtures/counterparty_nda.docx --playbook playbooks/nda.yaml \
		--offline fixtures/demo_response.json --date $(DEMO_DATE) --out out/demo_redlined.docx
