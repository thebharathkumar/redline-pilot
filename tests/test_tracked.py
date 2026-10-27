import io
from datetime import datetime, timezone

import docx
import pytest
from docx.oxml.ns import qn

from redline.diff import diff_changes
from redline.parse import parse_document
from redline.revisions import document_texts
from redline.tracked import Revisions, apply_changes

DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def edit(document, *edits):
    """Apply (paragraph_id, find, replace) edits, one paragraph at a time."""
    parsed = parse_document(document)
    revisions = Revisions(document.element.body, "Reviewer", DATE)
    by_para = {}
    for pid, find, replace in edits:
        para = parsed.by_id[pid]
        by_para.setdefault(pid, []).extend(diff_changes(find, replace, para.text.index(find)))
    for pid, changes in by_para.items():
        apply_changes(parsed.by_id[pid], changes, revisions)


def texts(document, accept):
    return document_texts(document.element.body, accept)


def roundtrip(document):
    buf = io.BytesIO()
    document.save(buf)
    buf.seek(0)
    return docx.Document(buf)


def test_diff_is_word_level():
    changes = diff_changes("for five years.", "for two years.")
    assert [(c.start, c.end, c.insert) for c in changes] == [(4, 9, "two ")]


def test_trailing_whitespace_difference_is_not_a_word_change():
    changes = diff_changes("all Confidential Information", "all Confidential Information of the Discloser")
    assert [(c.start, c.end, c.insert) for c in changes] == [(28, 28, " of the Discloser")]


def test_low_similarity_is_one_delete_then_one_insert():
    changes = diff_changes("for five years.", "until terminated by notice")
    assert [(c.start, c.end, c.insert) for c in changes] == [(0, 15, "until terminated by notice")]


def test_accept_and_reject_across_formatted_runs(document):
    original = texts(document, accept=True)
    find = "strictly confidential and secure for five years."
    replace = "confidential for two years."
    edit(document, ("p0002", find, replace))
    document = roundtrip(document)
    expected = original[1].replace(find, replace)
    assert texts(document, accept=True)[1] == expected
    assert texts(document, accept=False) == original


def test_delete_only(document):
    original = texts(document, accept=True)
    edit(document, ("p0002", " strictly", ""))
    assert texts(document, accept=True)[1] == original[1].replace(" strictly", "")
    assert texts(document, accept=False) == original


def test_several_edits_in_one_paragraph(document):
    original = texts(document, accept=True)
    edit(document, ("p0002", "The Recipient", "Each Recipient"), ("p0002", "five years.", "three years."))
    assert texts(document, accept=True)[1] == original[1].replace("The", "Each").replace("five", "three")
    assert texts(document, accept=False) == original


def test_formatting_is_kept_inside_bold_and_italic_runs(document):
    edit(
        document,
        ("p0002", "all Confidential Information", "all Confidential Information of the Discloser"),
        ("p0002", "confidential and secure", "confidential and protected"),
    )
    body = roundtrip(document).element.body
    p = list(body.iter(qn("w:p")))[1]
    for ins in p.iter(qn("w:ins")):
        r = ins.find(qn("w:r"))
        text = "".join(t.text for t in r.iter(qn("w:t")))
        if "Discloser" in text:
            assert r.find(qn("w:rPr")).find(qn("w:b")) is not None
        else:
            assert text == "protected"
            assert r.find(qn("w:rPr")).find(qn("w:i")) is not None
    deleted = [r for d in p.iter(qn("w:del")) for r in d.iter(qn("w:r"))]
    assert ["".join(t.text for t in r.iter(qn("w:delText"))) for r in deleted] == ["secure"]
    assert deleted[0].find(qn("w:rPr")).find(qn("w:i")) is not None
    bold_text = "".join(
        t.text for r in p.iter(qn("w:r")) if r.find(qn("w:rPr")) is not None and r.find(qn("w:rPr")).find(qn("w:b")) is not None
        for t in r.iter(qn("w:t"))
    )
    assert bold_text == "all Confidential Information of the Discloser"


def test_revision_markup_is_well_formed(document):
    edit(document, ("p0002", "strictly confidential", "confidential"), ("p0005", "State of New York", "State of Delaware"))
    body = roundtrip(document).element.body
    marks = list(body.iter(qn("w:ins"), qn("w:del")))
    assert len(marks) >= 3
    ids = [m.get(qn("w:id")) for m in marks]
    assert len(ids) == len(set(ids))
    for m in marks:
        assert m.get(qn("w:author")) == "Reviewer"
        assert m.get(qn("w:date")) == "2026-01-01T00:00:00Z"
    for d in body.iter(qn("w:del")):
        assert d.find(".//" + qn("w:t")) is None
        for dt in d.iter(qn("w:delText")):
            assert dt.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve"


@pytest.mark.parametrize("find,replace", [
    ("Mutual", "Unilateral"),
    ("Agreement", "Agreement (the NDA)"),
    ("Mutual Non-Disclosure Agreement", "Confidentiality Terms"),
])
def test_first_paragraph_variants(document, find, replace):
    original = texts(document, accept=True)
    edit(document, ("p0001", find, replace))
    assert texts(document, accept=True)[0] == original[0].replace(find, replace)
    assert texts(document, accept=False) == original
