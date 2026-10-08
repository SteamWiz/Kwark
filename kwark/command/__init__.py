from functools import cached_property
from wizlib.command import WizCommand
from wizlib.parser import WizParser

from kwark.ai_services import AIService


class KwarkUsageError(Exception):
    """A missing or invalid command-line argument. Raised from handle_vals
    instead of making an argument required in argparse: WizLib's --help still
    enforces required arguments, and its fallback to the default command then
    reports a misleading 'unrecognized arguments' error. WizApp.start prints
    this to stderr and exits with status 1."""


class KwarkCommand(WizCommand):

    default = 'null'
    ai_service_type = 'anthropic'

    @classmethod
    def add_args(cls, parser: WizParser):
        super().add_args(parser)
        parser.add_argument('--api-key', '-k')

    def handle_vals(self):
        super().handle_vals()
        if not self.provided('api_key'):  # Fixed: use 'api_key' not 'api-key'
            if key := self.app.config.get('kwark-api-anthropic-key'):
                self.api_key = key


class AICommand(KwarkCommand):
    """Base class for commands that perform AI messaging."""

    # Model used when neither --model nor config designates one. None means
    # the AI service default. Override per command.
    default_model = None

    @classmethod
    def add_args(cls, parser: WizParser):
        super().add_args(parser)
        parser.add_argument('--model', '-m')

    def handle_vals(self):
        super().handle_vals()
        if not self.provided('model'):
            self.model = (
                self.app.config.get('kwark-model') or self.default_model
            )

    @cached_property
    def ai_service(self):
        return AIService.create(
            self.ai_service_type,
            self.api_key,
            model=self.model,
        )


class PromptBasedCommand(AICommand):
    """Base class for commands that use AI with a prompt template."""

    # Set to True if command requires non-empty input
    require_input = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from kwark.util import load_prompt
        self.prompt = load_prompt(self.name)

    @KwarkCommand.wrap
    def execute(self):

        input_text = self.app.stream.text

        # Validate input if required
        if self.require_input and not input_text.strip():
            self.status = "Error: No input text provided"
            return ""

        # Format prompt and query AI
        formatted_prompt = self.prompt.format(text=input_text)
        response = self.ai_service.ask(formatted_prompt).strip()

        # Set status message
        self.status = getattr(
            self, 'success_message', f"Generated {self.name} " +
            f"from {self.get_input_type()}")

        return response

    def get_input_type(self):
        """Override this to customize the input type in status messages."""
        return "input text"


class NullCommand(KwarkCommand):

    name = 'null'
