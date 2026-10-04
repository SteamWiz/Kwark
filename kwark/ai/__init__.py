"""Kwark library layer for other applications.

Rules: no WizLib, no config reading, no printing and no ``mcp``. Settings
come in as arguments, and errors are raised as ``KwarkAIError`` subclasses.
"""

from kwark.ai.errors import APIError
from kwark.ai.errors import KwarkAIError
from kwark.ai.errors import TruncatedResponseError
from kwark.ai.errors import UnsupportedFileTypeError
from kwark.ai.transcription import TRANSCRIBE_DISCLAIMER
from kwark.ai.transcription import TRANSCRIBE_PROMPT
from kwark.ai.transcription import transcribe

__all__ = [
    'APIError',
    'KwarkAIError',
    'TruncatedResponseError',
    'UnsupportedFileTypeError',
    'TRANSCRIBE_DISCLAIMER',
    'TRANSCRIBE_PROMPT',
    'transcribe',
]
