"""Policy check tool — evaluate accreditation eligibility using RAG + business rules.

This tool combines document retrieval with structured logic to determine
whether a teacher meets accreditation requirements.
"""

from pydantic import BaseModel
from tools.rag_tool import rag_search, format_context_for_llm


class PolicyResult(BaseModel):
    """Structured output from policy check."""
    eligible: bool | None  # None = unable to determine
    reason: str
    requirements_met: list[str]
    requirements_missing: list[str]
    confidence: float  # 0.0 to 1.0
    next_steps: list[str]


# Accreditation level requirements (simplified business rules)
LEVEL_REQUIREMENTS = {
    "Provisional": {
        "qualifications": ["approved teaching qualification"],
        "experience": "none required",
        "pd_hours": 0,
        "description": "Entry-level accreditation for new teachers",
    },
    "Proficient": {
        "qualifications": ["approved teaching qualification"],
        "experience": "demonstrated proficiency in classroom",
        "pd_hours": 100,
        "description": "Standard accreditation demonstrating competence",
    },
    "Highly Accomplished": {
        "qualifications": ["approved teaching qualification", "evidence portfolio"],
        "experience": "extensive teaching record",
        "pd_hours": 100,
        "description": "Advanced accreditation for experienced teachers",
    },
    "Lead": {
        "qualifications": ["approved teaching qualification", "evidence portfolio", "peer references"],
        "experience": "leadership in educational settings",
        "pd_hours": 100,
        "description": "Highest accreditation level for teacher leaders",
    },
}


async def check_eligibility(
    qualification: str,
    jurisdiction: str = "NSW",
    accreditation_level: str = "Provisional",
) -> PolicyResult:
    """Check if a teacher is eligible for accreditation.

    Combines RAG search for policy context with hardcoded business rules.
    """
    level = accreditation_level.strip().title()
    reqs = LEVEL_REQUIREMENTS.get(level)

    if not reqs:
        return PolicyResult(
            eligible=None,
            reason=f"Unknown accreditation level: {accreditation_level}",
            requirements_met=[],
            requirements_missing=[],
            confidence=0.0,
            next_steps=[f"Valid levels: {', '.join(LEVEL_REQUIREMENTS.keys())}"],
        )

    # Search for relevant policy documents
    search = await rag_search(
        f"accreditation eligibility {level} qualification requirements {jurisdiction}",
        top_k=3,
    )
    policy_context = format_context_for_llm(search) if search.success else ""

    # Apply business rules
    met = []
    missing = []

    if qualification and len(qualification) > 3:
        met.append(f"Teaching qualification provided: {qualification}")
    else:
        missing.append("Approved teaching qualification required")

    if jurisdiction.upper() in ("NSW", "ACT", "VIC", "QLD", "SA", "WA", "TAS", "NT"):
        met.append(f"Australian jurisdiction: {jurisdiction}")
    else:
        missing.append(f"Overseas qualification from {jurisdiction} may require AITSL assessment")

    eligible = len(missing) == 0
    confidence = 0.7 if eligible else 0.5  # Lower if missing items

    next_steps = []
    if eligible:
        next_steps.append(f"Apply for {level} accreditation via NESA portal")
        next_steps.append("Prepare supporting documentation")
    else:
        next_steps.extend(missing)
        next_steps.append("Contact NESA for eligibility assessment")

    return PolicyResult(
        eligible=eligible,
        reason=f"Eligibility assessment for {level} accreditation based on provided information",
        requirements_met=met,
        requirements_missing=missing,
        confidence=confidence,
        next_steps=next_steps,
    )
