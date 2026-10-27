"""Download ContractNLI (CC BY 4.0) into data/ and convert test-split documents to .docx."""

import argparse
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from redline import contractnli  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=25, help="number of test-split documents to convert")
    args = parser.parse_args()

    zip_path = ROOT / contractnli.ZIP
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if not zip_path.exists():
        print(f"downloading {contractnli.URL}", file=sys.stderr)
        try:
            urllib.request.urlretrieve(contractnli.URL, zip_path)
        except OSError as e:
            zip_path.unlink(missing_ok=True)
            raise SystemExit(
                f"download failed ({e}); download {contractnli.URL} by hand and save it as {contractnli.ZIP}"
            )
    with zipfile.ZipFile(zip_path) as z:
        z.extract("contract-nli/test.json", ROOT / contractnli.DATA)
    manifest = contractnli.convert(ROOT / contractnli.TEST_JSON, ROOT / contractnli.DOCX_DIR, args.n)
    print(f"wrote {len(manifest)} documents to {contractnli.DOCX_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
