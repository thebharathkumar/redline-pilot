#!/bin/sh
# Runs every step that calls the live model. Run on a machine with a filled-in .env:
#   cp .env.example .env    # then set ANTHROPIC_API_KEY and REDLINE_MODEL
#   scripts/run_live.sh             # all steps
#   scripts/run_live.sh demo        # one step
set -eu
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    echo "error: .env not found; cp .env.example .env and fill it in" >&2
    exit 1
fi
set -a; . ./.env; set +a
: "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY in .env}"
: "${REDLINE_MODEL:?set REDLINE_MODEL in .env}"

PY=.venv/bin/python
if [ ! -x "$PY" ]; then
    echo "error: $PY not found; run make install first" >&2
    exit 1
fi

demo() {
    mkdir -p out
    "$PY" -m redline.cli review fixtures/counterparty_nda.docx --playbook playbooks/nda.yaml \
        --date 2026-01-01T00:00:00Z --save-response fixtures/demo_response.json \
        --out out/demo_live.docx
    make demo
}

detection() {
    "$PY" scripts/fetch_contractnli.py --n 25
    "$PY" -m redline.cli eval --detection contractnli --n 25
}

edits() {
    if ! ls eval/gold/*.yaml 2>/dev/null | grep -qv TEMPLATE.yaml; then
        echo "skipping edit eval: no gold files in eval/gold yet" >&2
        return 0
    fi
    "$PY" -m redline.cli eval --edits eval/gold
}

step="${1:-all}"
case "$step" in
    demo) demo ;;
    detection) detection ;;
    edits) edits ;;
    all) demo; detection; edits ;;
    *) echo "usage: scripts/run_live.sh [demo|detection|edits|all]" >&2; exit 2 ;;
esac
