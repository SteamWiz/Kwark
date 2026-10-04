"""Exceptions raised by the kwark.ai library layer"""


class KwarkAIError(Exception):
    """Base class for all kwark.ai errors"""


class UnsupportedFileTypeError(KwarkAIError):
    """The file type is not supported by the requested operation"""


class TruncatedResponseError(KwarkAIError):
    """The model stopped because it reached the max_tokens limit"""


class APIError(KwarkAIError):
    """The Anthropic API call failed"""
