import unittest
from unittest.mock import patch, call
from wizlib.test_case import WizLibTestCase

from kwark.ai_services.anthropic_ai_service import AnthropicAIService
from test.mocks.mock_anthropic_sdk import MockAnthropicSDK


class TestRemoveAnthropicTemperatureParameter(WizLibTestCase):

    def test_temperature_not_in_base_arguments(self):
        """_base_arguments does not include temperature."""
        with MockAnthropicSDK.patch():
            ai = AnthropicAIService(api_key='k')
        from kwark.ai_services.anthropic_ai_service import (
            AnthropicMessagesBlock)
        msgs = AnthropicMessagesBlock()
        msgs.user_says('hi')
        args = ai._base_arguments(msgs)
        self.assertNotIn('temperature', args)

    def test_api_arguments_do_not_include_temperature(self):
        """_api_arguments does not include temperature."""
        with MockAnthropicSDK.patch():
            ai = AnthropicAIService(api_key='k')
        from kwark.ai_services.anthropic_ai_service import (
            AnthropicMessagesBlock)
        msgs = AnthropicMessagesBlock()
        msgs.user_says('hi')
        args = ai._api_arguments(msgs)
        self.assertNotIn('temperature', args)

    def test_default_temperature_constant_removed(self):
        """DEFAULT_TEMPERATURE constant no longer exists in the module."""
        import kwark.ai_services.anthropic_ai_service as m
        self.assertFalse(hasattr(m, 'DEFAULT_TEMPERATURE'))


if __name__ == '__main__':
    unittest.main()
