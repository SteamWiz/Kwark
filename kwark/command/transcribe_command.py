import kwark.ai
from kwark.command import AICommand
from wizlib.parser import WizParser


class TranscribeCommand(AICommand):
    """Transcribe a file (PDF, image or text) to Markdown using
    kwark.ai.transcribe and write it to stdout, preceded by the
    TRANSCRIBE_DISCLAIMER as an HTML comment unless --no-disclaimer is given.

    Example:
        kwark transcribe invoice.pdf > invoice.pdf.md
    """

    name = 'transcribe'
    default_model = 'claude-opus-4-6'

    @classmethod
    def add_args(cls, parser: WizParser):
        super().add_args(parser)
        parser.add_argument('file')
        parser.add_argument('--no-disclaimer', action='store_true')

    def handle_vals(self):
        # Check before super(), which fills model from the general kwark-model
        model_provided = self.provided('model')
        super().handle_vals()
        # Explicit chain for transcribe: --model, then kwark-transcribe-model,
        # then the class default (the general kwark-model is not used)
        if not model_provided:
            self.model = (
                self.app.config.get('kwark-transcribe-model')
                or self.default_model
            )

    @AICommand.wrap
    def execute(self):
        # KwarkAIError propagates: WizApp.start prints it to stderr and exits
        # with status 1, so nothing but the Markdown reaches stdout
        markdown = kwark.ai.transcribe(
            self.file, model=self.model, api_key=self.api_key or None)
        markdown = markdown.strip('\n') + '\n'
        if self.no_disclaimer:
            return markdown
        return f"<!-- {kwark.ai.TRANSCRIBE_DISCLAIMER} -->\n\n{markdown}"
