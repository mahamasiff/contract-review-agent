import json
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

DEFAULT_MODEL = "gemini-3.5-flash"

_client = None


def get_client():
    global _client
    if _client is None:
        # GOOGLE_API_KEY first: GEMINI_API_KEY hit its free-tier daily
        # quota (20 requests/day) during testing -- GOOGLE_API_KEY is a
        # separate key with its own quota bucket.
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "No GEMINI_API_KEY or GOOGLE_API_KEY found in environment. "
                "Add one to .env."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def generate_text(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Plain text response, e.g. for explaining a clause in prose."""
    client = get_client()
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text


def generate_json(prompt: str, schema: dict = None, model: str = DEFAULT_MODEL,
                   max_retries: int = 3) -> dict:
    """Response constrained to valid JSON, e.g. for structured compliance
    verdicts. Pass `schema` (plain JSON Schema dict) when possible --
    schema-constrained output is materially more reliable than mime-type
    alone, which in testing still occasionally produced JSON with
    unescaped quotes from contract text embedded in a string field.

    Retries on: malformed JSON (LLM sampling is non-deterministic, a
    second attempt is often clean) and HTTP 429 rate limits (with
    backoff -- easy to hit when firing several calls in a tight loop,
    as the report pipeline does)."""
    client = get_client()
    config_kwargs = {"responseMimeType": "application/json"}
    if schema:
        config_kwargs["responseJsonSchema"] = schema
    config = types.GenerateContentConfig(**config_kwargs)

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            last_error = e
        except errors.APIError as e:
            last_error = e
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(15 * (attempt + 1))
                continue
            if e.code != 429:
                raise
    raise last_error
