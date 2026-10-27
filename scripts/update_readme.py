"""Copy the tables from eval/results.md into the Eval section of README.md."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- eval:start -->", "<!-- eval:end -->"


def eval_section(results_md: Path) -> str:
    if not results_md.exists():
        return "Not measured. `redline eval` has not been run yet."
    text = results_md.read_text(encoding="utf-8")
    body = text.split("Do not edit by hand.", 1)[-1].strip()
    # Demote headings one level so they sit under the README's "## Eval".
    return re.sub(r"^## ", "### ", body, flags=re.M)


def update(readme: Path, results_md: Path) -> None:
    text = readme.read_text(encoding="utf-8")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    readme.write_text(f"{before}{START}\n{eval_section(results_md)}\n{END}{after}", encoding="utf-8")


if __name__ == "__main__":
    update(ROOT / "README.md", ROOT / "eval/results.md")
