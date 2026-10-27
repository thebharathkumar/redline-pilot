import json
from pathlib import Path

import docx

from redline.review import save_stable

URL = "https://stanfordnlp.github.io/contract-nli/resources/contract-nli.zip"
DATA = Path("data")
ZIP = DATA / "contract-nli.zip"
TEST_JSON = DATA / "contract-nli" / "test.json"
DOCX_DIR = DATA / "contractnli_docx"
LABELS = DOCX_DIR / "labels.json"


def labels_of(document: dict) -> dict[str, str]:
    annotations = document["annotation_sets"][0]["annotations"]
    return {hypothesis: a["choice"] for hypothesis, a in annotations.items()}


def to_docx(document: dict, path: Path) -> None:
    out = docx.Document()
    for line in document["text"].split("\n"):
        if line.strip():
            out.add_paragraph(line.strip())
    save_stable(out, str(path))


def convert(test_json: Path, out_dir: Path, n: int) -> list[dict]:
    """Write the first n test-split documents as .docx plus labels.json."""
    with open(test_json, encoding="utf-8") as f:
        documents = json.load(f)["documents"][:n]
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, document in enumerate(documents):
        name = f"{i:03d}_{document['id']}.docx"
        to_docx(document, out_dir / name)
        manifest.append({"file": name, "id": document["id"], "source": document["file_name"], "labels": labels_of(document)})
    (out_dir / "labels.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_manifest(path: Path = LABELS) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} not found; run: python scripts/fetch_contractnli.py --n 25")
    return json.loads(path.read_text(encoding="utf-8"))
