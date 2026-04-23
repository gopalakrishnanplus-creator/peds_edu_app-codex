from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from user_flow_pack_data import OUTPUT_ROOT, PACK_SUBTITLE, PACK_TITLE, SECTION_ORDER, VERIFIED_ON, WORKFLOWS
from user_flow_pptx import (
    COLORS,
    FONT_BODY,
    FONT_DISPLAY,
    accent_for,
    add_card,
    add_label_chip,
    add_picture_card,
    add_textbox,
    apply_background,
    make_presentation,
)


def grouped_workflows():
    groups = defaultdict(list)
    for workflow in WORKFLOWS:
        groups[workflow.section].append(workflow)
    return groups


def add_cover_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_background(slide, "Platform and Campaign Setup", footer_text=f"Open this deck first • Verified {VERIFIED_ON}")

    add_label_chip(slide, "Master index", 0.66, 0.5, accent=accent_for("Platform and Campaign Setup"))
    add_textbox(
        slide,
        0.68,
        1.05,
        6.2,
        1.0,
        text=PACK_TITLE,
        font_name=FONT_DISPLAY,
        font_size=28,
        color=COLORS["ink"],
        bold=True,
        auto_fit=True,
    )
    add_textbox(
        slide,
        0.7,
        2.0,
        6.0,
        0.9,
        text=PACK_SUBTITLE,
        font_name=FONT_BODY,
        font_size=13,
        color=COLORS["muted"],
        auto_fit=True,
    )

    add_textbox(
        slide,
        0.7,
        3.05,
        5.8,
        1.4,
        text=(
            "Keep this index deck in the same folder as the workflow decks. "
            "All links below are written as sibling-file links so the pack remains shareable."
        ),
        font_name=FONT_BODY,
        font_size=13,
        color=COLORS["ink"],
        auto_fit=True,
    )

    add_card(slide, 0.7, 4.7, 5.8, 1.45, fill_color=COLORS["sand"], line_color=COLORS["line"])
    add_label_chip(slide, "Included", 0.88, 4.88, accent=accent_for("Platform and Campaign Setup"))
    add_textbox(
        slide,
        0.88,
        5.25,
        5.45,
        0.56,
        text=f"{len(WORKFLOWS)} workflow decks plus this master index deck.",
        font_name=FONT_BODY,
        font_size=13,
        color=COLORS["ink"],
        auto_fit=True,
    )

    add_picture_card(
        slide,
        WORKFLOWS[0].cover_image,
        left=7.05,
        top=0.9,
        width=5.55,
        height=5.95,
        crop=WORKFLOWS[0].cover_crop,
        target_ratio=0.94,
        anchor="top",
    )


def add_link_card(slide, workflow, *, left: float, top: float, width: float, height: float):
    accent = accent_for(workflow.section)
    card = add_card(slide, left, top, width, height, fill_color=COLORS["card"], line_color=COLORS["line"])
    try:
        card.click_action.hyperlink.address = workflow.deck_filename
    except Exception:
        pass

    add_label_chip(slide, f"{workflow.number:02d}", left + 0.14, top + 0.14, accent=accent)
    title_box = slide.shapes.add_textbox(
        card.left + Inches(0.18),
        card.top + Inches(0.5),
        card.width - Inches(0.36),
        card.height - Inches(0.7),
    )
    frame = title_box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.TOP

    p1 = frame.paragraphs[0]
    run1 = p1.add_run()
    run1.text = workflow.short_title
    run1.font.name = FONT_DISPLAY
    run1.font.size = Pt(16)
    run1.font.bold = True
    run1.font.color.rgb = RGBColor(*COLORS["ink"])
    p1.alignment = PP_ALIGN.LEFT
    p1.space_before = 0
    p1.space_after = 6

    p2 = frame.add_paragraph()
    run2 = p2.add_run()
    run2.text = workflow.document_purpose
    run2.font.name = FONT_BODY
    run2.font.size = Pt(10.8)
    run2.font.color.rgb = RGBColor(*COLORS["muted"])
    p2.space_after = 6

    p3 = frame.add_paragraph()
    run3 = p3.add_run()
    run3.text = workflow.deck_filename
    run3.font.name = FONT_BODY
    run3.font.size = Pt(10)
    run3.font.bold = True
    run3.font.color.rgb = RGBColor(*accent)
    try:
        run3.hyperlink.address = workflow.deck_filename
    except Exception:
        pass


def add_index_slide(prs, title: str, sections: list[str]):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_background(slide, sections[0], footer_text=f"Index • {title}")
    add_label_chip(slide, "Workflow links", 0.66, 0.5, accent=accent_for(sections[0]))
    add_textbox(
        slide,
        0.68,
        1.0,
        8.8,
        0.72,
        text=title,
        font_name=FONT_DISPLAY,
        font_size=23,
        color=COLORS["ink"],
        bold=True,
        auto_fit=True,
    )

    groups = grouped_workflows()
    cursor_y = 1.95
    for section in sections:
        accent = accent_for(section)
        add_label_chip(slide, section, 0.68, cursor_y, accent=accent)
        cursor_y += 0.45
        cards = groups.get(section, [])
        col_w = 5.85
        gap_x = 0.3
        gap_y = 0.22
        row_h = 1.25
        for index, workflow in enumerate(cards):
            row = index // 2
            col = index % 2
            left = 0.68 + (col * (col_w + gap_x))
            top = cursor_y + (row * (row_h + gap_y))
            add_link_card(slide, workflow, left=left, top=top, width=col_w, height=row_h)
        used_rows = max(1, ((len(cards) - 1) // 2) + 1)
        cursor_y += (used_rows * (row_h + gap_y)) + 0.25

    add_textbox(
        slide,
        9.6,
        0.95,
        2.4,
        0.6,
        text="Click a workflow title or filename to open the sibling deck.",
        font_name=FONT_BODY,
        font_size=10,
        color=COLORS["muted"],
        align=PP_ALIGN.RIGHT,
        auto_fit=True,
    )


def build_master_index() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    prs = make_presentation()
    add_cover_slide(prs)
    add_index_slide(prs, "Platform and clinic workflows", ["Platform and Campaign Setup", "Clinic Onboarding and Sharing"])
    add_index_slide(prs, "Caregiver and internal workflows", ["Caregiver Experience", "Internal Operations"])
    target = OUTPUT_ROOT / "00-user-flow-training-index.pptx"
    prs.save(target)
    print(f"Wrote {target}")
    return target


if __name__ == "__main__":
    build_master_index()
