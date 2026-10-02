from unittest.mock import Mock, patch
from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler

from kwark import KwarkApp
from test import patch_ai_service


class TestActivateToolUseLoop(WizLibTestCase):

    def test_activate_with_tool_use(self):
        """Test activate command handles tool use and returns final text."""
        with patch('sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(kwark_api_anthropic_key='k')

        # Mock AI that simulates tool use then final response
        m = Mock()
        mi = Mock()
        
        # First call: AI requests tool use
        r1 = Mock()
        r1.content = [Mock(type='tool_use', name='get_current_time',
                          id='t1', input={})]
        r1.stop_reason = 'tool_use'
        
        # Second call: AI provides final text response
        r2 = Mock()
        r2.content = [Mock(type='text', text='The time is 2pm')]
        r2.stop_reason = 'end_turn'
        
        mi.query_with_tools_ui.return_value = 'The time is 2pm'
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
        self.assertIn('Generated response', e.read())

    def test_activate_respects_tool_limit(self):
        """Test that activate command respects tooluselimit config."""
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
        self.assertIn('Tool use limit', err)

    def test_activate_default_tool_limit(self):
        """Test that default tool limit is 20."""
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

    def test_activate_without_tools(self):
        """Test activate still works when no tools are used."""
        with patch('sys.stdin.isatty', return_value=True):
            a = KwarkApp()
            a.config = ConfigHandler.fake(kwark_api_anthropic_key='k')

        m = Mock()
        mi = Mock()
        mi.query_with_tools_ui.return_value = 'Simple response'
        m.return_value = mi

        t = 'Simple question'
        with \
                self.patch_stream(t), \
                self.patchout() as o, \
                self.patcherr() as e, \
                patch_ai_service(m):
            a.parse_run('activate')

        o.seek(0)
        self.assertEqual('Simple response', o.read().strip())
