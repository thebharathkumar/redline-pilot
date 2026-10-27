from copy import deepcopy

from docx.oxml.ns import qn
from lxml import etree

from redline.parse import in_text_box, paragraph_runs, run_text


def unwrap(el: etree._Element) -> None:
    parent = el.getparent()
    index = parent.index(el)
    for child in reversed(list(el)):
        parent.insert(index, child)
    parent.remove(el)


def resolved_text(p: etree._Element, accept: bool) -> str:
    """Paragraph text as Word would show it after accepting or rejecting every revision."""
    p = deepcopy(p)
    drop, keep = ("w:del", "w:ins") if accept else ("w:ins", "w:del")
    for el in list(p.iter(qn(drop))):
        el.getparent().remove(el)
    for el in list(p.iter(qn(keep))):
        unwrap(el)
    for el in p.iter(qn("w:delText")):
        el.tag = qn("w:t")
    return "".join(run_text(s.element) for s in paragraph_runs(p))


def document_texts(body: etree._Element, accept: bool) -> list[str]:
    return [resolved_text(p, accept) for p in body.iter(qn("w:p")) if not in_text_box(p)]
