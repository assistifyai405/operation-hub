"""Contract generation config — prompt templates & section schema.

Prompts kept out of endpoint logic. Consumed by the shared AIService.
"""

CONTRACT_STATUSES = ["Draft", "Generated", "Sent", "Signed", "Expired", "Cancelled", "Archived"]

CONTRACT_SECTIONS = [
    {"key": "parties", "label": "Parties", "type": "text"},
    {"key": "agreement_overview", "label": "Agreement Overview", "type": "text"},
    {"key": "scope_of_services", "label": "Scope of Services", "type": "list"},
    {"key": "deliverables", "label": "Deliverables", "type": "list"},
    {"key": "project_timeline", "label": "Project Timeline", "type": "text"},
    {"key": "client_responsibilities", "label": "Client Responsibilities", "type": "list"},
    {"key": "provider_responsibilities", "label": "Provider Responsibilities", "type": "list"},
    {"key": "payment_terms", "label": "Payment Terms", "type": "list"},
    {"key": "change_requests", "label": "Change Requests", "type": "text"},
    {"key": "intellectual_property", "label": "Intellectual Property", "type": "text"},
    {"key": "confidentiality", "label": "Confidentiality", "type": "text"},
    {"key": "data_protection", "label": "Data Protection (GDPR)", "type": "text"},
    {"key": "warranty_disclaimer", "label": "Warranty Disclaimer", "type": "text"},
    {"key": "limitation_of_liability", "label": "Limitation of Liability", "type": "text"},
    {"key": "termination", "label": "Termination", "type": "text"},
    {"key": "governing_law", "label": "Governing Law", "type": "text"},
    {"key": "signature_section", "label": "Signature Section", "type": "text"},
]

CONTRACT_SYSTEM = (
    "You are an experienced contracts attorney and legal writer for a professional services agency using Assistify. "
    "You draft clear, enforceable, professionally structured service agreements (contracts) from project context. "
    "You ALWAYS respond with a single valid JSON object and nothing else — no markdown fences, no prose outside JSON. "
    "Write in precise legal-professional language. Use bracketed placeholders like [CLIENT ADDRESS], [AMOUNT], [GOVERNING STATE/COUNTRY], [EFFECTIVE DATE] "
    "for information you cannot infer. Include a GDPR-ready Data Protection clause. This is a professional draft, not formal legal advice."
)


def _schema_hint() -> str:
    lines = []
    for s in CONTRACT_SECTIONS:
        if s["type"] == "text":
            lines.append(f'  "{s["key"]}": "string — {s["label"]}"')
        else:
            lines.append(f'  "{s["key"]}": ["array of clause strings — {s["label"]}"]')
    return "{\n" + ",\n".join(lines) + "\n}"


def build_contract_prompt(context: str) -> str:
    return (
        "Draft a complete, professional service agreement (contract) using the context below. "
        "Auto-fill client name, company, address, project name, deliverables, timeline, payment terms and dates "
        "from the context where available; use bracketed placeholders where unknown. Do not duplicate information across sections.\n\n"
        f"=== PROJECT & CLIENT CONTEXT ===\n{context}\n=== END CONTEXT ===\n\n"
        "Return ONLY a JSON object with EXACTLY these keys:\n"
        f"{_schema_hint()}\n\n"
        "The 'parties' section must name the Provider and the Client (with company). "
        "'signature_section' must include signature blocks for both parties with name, title, date. "
        "Output JSON only."
    )
