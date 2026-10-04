"""Kwark: tap into AI brilliance from a simple shell command.

The CLI application class is loaded lazily (PEP 562) so that the library
layer (``kwark.ai``) can be imported without pulling in WizLib UI code,
the command classes or ``mcp``.
"""


def __getattr__(name):
    if name == 'KwarkApp':
        from kwark.app import KwarkApp
        return KwarkApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
