import json

import pytest
import yaml

from redline import evaluate
from redline.gold import GoldEdit, GoldFile, load_gold_dir, match_edits, token_f1
from redline.schema import Edit, ReviewResult


def test_template_parses_and_is_skipped(tmp_path):
    template = yaml.safe_load(open("eval/gold/TEMPLATE.yaml"))
    GoldFile.model_validate(template)
    assert load_gold_dir(tmp_path) == []
    (tmp_path / "TEMPLATE.yaml").write_text(open("eval/gold/TEMPLATE.yaml").read())
    assert load_gold_dir(tmp_path) == []


def test_token_f1():
    assert token_f1("courts in Texas", "courts in Texas") == 1.0
    assert token_f1("Texas", "New York") == 0.0
    assert token_f1("Travis County Texas", "Travis County") == pytest.approx(0.8)
    assert token_f1("Travis County, Texas", "Travis County") == pytest.approx(0.4)


def edit(pid, rule, find, replace="x"):
    return Edit(paragraph_id=pid, rule_id=rule, find=find, replace=replace, comment="c")


def gold(pid, rule, find, replace="x"):
    return GoldEdit(paragraph_id=pid, rule_id=rule, find=find, replace=replace)


def test_matching_is_one_to_one_on_paragraph_and_rule():
    predicted = [edit("p1", "a", "one two"), edit("p1", "a", "three"), edit("p2", "b", "four")]
    golds = [gold("p1", "a", "three"), gold("p2", "c", "four")]
    pairs = match_edits(predicted, golds)
    assert [(p.find, g.find) for p, g in pairs] == [("three", "three")]


def test_run_edits_scores_validated_edits(tmp_path):
    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()
    (gold_dir / "case.yaml").write_text(yaml.safe_dump({
        "document": "fixtures/counterparty_nda.docx",
        "edits": [
            {"paragraph_id": "p0013", "rule_id": "law-venue", "find": "Texas", "replace": "New York"},
            {"paragraph_id": "p0011", "rule_id": "term-length", "find": "In perpetuity.", "replace": "1 year."},
        ],
    }))

    class Fake:
        model = "fake-model"

        def review(self, document, playbook):
            return ReviewResult(edits=[
                edit("p0013", "law-venue", "Texas", "New York"),
                edit("p0015", "law-venue", "Travis County, Texas", "New York County, New York"),
                edit("p0015", "law-venue", "not in the paragraph"),
            ])

    data = evaluate.run_edits(Fake(), gold_dir, tmp_path / "responses")
    assert (data["predicted"], data["gold"]) == (2, 2)
    assert (data["precision"]["k"], data["precision"]["n"]) == (1, 2)
    assert (data["recall"]["k"], data["recall"]["n"]) == (1, 2)
    assert data["span_token_f1"] == 1.0
    md_path = tmp_path / "results.md"
    evaluate.write_results("edits", data, "fake-model", "redline eval --edits gold", tmp_path / "r.json", md_path)
    assert "| precision | 1/2" in md_path.read_text()
    assert json.loads((tmp_path / "r.json").read_text())["edits"]["gold_files"] == 1
