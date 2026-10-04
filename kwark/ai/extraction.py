"""Extract structured data matching a JSON schema from text with Claude"""

from kwark.ai.client import DEFAULT_MODEL
from kwark.ai.client import create_client
from kwark.ai.client import thinking_arguments
from kwark.ai.client import wrap_api_errors
from kwark.ai.errors import KwarkAIError
from kwark.ai.errors import MissingToolUseError
from kwark.ai.errors import SchemaValidationError
from kwark.ai.errors import TruncatedResponseError


TOOL_NAME = 'record'

TOOL_DESCRIPTION = (
    "Record the structured data extracted from the text. The input must "
    "match the schema.")

SYSTEM_PROMPT = (
    f"You extract structured data from the text the user provides. Call "
    f"the {TOOL_NAME} tool exactly once with data that matches its input "
    f"schema. Base the data only on the text.")


def extract(text, schema, *, instructions=None, model=DEFAULT_MODEL,
            api_key=None, max_tokens=4096):
    """Extract structured data from text with Claude.

    Uses forced tool use: the schema becomes the input schema of a single
    tool that the model must call.

    Args:
        text: The text to extract data from
        schema: JSON Schema dict describing the result (type 'object')
        instructions: Optional task description added to the system prompt
        model: Anthropic model ID (default DEFAULT_MODEL, Claude Sonnet 5)
        api_key: Anthropic API key; None uses the SDK default
            (ANTHROPIC_API_KEY)
        max_tokens: Maximum output tokens

    Returns:
        A dict matching the schema

    Raises:
        KwarkAIError: the schema is not a JSON Schema object
        TruncatedResponseError: the output hit max_tokens
        MissingToolUseError: the response had no call to the tool
        SchemaValidationError: a required property is missing
        APIError: the Anthropic API call failed
    """
    if not isinstance(schema, dict) or schema.get('type') != 'object':
        raise KwarkAIError(
            "schema must be a JSON Schema dict with type 'object'")
    system = SYSTEM_PROMPT
    if instructions:
        system = f"{system}\n\n{instructions}"
    # Forced tool use is incompatible with thinking, so turn it off for
    # models that would otherwise think
    with wrap_api_errors('extracting data'):
        client = create_client(api_key)
        message = client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            tools=[{'name': TOOL_NAME, 'description': TOOL_DESCRIPTION,
                    'input_schema': schema}],
            tool_choice={'type': 'tool', 'name': TOOL_NAME},
            messages=[{'role': 'user', 'content': text}],
            **thinking_arguments(model))
    if message.stop_reason == 'max_tokens':
        raise TruncatedResponseError(
            f"Extraction was truncated at max_tokens={max_tokens}; "
            f"increase max_tokens")
    block = next((b for b in message.content
                  if b.type == 'tool_use' and b.name == TOOL_NAME), None)
    if block is None:
        raise MissingToolUseError(
            f"The response did not call the {TOOL_NAME} tool")
    result = dict(block.input)
    missing = [k for k in schema.get('required', []) if k not in result]
    if missing:
        raise SchemaValidationError(
            f"Extracted data is missing required properties: "
            f"{', '.join(missing)}")
    return result
