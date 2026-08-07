"""
Thin MCP protocol wrapper around the plain functions in mcp_tools.py.
Deliberately kept separate from mcp_tools.py: the functions there are
tested directly as plain Python (no protocol round-trip needed to
iterate on their logic), and this file's only job is exposing them over
MCP. Run directly for stdio transport:

    python -m backend.mcp_server
"""

from mcp.server import MCPServer

from backend import mcp_tools

server = MCPServer(name="contract-review-tools")


@server.tool()
def list_clause_types() -> list[dict]:
    """Returns the 7 clause types this project reviews (slug,
    display_name, description for each), so the caller can loop over
    all of them without hardcoding the list."""
    return mcp_tools.list_clause_types()


@server.tool()
def get_playbook_policy(clause_type: str) -> dict:
    """Returns the company's playbook position for one clause type:
    {default, fallback, escalate, rationale}. clause_type must be one
    of the slugs returned by list_clause_types (e.g. 'cap_on_liability')."""
    return mcp_tools.get_playbook_policy(clause_type)


@server.tool()
def retrieve_clause(contract_id: str, clause_type: str, n_results: int = 3) -> list[dict]:
    """Semantic search for the chunk(s) of an ingested contract's text
    most relevant to one clause type. Returns a ranked list of
    {text, start, end, distance} -- lower distance means more similar.
    The contract must already be ingested under contract_id, or this
    raises an error."""
    return mcp_tools.retrieve_clause(contract_id, clause_type, n_results)


if __name__ == "__main__":
    server.run(transport="stdio")
