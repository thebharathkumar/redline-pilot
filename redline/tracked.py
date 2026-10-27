from copy import deepcopy
from datetime import datetime, timezone

from docx.oxml.ns import qn
from lxml import etree

from redline.diff import Change
from redline.parse import TEXT_TAGS, Paragraph, paragraph_runs

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
EDITABLE_TAGS = set(TEXT_TAGS) | {qn("w:rPr"), qn("w:lastRenderedPageBreak")}


def format_date(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Revisions:
    """Hands out w:ins / w:del elements with document-wide unique ids."""

    def __init__(self, body: etree._Element, author: str, date: datetime):
        self.author = author
        self.date = format_date(date)
        # Start above any id already in the body so bookmarks and revisions never collide.
        ids = [int(v) for v in body.xpath(".//@w:id") if v.lstrip("-").isdigit()]
        self.next_id = max(ids, default=0) + 1

    def element(self, tag: str) -> etree._Element:
        el = etree.Element(qn(tag))
        el.set(qn("w:id"), str(self.next_id))
        el.set(qn("w:author"), self.author)
        el.set(qn("w:date"), self.date)
        self.next_id += 1
        return el


def text_element(tag: str, text: str) -> etree._Element:
    el = etree.Element(qn(tag))
    el.text = text
    el.set(XML_SPACE, "preserve")
    return el


def new_run(text: str, rPr: etree._Element | None) -> etree._Element:
    r = etree.Element(qn("w:r"))
    if rPr is not None:
        r.append(deepcopy(rPr))
    buf = ""
    for ch in text:
        if ch in "\t\n":
            if buf:
                r.append(text_element("w:t", buf))
                buf = ""
            r.append(etree.Element(qn("w:tab" if ch == "\t" else "w:br")))
        else:
            buf += ch
    if buf:
        r.append(text_element("w:t", buf))
    return r


def is_editable(r: etree._Element) -> bool:
    return all(child.tag in EDITABLE_TAGS for child in r)


def blocked_reason(para: Paragraph, start: int, end: int) -> str | None:
    for span in para.runs:
        touches = span.start < end and span.end > start
        inside_empty = span.start == span.end and start < span.start < end
        if (touches or inside_empty) and not is_editable(span.element):
            return "range touches a field, drawing or other non-text run"
    return None


def split_run(r: etree._Element, k: int) -> etree._Element:
    """Split run r at character offset k; r keeps the left part, the new right run is returned."""
    right = etree.Element(r.tag, dict(r.attrib))
    rPr = r.find(qn("w:rPr"))
    if rPr is not None:
        right.append(deepcopy(rPr))
    offset = 0
    for child in list(r):
        if child.tag == qn("w:rPr"):
            continue
        length = len(child.text or "") if child.tag == qn("w:t") else (1 if child.tag in TEXT_TAGS else 0)
        if offset >= k:
            right.append(child)
        elif offset + length > k:
            cut = k - offset
            right.append(text_element("w:t", child.text[cut:]))
            child.text = child.text[:cut]
            child.set(XML_SPACE, "preserve")
        offset += length
    r.addnext(right)
    return right


def split_at(p: etree._Element, offsets: set[int]) -> None:
    for k in sorted(offsets):
        for span in paragraph_runs(p):
            if span.start < k < span.end:
                split_run(span.element, k - span.start)
                break


def consecutive_groups(elements: list[etree._Element]) -> list[list[etree._Element]]:
    groups: list[list[etree._Element]] = []
    for el in elements:
        if groups and groups[-1][-1].getnext() is el:
            groups[-1].append(el)
        else:
            groups.append([el])
    return groups


def apply_changes(para: Paragraph, changes: list[Change], revisions: Revisions) -> list[list[etree._Element]]:
    """Write non-overlapping changes into the paragraph as tracked revisions.

    Returns, for each change in the given order, the w:del / w:ins elements created for it.
    """
    p = para.element
    split_at(p, {c.start for c in changes} | {c.end for c in changes})
    spans = paragraph_runs(p)
    created: dict[int, list[etree._Element]] = {}
    order = sorted(range(len(changes)), key=lambda i: (changes[i].start, changes[i].end), reverse=True)
    for i in order:
        change = changes[i]
        deleted = [s.element for s in spans if s.start >= change.start and s.end <= change.end and s.end > s.start]
        before = [s.element for s in spans if s.end == change.start and s.end > s.start]
        after = [s.element for s in spans if s.start == change.start and s.end > s.start]
        wrappers = []
        for group in consecutive_groups(deleted):
            wrapper = revisions.element("w:del")
            group[0].addprevious(wrapper)
            for r in group:
                for t in r.iter(qn("w:t")):
                    t.tag = qn("w:delText")
                    t.set(XML_SPACE, "preserve")
                wrapper.append(r)
            wrappers.append(wrapper)
        if change.insert:
            source = (deleted or before[-1:] or after[:1] or [None])[0]
            rPr = source.find(qn("w:rPr")) if source is not None else None
            ins = revisions.element("w:ins")
            ins.append(new_run(change.insert, rPr))
            if wrappers:
                wrappers[-1].addnext(ins)
            elif before:
                before[-1].addnext(ins)
            elif after:
                after[0].addprevious(ins)
            else:
                p.append(ins)
            wrappers.append(ins)
        created[i] = wrappers
    return [created[i] for i in range(len(changes))]
