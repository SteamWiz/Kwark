"""Kwark must work without the optional mcp package (kwark[mcp])"""
import importlib
import sys
from unittest.mock import patch

from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler


# Setting a sys.modules entry to None makes any import of it raise
# ImportError, which simulates mcp not being installed.
BLOCKED_MCP_MODULES = {
    'mcp': None,
    'mcp.client': None,
    'mcp.client.stdio': None,
    'mcp.types': None,
}

MOCK_AI_SERVICE = 'kwark.ai_services.AIService.create'


class MockAI:

    def __init__(self, *args, **kwargs):
        pass

    def ask(self, text):
        return "Mock AI response"

    def chat(self, ui, *args, **kwargs):
        pass

    def query_with_tools_ui(self, prompt, ui, **kwargs):
        return "Mock tool response"


class TestMCPOptionalExtra(WizLibTestCase):

    def setUp(self):
        # Restore the whole of sys.modules after each test, so the fresh
        # mcp-less kwark modules don't leak into other tests
        self.modules_patch = patch.dict(sys.modules)
        self.modules_patch.start()
        for name in list(sys.modules):
            if name == 'kwark' or name.startswith('kwark.') or \
                    name == 'mcp' or name.startswith('mcp.'):
                del sys.modules[name]
        sys.modules.update(BLOCKED_MCP_MODULES)

    def tearDown(self):
        self.modules_patch.stop()

    def new_app(self, **config):
        kwark = importlib.import_module('kwark')
        kwark.KwarkApp.initialize()
        with patch('sys.stdin.isatty', return_value=True):
            app = kwark.KwarkApp()
            app.config = ConfigHandler.fake(
                kwark_api_anthropic_key='fake-api-key', **config)
        return app

    def test_mcp_is_blocked(self):
        with self.assertRaises(ImportError):
            import mcp  # noqa: F401

    def test_import_kwark_without_mcp(self):
        kwark = importlib.import_module('kwark')
        self.assertTrue(hasattr(kwark, 'KwarkApp'))
        mcp_client = importlib.import_module('kwark.ai_services.mcp_client')
        self.assertFalse(mcp_client.mcp_available())
        self.assertIsNone(mcp_client.stdio_client)

    def test_ai_service_family_loads_without_mcp(self):
        # ClassFamily imports every module in kwark.ai_services,
        # including mcp_client
        importlib.import_module('kwark')
        ai_services = importlib.import_module('kwark.ai_services')
        service = ai_services.AIService.create('anthropic', 'fake-key')
        self.assertEqual('anthropic', service.service_type)

    def test_non_mcp_command_runs_without_mcp(self):
        app = self.new_app()
        with \
                self.patch_stream('some diff'), \
                self.patchout() as out, \
                patch(MOCK_AI_SERVICE, lambda *a, **k: MockAI()):
            app.parse_run('commit')
        out.seek(0)
        self.assertEqual('Mock AI response', out.read().strip())

    def test_activate_without_mcp_servers_runs(self):
        app = self.new_app()
        with \
                self.patch_stream('prompt: Hello'), \
                self.patchout() as out, \
                patch(MOCK_AI_SERVICE, lambda *a, **k: MockAI()):
            app.parse_run('activate')
        out.seek(0)
        self.assertEqual('Mock tool response', out.read().strip())

    def test_activate_with_config_mcp_fails_clearly(self):
        app = self.new_app(kwark_mcp=['python server.py'])
        with \
                self.patch_stream('prompt: Hello'), \
                self.patchout(), \
                patch(MOCK_AI_SERVICE, lambda *a, **k: MockAI()):
            with self.assertRaises(RuntimeError) as ctx:
                app.parse_run('activate')
        self.assertIn("kwark[mcp]", str(ctx.exception))
        self.assertIn("'mcp' package is not installed", str(ctx.exception))

    def test_activate_with_input_mcp_fails_clearly(self):
        app = self.new_app()
        yaml_input = "prompt: Hello\nmcp:\n  - python server.py\n"
        with \
                self.patch_stream(yaml_input), \
                self.patchout(), \
                patch(MOCK_AI_SERVICE, lambda *a, **k: MockAI()):
            with self.assertRaises(RuntimeError) as ctx:
                app.parse_run('activate')
        self.assertIn("kwark[mcp]", str(ctx.exception))

    def test_chat_with_mcp_fails_clearly(self):
        app = self.new_app(kwark_mcp=['python server.py'])
        with \
                self.patch_stream('prompt: Hello'), \
                self.patchout(), \
                patch(MOCK_AI_SERVICE, lambda *a, **k: MockAI()):
            with self.assertRaises(RuntimeError) as ctx:
                app.parse_run('chat')
        self.assertIn("kwark[mcp]", str(ctx.exception))

    def test_start_exits_nonzero_with_message(self):
        kwark = importlib.import_module('kwark')
        with \
                self.patch_stream('prompt: Hello\nmcp:\n  - python s.py\n'), \
                self.patchout(), \
                self.patcherr() as err, \
                patch('sys.stdin.isatty', return_value=True), \
                patch(MOCK_AI_SERVICE, lambda *a, **k: MockAI()):
            with self.assertRaises(SystemExit) as ctx:
                kwark.KwarkApp.start('activate', '--api-key', 'fake')
        self.assertEqual(1, ctx.exception.code)
        err.seek(0)
        self.assertIn("kwark[mcp]", err.read())


class TestMCPAvailable(WizLibTestCase):

    def test_require_mcp_passes_when_installed(self):
        from kwark.ai_services import mcp_client
        self.assertTrue(mcp_client.mcp_available())
        mcp_client.require_mcp()
