"""The Anthropic client wrapper shared by the kwark.ai functions and the CLI.

Holds the default model and the thinking rule, so they live in one place.
"""

from contextlib import contextmanager

import anthropic
from anthropic import Anthropic

from kwark.ai.errors import APIError


DEFAULT_MODEL = 'claude-sonnet-5'

# Models that think adaptively when no `thinking` field is sent, and that
# accept `thinking: {"type": "disabled"}` to turn it off. Matched by exact
# model ID only, because other models (e.g. claude-sonnet-5-5) reject it.
THINKING_DISABLE_MODELS = frozenset({'claude-sonnet-5'})


def thinking_arguments(model):
    """Return the extra request arguments that turn thinking off for the
    model, or an empty dict if none are needed"""
    if model in THINKING_DISABLE_MODELS:
        return {'thinking': {'type': 'disabled'}}
    return {}


def create_client(api_key=None):
    """Return an Anthropic client, raising APIError if there is no API key.

    Args:
        api_key: Anthropic API key; None uses the SDK default
            (ANTHROPIC_API_KEY)
    """
    client = Anthropic(api_key=api_key)
    if client.api_key is None and client.auth_token is None:
        raise APIError(
            "No Anthropic API key: pass api_key or set ANTHROPIC_API_KEY")
    return client


@contextmanager
def wrap_api_errors(action):
    """Re-raise Anthropic SDK errors as APIError, e.g.
    'Anthropic API error {action}: ...'"""
    try:
        yield
    except anthropic.AnthropicError as e:
        raise APIError(f"Anthropic API error {action}: {e}") from e
