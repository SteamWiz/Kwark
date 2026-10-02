from unittest.mock import Mock, patch
from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler

from kwark import KwarkApp
from test import MockAI, patch_ai_service


class TestCommitCommand(WizLibTestCase):

    def test_empty_input(self):
        app = KwarkApp()
        app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')

        # Create a custom MockAI that returns a dot for empty input
        custom_mock_ai = Mock()
        custom_mock_ai().ask.return_value = "."

        with \
                self.patch_stream(''), \
                self.patchout() as out, \
               self.patcherr() as err, \
               patch_ai_service(custom_mock_ai):
            app.parse_run('commit')

        out.seek(0)
        err.seek(0)
        self.assertEqual('.', out.read().strip())  # A dot for empty input
        self.assertIn('Generated commit message from diff', err.read())

    def test_with_input(self):
        app = KwarkApp()
        app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')

        # Create a custom MockAI that returns a specific commit message
        custom_mock_ai = Mock()
        commit_message = "Add user authentication feature"
        custom_mock_ai().ask.return_value = commit_message

        input_text = ('diff --git a/auth.py b/auth.py\n'
                      'index 1234567..abcdefg 100644\n'
                      '--- a/auth.py\n'
                      '+++ b/auth.py\n'
                      '@@ -10,6 +10,15 @@\n'
                      ' def login(username, password):\n'
                      '     # Existing login code\n'
                      '     pass\n'
                      '+\n'
                      '+def authenticate_user(token):\n'
                      '+    """Authenticate a user with a token"""\n'
                      '+    # Verify token\n'
                      '+    # Check expiration\n'
                      '+    # Return user info\n'
                      '+    return {"authenticated": True}\n')

        with \
                self.patch_stream(input_text), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service(custom_mock_ai):
            app.parse_run('commit')

        out.seek(0)
        err.seek(0)
        self.assertEqual(
            commit_message,
            out.read().strip())
        self.assertIn(
            'Generated commit message from diff',
            err.read())
