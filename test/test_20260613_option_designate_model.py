import unittest
from unittest.mock import Mock, patch, call
from wizlib.test_case import WizLibTestCase
from wizlib.config_handler import ConfigHandler

from kwark import KwarkApp
from test import patch_ai_service, AI_SERVICE_FACTORY_METHOD


class TestOptionDesignateModel(WizLibTestCase):

    def _make_app(self, model=None):
        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            kw = dict(kwark_api_anthropic_key='k')
            if model:
                kw['kwark_model'] = model
            app.config = ConfigHandler.fake(**kw)
        return app

    # --- commit (PromptBasedCommand) ---

    def test_commit_passes_model_to_factory(self):
        """--model is forwarded to AIService.create for commit."""
        m = Mock()
        m().ask.return_value = 'msg'
        with \
                self.patch_stream('diff'), \
                self.patchout(), \
                self.patcherr(), \
                patch(AI_SERVICE_FACTORY_METHOD, m):
            self._make_app().parse_run(
                'commit', '--model', 'claude-test-1')
        self.assertEqual(
            'claude-test-1', m.call_args[1]['model'])

    def test_commit_no_model_option_uses_none(self):
        """Without --model, model=None is passed to factory."""
        m = Mock()
        m().ask.return_value = 'msg'
        with \
                self.patch_stream('diff'), \
                self.patchout(), \
                self.patcherr(), \
                patch(AI_SERVICE_FACTORY_METHOD, m):
            self._make_app().parse_run('commit')
        self.assertIsNone(m.call_args[1]['model'])

    # --- branch ---

    def test_branch_passes_model_to_factory(self):
        """--model is forwarded to AIService.create for branch."""
        m = Mock()
        m().ask.return_value = '20260613-foo'
        with \
                self.patch_stream('add a thing'), \
                self.patchout(), \
                self.patcherr(), \
                patch(AI_SERVICE_FACTORY_METHOD, m):
            self._make_app().parse_run(
                'branch', '--model', 'my-model')
        self.assertEqual('my-model', m.call_args[1]['model'])

    # --- doc ---

    def test_doc_passes_model_to_factory(self):
        """--model is forwarded to AIService.create for doc."""
        m = Mock()
        m().ask.return_value = 'summary'
        with \
                self.patch_stream('some text'), \
                self.patchout(), \
                self.patcherr(), \
                patch(AI_SERVICE_FACTORY_METHOD, m):
            self._make_app().parse_run(
                'doc', '--model', 'my-model')
        self.assertEqual('my-model', m.call_args[1]['model'])

    # --- activate ---

    def test_activate_passes_model_to_factory(self):
        """--model is forwarded to AIService.create for activate."""
        m = Mock()
        m().query_with_tools_ui.return_value = 'resp'
        with \
                self.patch_stream('prompt: hello'), \
                self.patchout(), \
                self.patcherr(), \
                patch(AI_SERVICE_FACTORY_METHOD, m):
            self._make_app().parse_run(
                'activate', '--model', 'my-model')
        self.assertEqual('my-model', m.call_args[1]['model'])

    # --- chat ---

    def test_chat_passes_model_to_factory(self):
        """--model is forwarded to AIService.create for chat."""
        m = Mock()
        m().chat.return_value = None
        with \
                self.patch_stream(''), \
                self.patchout(), \
                self.patcherr(), \
                patch(AI_SERVICE_FACTORY_METHOD, m):
            self._make_app().parse_run(
                'chat', '--model', 'my-model')
        self.assertEqual('my-model', m.call_args[1]['model'])

    # --- models (excluded) ---

    def test_models_command_has_no_model_option(self):
        """The models command does not accept --model."""
        from argparse import ArgumentError
        with \
                self.patch_stream(''), \
                self.patchout(), \
                self.patcherr(), \
                patch_ai_service():
            with self.assertRaises(ArgumentError):
                self._make_app().parse_run(
                    'models', '--model', 'x')


if __name__ == '__main__':
    unittest.main()
