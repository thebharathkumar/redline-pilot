import json
from typing import Protocol

from redline.parse import ParsedDocument
from redline.playbook import Playbook
from redline.schema import ReviewResult


class Provider(Protocol):
    def review(self, document: ParsedDocument, playbook: Playbook) -> ReviewResult: ...


class ReplayProvider:
    """Returns a previously saved model response instead of calling a model."""

    def __init__(self, path: str):
        self.path = path

    def review(self, document: ParsedDocument, playbook: Playbook) -> ReviewResult:
        with open(self.path, encoding="utf-8") as f:
            return ReviewResult.model_validate(json.load(f))


def save_response(result: ReviewResult, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2) + "\n")
