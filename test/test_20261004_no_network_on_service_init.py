import unittest
from unittest.mock import Mock, patch

import yaml
from wizlib.config_handler import ConfigHandler
from wizlib.test_case import WizLibTestCase

from kwark import KwarkApp
from kwark.ai_services.anthropic_ai_service import (
    DEFAULT_MODEL, AnthropicAIService)
from test.mocks.mock_anthropic_sdk import MockAnthropicSDK


class TestNoNetworkOnServiceInit(WizLibTestCase):

    def test_construction_makes_no_api_calls(self):
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK',
                   Mock()) as m:
            ai = AnthropicAIService(api_key='k', model='claude-test-1')
        m().models.list.assert_not_called()
        m().messages.create.assert_not_called()
        m().messages.stream.assert_not_called()
        m().beta.files.upload.assert_not_called()
        self.assertIn('claude-test-1', ai.system_prompt)

    def test_system_prompt_uses_default_model_id(self):
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK',
                   Mock()) as m:
            ai = AnthropicAIService(api_key='k')
        m().models.list.assert_not_called()
        self.assertIn(DEFAULT_MODEL, ai.system_prompt)

    def test_available_models_calls_list_once(self):
        with MockAnthropicSDK.patch():
            ai = AnthropicAIService(api_key='k')
        ai.client.models.list = Mock(
            wraps=ai.client.models.list)
        models = ai.available_models
        ai.available_models
        ai.client.models.list.assert_called_once()
        self.assertIn('claude-sonnet-5', [m['id'] for m in models])
        for model in models:
            self.assertEqual(
                {'id', 'display_name', 'created_at'}, set(model))

    def test_models_command_lists_models(self):
        app = KwarkApp()
        app.config = ConfigHandler.fake(kwark_api_anthropic_key='k')
        with \
                self.patchout() as out, \
                self.patcherr() as err, \
                MockAnthropicSDK.patch():
            app.parse_run('models')
        out.seek(0)
        err.seek(0)
        ids = [m['id'] for m in yaml.safe_load(out.read())]
        self.assertIn('claude-sonnet-5', ids)
        self.assertIn('claude-haiku-4-5-20251001', ids)
        self.assertIn('Retrieved available models', err.read())


if __name__ == '__main__':
    unittest.main()
