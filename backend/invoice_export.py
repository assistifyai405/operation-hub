"""Invoice exporters — professional PDF (reportlab) and DOCX (python-docx). Reuses export architecture."""
import io
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

VIOLET = "#7C3AED"


def _money(v):
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return "0.00"


def _rows(invoice):
    return invoice.get("line_items", []) or []


def build_invoice_pdf(invoice: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, topMargin=0.8 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.8 * inch, rightMargin=0.8 * inch)
    ss = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=ss["Title"], fontSize=26, textColor=HexColor(VIOLET), spaceAfter=0)
    small = ParagraphStyle("s", parent=ss["Normal"], fontSize=9.5, textColor=HexColor("#52525B"), leading=13)
    label = ParagraphStyle("l", parent=ss["Normal"], fontSize=9, textColor=HexColor("#A1A1AA"), spaceAfter=1)
    body = ParagraphStyle("b", parent=ss["Normal"], fontSize=10, textColor=HexColor("#27272A"), leading=14)
    c = invoice.get("content", {})

    story = [Paragraph("INVOICE", title),
             Paragraph(f"{invoice.get('invoice_number', '')} · Status: {invoice.get('status', 'Draft')}", small),
             Spacer(1, 12), HRFlowable(width="100%", color=HexColor("#E4E4E7")), Spacer(1, 12)]

    meta = [
        [Paragraph("BILL TO", label), Paragraph("DETAILS", label)],
        [Paragraph(f"<b>{c.get('company') or c.get('client_name') or '—'}</b><br/>{(c.get('billing_address') or '').replace(chr(10), '<br/>')}", body),
         Paragraph(f"Issue Date: {c.get('issue_date') or '—'}<br/>Due Date: {c.get('due_date') or '—'}<br/>Project: {c.get('project_name') or '—'}", body)],
    ]
    mt = Table(meta, colWidths=[3.4 * inch, 3.4 * inch])
    mt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, 0), 4)]))
    story += [mt, Spacer(1, 8)]
    if c.get("description"):
        story += [Paragraph(c["description"], body), Spacer(1, 10)]

    data = [["Description", "Qty", "Unit Price", "Amount"]]
    for li in _rows(invoice):
        data.append([Paragraph(str(li.get("description", "")), body), str(li.get("quantity", 0)),
                     _money(li.get("unit_price", 0)), _money(li.get("amount", 0))])
    tbl = Table(data, colWidths=[3.6 * inch, 0.7 * inch, 1.25 * inch, 1.25 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor(VIOLET)),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), HexColor("#F4F4F5")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, HexColor("#E4E4E7")),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [tbl, Spacer(1, 10)]

    totals = [["Subtotal", _money(invoice.get("subtotal", 0))],
              [f"VAT ({c.get('vat_rate', 0)}%)", _money(invoice.get("vat", 0))],
              ["Total", _money(invoice.get("total", 0))]]
    tt = Table(totals, colWidths=[1.5 * inch, 1.25 * inch], hAlign="RIGHT")
    tt.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEABOVE", (0, -1), (-1, -1), 1, HexColor(VIOLET)),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [tt, Spacer(1, 16)]

    for key in ("payment_terms", "bank_details", "notes"):
        if c.get(key):
            story += [Paragraph(key.replace("_", " ").title(), label), Paragraph(str(c[key]).replace("\n", "<br/>"), body), Spacer(1, 6)]
    doc.build(story)
    return buf.getvalue()


def build_invoice_docx(invoice: dict) -> bytes:
    d = Document()
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(11)
    c = invoice.get("content", {})

    h = d.add_paragraph()
    r = h.add_run("INVOICE")
    r.bold = True; r.font.size = Pt(26); r.font.color.rgb = RGBColor(0x7C, 0x3A, 0xED)
    m = d.add_paragraph(); mr = m.add_run(f"{invoice.get('invoice_number', '')}  ·  Status: {invoice.get('status', 'Draft')}")
    mr.font.size = Pt(10); mr.font.color.rgb = RGBColor(0x52, 0x52, 0x5B)

    d.add_paragraph(f"Bill To: {c.get('company') or c.get('client_name') or '—'}")
    if c.get("billing_address"):
        d.add_paragraph(str(c["billing_address"]))
    d.add_paragraph(f"Issue Date: {c.get('issue_date') or '—'}    Due Date: {c.get('due_date') or '—'}    Project: {c.get('project_name') or '—'}")
    if c.get("description"):
        d.add_paragraph(str(c["description"]))

    table = d.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 4"
    hdr = table.rows[0].cells
    for i, t in enumerate(["Description", "Qty", "Unit Price", "Amount"]):
        hdr[i].text = t
    for li in _rows(invoice):
        row = table.add_row().cells
        row[0].text = str(li.get("description", ""))
        row[1].text = str(li.get("quantity", 0))
        row[2].text = _money(li.get("unit_price", 0))
        row[3].text = _money(li.get("amount", 0))

    d.add_paragraph()
    for lbl, val in [("Subtotal", invoice.get("subtotal", 0)), (f"VAT ({c.get('vat_rate', 0)}%)", invoice.get("vat", 0)), ("Total", invoice.get("total", 0))]:
        p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = p.add_run(f"{lbl}: {_money(val)}")
        if lbl == "Total":
            run.bold = True; run.font.color.rgb = RGBColor(0x7C, 0x3A, 0xED)

    for key in ("payment_terms", "bank_details", "notes"):
        if c.get(key):
            hp = d.add_paragraph(); hr = hp.add_run(key.replace("_", " ").title()); hr.bold = True
            d.add_paragraph(str(c[key]))

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
