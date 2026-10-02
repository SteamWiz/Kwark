from unittest.mock import Mock, patch
from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler

from kwark import KwarkApp
from test import patch_ai_service


class TestActivateCommand(WizLibTestCase):

    def test_empty_input(self):
        """Test that activate command requires input text."""
        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')
        with \
                self.patch_stream(''), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service():
            app.parse_run('activate')

        out.seek(0)
        err.seek(0)
        self.assertEqual('', out.read().strip())  # No output for empty input
        self.assertIn('Error: No prompt text provided', err.read())



    def test_with_yaml_prompt(self):
        """Test activate command with YAML-formatted prompt."""
        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')

        custom_mock_ai = Mock()
        expected_response = "The capital is Paris."
        custom_mock_ai().query_with_tools_ui.return_value = expected_response

        yaml_input = """prompt: What is the capital of France?"""
        with \
                self.patch_stream(yaml_input), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service(custom_mock_ai):
            app.parse_run('activate')

        out.seek(0)
        err.seek(0)
        self.assertEqual(expected_response, out.read().strip())
        
        # Verify the prompt was extracted from YAML
        c = custom_mock_ai().query_with_tools_ui.call_args
        self.assertEqual("What is the capital of France?", c[0][0])

    def test_yaml_without_prompt_fails(self):
        """Test that activate command fails when YAML has no prompt."""
        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')

        yaml_input = """other:
  - value"""
        
        with \
                self.patch_stream(yaml_input), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service():
            app.parse_run('activate')

        out.seek(0)
        err.seek(0)
        self.assertEqual('', out.read().strip())
        self.assertIn('Error: No prompt text provided', err.read())

    def test_with_mcp_servers_in_yaml(self):
        """Test activate command with MCP servers in YAML input."""
        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake-api-key')

        custom_mock_ai = Mock()
        expected_response = "MCP response"
        custom_mock_ai().query_with_tools_ui.return_value = expected_response

        yaml_input = """prompt: Test prompt
mcp_servers:
  - command: python
    args: [test/minimal_mcp_server.py]"""
        
        with \
                self.patch_stream(yaml_input), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service(custom_mock_ai):
            app.parse_run('activate')

        out.seek(0)
        self.assertEqual(expected_response, out.read().strip())

    def test_with_mcp_servers_in_config(self):
        """Test activate command with MCP servers in config."""
        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            app.config = ConfigHandler.fake(
                kwark_api_anthropic_key='fake-api-key',
                kwark_mcp=['python test/minimal_mcp_server.py'])

        custom_mock_ai = Mock()
        expected_response = "MCP config response"
        custom_mock_ai().query_with_tools_ui.return_value = expected_response

        yaml_input = """prompt: Test prompt"""
        
        with \
                self.patch_stream(yaml_input), \
                self.patchout() as out, \
                self.patcherr() as err, \
                patch_ai_service(custom_mock_ai):
            app.parse_run('activate')

        out.seek(0)
        self.assertEqual(expected_response, out.read().strip())
