import io
import zipfile
from dataclasses import dataclass, field
from datetime import datetime

from redline.comments import add_comment, comment_on_paragraph
from redline.diff import diff_changes
from redline.parse import ParsedDocument
from redline.playbook import Playbook
from redline.schema import ReviewResult
from redline.tracked import Revisions, apply_changes
from redline.validate import Rejected, validate


@dataclass
class ReviewStats:
    edits: int = 0
    missing: int = 0
    rejected: list[Rejected] = field(default_factory=list)


def apply_review(
    document: ParsedDocument, playbook: Playbook, result: ReviewResult, author: str, date: datetime
) -> ReviewStats:
    accepted, missing, rejected = validate(result, document, playbook)
    revisions = Revisions(document.document.element.body, author, date)
    order = {p.id: i for i, p in enumerate(document.paragraphs)}
    by_para: dict[str, list] = {}
    for item in accepted:
        by_para.setdefault(item.edit.paragraph_id, []).append(item)

    for pid in sorted(by_para, key=order.get):
        items = by_para[pid]
        changes, owner = [], []
        for n, item in enumerate(items):
            for change in diff_changes(item.edit.find, item.edit.replace, item.start):
                changes.append(change)
                owner.append(n)
        created = apply_changes(document.by_id[pid], changes, revisions)
        for n, item in enumerate(items):
            elements = [el for group, o in zip(created, owner) if o == n for el in group]
            add_comment(
                document.document, elements[0], elements[-1],
                f"[{item.edit.rule_id}] {item.edit.comment}", author, date,
            )

    for m in sorted(missing, key=lambda m: order[m.after_paragraph_id]):
        text = f"[{m.rule_id}] {m.comment}\nSuggested text: {m.text}"
        comment_on_paragraph(document.document, document.by_id[m.after_paragraph_id], text, author, date)

    return ReviewStats(len(accepted), len(missing), rejected)


def save_stable(document, path: str) -> None:
    """Save with fixed zip timestamps so the same input gives byte-identical output."""
    buf = io.BytesIO()
    document.save(buf)
    with zipfile.ZipFile(buf) as src, zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            fixed = zipfile.ZipInfo(info.filename, date_time=(1980, 1, 1, 0, 0, 0))
            fixed.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(fixed, src.read(info.filename))
