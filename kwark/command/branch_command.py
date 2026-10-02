from kwark.command import PromptBasedCommand


class BranchCommand(PromptBasedCommand):
    """Generate a git branch name from input text using AI.
    The branch name will be hyphen-separated, lowercase, starting with
    the current date in YYYYMMDD format, followed by 1-4 important words
    from the input text."""

    name = 'branch'
    require_input = True
    success_message = "Generated branch name from input text"
