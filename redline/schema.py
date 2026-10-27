from pydantic import BaseModel, ConfigDict


class Edit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph_id: str
    rule_id: str
    find: str
    replace: str
    comment: str


class Missing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    after_paragraph_id: str
    text: str
    comment: str


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = None
    edits: list[Edit] = []
    missing: list[Missing] = []
