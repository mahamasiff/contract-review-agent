"""
Report-generation agent, fixed-pipeline mode
"""

from backend import mcp_client
from backend.clause_types import CLAUSE_SLUGS, CLAUSE_TYPES
from backend.models import clients

_VERDICT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "clause_type": {"type": "string", "enum": CLAUSE_SLUGS},
        "clause_present": {"type": "boolean"},
        "verdict": {
            "type": "string",
            "enum": ["compliant", "fallback_acceptable", "violation",
                     "missing_required", "needs_escalation"],
        },
        "explanation": {"type": "string"},
        "quoted_text": {"type": ["string", "null"]},
    },
    "required": ["clause_type", "clause_present", "verdict", "explanation", "quoted_text"],
}

REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": _VERDICT_ITEM_SCHEMA,
            "minItems": len(CLAUSE_SLUGS),
            "maxItems": len(CLAUSE_SLUGS),
        },
    },
    "required": ["verdicts"],
}

CLAUSE_BLOCK_TEMPLATE = """### {display_name} ({slug})
What this clause governs: {description}

Our playbook position:
- Default (what we want): {default}
- Fallback (acceptable if not default): {fallback}
- Escalate to human review if: {escalate}

Retrieved chunks (ranked by reranker relevance, higher rerank_score = more relevant):
{chunks_block}
"""

REPORT_PROMPT = """You are reviewing a vendor contract against our company's playbook, across all 7 clause types we track. Each section below covers one clause type: what it governs, our playbook position, and the text chunks retrieved from the contract as the closest semantic matches for that clause type.

Vector search returns the nearest matches regardless of whether the clause actually exists in the contract -- so for each clause type, first judge for yourself from the actual retrieved text whether that clause type is genuinely present. Don't force a compliance verdict onto unrelated text.

{clause_blocks}

Respond with JSON only, matching this shape:
{{
  "verdicts": [
    {{
      "clause_type": "<the slug in parentheses above, e.g. renewal_term>",
      "clause_present": true or false,
      "verdict": "compliant" | "fallback_acceptable" | "violation" | "missing_required" | "needs_escalation",
      "explanation": "1-3 sentences citing what the contract actually says (or doesn't) versus the playbook position for THIS clause type",
      "quoted_text": "the exact supporting quote from the retrieved text for THIS clause type, or null if clause_present is false"
    }},
    ... one entry per clause type, all 7, in the order they appear above ...
  ]
}}

Notes on picking a verdict:
- "missing_required" is ONLY for clause_present = false, when that clause type's absence is a real gap (not every absence is bad -- some playbook defaults ARE "this clause shouldn't exist", which is "compliant", not "missing_required"). Never use "missing_required" when clause_present is true -- if the clause exists but is inadequate (e.g. one-sided, insufficient, wrong terms), that is "violation" or "needs_escalation", not "missing_required".
- "needs_escalation" is for cases matching that clause type's escalate conditions specifically, not just any violation.
- Judge each clause type independently -- don't let one clause type's retrieved text influence another's verdict.
"""


async def _build_clause_block(contract_id: str, clause_meta: dict) -> tuple[str, list[dict]]:
    policy = await mcp_client.get_playbook_policy(clause_meta["slug"])
    # n_results=5 kept as the final count handed to the LLM; retrieve_clause
    # itself now widens to a 15-candidate pool and reranks with a
    # cross-encoder before returning these 5 (see vectorstore.py
    # query_with_rerank) -- this is what actually fixed the
    # governing_law/minimum_commitment weak spots retrieval_eval.py found,
    # not just raising n_results on the plain vector search.
    chunks = await mcp_client.retrieve_clause(contract_id, clause_meta["slug"], n_results=5)
    chunks_block = "\n\n".join(
        f"[rerank_score={c['rerank_score']:.3f}] {c['text']}" for c in chunks
    ) if chunks else "(no chunks retrieved)"

    block = CLAUSE_BLOCK_TEMPLATE.format(
        display_name=clause_meta["display_name"],
        slug=clause_meta["slug"],
        description=clause_meta["description"],
        default=policy["default"],
        fallback=policy["fallback"],
        escalate=policy["escalate"],
        chunks_block=chunks_block,
    )
    return block, chunks


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def _is_grounded(quoted_text: str | None, chunks: list[dict]) -> bool:
    """Checks quoted_text actually appears in the chunks that were
    retrieved for this clause type -- catches both plain hallucination
    and the subtler case where the LLM recalls real contract text from
    training-data memorization (public CUAD documents) rather than from
    what retrieval actually surfaced. Either way, if it's not grounded
    in what we gave the model, we can't trust the verdict was reasoned
    from our pipeline's retrieval."""
    if not quoted_text:
        return False
    norm_quote = _normalize(quoted_text)
    if not norm_quote:
        return False
    return any(norm_quote in _normalize(c["text"]) for c in chunks)


def _verify_grounding(verdicts: list[dict], chunks_by_slug: dict) -> list[dict]:
    for v in verdicts:
        # Prompt instructions alone aren't reliable enough to trust --
        # seen in testing: clause_present=true (the clause exists, just
        # inadequate) paired with verdict="missing_required" (which
        # should mean the clause is absent). Enforce the invariant in
        # code rather than hoping the model always follows the prompt.
        if v["clause_present"] and v["verdict"] == "missing_required":
            v["verdict"] = "needs_escalation"
            v["explanation"] = (
                "NOTE: model returned clause_present=true with verdict="
                "missing_required, which is contradictory (corrected to "
                f"needs_escalation). Original explanation: {v['explanation']}"
            )

        if not v["clause_present"]:
            v["grounded"] = True  # nothing to verify when nothing was quoted
            continue
        chunks = chunks_by_slug.get(v["clause_type"], [])
        grounded = _is_grounded(v.get("quoted_text"), chunks)
        v["grounded"] = grounded
        if not grounded:
            original = v["explanation"]
            v["verdict"] = "needs_escalation"
            v["explanation"] = (
                "VERIFICATION FAILED: the quoted text does not appear in the "
                "chunks actually retrieved for this clause type -- the model's "
                "claim is ungrounded (possible hallucination, or recall from "
                "training data rather than the retrieved context). Escalating "
                f"for human review rather than trusting it. Original claim: {original}"
            )
    return verdicts


async def generate_report(contract_id: str) -> list[dict]:
    """One verdict per clause type, all from a single Gemini call, then
    verified against the actually-retrieved text before being returned."""
    clause_types = await mcp_client.list_clause_types()

    blocks = []
    chunks_by_slug = {}
    for c in clause_types:
        block, chunks = await _build_clause_block(contract_id, c)
        blocks.append(block)
        chunks_by_slug[c["slug"]] = chunks

    prompt = REPORT_PROMPT.format(clause_blocks="\n".join(blocks))

    response = clients.generate_json(prompt, schema=REPORT_SCHEMA)
    verdicts = response["verdicts"]

    by_slug = {c["slug"]: c["display_name"] for c in CLAUSE_TYPES}
    for v in verdicts:
        v["display_name"] = by_slug.get(v["clause_type"], v["clause_type"])

    return _verify_grounding(verdicts, chunks_by_slug)
