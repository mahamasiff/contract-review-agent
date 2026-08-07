"""
Canonical list of the 7 clause types this project reviews. Single source
of truth -- eval scripts (retrieval_eval.py, select_contracts.py) and the
MCP tools both need this same list/slugs and currently redefine it
separately; new code should import from here instead.
"""

CLAUSE_TYPES = [
    {
        "slug": "renewal_term",
        "display_name": "Renewal Term",
        "description": (
            "Does this agreement automatically renew, what is the renewal "
            "period, and what notice is required to terminate the renewal?"
        ),
    },
    {
        "slug": "termination_for_convenience",
        "display_name": "Termination For Convenience",
        "description": (
            "Can either party terminate this agreement without cause, and "
            "what conditions or notice period apply?"
        ),
    },
    {
        "slug": "cap_on_liability",
        "display_name": "Cap On Liability",
        "description": (
            "What is the maximum liability cap for either party under "
            "this agreement?"
        ),
    },
    {
        "slug": "uncapped_liability",
        "display_name": "Uncapped Liability",
        "description": (
            "Are there exceptions where a party's liability is not "
            "subject to any cap?"
        ),
    },
    {
        "slug": "minimum_commitment",
        "display_name": "Minimum Commitment",
        "description": (
            "Is there a minimum purchase, spend, or volume commitment "
            "required under this agreement?"
        ),
    },
    {
        "slug": "audit_rights",
        "display_name": "Audit Rights",
        "description": (
            "Does either party have the right to audit the other party's "
            "records or compliance?"
        ),
    },
    {
        "slug": "governing_law",
        "display_name": "Governing Law",
        "description": (
            "Which state or country's law governs the interpretation of "
            "this agreement?"
        ),
    },
]

CLAUSE_SLUGS = [c["slug"] for c in CLAUSE_TYPES]
