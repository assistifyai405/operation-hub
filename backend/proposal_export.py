"""Proposal exporters — professional PDF (reportlab) and DOCX (python-docx)."""
import io
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from proposal_config import PROPOSAL_SECTIONS

VIOLET = "#7C3AED"


def _as_list(v):
    if isinstance(v, list):
        return v
    return [v] if v else []


def build_pdf(proposal: dict, sections=PROPOSAL_SECTIONS, doc_type: str = "Proposal") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, topMargin=0.9 * inch, bottomMargin=0.8 * inch,
                            leftMargin=0.9 * inch, rightMargin=0.9 * inch)
    ss = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=ss["Title"], fontSize=24, textColor=HexColor("#18181B"), spaceAfter=2)
    sub = ParagraphStyle("s", parent=ss["Normal"], fontSize=10, textColor=HexColor("#71717A"), spaceAfter=18)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13, textColor=HexColor(VIOLET), spaceBefore=16, spaceAfter=6)
    body = ParagraphStyle("b", parent=ss["Normal"], fontSize=10.5, leading=15, textColor=HexColor("#27272A"), alignment=TA_LEFT)

    content = proposal.get("content", {})
    story = [Paragraph(proposal.get("title", doc_type), title),
             Paragraph(f"Assistify OS · {doc_type} v{proposal.get('version', 1)} · Status: {proposal.get('status', 'Draft')}", sub),
             HRFlowable(width="100%", color=HexColor("#E4E4E7"), spaceAfter=6)]
    for sec in sections:
        val = content.get(sec["key"])
        if not val:
            continue
        story.append(Paragraph(sec["label"], h2))
        if sec["type"] == "list":
            items = [ListItem(Paragraph(str(i), body), leftIndent=8) for i in _as_list(val)]
            if items:
                story.append(ListFlowable(items, bulletType="bullet", start="•"))
        else:
            story.append(Paragraph(str(val).replace("\n", "<br/>"), body))
        story.append(Spacer(1, 4))
    doc.build(story)
    return buf.getvalue()


def build_docx(proposal: dict, sections=PROPOSAL_SECTIONS, doc_type: str = "Proposal") -> bytes:
    d = Document()
    style = d.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    content = proposal.get("content", {})
    t = d.add_paragraph()
    run = t.add_run(proposal.get("title", doc_type))
    run.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = RGBColor(0x18, 0x18, 0x1B)

    meta = d.add_paragraph()
    mr = meta.add_run(f"Assistify OS  ·  {doc_type} v{proposal.get('version', 1)}  ·  Status: {proposal.get('status', 'Draft')}")
    mr.font.size = Pt(10)
    mr.font.color.rgb = RGBColor(0x71, 0x71, 0x7A)

    for sec in sections:
        val = content.get(sec["key"])
        if not val:
            continue
        h = d.add_heading(level=2)
        hr = h.add_run(sec["label"])
        hr.font.color.rgb = RGBColor(0x7C, 0x3A, 0xED)
        if sec["type"] == "list":
            for item in _as_list(val):
                d.add_paragraph(str(item), style="List Bullet")
        else:
            d.add_paragraph(str(val))

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
