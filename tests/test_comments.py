import io
from datetime import datetime, timezone

import docx
from docx.oxml.ns import qn

from redline.comments import add_comment, comment_on_paragraph
from redline.diff import diff_changes
from redline.parse import parse_document
from redline.revisions import document_texts
from redline.tracked import Revisions, apply_changes

DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def reviewed(document):
    original = document_texts(document.element.body, accept=True)
    parsed = parse_document(document)
    revisions = Revisions(document.element.body, "Reviewer", DATE)
    para = parsed.by_id["p0002"]
    find = "strictly confidential and secure"
    created = apply_changes(para, diff_changes(find, "confidential", para.text.index(find)), revisions)
    elements = [el for group in created for el in group]
    add_comment(document, elements[0], elements[-1], "[conf-1] Keep the standard of care plain.", "Reviewer", DATE)
    comment_on_paragraph(
        document, parsed.by_id["p0006"], "[law-1] Missing: governing law.\nSuggested text: New York law applies.",
        "Reviewer", DATE,
    )
    comment_on_paragraph(document, parsed.by_id["p0003"], "[x-1] Empty anchor.", "Reviewer", DATE)
    buf = io.BytesIO()
    document.save(buf)
    buf.seek(0)
    return original, docx.Document(buf)


def test_every_comment_has_range_and_reference(document):
    _, document = reviewed(document)
    body = document.element.body
    ids = [str(c.comment_id) for c in document.comments]
    assert ids == ["0", "1", "2"]
    for cid in ids:
        assert len(body.xpath(f'.//w:commentRangeStart[@w:id="{cid}"]')) == 1
        assert len(body.xpath(f'.//w:commentRangeEnd[@w:id="{cid}"]')) == 1
        refs = body.xpath(f'.//w:commentReference[@w:id="{cid}"]')
        assert len(refs) == 1
        assert not list(refs[0].iterancestors(qn("w:del"), qn("w:ins")))


def test_comment_text_author_and_date(document):
    _, document = reviewed(document)
    comments = list(document.comments)
    assert comments[0].text == "[conf-1] Keep the standard of care plain."
    assert comments[1].text == "[law-1] Missing: governing law.\nSuggested text: New York law applies."
    assert all(c.author == "Reviewer" and c.initials == "R" for c in comments)
    assert all(c.timestamp == DATE for c in comments)


def test_comments_do_not_change_text(document):
    original, document = reviewed(document)
    accepted = document_texts(document.element.body, accept=True)
    assert accepted[1] == original[1].replace("strictly confidential and secure", "confidential")
    assert document_texts(document.element.body, accept=False) == original
