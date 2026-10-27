import re
from dataclasses import dataclass

from redline.parse import ParsedDocument
from redline.playbook import Playbook
from redline.schema import Edit, Missing, ReviewResult
from redline.tracked import blocked_reason


@dataclass
class Located:
    edit: Edit
    start: int
    end: int


@dataclass
class Rejected:
    kind: str
    paragraph_id: str
    rule_id: str
    reason: str


def whole_word_starts(text: str, find: str) -> list[int]:
    pattern = re.escape(find)
    if re.match(r"\w", find):
        pattern = r"(?<!\w)" + pattern
    if re.search(r"\w$", find):
        pattern += r"(?!\w)"
    # Lookahead so overlapping occurrences are counted too.
    return [m.start() for m in re.finditer(f"(?={pattern})", text)]


def locate(edit: Edit, document: ParsedDocument, playbook: Playbook) -> Located | str:
    if playbook.rule(edit.rule_id) is None:
        return "unknown rule_id"
    para = document.by_id.get(edit.paragraph_id)
    if para is None:
        return "unknown paragraph_id"
    if not edit.find:
        return "find is empty"
    if edit.find == edit.replace:
        return "replace equals find"
    starts = whole_word_starts(para.text, edit.find)
    if not starts:
        return "find not in paragraph"
    if len(starts) > 1:
        return f"find occurs {len(starts)} times"
    start, end = starts[0], starts[0] + len(edit.find)
    reason = blocked_reason(para, start, end)
    return reason or Located(edit, start, end)


def validate(
    result: ReviewResult, document: ParsedDocument, playbook: Playbook
) -> tuple[list[Located], list[Missing], list[Rejected]]:
    rejected: list[Rejected] = []
    located: list[Located] = []
    for edit in result.edits:
        outcome = locate(edit, document, playbook)
        if isinstance(outcome, str):
            rejected.append(Rejected("edit", edit.paragraph_id, edit.rule_id, outcome))
        else:
            located.append(outcome)

    accepted: list[Located] = []
    for item in sorted(located, key=lambda x: (x.edit.paragraph_id, x.start)):
        prev = accepted[-1] if accepted else None
        if prev and prev.edit.paragraph_id == item.edit.paragraph_id and item.start < prev.end:
            rejected.append(Rejected("edit", item.edit.paragraph_id, item.edit.rule_id, f"overlaps {prev.edit.rule_id}"))
        else:
            accepted.append(item)

    missing: list[Missing] = []
    for m in result.missing:
        if playbook.rule(m.rule_id) is None:
            rejected.append(Rejected("missing", m.after_paragraph_id, m.rule_id, "unknown rule_id"))
        elif m.after_paragraph_id not in document.by_id:
            rejected.append(Rejected("missing", m.after_paragraph_id, m.rule_id, "unknown paragraph_id"))
        else:
            missing.append(m)
    return accepted, missing, rejected


def format_rejections(rejected: list[Rejected]) -> str:
    if not rejected:
        return ""
    rows = [("kind", "paragraph", "rule", "reason")] + [(r.kind, r.paragraph_id, r.rule_id, r.reason) for r in rejected]
    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    lines = ["  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip() for row in rows]
    return "dropped:\n" + "\n".join(lines)
