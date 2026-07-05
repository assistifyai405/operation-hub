"""Proposal generation config — prompt templates & section schema.

Kept out of endpoints so prompts are configurable and not hardcoded in logic.
"""

PROPOSAL_STATUSES = ["Draft", "Generated", "Sent", "Accepted", "Rejected", "Archived"]

PROPOSAL_SECTIONS = [
    {"key": "executive_summary", "label": "Executive Summary", "type": "text"},
    {"key": "client_goals", "label": "Client Goals", "type": "list"},
    {"key": "business_challenges", "label": "Business Challenges", "type": "list"},
    {"key": "recommended_solution", "label": "Recommended Solution", "type": "text"},
    {"key": "project_scope", "label": "Project Scope", "type": "list"},
    {"key": "deliverables", "label": "Deliverables", "type": "list"},
    {"key": "timeline", "label": "Timeline", "type": "text"},
    {"key": "milestones", "label": "Milestones", "type": "list"},
    {"key": "technical_approach", "label": "Technical Approach", "type": "text"},
    {"key": "success_metrics", "label": "Success Metrics", "type": "list"},
    {"key": "pricing_placeholder", "label": "Pricing", "type": "text"},
    {"key": "payment_schedule", "label": "Payment Schedule", "type": "list"},
    {"key": "assumptions", "label": "Assumptions", "type": "list"},
    {"key": "terms_conditions", "label": "Terms & Conditions", "type": "list"},
    {"key": "acceptance_section", "label": "Acceptance", "type": "text"},
]

PROPOSAL_SYSTEM = (
    "You are a senior proposal writer for a premium agency using Assistify OS. "
    "You transform internal project context into a polished, persuasive, client-ready proposal. "
    "You ALWAYS respond with a single valid JSON object and nothing else — no markdown fences, no prose outside JSON. "
    "Write in a confident, professional, client-facing tone. Use placeholders like [PRICE] and [AMOUNT] for pricing you cannot know."
)


def _schema_hint() -> str:
    lines = []
    for s in PROPOSAL_SECTIONS:
        if s["type"] == "text":
            lines.append(f'  "{s["key"]}": "string — {s["label"]}"')
        else:
            lines.append(f'  "{s["key"]}": ["array of strings — {s["label"]}"]')
    return "{\n" + ",\n".join(lines) + "\n}"


def build_proposal_prompt(context: str) -> str:
    return (
        f"Using the internal project context below, write a complete client-facing proposal.\n\n"
        f"=== PROJECT CONTEXT ===\n{context}\n=== END CONTEXT ===\n\n"
        "Return ONLY a JSON object with EXACTLY these keys:\n"
        f"{_schema_hint()}\n\n"
        "Guidance: pricing_placeholder should present a clear pricing structure using [PRICE]/[AMOUNT] placeholders. "
        "payment_schedule as milestone-based installments. terms_conditions concise and professional. "
        "acceptance_section should include a signature/acceptance statement. Tailor everything to the actual context. Output JSON only."
    )
