from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

from user_flow_pack_data import DOCS_ROOT, OUTPUT_ROOT, QA_ROOT, WORKFLOWS
from user_flow_pptx import resolve_repo_path


PLACEHOLDER_PATTERNS = [
    r"Screenshot Placeholder",
    r"\{\{.+?\}\}",
    r"TODO",
    r"Lorem ipsum",
    r"Insert text",
]


def xml_texts(pptx_path: Path) -> str:
    with zipfile.ZipFile(pptx_path) as archive:
        parts = []
        for name in archive.namelist():
            if name.endswith(".xml") and name.startswith("ppt/"):
                try:
                    parts.append(archive.read(name).decode("utf-8", errors="ignore"))
                except Exception:
                    continue
        return "\n".join(parts)


def slide_count(pptx_path: Path) -> int:
    with zipfile.ZipFile(pptx_path) as archive:
        return len([name for name in archive.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", name)])


def master_index_targets(index_path: Path) -> list[str]:
    with zipfile.ZipFile(index_path) as archive:
        targets = []
        for name in archive.namelist():
            if not name.endswith(".rels"):
                continue
            try:
                text = archive.read(name).decode("utf-8", errors="ignore")
            except Exception:
                continue
            targets.extend(re.findall(r'Target="([^"]+\.pptx)"', text))
        return sorted(set(targets))


def main() -> int:
    report: dict[str, object] = {
        "manuals": {},
        "decks": {},
        "master_index": {},
        "qa_previews": {},
        "errors": [],
    }
    errors: list[str] = []

    for workflow in WORKFLOWS:
        manual_path = DOCS_ROOT / workflow.manual_filename
        manual_ok = manual_path.exists()
        report["manuals"][workflow.manual_filename] = {"exists": manual_ok}
        if not manual_ok:
            errors.append(f"Missing manual: {manual_path}")

        for step in workflow.steps:
            if not step.screenshot_path:
                continue
            shot = resolve_repo_path(step.screenshot_path)
            if not shot.exists():
                errors.append(f"Missing screenshot asset for {workflow.slug} step {step.number}: {shot}")

        deck_path = OUTPUT_ROOT / workflow.deck_filename
        deck_info = {"exists": deck_path.exists()}
        if deck_path.exists():
            text = xml_texts(deck_path)
            deck_info["slides"] = slide_count(deck_path)
            deck_info["size_bytes"] = deck_path.stat().st_size
            placeholders = [pattern for pattern in PLACEHOLDER_PATTERNS if re.search(pattern, text, flags=re.IGNORECASE)]
            absolute_hits = []
            cwd_string = str(OUTPUT_ROOT.parents[2])
            if cwd_string in text:
                absolute_hits.append(cwd_string)
            deck_info["placeholder_hits"] = placeholders
            deck_info["absolute_path_hits"] = absolute_hits
            if placeholders:
                errors.append(f"Placeholder text found in {deck_path.name}: {placeholders}")
            if absolute_hits:
                errors.append(f"Absolute path leaked into {deck_path.name}: {absolute_hits}")
        else:
            errors.append(f"Missing deck: {deck_path}")
        report["decks"][workflow.deck_filename] = deck_info

    index_path = OUTPUT_ROOT / "00-user-flow-training-index.pptx"
    index_info = {"exists": index_path.exists()}
    if index_path.exists():
        targets = master_index_targets(index_path)
        expected = sorted([workflow.deck_filename for workflow in WORKFLOWS])
        index_info["targets"] = targets
        index_info["expected"] = expected
        index_info["all_expected_present"] = set(expected).issubset(set(targets))
        index_info["all_relative"] = all(
            not (
                target.startswith("/")
                or target.startswith("file:")
                or target.startswith("http://")
                or target.startswith("https://")
                or re.match(r"^[A-Za-z]:", target)
            )
            for target in targets
        )
        if not index_info["all_expected_present"]:
            errors.append("Master index deck is missing one or more workflow deck targets.")
        if not index_info["all_relative"]:
            errors.append("Master index deck contains a non-relative hyperlink target.")
    else:
        errors.append(f"Missing master index deck: {index_path}")
    report["master_index"] = index_info

    qa_pdf_dir = QA_ROOT / "pdf"
    qa_png_dir = QA_ROOT / "png"
    report["qa_previews"] = {
        "pdf_dir_exists": qa_pdf_dir.exists(),
        "png_dir_exists": qa_png_dir.exists(),
        "pdf_count": len(list(qa_pdf_dir.glob("*.pdf"))) if qa_pdf_dir.exists() else 0,
        "png_count": len(list(qa_png_dir.glob("*.png"))) if qa_png_dir.exists() else 0,
    }

    report["errors"] = errors
    QA_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = QA_ROOT / "verification-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {report_path}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

