"""
The agent's actual connection to the MCP server -- this is what makes
"the agent uses MCP tools" literally true, as opposed to backend/agent
importing backend/mcp_tools.py's functions directly (which is what it
did before, and is not the same thing even though the result looks
identical).

Spawns backend/mcp_server.py as a subprocess ONCE and keeps the stdio
session open for reuse across calls -- respawning a subprocess and
redoing the MCP handshake on every single tool call would be needless
latency for a session that's really just talking to itself in-process
anyway. AsyncExitStack holds the two nested async context managers
(stdio_client, ClientSession) open across calls instead of closing them
immediately, which is the standard pattern for "enter once, use many
times, close at shutdown."
"""

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters, stdio_client

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)  # backend/ -> project root

_exit_stack = None
_session = None
_init_lock = asyncio.Lock()


async def get_session() -> ClientSession:
    global _exit_stack, _session
    if _session is not None:
        return _session

    async with _init_lock:
        if _session is not None:  # someone else won the race while we waited
            return _session

        _exit_stack = AsyncExitStack()
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "backend.mcp_server"],
            cwd=PROJECT_ROOT,
        )
        read, write = await _exit_stack.enter_async_context(stdio_client(params))
        session = await _exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        _session = session
        return _session


async def close_session():
    global _exit_stack, _session
    if _exit_stack is not None:
        await _exit_stack.aclose()
    _exit_stack = None
    _session = None


def _parse_result(result):
    """This SDK's result shape differs by return type -- list-returning
    tools get real structured_content ({"result": [...]}), dict-returning
    tools get structured_content=None and must be parsed from the text
    content block(s) instead. Same logic proven in the original
    end-to-end smoke test."""
    if result.is_error:
        raise RuntimeError(result.content[0].text)
    if result.structured_content is not None:
        payload = result.structured_content
        if isinstance(payload, dict) and set(payload.keys()) == {"result"}:
            return payload["result"]
        return payload
    parsed = [json.loads(block.text) for block in result.content]
    return parsed[0] if len(parsed) == 1 else parsed


#  A tool call hung indefinitely in testing on one specific error path
# (retrieve_clause against a not-yet-ingested contract_id) -- root cause
# not fully pinned down (looked like the subprocess's stdio channel
# getting corrupted on that exception path), but the real app always
# ingests before calling these, so it's not expected to hit. This is a
# safety net so a recurrence times out loudly instead of hanging the
# whole app forever.
TOOL_CALL_TIMEOUT_SECONDS = 45


async def _call_tool(name: str, arguments: dict):
    session = await get_session()
    try:
        return await asyncio.wait_for(
            session.call_tool(name, arguments), timeout=TOOL_CALL_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        raise RuntimeError(
            f"MCP tool call '{name}' did not respond within "
            f"{TOOL_CALL_TIMEOUT_SECONDS}s -- the server may be stuck. "
            "Known trigger: calling retrieve_clause on a contract_id that "
            "isn't ingested yet."
        )


async def list_clause_types():
    result = await _call_tool("list_clause_types", {})
    return _parse_result(result)


async def get_playbook_policy(clause_type: str):
    result = await _call_tool("get_playbook_policy", {"clause_type": clause_type})
    return _parse_result(result)


async def retrieve_clause(contract_id: str, clause_type: str, n_results: int = 5):
    result = await _call_tool(
        "retrieve_clause",
        {"contract_id": contract_id, "clause_type": clause_type, "n_results": n_results},
    )
    return _parse_result(result)
