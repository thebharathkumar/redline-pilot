import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from redline import contractnli
from redline.gold import load_gold_dir, match_edits, token_f1
from redline.parse import load
from redline.playbook import Playbook
from redline.provider import Provider, save_response
from redline.stats import format_rate, rate

RESULTS_JSON = Path("eval/results.json")
RESULTS_MD = Path("eval/results.md")


def should_flag(label: str, required: bool) -> bool:
    return label == "Contradiction" or (label == "NotMentioned" and required)


def outcome(gold: bool, predicted: bool) -> str:
    return {(True, True): "tp", (False, True): "fp", (True, False): "fn", (False, False): "tn"}[(gold, predicted)]


def scores(c: Counter) -> dict:
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    return {
        "counts": {k: c[k] for k in ("tp", "fp", "fn", "tn")},
        "precision": rate(tp, tp + fp),
        "recall": rate(tp, tp + fn),
        "f1": 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None,
    }


def usage_summary(provider) -> dict | None:
    calls = getattr(provider, "calls", None)
    if not calls:
        return None
    return {
        "calls": len(calls),
        "input_tokens": sum(c.input_tokens for c in calls),
        "output_tokens": sum(c.output_tokens for c in calls),
        "mean_seconds": sum(c.seconds for c in calls) / len(calls),
    }


def run_detection(provider: Provider, playbook: Playbook, n: int, docx_dir: Path, responses_dir: Path) -> dict:
    manifest = contractnli.load_manifest(docx_dir / "labels.json")[:n]
    rules = [r for r in playbook.rules if r.contractnli]
    per_rule = {r.id: Counter() for r in rules}
    responses_dir.mkdir(parents=True, exist_ok=True)
    for item in manifest:
        result = provider.review(load(str(docx_dir / item["file"])), playbook)
        save_response(result, str(responses_dir / f"{item['id']}.json"))
        flagged = {e.rule_id for e in result.edits} | {m.rule_id for m in result.missing}
        for r in rules:
            gold = should_flag(item["labels"][r.contractnli], r.required)
            per_rule[r.id][outcome(gold, r.id in flagged)] += 1
    overall = sum(per_rule.values(), Counter())
    return {
        "dataset": "ContractNLI test split",
        "documents": len(manifest),
        "per_rule": {
            r.id: {"hypothesis": r.contractnli, "required": r.required, **scores(per_rule[r.id])} for r in rules
        },
        "overall": scores(overall),
        "usage": usage_summary(provider),
    }


def run_edits(provider: Provider, gold_dir: Path, responses_dir: Path) -> dict:
    from redline.playbook import load_playbook
    from redline.validate import validate

    gold_files = load_gold_dir(gold_dir)
    if not gold_files:
        raise SystemExit(f"no gold files in {gold_dir} (TEMPLATE.yaml is ignored)")
    responses_dir.mkdir(parents=True, exist_ok=True)
    n_predicted = n_gold = n_matched = 0
    span_f1 = []
    for path, gold in gold_files:
        playbook = load_playbook(gold.playbook)
        document = load(gold.document)
        result = provider.review(document, playbook)
        save_response(result, str(responses_dir / f"{path.stem}.json"))
        # Score only the edits that would actually be written into the document.
        accepted, _, _ = validate(result, document, playbook)
        predicted = [a.edit for a in accepted]
        pairs = match_edits(predicted, gold.edits)
        n_predicted += len(predicted)
        n_gold += len(gold.edits)
        n_matched += len(pairs)
        span_f1 += [token_f1(p.find, g.find) for p, g in pairs]
    return {
        "gold_files": len(gold_files),
        "predicted": n_predicted,
        "gold": n_gold,
        "precision": rate(n_matched, n_predicted),
        "recall": rate(n_matched, n_gold),
        "span_token_f1": sum(span_f1) / len(span_f1) if span_f1 else None,
        "usage": usage_summary(provider),
    }


def write_results(section: str, data: dict, model: str | None, command: str,
                  json_path: Path = RESULTS_JSON, md_path: Path = RESULTS_MD) -> dict:
    results = json.loads(json_path.read_text()) if json_path.exists() else {}
    results[section] = {
        "model": model,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": command,
        **data,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(results), encoding="utf-8")
    return results


def f1_text(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def header(section: dict) -> list[str]:
    return [
        f"Model: {section['model']}  ",
        f"Date: {section['date']}  ",
        f"Command: `{section['command']}`",
        "",
    ]


def usage_line(usage: dict | None) -> list[str]:
    if not usage:
        return []
    return [
        f"Model calls: {usage['calls']}, input tokens: {usage['input_tokens']}, "
        f"output tokens: {usage['output_tokens']}, mean latency: {usage['mean_seconds']:.1f} s",
        "",
    ]


def render_detection(d: dict) -> list[str]:
    lines = ["## Detection", ""] + header(d) + [
        f"{d['dataset']}, n = {d['documents']} documents. A rule should be flagged when the ContractNLI "
        "label is Contradiction, or NotMentioned for a required rule. Rates are k/n with a Wilson 95% interval.",
        "",
        "| rule | hypothesis | precision | recall | F1 |",
        "|---|---|---|---|---|",
    ]
    for rule_id, s in d["per_rule"].items():
        lines.append(
            f"| {rule_id} | {s['hypothesis']} | {format_rate(s['precision'])} | {format_rate(s['recall'])} | {f1_text(s['f1'])} |"
        )
    o = d["overall"]
    lines.append(f"| overall | | {format_rate(o['precision'])} | {format_rate(o['recall'])} | {f1_text(o['f1'])} |")
    return lines + [""] + usage_line(d.get("usage"))


def render_edits(e: dict) -> list[str]:
    lines = ["## Edits", ""] + header(e) + [
        f"Gold files: {e['gold_files']}. An edit matches when (paragraph_id, rule_id) agree. "
        "Rates are k/n with a Wilson 95% interval.",
        "",
        "| metric | value |",
        "|---|---|",
        f"| precision | {format_rate(e['precision'])} |",
        f"| recall | {format_rate(e['recall'])} |",
        f"| mean token F1 of matched spans | {f1_text(e['span_token_f1'])} |",
    ]
    return lines + [""] + usage_line(e.get("usage"))


def render_markdown(results: dict) -> str:
    lines = ["# Eval results", "", "Written by `redline eval`. Do not edit by hand.", ""]
    if "detection" in results:
        lines += render_detection(results["detection"])
    if "edits" in results:
        lines += render_edits(results["edits"])
    return "\n".join(lines).rstrip() + "\n"
