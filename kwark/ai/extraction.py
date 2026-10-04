"""Extract structured data matching a JSON schema from text with Claude"""

from copy import deepcopy

from kwark.ai.client import DEFAULT_MODEL
from kwark.ai.client import create_client
from kwark.ai.client import supports_forced_tool_use
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


# Keywords whose value is a single subschema, a list of subschemas, or a
# mapping of names to subschemas
SUBSCHEMA_KEYWORDS = {'items', 'additionalProperties', 'not', 'contains',
                      'if', 'then', 'else'}
SUBSCHEMA_LIST_KEYWORDS = {'anyOf', 'allOf', 'oneOf', 'prefixItems'}
SUBSCHEMA_MAP_KEYWORDS = {'properties', 'patternProperties', '$defs',
                          'definitions'}


def _is_object_schema(schema):
    schema_type = schema.get('type')
    if isinstance(schema_type, list):
        return 'object' in schema_type
    return schema_type == 'object' or (
        schema_type is None and 'properties' in schema)


def _strict_schema(schema):
    """Return a copy of the schema prepared for strict tool use.

    Strict mode requires additionalProperties false on every object, so it
    is added wherever the caller didn't set it. Nothing else changes:
    keywords such as enum, const and pattern are kept, and any keyword
    strict mode doesn't support makes the API return an error (raised as
    APIError) rather than being dropped. The caller's schema is not changed.
    """
    if isinstance(schema, list):
        return [_strict_schema(s) for s in schema]
    if not isinstance(schema, dict):
        return schema
    result = {}
    for key, value in schema.items():
        if key in SUBSCHEMA_KEYWORDS or key in SUBSCHEMA_LIST_KEYWORDS:
            result[key] = _strict_schema(value)
        elif key in SUBSCHEMA_MAP_KEYWORDS and isinstance(value, dict):
            result[key] = {k: _strict_schema(v) for k, v in value.items()}
        else:
            result[key] = deepcopy(value)
    if _is_object_schema(result):
        result.setdefault('additionalProperties', False)
    return result


def _tool_arguments(schema, model):
    """Return the tools and tool_choice request arguments for the model.

    Models that accept it get forced tool use with the schema unchanged.
    Models that reject forced tool use get tool_choice 'auto' with a strict
    tool, whose schema has additionalProperties false added to every object.
    """
    tool = {'name': TOOL_NAME, 'description': TOOL_DESCRIPTION}
    if supports_forced_tool_use(model):
        tool['input_schema'] = schema
        tool_choice = {'type': 'tool', 'name': TOOL_NAME}
    else:
        tool['input_schema'] = _strict_schema(schema)
        tool['strict'] = True
        tool_choice = {'type': 'auto'}
    return {'tools': [tool], 'tool_choice': tool_choice}


def extract(text, schema, *, instructions=None, model=DEFAULT_MODEL,
            api_key=None, max_tokens=4096):
    """Extract structured data from text with Claude.

    The schema becomes the input schema of a single tool. Most models are
    forced to call it (tool_choice 'tool'). Models that reject forced tool
    use (see FORCED_TOOL_UNSUPPORTED_MODELS in kwark.ai.client, e.g.
    claude-sonnet-5-5 and claude-opus-5-5) get tool_choice 'auto' with a
    strict tool instead; if such a model doesn't call the tool,
    MissingToolUseError is raised. For the strict tool, additionalProperties
    false is added to every object in a copy of the schema; other keywords
    (including enum, const and pattern) are sent unchanged, and keywords
    strict mode doesn't support cause an APIError.

    Args:
        text: The text to extract data from
        schema: JSON Schema dict describing the result (type 'object')
        instructions: Optional task description added to the system prompt
        model: Anthropic model ID (default DEFAULT_MODEL, Claude Sonnet 5)
        api_key: Anthropic API key; None uses the SDK default
            (ANTHROPIC_API_KEY)
        max_tokens: Maximum output tokens, including any thinking

    Returns:
        A dict matching the schema

    Raises:
        KwarkAIError: the schema is not a JSON Schema object
        TruncatedResponseError: the output hit max_tokens
        MissingToolUseError: the response had no call to the tool
        SchemaValidationError: the tool input is not an object, or a
            required property is missing
        APIError: the Anthropic API call failed
    """
    if not isinstance(schema, dict) or schema.get('type') != 'object':
        raise KwarkAIError(
            "schema must be a JSON Schema dict with type 'object'")
    system = SYSTEM_PROMPT
    if instructions:
        system = f"{system}\n\n{instructions}"
    tool_arguments = _tool_arguments(schema, model)
    with wrap_api_errors('extracting data'):
        client = create_client(api_key)
        message = client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{'role': 'user', 'content': text}],
            **tool_arguments)
    if message.stop_reason == 'max_tokens':
        raise TruncatedResponseError(
            f"Extraction was truncated at max_tokens={max_tokens}; "
            f"increase max_tokens")
    block = next((b for b in message.content
                  if b.type == 'tool_use' and b.name == TOOL_NAME), None)
    if block is None:
        raise MissingToolUseError(
            f"The response did not call the {TOOL_NAME} tool")
    if not isinstance(block.input, dict):
        raise SchemaValidationError(
            f"Extracted data is not an object: "
            f"{type(block.input).__name__}")
    result = dict(block.input)
    missing = [k for k in schema.get('required', []) if k not in result]
    if missing:
        raise SchemaValidationError(
            f"Extracted data is missing required properties: "
            f"{', '.join(missing)}")
    return result
