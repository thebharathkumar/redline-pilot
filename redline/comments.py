from datetime import datetime

from docx.document import Document
from docx.oxml.ns import qn
from docx.text.run import Run
from lxml import etree

from redline.parse import Paragraph

REVISION_WRAPPERS = (qn("w:ins"), qn("w:del"))


def initials(author: str) -> str:
    return "".join(word[0] for word in author.split()).upper()


def first_run(el: etree._Element) -> etree._Element:
    return el if el.tag == qn("w:r") else el.find(".//" + qn("w:r"))


def last_run(el: etree._Element) -> etree._Element:
    return el if el.tag == qn("w:r") else el.findall(".//" + qn("w:r"))[-1]


def lift_out_of_revisions(body: etree._Element, comment_id: int) -> None:
    """Move comment markers that python-docx placed inside w:ins / w:del next to the wrapper.

    A reference run left inside w:del would itself be a deleted run.
    """
    cid = str(comment_id)
    start = body.xpath(f'.//w:commentRangeStart[@w:id="{cid}"]')[0]
    end = body.xpath(f'.//w:commentRangeEnd[@w:id="{cid}"]')[0]
    reference = end.getnext()
    if start.getparent().tag in REVISION_WRAPPERS:
        start.getparent().addprevious(start)
    if end.getparent().tag in REVISION_WRAPPERS:
        wrapper = end.getparent()
        wrapper.addnext(reference)
        wrapper.addnext(end)


def add_comment(
    document: Document,
    first: etree._Element,
    last: etree._Element,
    text: str,
    author: str,
    date: datetime,
) -> int:
    """Comment on the range from first to last, each a w:r or a w:ins / w:del wrapper."""
    runs = [Run(first_run(first), None), Run(last_run(last), None)]
    comment = document.add_comment(runs, text=text, author=author, initials=initials(author))
    comment._comment_elm.date = date
    lift_out_of_revisions(document.element.body, comment.comment_id)
    return comment.comment_id


def comment_on_paragraph(document: Document, para: Paragraph, text: str, author: str, date: datetime) -> int:
    runs = [s.element for s in para.runs if s.end > s.start] or [s.element for s in para.runs]
    if not runs:
        r = etree.SubElement(para.element, qn("w:r"))
        runs = [r]
    return add_comment(document, runs[0], runs[-1], text, author, date)
