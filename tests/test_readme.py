import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("update_readme", Path("scripts/update_readme.py"))
update_readme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_readme)

README = "# x\n\n## Eval\n\n<!-- eval:start -->\nold\n<!-- eval:end -->\n\n## Decisions\n"


def test_missing_results_say_not_measured(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README)
    update_readme.update(readme, tmp_path / "results.md")
    text = readme.read_text()
    assert "Not measured." in text and "old" not in text and text.endswith("## Decisions\n")


def test_results_tables_are_copied(tmp_path):
    readme, results = tmp_path / "README.md", tmp_path / "results.md"
    readme.write_text(README)
    results.write_text("# Eval results\n\nWritten by `redline eval`. Do not edit by hand.\n\n## Detection\n\n| a |\n")
    update_readme.update(readme, results)
    assert "### Detection\n\n| a |\n<!-- eval:end -->" in readme.read_text()
