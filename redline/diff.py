import re
from dataclasses import dataclass
from difflib import SequenceMatcher

TOKEN = re.compile(r"\S+\s*|\s+")
MIN_RATIO = 0.4


@dataclass(frozen=True)
class Change:
    """Replace paragraph text [start, end) with insert. start == end is a pure insertion."""

    start: int
    end: int
    insert: str


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text)


def diff_changes(find: str, replace: str, base: int = 0) -> list[Change]:
    """Minimal word-level changes turning find (located at base) into replace."""
    if find == replace:
        return []
    a, b = tokenize(find), tokenize(replace)
    # Match on the word alone so "Information" and "Information " count as equal; the
    # whitespace difference is emitted separately below.
    matcher = SequenceMatcher(None, [t.rstrip() for t in a], [t.rstrip() for t in b], autojunk=False)
    if not replace or matcher.ratio() < MIN_RATIO:
        return [Change(base, base + len(find), replace)]
    offsets = [0]
    for token in a:
        offsets.append(offsets[-1] + len(token))
    changes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            changes.append(Change(base + offsets[i1], base + offsets[i2], "".join(b[j1:j2])))
            continue
        for k in range(i2 - i1):
            ta, tb = a[i1 + k], b[j1 + k]
            if ta != tb:
                word = len(ta.rstrip())
                changes.append(Change(base + offsets[i1 + k] + word, base + offsets[i1 + k + 1], tb[word:]))
    return merge_adjacent(sorted(changes, key=lambda c: (c.start, c.end)))


def merge_adjacent(changes: list[Change]) -> list[Change]:
    merged: list[Change] = []
    for c in changes:
        if merged and merged[-1].end == c.start:
            prev = merged.pop()
            c = Change(prev.start, c.end, prev.insert + c.insert)
        merged.append(c)
    return merged
