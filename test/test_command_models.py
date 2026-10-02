from unittest.mock import Mock, patch
import yaml
from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler

from kwark import KwarkApp
from test import MockAI


class TestModelsCommand(WizLibTestCase):

    def test_models_command_with_api_key(self):
        app = KwarkApp()
        app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')

        # Create a custom MockAI that returns a list of models
        custom_mock_ai = Mock()
        mock_models = [
            {'id': 'claude-3-5-sonnet-20241022',
                'display_name': 'Claude 3.5 Sonnet',
                'created_at': '2024-10-22'},
            {'id': 'claude-3-haiku-20240307',
                'display_name': 'Claude 3 Haiku',
                'created_at': '2024-03-07'},
            {'id': 'claude-3-opus-20240229',
                'display_name': 'Claude 3 Opus',
                'created_at': '2024-02-29'}
        ]
        custom_mock_ai().available_models = mock_models

        with \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch('kwark.command.models_command.AnthropicAIService', custom_mock_ai):
            app.parse_run('models')

        out.seek(0)
        err.seek(0)
        output = out.read().strip()

        # Parse YAML output and check structure
        parsed_output = yaml.safe_load(output)

        # Should be a list of model dictionaries
        self.assertIsInstance(parsed_output, list)
        self.assertEqual(len(parsed_output), 3)

        # Check each model has expected structure
        for model in parsed_output:
            self.assertIsInstance(model, dict)
            self.assertIn('id', model)
            self.assertIn('display_name', model)
            self.assertIn('created_at', model)

        # Check specific models are present
        model_ids = [model['id'] for model in parsed_output]
        self.assertIn('claude-3-5-sonnet-20241022', model_ids)
        self.assertIn('claude-3-haiku-20240307', model_ids)
        self.assertIn('claude-3-opus-20240229', model_ids)

        self.assertIn('Retrieved available models', err.read())

    def test_models_command_without_api_key(self):
        app = KwarkApp()
        app.config = ConfigHandler.fake()

        # Create a custom MockAI that returns empty models when no API key
        custom_mock_ai = Mock()
        custom_mock_ai().available_models = []

        with \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch('kwark.command.models_command.AnthropicAIService', custom_mock_ai):
            app.parse_run('models')

        out.seek(0)
        err.seek(0)
        output = out.read().strip()

        # Parse YAML output - should be empty list
        parsed_output = yaml.safe_load(output)
        self.assertIsInstance(parsed_output, list)
        self.assertEqual(len(parsed_output), 0)

        self.assertIn('Retrieved available models', err.read())
