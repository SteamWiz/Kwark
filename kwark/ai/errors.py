"""Exceptions raised by the kwark.ai library layer"""


class KwarkAIError(Exception):
    """Base class for all kwark.ai errors"""


class UnsupportedFileTypeError(KwarkAIError):
    """The file type is not supported by the requested operation"""


class TruncatedResponseError(KwarkAIError):
    """The model stopped because it reached the max_tokens limit"""


class APIError(KwarkAIError):
    """The Anthropic API call failed"""


class MissingToolUseError(KwarkAIError):
    """The model's response did not include the expected tool call"""


class SchemaValidationError(KwarkAIError):
    """The extracted data does not match the requested JSON schema"""
