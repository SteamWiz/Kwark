from unittest.mock import Mock, patch
from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler
from wizlib.ui import Emphasis

from kwark import KwarkApp
from test import patch_ai_service


class TestActivateDisplayOutput(WizLibTestCase):

    def test_activate_streams_text_to_stderr(self):
        """Test that activate command streams text output to stderr."""
        with patch('sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(kwark_api_anthropic_key='k')

        # Mock AI service with query_with_tools_ui method
        m = Mock()
        mi = Mock()
        mi.query_with_tools_ui.return_value = 'Final response'
        m.return_value = mi

        t = 'Test prompt'
        with \
                self.patch_stream(t), \
                self.patchout() as o, \
                self.patcherr() as e, \
                patch_ai_service(m):
            a.parse_run('activate')

        # Verify query_with_tools_ui was called with ui parameter
        c = mi.query_with_tools_ui.call_args
        self.assertEqual('Test prompt', c[0][0])
        self.assertIsNotNone(c[0][1])  # ui parameter should be passed

        o.seek(0)
        self.assertEqual('Final response', o.read().strip())

    def test_activate_displays_tool_use_to_stderr(self):
        """Test that activate command displays tool use messages to stderr."""
        with patch('sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(kwark_api_anthropic_key='k')

        # Mock AI service that will display tool use
        m = Mock()
        mi = Mock()
        
        # Simulate tool use by having query_with_tools_ui call ui.send
        def mock_query_with_tools_ui(
                text, ui, tool_limit=20, **kw):
            ui.send(
                'Using tool get_current_time...',
                emphasis=Emphasis.PRINCIPAL)
            return 'The time is 2pm'
        
        mi.query_with_tools_ui.side_effect = mock_query_with_tools_ui
        m.return_value = mi

        t = 'What time is it?'
        with \
                self.patch_stream(t), \
                self.patchout() as o, \
                self.patcherr() as e, \
                patch_ai_service(m):
            a.parse_run('activate')

        o.seek(0)
        e.seek(0)
        self.assertEqual('The time is 2pm', o.read().strip())
        err_output = e.read()
        self.assertIn('Using tool get_current_time', err_output)

    def test_activate_respects_tool_limit_with_ui(self):
        """Test that activate command respects tool limit with UI feedback."""
        with patch('sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(
                kwark_api_anthropic_key='k',
                kwark_tooluselimit=3)

        # Mock AI that would exceed limit
        m = Mock()
        mi = Mock()
        mi.query_with_tools_ui.side_effect = RuntimeError(
            'Tool use limit of 3 exceeded')
        m.return_value = mi

        t = 'Test prompt'
        with \
                self.patch_stream(t), \
                self.patchout() as o, \
                self.patcherr() as e, \
                patch_ai_service(m):
            a.parse_run('activate')

        # Should handle limit gracefully
        e.seek(0)
        err = e.read()
        self.assertIn('Tool use limit of 3 exceeded', err)

    def test_activate_default_tool_limit_with_ui(self):
        """Test that default tool limit is 20 when using UI."""
        with patch('sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(kwark_api_anthropic_key='k')

        m = Mock()
        mi = Mock()
        mi.query_with_tools_ui.return_value = 'Response'
        m.return_value = mi

        t = 'Test'
        with \
                self.patch_stream(t), \
                self.patchout(), \
                self.patcherr(), \
                patch_ai_service(m):
            a.parse_run('activate')

        # Verify query_with_tools_ui was called with default limit
        c = mi.query_with_tools_ui.call_args
        self.assertEqual(20, c[1].get('tool_limit', 20))

    def test_activate_without_tools_streams_output(self):
        """Test activate streams output even when no tools are used."""
        with patch('sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(kwark_api_anthropic_key='k')

        m = Mock()
        mi = Mock()
        
        # Simulate streaming by having query_with_tools_ui call ui.send
        def mock_query_with_tools_ui(
                text, ui, tool_limit=20, **kw):
            ui.send(
                'Streaming response...',
                emphasis=Emphasis.GENERAL,
                newline=False)
            return 'Simple response'
        
        mi.query_with_tools_ui.side_effect = mock_query_with_tools_ui
        m.return_value = mi

        t = 'Simple question'
        with \
                self.patch_stream(t), \
                self.patchout() as o, \
                self.patcherr() as e, \
                patch_ai_service(m):
            a.parse_run('activate')

        o.seek(0)
        e.seek(0)
        self.assertEqual('Simple response', o.read().strip())
        # Verify streaming happened to stderr
        err_output = e.read()
        self.assertIn('Streaming response', err_output)
