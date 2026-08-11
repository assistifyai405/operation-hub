"""Invoice generation config — prompt template & schema. No hardcoded prompts in endpoints."""

INVOICE_STATUSES = ["Draft", "Generated", "Sent", "Paid", "Overdue", "Cancelled", "Archived"]

# Editable text fields on the invoice body (client/company/project auto-filled by backend)
INVOICE_FIELDS = [
    {"key": "client_name", "label": "Client"},
    {"key": "company", "label": "Company"},
    {"key": "billing_address", "label": "Billing Address"},
    {"key": "project_name", "label": "Project"},
    {"key": "description", "label": "Description"},
    {"key": "payment_terms", "label": "Payment Terms"},
    {"key": "notes", "label": "Notes"},
    {"key": "bank_details", "label": "Bank Details"},
]

INVOICE_SYSTEM = (
    "You are a professional billing specialist for an agency using Assistify. "
    "You produce clean, accurate invoices from project context. "
    "You ALWAYS respond with a single valid JSON object and nothing else — no markdown fences, no prose outside JSON. "
    "Use bracketed placeholders like [BANK NAME], [ACCOUNT NUMBER], [CLIENT ADDRESS] for details you cannot infer. "
    "Never invent totals — only provide line item descriptions, quantities and unit prices; the system computes totals."
)


def build_invoice_prompt(context: str) -> str:
    return (
        "Create a professional invoice from the context below. Derive concrete billable line items from the "
        "project's proposal deliverables, scope, and payment schedule. Use realistic quantities and unit prices "
        "(use round placeholder amounts if pricing is unknown).\n\n"
        f"=== PROJECT / CLIENT / PROPOSAL / CONTRACT CONTEXT ===\n{context}\n=== END CONTEXT ===\n\n"
        "Return ONLY a JSON object with EXACTLY these keys:\n"
        "{\n"
        '  "description": "string — short summary of what is being billed",\n'
        '  "line_items": [{"description": "string", "quantity": number, "unit_price": number}],\n'
        '  "vat_rate": number,\n'
        '  "payment_terms": "string — e.g. Net 14",\n'
        '  "notes": "string — short thank-you / payment note",\n'
        '  "bank_details": "string — placeholder bank/payment details",\n'
        '  "billing_address": "string — client billing address or [CLIENT ADDRESS] placeholder"\n'
        "}\n"
        "vat_rate is a percentage number (e.g. 20 for 20%, 0 if not applicable). Output JSON only."
    )
