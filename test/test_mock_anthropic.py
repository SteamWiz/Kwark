"""
Demonstration tests for MockAnthropicAPI usage.

These tests show how to use the MockAnthropicAPI mock from test.mocks
to test code that uses the Anthropic API.
"""
from wizlib.test_case import WizLibTestCase

from kwark.ai_services.anthropic_ai_service import AnthropicAIService
from test.mocks.mock_anthropic_sdk import MockAnthropicSDK


class TestMockAnthropicAPI(WizLibTestCase):
    """Tests demonstrating MockAnthropicAPI usage"""

    # def test_basic_usage(self):
    #     """Basic usage: patch and create AI instance"""
    #     with MockAnthropicSDK.patch():
    #         ai = AnthropicAIService(api_key='test-key')
    #         result = ai.query('What is 2+2?')
        
    #     self.assertEqual("Mock AI response", result)

    # def test_custom_response(self):
    #     """Customize the response for specific test needs"""
    #     with MockAnthropicSDK.patch():
    #         ai = AnthropicAIService(api_key='test-key')
    #         # Customize response after initialization
    #         ai.client.messages.default_response = "Custom answer: 4"
    #         result = ai.query('What is 2+2?')
        
        # self.assertEqual("Custom answer: 4", result)

    def test_models_list(self):
        """Test that model listing works"""
        with MockAnthropicSDK.patch():
            ai = AnthropicAIService(api_key='test-key')
        
        # Check that models were fetched
        self.assertIsNotNone(ai.available_models)
        self.assertGreater(len(ai.available_models), 0)
        
        # Check that the default model is in the list
        model_ids = [m['id'] for m in ai.available_models]
        self.assertIn('claude-sonnet-5', model_ids)

    def test_streaming_response(self):
        """Test streaming chat response"""
        from unittest.mock import Mock
        
        with MockAnthropicSDK.patch():
            ai = AnthropicAIService(api_key='test-key')
            # Customize streaming response
            ai.client.messages.default_stream_response = "Streamed response"
            
            ui = Mock()
            ui.get_text.return_value = 'quit'
            
            ai.chat(ui)
        
        # Verify streaming was called
        self.assertTrue(ui.send.called)

    # def test_query_with_different_model(self):
    #     """Test querying with a specific model"""
    #     with MockAnthropicSDK.patch():
    #         ai = AnthropicAIService(api_key='test-key')
    #         # Customize response
    #         ai.client.messages.default_response = "Opus response"
    #         result = ai.query('test', model='claude-opus-4-5-20251022')
        
    #     self.assertEqual("Opus response", result)
