import io
import asyncio

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from core import db, log_activity
from dependencies import current_org, require_project
import storage as S
from proposal_export import build_pdf, build_docx
from invoice_export import build_invoice_pdf, build_invoice_docx
from contract_config import CONTRACT_SECTIONS

router = APIRouter(prefix="/api")


# ------------------- shared document fetch helpers -------------------
async def _get_ai_proposal(project_id: str, org: str):
    return await db.ai_proposals.find_one({"project_id": project_id, "organizationId": org}, {"_id": 0})


async def _get_ai_contract(project_id: str, org: str):
    return await db.ai_contracts.find_one({"project_id": project_id, "organizationId": org}, {"_id": 0})


async def _get_ai_invoice(project_id: str, org: str):
    return await db.ai_invoices.find_one({"project_id": project_id, "organizationId": org}, {"_id": 0})


def _export_or_404(project_id, proposal):
    if not proposal:
        raise HTTPException(status_code=404, detail="Save the proposal before exporting")


def _safe_filename(name: str) -> str:
    ascii_name = "".join(c if (c.isalnum() or c in " -_") else "_" for c in (name or "proposal"))
    return ascii_name.strip().replace(" ", "_")[:60] or "proposal"


async def _brand_context(org_id: str, footer_key: str) -> dict:
    from server import _merged_settings  # lazy import: settings helpers live in the app module
    org_doc = await db.organizations.find_one({"id": org_id}, {"_id": 0}) or {}
    s = _merged_settings(org_doc)
    b, o = s["branding"], s["organization"]
    logo_url = b.get("pdfLogo") or b.get("logo") or o.get("logo") or ""
    logo_bytes = None
    if logo_url and "/api/settings/image/" in logo_url:
        asset_id = logo_url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
        asset = await db.branding_assets.find_one({"id": asset_id, "organizationId": org_id}, {"_id": 0})
        if asset and asset.get("storage_path"):
            try:
                logo_bytes, _ = await asyncio.to_thread(S.get_object, asset["storage_path"])
            except Exception:
                logo_bytes = None
    return {
        "company_name": o.get("name", "") or "Assistify",
        "logo_bytes": logo_bytes,
        "primary": b.get("primaryColor") or "#16A34A",
        "secondary": b.get("secondaryColor") or "#22D3EE",
        "address": o.get("address", ""), "website": o.get("website", ""),
        "email": o.get("businessEmail", ""), "phone": o.get("phone", ""),
        "vat": o.get("vatNumber", ""), "kvk": o.get("kvkNumber", ""),
        "footer": b.get(footer_key, ""),
    }


# ------------------- Proposal exports -------------------
@router.get("/projects/{project_id}/proposal/export/pdf")
async def export_proposal_pdf(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    proposal = await _get_ai_proposal(project_id, org)
    _export_or_404(project_id, proposal)
    brand = await _brand_context(org, "proposalFooter")
    data = build_pdf(proposal, brand=brand)
    await log_activity(project_id, "proposal_exported", "Proposal exported as PDF")
    fname = _safe_filename(proposal.get("title"))
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@router.get("/projects/{project_id}/proposal/export/docx")
async def export_proposal_docx(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    proposal = await _get_ai_proposal(project_id, org)
    _export_or_404(project_id, proposal)
    brand = await _brand_context(org, "proposalFooter")
    data = build_docx(proposal, brand=brand)
    await log_activity(project_id, "proposal_exported", "Proposal exported as DOCX")
    fname = _safe_filename(proposal.get("title"))
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.docx"'})


# ------------------- Contract exports -------------------
@router.get("/projects/{project_id}/contract/export/pdf")
async def export_contract_pdf(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    contract = await _get_ai_contract(project_id, org)
    if not contract:
        raise HTTPException(status_code=404, detail="Save the contract before exporting")
    brand = await _brand_context(org, "contractFooter")
    data = build_pdf(contract, CONTRACT_SECTIONS, "Service Agreement", brand=brand, signature=True)
    await log_activity(project_id, "contract_exported", "Contract exported as PDF")
    fname = _safe_filename(contract.get("title"))
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@router.get("/projects/{project_id}/contract/export/docx")
async def export_contract_docx(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    contract = await _get_ai_contract(project_id, org)
    if not contract:
        raise HTTPException(status_code=404, detail="Save the contract before exporting")
    brand = await _brand_context(org, "contractFooter")
    data = build_docx(contract, CONTRACT_SECTIONS, "Service Agreement", brand=brand, signature=True)
    await log_activity(project_id, "contract_exported", "Contract exported as DOCX")
    fname = _safe_filename(contract.get("title"))
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.docx"'})


# ------------------- Invoice exports -------------------
@router.get("/projects/{project_id}/invoice/export/pdf")
async def export_invoice_pdf(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    invoice = await _get_ai_invoice(project_id, org)
    if not invoice:
        raise HTTPException(status_code=404, detail="Save the invoice before exporting")
    brand = await _brand_context(org, "invoiceFooter")
    data = build_invoice_pdf(invoice, brand=brand)
    await log_activity(project_id, "invoice_exported", "Invoice exported as PDF")
    fname = _safe_filename(invoice.get("invoice_number") or invoice.get("title"))
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@router.get("/projects/{project_id}/invoice/export/docx")
async def export_invoice_docx(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    invoice = await _get_ai_invoice(project_id, org)
    if not invoice:
        raise HTTPException(status_code=404, detail="Save the invoice before exporting")
    brand = await _brand_context(org, "invoiceFooter")
    data = build_invoice_docx(invoice, brand=brand)
    await log_activity(project_id, "invoice_exported", "Invoice exported as DOCX")
    fname = _safe_filename(invoice.get("invoice_number") or invoice.get("title"))
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.docx"'})
