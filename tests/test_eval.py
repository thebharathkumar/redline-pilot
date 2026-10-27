import json

import pytest

from redline import contractnli, evaluate
from redline.parse import load
from redline.playbook import load_playbook
from redline.schema import Edit, Missing, ReviewResult
from redline.stats import format_rate, wilson

HYPOTHESES = ["nda-3", "nda-5", "nda-7", "nda-8", "nda-16", "nda-19", "nda-20"]


def test_wilson_interval():
    lo, hi = wilson(5, 10)
    assert lo == pytest.approx(0.2366, abs=1e-4) and hi == pytest.approx(0.7634, abs=1e-4)
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-4)
    assert wilson(0, 0) is None


def test_should_flag():
    assert evaluate.should_flag("Contradiction", required=False)
    assert evaluate.should_flag("NotMentioned", required=True)
    assert not evaluate.should_flag("NotMentioned", required=False)
    assert not evaluate.should_flag("Entailment", required=True)


def synthetic(tmp_path, overrides):
    documents = []
    for i, changed in enumerate(overrides):
        labels = {h: "Entailment" for h in HYPOTHESES}
        labels.update(changed)
        documents.append({
            "id": i + 1,
            "file_name": f"doc{i}.pdf",
            "text": f"NON-DISCLOSURE AGREEMENT {i}\nThe parties agree.\n\nSigned.",
            "annotation_sets": [{"annotations": {h: {"choice": c, "spans": []} for h, c in labels.items()}}],
        })
    source = tmp_path / "test.json"
    source.write_text(json.dumps({"documents": documents, "labels": {}}))
    return contractnli.convert(source, tmp_path / "docx", n=len(documents))


def test_convert_writes_docx_and_labels(tmp_path):
    manifest = synthetic(tmp_path, [{}, {"nda-8": "NotMentioned"}])
    assert [m["file"] for m in manifest] == ["000_1.docx", "001_2.docx"]
    assert manifest[1]["labels"]["nda-8"] == "NotMentioned"
    parsed = load(str(tmp_path / "docx" / "000_1.docx"))
    assert [p.text for p in parsed.paragraphs] == ["NON-DISCLOSURE AGREEMENT 0", "The parties agree.", "Signed."]
    assert json.loads((tmp_path / "docx" / "labels.json").read_text()) == manifest


class FakeProvider:
    model = "fake-model"

    def __init__(self, flags):
        self.flags = list(flags)

    def review(self, document, playbook):
        rules = self.flags.pop(0)
        edits = [Edit(paragraph_id="p0002", rule_id=r, find="agree", replace="agree", comment="c") for r in rules[:1]]
        missing = [Missing(rule_id=r, after_paragraph_id="p0002", text="t", comment="c") for r in rules[1:]]
        return ReviewResult(edits=edits, missing=missing)


def test_detection_counts_and_results_files(tmp_path):
    synthetic(tmp_path, [{"nda-8": "NotMentioned"}, {"nda-7": "Contradiction"}, {"nda-3": "NotMentioned"}])
    provider = FakeProvider([["disc-legal"], [], ["ci-oral"]])
    playbook = load_playbook("playbooks/nda.yaml")
    data = evaluate.run_detection(provider, playbook, 3, tmp_path / "docx", tmp_path / "responses")

    assert data["documents"] == 3
    assert data["per_rule"]["disc-legal"]["counts"] == {"tp": 1, "fp": 0, "fn": 0, "tn": 2}
    assert data["per_rule"]["disc-advisors"]["counts"] == {"tp": 0, "fp": 0, "fn": 1, "tn": 2}
    assert data["per_rule"]["ci-oral"]["counts"] == {"tp": 0, "fp": 1, "fn": 0, "tn": 2}
    overall = data["overall"]
    assert overall["counts"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 18}
    assert (overall["precision"]["k"], overall["precision"]["n"]) == (1, 2)
    assert (overall["recall"]["k"], overall["recall"]["n"]) == (1, 2)
    assert overall["f1"] == pytest.approx(0.5)
    assert len(list((tmp_path / "responses").glob("*.json"))) == 3

    json_path, md_path = tmp_path / "results.json", tmp_path / "results.md"
    evaluate.write_results("detection", data, provider.model, "redline eval --detection contractnli --n 3", json_path, md_path)
    saved = json.loads(json_path.read_text())["detection"]
    assert saved["model"] == "fake-model" and saved["documents"] == 3
    assert saved["command"] == "redline eval --detection contractnli --n 3"
    md = md_path.read_text()
    assert "n = 3 documents" in md
    assert f"| overall | | {format_rate(overall['precision'])} |" in md
