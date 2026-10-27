import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="redline")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="review a contract against a playbook")
    review.add_argument("contract")
    review.add_argument("--playbook", required=True)
    review.add_argument("--out", required=True)
    review.add_argument("--author", default="Reviewer")
    review.add_argument("--date", help="ISO 8601 UTC timestamp, e.g. 2026-01-01T00:00:00Z")
    review.add_argument("--offline", metavar="RESPONSE.json", help="replay a saved model response")
    review.add_argument("--save-response", metavar="RESPONSE.json")
    review.add_argument("--mode", choices=["single"], default="single")

    ev = sub.add_parser("eval", help="run detection and edit evaluations")
    ev.add_argument("--detection", choices=["contractnli"])
    ev.add_argument("--edits", metavar="GOLD_DIR")
    ev.add_argument("--n", type=int, default=25)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"redline {args.command}: not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
