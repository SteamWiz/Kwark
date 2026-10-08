import yaml

import kwark.ai
from kwark.ai import KwarkAIError
from kwark.command import AICommand, KwarkUsageError
from wizlib.parser import WizParser


class ExtractCommand(AICommand):
    """Extract structured data from text on stdin using kwark.ai.extract,
    with a JSON Schema loaded from a YAML or JSON file, and write the result
    to stdout as YAML.

    Example:
        cat note.md | kwark extract -S schema.yaml -i 'Extract the contact'
    """

    name = 'extract'
    default_model = 'claude-haiku-4-5'

    @classmethod
    def add_args(cls, parser: WizParser):
        super().add_args(parser)
        # Not required=True so that 'kwark extract --help' works; checked in
        # handle_vals (see KwarkUsageError)
        parser.add_argument('--schema', '-S')
        parser.add_argument('--instructions', '-i')

    def handle_vals(self):
        if not self.provided('schema'):
            raise KwarkUsageError('--schema/-S is required')
        # Check before super(), which fills model from the general kwark-model
        model_provided = self.provided('model')
        super().handle_vals()
        # Explicit chain for extract: --model, then kwark-extract-model, then
        # the class default (the general kwark-model is not used)
        if not model_provided:
            self.model = (
                self.app.config.get('kwark-extract-model')
                or self.default_model
            )

    def load_schema(self):
        """Load the schema file. Valid JSON is also YAML, so one loader
        handles both formats. Raise KwarkAIError for anything unusable."""
        try:
            with open(self.schema, encoding='utf-8') as file:
                schema = yaml.safe_load(file)
        except OSError as error:
            raise KwarkAIError(
                f"Can't read schema file '{self.schema}': {error}"
            ) from error
        except yaml.YAMLError as error:
            raise KwarkAIError(
                f"Invalid YAML/JSON in schema file '{self.schema}': {error}"
            ) from error
        if not isinstance(schema, dict):
            raise KwarkAIError(
                f"Schema file '{self.schema}' must contain a mapping")
        return schema

    @AICommand.wrap
    def execute(self):
        # KwarkAIError propagates: WizApp.start prints it to stderr and exits
        # with status 1, so nothing but the YAML reaches stdout
        schema = self.load_schema()
        text = self.app.stream.text
        if not text or not text.strip():
            raise KwarkAIError("No input text provided on stdin")
        result = kwark.ai.extract(
            text, schema,
            instructions=self.instructions or None,
            model=self.model,
            api_key=self.api_key or None)
        return yaml.safe_dump(result, sort_keys=False, allow_unicode=True,
                              default_flow_style=False)
