from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from redline.diff import tokenize
from redline.schema import Edit


class GoldEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph_id: str
    rule_id: str
    find: str
    replace: str


class GoldFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: str
    playbook: str = "playbooks/nda.yaml"
    edits: list[GoldEdit]


def load_gold_dir(path: Path) -> list[tuple[Path, GoldFile]]:
    files = sorted(p for p in path.glob("*.yaml") if p.name != "TEMPLATE.yaml")
    return [(p, GoldFile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))) for p in files]


def token_f1(predicted: str, gold: str) -> float:
    """Token-overlap F1 (bag of words, whitespace stripped)."""
    p = [t.strip() for t in tokenize(predicted) if t.strip()]
    g = [t.strip() for t in tokenize(gold) if t.strip()]
    if not p and not g:
        return 1.0
    remaining = list(g)
    common = 0
    for token in p:
        if token in remaining:
            remaining.remove(token)
            common += 1
    if common == 0:
        return 0.0
    precision, recall = common / len(p), common / len(g)
    return 2 * precision * recall / (precision + recall)


def match_edits(predicted: list[Edit], gold: list[GoldEdit]) -> list[tuple[Edit, GoldEdit]]:
    """Pair edits one to one on (paragraph_id, rule_id), best find-span overlap first."""
    candidates = [
        (token_f1(p.find, g.find), i, j)
        for i, p in enumerate(predicted)
        for j, g in enumerate(gold)
        if (p.paragraph_id, p.rule_id) == (g.paragraph_id, g.rule_id)
    ]
    used_p, used_g, pairs = set(), set(), []
    for _, i, j in sorted(candidates, key=lambda c: (-c[0], c[1], c[2])):
        if i not in used_p and j not in used_g:
            used_p.add(i)
            used_g.add(j)
            pairs.append((predicted[i], gold[j]))
    return pairs
