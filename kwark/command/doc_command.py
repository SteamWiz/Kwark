from kwark.command import PromptBasedCommand


class DocCommand(PromptBasedCommand):
    """Summarize observations and conclusions from random text such as a
    thread, email, or notes"""

    name = 'doc'
    success_message = "Generated documentation summary"
