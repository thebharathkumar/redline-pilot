import argparse
import sys
from datetime import datetime, timezone

import docx

from redline.parse import ExistingRevisionsError, parse_document
from redline.playbook import load_playbook
from redline.provider import ReplayProvider, save_response
from redline.review import apply_review, save_stable
from redline.validate import format_rejections


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


def parse_date(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise SystemExit("--date needs a timezone, e.g. 2026-01-01T00:00:00Z")
    return parsed.astimezone(timezone.utc)


def live_provider(mode: str):
    from redline.anthropic_provider import AnthropicProvider, ProviderError

    try:
        return AnthropicProvider()
    except ProviderError as e:
        raise SystemExit(f"error: {e}")


def run_review(args) -> int:
    date = parse_date(args.date)
    try:
        document = parse_document(docx.Document(args.contract))
    except ExistingRevisionsError as e:
        print(f"error: {args.contract}: {e}", file=sys.stderr)
        return 1
    playbook = load_playbook(args.playbook)
    provider = ReplayProvider(args.offline) if args.offline else live_provider(args.mode)
    result = provider.review(document, playbook)
    if args.save_response:
        save_response(result, args.save_response)
    stats = apply_review(document, playbook, result, args.author, date)
    table = format_rejections(stats.rejected)
    if table:
        print(table, file=sys.stderr)
    save_stable(document.document, args.out)
    print(
        f"{args.out}: {stats.edits} edits, {stats.missing} missing-clause comments, "
        f"{len(stats.rejected)} dropped",
        file=sys.stderr,
    )
    return 0


def run_eval(args, argv: list[str], provider=None) -> int:
    from pathlib import Path

    from redline import contractnli, evaluate

    if not args.detection and not args.edits:
        print("error: give --detection contractnli and/or --edits GOLD_DIR", file=sys.stderr)
        return 2
    playbook = load_playbook("playbooks/nda.yaml")
    provider = provider or live_provider("single")
    command = "redline " + " ".join(argv)
    model = getattr(provider, "model", None)
    if args.detection:
        data = evaluate.run_detection(
            provider, playbook, args.n, contractnli.DOCX_DIR, contractnli.DATA / "responses" / "contractnli",
        )
        evaluate.write_results("detection", data, model, command)
    if args.edits:
        print("error: --edits is not implemented yet", file=sys.stderr)
        return 2
    print(f"wrote {evaluate.RESULTS_JSON} and {evaluate.RESULTS_MD}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None, provider=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(argv)
    if args.command == "review":
        return run_review(args)
    return run_eval(args, argv, provider)


if __name__ == "__main__":
    sys.exit(main())
