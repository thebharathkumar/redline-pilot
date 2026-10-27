from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

ClauseType = Literal[
    "definition",
    "permitted_disclosure",
    "term_survival",
    "return_destruction",
    "remedies_law",
]


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z]+(-[a-z]+)*$")
    clause_type: ClauseType
    name: str
    preferred: str
    fallbacks: list[str] = []
    red_flags: list[str] = []
    required: bool
    suggested_text: str | None = None
    contractnli: str | None = Field(default=None, pattern=r"^nda-\d+$")

    @model_validator(mode="after")
    def required_rules_have_text(self):
        if self.required and not self.suggested_text:
            raise ValueError(f"rule {self.id} is required but has no suggested_text")
        return self


class Playbook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    based_on: str
    rules: list[Rule]

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [r.id for r in self.rules]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError("duplicate rule ids: " + ", ".join(duplicates))
        return self

    def rule(self, rule_id: str) -> Rule | None:
        return next((r for r in self.rules if r.id == rule_id), None)

    def by_clause_type(self, clause_type: str) -> list[Rule]:
        return [r for r in self.rules if r.clause_type == clause_type]


def load_playbook(path: str) -> Playbook:
    with open(path, encoding="utf-8") as f:
        return Playbook.model_validate(yaml.safe_load(f))
