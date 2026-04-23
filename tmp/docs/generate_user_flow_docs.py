from __future__ import annotations

import argparse
from pathlib import Path

from user_flow_pack_data import DOCS_ROOT, STATUS_TEXT, select_workflows


def related_link(item: str) -> str:
    target = item
    if item.startswith("../") or item.startswith("./"):
        target = item
    elif item[:2].isdigit() and item.endswith(".md"):
        target = item
    else:
        target = f"../../{item}"
    return f"[`{item}`]({target})"


def render_workflow(workflow) -> str:
    lines: list[str] = []
    lines.append(f"# {workflow.number:02d}. {workflow.title}")
    lines.append("")
    lines.append("## 1. Title")
    lines.append("")
    lines.append(workflow.title)
    lines.append("")
    lines.append("## 2. Document Purpose")
    lines.append("")
    lines.append(workflow.document_purpose)
    lines.append("")
    lines.append("## 3. Primary User")
    lines.append("")
    lines.append(workflow.primary_user)
    lines.append("")
    lines.append("## 4. Entry Point")
    lines.append("")
    lines.append(workflow.entry_point)
    lines.append("")
    lines.append("## 5. Workflow Summary")
    lines.append("")
    for bullet in workflow.workflow_summary:
        lines.append(f"- {bullet}")

    if workflow.role_map:
        lines.append("")
        lines.append("### Role Map")
        lines.append("")
        for role, description in workflow.role_map:
            lines.append(f"- **{role}:** {description}")

    if workflow.start_points:
        lines.append("")
        lines.append("### Where Each Workflow Starts")
        lines.append("")
        for label, entry in workflow.start_points:
            lines.append(f"- **{label}:** {entry}")

    if workflow.flow_diagram_mermaid:
        lines.append("")
        lines.append("### End-To-End Flow")
        lines.append("")
        lines.append(workflow.flow_diagram_mermaid)

    if workflow.decision_points:
        lines.append("")
        lines.append("### Decision Points")
        lines.append("")
        for title, when_to_use, outcome in workflow.decision_points:
            lines.append(f"- **{title}:** {when_to_use} Outcome: {outcome}")

    lines.append("")
    lines.append("## 6. Step-By-Step Instructions")
    lines.append("")

    for step in workflow.steps:
        lines.append(f"### Step {step.number}. {step.title}")
        lines.append("")
        lines.append("**What the user does**")
        lines.append("")
        lines.append(step.user_does)
        lines.append("")
        lines.append("**What the user sees**")
        lines.append("")
        lines.append(step.user_sees)
        lines.append("")
        lines.append("**Why the step matters**")
        lines.append("")
        lines.append(step.why_it_matters)
        lines.append("")
        lines.append("**Expected result**")
        lines.append("")
        lines.append(step.expected_result)
        lines.append("")
        if step.trainer_notes:
            lines.append("**Common issues or trainer notes**")
            lines.append("")
            lines.append(step.trainer_notes)
            lines.append("")
        else:
            lines.append("**Common issues or trainer notes**")
            lines.append("")
            lines.append("No special trainer note for this step.")
            lines.append("")
        lines.append("**Screenshot Placeholder**")
        lines.append("")
        lines.append(f"- Suggested file path: `{step.screenshot_path}`")
        lines.append(f"- Screenshot caption: {step.screenshot_caption}")
        lines.append(f"- What the screenshot should show: {step.screenshot_show}")
        if step.screenshot_path:
            lines.append("")
            lines.append(f"![{step.screenshot_caption}]({step.screenshot_path})")
        lines.append("")

    lines.append("## 7. Success Criteria")
    lines.append("")
    for item in workflow.success_criteria:
        lines.append(f"- {item}")

    if workflow.common_issues:
        lines.append("")
        lines.append("### Trainer Tips and Common Issues")
        lines.append("")
        for title, guidance in workflow.common_issues:
            lines.append(f"- **{title}:** {guidance}")

    lines.append("")
    lines.append("## 8. Related Documents")
    lines.append("")
    for item in workflow.related_documents:
        lines.append(f"- {related_link(item)}")

    lines.append("")
    lines.append("## 9. Status")
    lines.append("")
    lines.append(workflow.status or STATUS_TEXT)
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate editable Markdown manuals for the user-flow pack.")
    parser.add_argument(
        "--workflows",
        help="Comma-separated workflow numbers or slugs to regenerate. Defaults to the full pack.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workflows = select_workflows(args.workflows)
    DOCS_ROOT.mkdir(parents=True, exist_ok=True)
    for workflow in workflows:
        target = DOCS_ROOT / workflow.manual_filename
        target.write_text(render_workflow(workflow), encoding="utf-8")
        print(f"Wrote {target}")


if __name__ == "__main__":
    main()
