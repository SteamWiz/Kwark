import unittest
from unittest.mock import Mock
from wizlib.test_case import WizLibTestCase

import kwark.ai_services.anthropic_ai_service as service
from kwark.ai_services.anthropic_ai_service import (
    AnthropicAIService, AnthropicMessagesBlock)
from test.mocks.mock_anthropic_sdk import (
    MockAnthropicSDK, MockMessage, MockTextBlock)


class MockThinkingBlock:
    """Mock for a thinking content block"""

    def __init__(self):
        self.type = "thinking"
        self.thinking = ""
        self.signature = "sig"


class TestDefaultModelSonnet5(WizLibTestCase):

    def _ai(self, model=None):
        with MockAnthropicSDK.patch():
            return AnthropicAIService(api_key='k', model=model)

    @staticmethod
    def _messages():
        msgs = AnthropicMessagesBlock()
        msgs.user_says('hi')
        return msgs

    def test_default_model_is_sonnet_5(self):
        self.assertEqual('claude-sonnet-5', service.DEFAULT_MODEL)
        self.assertEqual('claude-sonnet-5', self._ai().model)

    def test_default_model_disables_thinking(self):
        args = self._ai()._base_arguments(self._messages())
        self.assertEqual({'type': 'disabled'}, args['thinking'])

    def test_streaming_arguments_disable_thinking(self):
        args = self._ai()._api_arguments(self._messages())
        self.assertEqual({'type': 'disabled'}, args['thinking'])

    def test_other_model_does_not_send_thinking(self):
        args = self._ai('claude-test-1')._base_arguments(self._messages())
        self.assertNotIn('thinking', args)

    def test_sonnet_5_5_does_not_send_thinking(self):
        """No prefix match: claude-sonnet-5-5 rejects thinking disabled."""
        args = self._ai('claude-sonnet-5-5')._api_arguments(
            self._messages())
        self.assertNotIn('thinking', args)

    def test_ask_sends_thinking_disabled(self):
        ai = self._ai()
        ai.client.messages.create = Mock(return_value=MockMessage('ok'))
        self.assertEqual('ok', ai.ask('hi'))
        kwargs = ai.client.messages.create.call_args.kwargs
        self.assertEqual('claude-sonnet-5', kwargs['model'])
        self.assertEqual({'type': 'disabled'}, kwargs['thinking'])

    def test_ask_skips_thinking_block(self):
        ai = self._ai('claude-test-1')
        message = MockMessage()
        message.content = [MockThinkingBlock(), MockTextBlock('answer')]
        ai.client.messages.create = Mock(return_value=message)
        self.assertEqual('answer', ai.ask('hi'))

    def test_ask_without_text_block_returns_empty(self):
        ai = self._ai('claude-test-1')
        message = MockMessage()
        message.content = [MockThinkingBlock()]
        ai.client.messages.create = Mock(return_value=message)
        self.assertEqual('', ai.ask('hi'))


if __name__ == '__main__':
    unittest.main()
