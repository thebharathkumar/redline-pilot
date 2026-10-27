import pytest
import yaml
from pydantic import ValidationError

from redline.playbook import Playbook, load_playbook

PATH = "playbooks/nda.yaml"


def test_nda_playbook_loads_and_covers_five_clause_types():
    playbook = load_playbook(PATH)
    assert {r.clause_type for r in playbook.rules} == {
        "definition", "permitted_disclosure", "term_survival", "return_destruction", "remedies_law",
    }
    assert playbook.rule("disc-legal").contractnli == "nda-8"
    assert playbook.rule("missing") is None


def raw():
    with open(PATH) as f:
        return yaml.safe_load(f)


def test_duplicate_ids_are_rejected():
    data = raw()
    data["rules"].append(dict(data["rules"][0]))
    with pytest.raises(ValidationError, match="duplicate rule ids"):
        Playbook.model_validate(data)


def test_required_rule_needs_suggested_text():
    data = raw()
    data["rules"][0]["suggested_text"] = None
    with pytest.raises(ValidationError, match="no suggested_text"):
        Playbook.model_validate(data)


def test_unknown_fields_and_bad_clause_types_are_rejected():
    data = raw()
    data["rules"][0]["priority"] = "high"
    with pytest.raises(ValidationError):
        Playbook.model_validate(data)
    data = raw()
    data["rules"][0]["clause_type"] = "indemnity"
    with pytest.raises(ValidationError):
        Playbook.model_validate(data)
