from kwark.command import PromptBasedCommand


class CommitCommand(PromptBasedCommand):
    """Generate a git commit message from diff output using AI.
    If there are no changes in the diff, use a dot as the commit message."""

    name = 'commit'
    success_message = "Generated commit message from diff"
