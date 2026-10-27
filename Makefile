PY ?= .venv/bin/python

.PHONY: install test

install:
	python3.11 -m venv .venv
	.venv/bin/pip install -e '.[test]'

test:
	$(PY) -m pytest -q
