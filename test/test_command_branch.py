from unittest.mock import Mock, patch
from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler

from kwark import KwarkApp
from test import patch_ai_service


class TestBranchCommand(WizLibTestCase):

    def test_empty_input(self):
        app = KwarkApp()
        app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')
        with \
                self.patch_stream(''), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service():
            app.parse_run('branch')

        out.seek(0)
        err.seek(0)
        self.assertEqual('', out.read().strip())  # No output for empty input
        self.assertIn('Error: No input text provided', err.read())

    def test_with_input(self):
        app = KwarkApp()
        app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')

        # Create a custom MockAI that returns a specific branch name
        custom_mock_ai = Mock()
        branch_name = "20250324-system-users-entry-database"
        custom_mock_ai().ask.return_value = branch_name

        input_text = ('Build a new system to load Users upon entry '
                      'into the Database')
        with \
                self.patch_stream(input_text), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service(custom_mock_ai):
            app.parse_run('branch')

        out.seek(0)
        err.seek(0)
        self.assertEqual(
            branch_name,
            out.read().strip())
        self.assertIn(
            'Generated branch name from input text',
            err.read())
