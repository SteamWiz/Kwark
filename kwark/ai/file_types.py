"""The file types Kwark can send to Claude, in one place.

Shared by ``kwark.ai.transcribe`` and the CLI's ``activate`` command (via
``kwark.ai_services.anthropic_ai_service.file_content_type``).
"""

# Lower-case suffix -> (Anthropic content block type, media type)
FILE_TYPES = {
    '.pdf': ('document', 'application/pdf'),
    '.png': ('image', 'image/png'),
    '.jpg': ('image', 'image/jpeg'),
    '.jpeg': ('image', 'image/jpeg'),
    '.gif': ('image', 'image/gif'),
    '.webp': ('image', 'image/webp'),
    '.txt': ('document', 'text/plain'),
    '.md': ('document', 'text/plain'),
    '.csv': ('document', 'text/plain'),
}

SUPPORTED_SUFFIXES = sorted(FILE_TYPES)
