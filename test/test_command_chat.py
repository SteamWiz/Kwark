from unittest.mock import Mock, patch
from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler

from kwark import KwarkApp
from test import MockAI, patch_ai_service


class TestChatCommand(WizLibTestCase):

    def test_empty_input(self):
        app = KwarkApp()
        app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')

        # Mock the AI chat method to avoid actual chat interaction
        mock_ai = Mock()
        mock_ai_instance = Mock()
        mock_ai.return_value = mock_ai_instance

        with \
                self.patch_stream(''), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service(mock_ai):
            app.parse_run('chat')

        out.seek(0)
        err.seek(0)
        self.assertEqual('', out.read().strip())  # No output for empty input
        self.assertIn('Chat session completed', err.read())

        # Verify chat was called with UI and no initial message
        mock_ai_instance.chat.assert_called_once_with(
            app.ui, initial_message=None)

    def test_with_input(self):
        app = KwarkApp()
        app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')

        # Mock the AI chat method to avoid actual chat interaction
        mock_ai = Mock()
        mock_ai_instance = Mock()
        mock_ai.return_value = mock_ai_instance

        input_text = 'Hello, how are you?'
        with \
                self.patch_stream(input_text), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service(mock_ai) as xx:
            app.parse_run('chat')

        out.seek(0)
        err.seek(0)
        self.assertEqual('', out.read().strip())  # No output for empty input
        self.assertIn('Chat session completed', err.read())

        # Verify chat was called with UI and the input text as initial message
        mock_ai_instance.chat.assert_called_once_with(
            app.ui, initial_message=input_text)

    def test_with_mcp_servers_in_yaml(self):
        """Test chat command with MCP servers in YAML input."""
        app = KwarkApp()
        app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')

        mock_ai = Mock()
        mock_ai_instance = Mock()
        mock_ai.return_value = mock_ai_instance

        yaml_input = """prompt: Test chat
mcp_servers:
  - command: python
    args: [test/minimal_mcp_server.py]"""
        
        with \
                self.patch_stream(yaml_input), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service(mock_ai):
            app.parse_run('chat')

        # Verify chat was called
        mock_ai_instance.chat.assert_called_once()

    def test_with_mcp_servers_in_config(self):
        """Test chat command with MCP servers in config."""
        app = KwarkApp()
        app.config = ConfigHandler.fake(
            kwark_api_anthropic_key='fake-api-key',
            kwark_mcp=['python test/minimal_mcp_server.py'])

        mock_ai = Mock()
        mock_ai_instance = Mock()
        mock_ai.return_value = mock_ai_instance

        yaml_input = """prompt: Test chat"""
        
        with \
                self.patch_stream(yaml_input), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service(mock_ai):
            app.parse_run('chat')

        # Verify chat was called
        mock_ai_instance.chat.assert_called_once()


