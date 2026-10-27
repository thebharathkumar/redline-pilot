# redline-pilot

redline-pilot reviews a counterparty NDA (.docx) against a playbook and writes a copy with Word tracked changes and comments that move the draft toward the customer's positions.

![Tracked changes and comments in Word](docs/word_redline.png)

(Screenshot not added yet.)

## Quickstart

```sh
make install
make demo
```

`make demo` replays a saved model response (`fixtures/demo_response.json`) against `fixtures/counterparty_nda.docx` with a fixed date and writes `out/demo_redlined.docx`. It needs no API key. The saved response is created once with `scripts/run_live.sh demo`; until then `make demo` stops with a message saying so.

Run the tests with `make test`. They need no network and no API key.

Live calls read `ANTHROPIC_API_KEY` and `REDLINE_MODEL` from the environment. Copy `.env.example` to `.env`, fill it in, and run `scripts/run_live.sh`, which loads `.env` and runs the demo response, the detection eval and the edit eval.

```sh
redline review CONTRACT.docx --playbook playbooks/nda.yaml --out OUT.docx \
    [--author "Reviewer"] [--date 2026-01-01T00:00:00Z] \
    [--offline RESPONSE.json] [--save-response RESPONSE.json] [--mode single]
redline eval [--detection contractnli] [--edits eval/gold] [--n 25]
```

## How it works

1. Parse body and table paragraphs, give each a stable id (p0001, ...) and map character offsets to runs; refuse input that already has tracked changes.
2. Send the contract (in `<contract>` tags, marked as data), the playbook and the instructions, in that order, to the model.
3. Validate the JSON reply with pydantic and retry once with the validation error; each edit names a paragraph, a rule, exact `find` text and its `replace`.
4. Drop edits whose `find` is missing, repeated, not on word boundaries, overlapping or tied to an unknown rule, and print them as a table on stderr.
5. Diff `find` against `replace` by word, split runs at the edit boundaries, and write `w:del` / `w:ins` with copied formatting, one id counter, author and UTC date.
6. Add one comment per edit (`[rule_id] rationale`) and a comment with suggested text for each missing clause.

## Playbook format

`playbooks/nda.yaml` holds one rule per position. Each rule has:

| field | meaning |
|---|---|
| `id` | short lowercase id, used in comments and eval files |
| `clause_type` | `definition`, `permitted_disclosure`, `term_survival`, `return_destruction` or `remedies_law` |
| `name` | short label |
| `preferred` | the customer's position, one or two sentences |
| `fallbacks` | acceptable alternatives, most preferred first |
| `red_flags` | wording that should always be changed |
| `required` | whether the clause must be present |
| `suggested_text` | text to propose when a required clause is missing |
| `contractnli` | ContractNLI hypothesis id used by the detection eval, or `null` |

```yaml
- id: disc-legal
  clause_type: permitted_disclosure
  name: Disclosure required by law
  preferred: >-
    Either party may disclose to the extent required by law, regulation, subpoena or court order,
    giving reasonable advance notice where legally permitted ...
  fallbacks:
    - Prompt notice after the disclosure, where advance notice is not legally permitted.
  red_flags:
    - No carve-out for legally compelled disclosure.
  required: true
  suggested_text: >-
    The Receiving Party may disclose Confidential Information to the extent required by law ...
  contractnli: nda-8
```

The preferred positions follow the Common Paper Mutual NDA Standard Terms v1.0, written from the buyer's side.

## Eval

Generated from `eval/results.md` by `scripts/update_readme.py`.

<!-- eval:start -->
### Detection

Model: claude-sonnet-5-5  
Date: 2026-10-27T08:36:06Z  
Command: `redline eval --detection contractnli --n 25`

ContractNLI test split, n = 25 documents. A rule should be flagged when the ContractNLI label is Contradiction, or NotMentioned for a required rule. Rates are k/n with a Wilson 95% interval.

| rule | hypothesis | precision | recall | F1 |
|---|---|---|---|---|
| ci-oral | nda-3 | 0/1 = 0.00 [0.00, 0.79] | 0/1 = 0.00 [0.00, 0.79] | 0.00 |
| disc-employees | nda-5 | 5/13 = 0.38 [0.18, 0.64] | 5/5 = 1.00 [0.57, 1.00] | 0.56 |
| disc-advisors | nda-7 | 3/10 = 0.30 [0.11, 0.60] | 3/4 = 0.75 [0.30, 0.95] | 0.43 |
| disc-legal | nda-8 | 9/19 = 0.47 [0.27, 0.68] | 9/13 = 0.69 [0.42, 0.87] | 0.56 |
| term-survival | nda-19 | 4/6 = 0.67 [0.30, 0.90] | 4/8 = 0.50 [0.22, 0.78] | 0.57 |
| ret-destroy | nda-16 | 19/22 = 0.86 [0.67, 0.95] | 19/20 = 0.95 [0.76, 0.99] | 0.90 |
| ret-retention | nda-20 | 21/22 = 0.95 [0.78, 0.99] | 21/21 = 1.00 [0.85, 1.00] | 0.98 |
| overall | | 61/93 = 0.66 [0.55, 0.74] | 61/72 = 0.85 [0.75, 0.91] | 0.74 |

Model calls: 25, input tokens: 174868, output tokens: 115769, mean latency: 32.2 s

### Edits

Model: claude-sonnet-5-5  
Date: 2026-10-27T08:52:44Z  
Command: `redline eval --edits eval/gold`

Gold files: 1. An edit matches when (paragraph_id, rule_id) agree. Rates are k/n with a Wilson 95% interval.

| metric | value |
|---|---|
| precision | 9/10 = 0.90 [0.60, 0.98] |
| recall | 9/9 = 1.00 [0.70, 1.00] |
| find F1: mean token F1 of the targeted wording, matched edits | 0.80 |
| replace F1: mean token F1 of the proposed wording, matched edits | 0.78 |

Model calls: 1, input tokens: 6193, output tokens: 4166, mean latency: 25.1 s
<!-- eval:end -->

The gold labels for the edit eval (`eval/gold/counterparty_nda.yaml`) were written by a language model from the playbook, without seeing the model's saved demo response. No human reviewer wrote them, so the edit scores measure agreement between two model passes, not accuracy against a lawyer. There is one gold file with 9 edits, so the sample is small.

## Decisions

TODO

## Limits

TODO

## Data and licenses

See [DATA.md](DATA.md). The fixtures and playbook are based on the Common Paper Mutual NDA Standard Terms v1.0 (CC BY 4.0). ContractNLI (CC BY 4.0) is downloaded into `data/` by `scripts/fetch_contractnli.py` and is not committed.

## Alternatives

- [Adeu](https://pypi.org/project/adeu/): a redlining engine that turns DOCX into CriticMarkup for the model and patches the XML back; this project keeps its own edit format (paragraph id plus exact quote) so validation and the eval can work on the same records.
- [Python-Redlines](https://pypi.org/project/python-redlines/): compares two whole .docx files with bundled .NET engines; this project applies individual edits from a model, so it writes the revisions directly instead of building a second document to compare.
- [docx-revisions](https://pypi.org/project/docx-revisions/): reads and writes `w:ins` / `w:del` on top of python-docx; this project writes the OOXML itself so run splitting, formatting copies and revision ids are covered by its own tests.
