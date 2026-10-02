from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class MockModel:
    """Mock for an Anthropic model object"""
    
    def __init__(self, model_id, display_name=None, created_at=None):
        self.id = model_id
        self.display_name = display_name or model_id
        self.created_at = created_at or datetime.now().isoformat()


class MockMessage:
    """Mock for an Anthropic message response"""
    
    def __init__(self, text="Mock response", role="assistant"):
        self.role = role
        self.content = [MockTextBlock(text)]
        self.model = "claude-haiku-4-5-20251001"
        self.stop_reason = "end_turn"
        self.usage = {"input_tokens": 10, "output_tokens": 20}


class MockTextBlock:
    """Mock for a text content block"""
    
    def __init__(self, text):
        self.type = "text"
        self.text = text


class MockStreamContext:
    """Mock for the streaming context manager"""
    
    def __init__(self, text="Mock streaming response"):
        self.text = text
        self.text_stream = self._generate_stream()
    
    def _generate_stream(self):
        """Generator that yields text chunks"""
        # Simulate streaming by yielding the text in chunks
        chunk_size = max(1, len(self.text) // 5)
        for i in range(0, len(self.text), chunk_size):
            yield self.text[i:i+chunk_size]
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class MockMessages:
    """Mock for the messages API"""
    
    def __init__(self):
        self.default_response = "Mock AI response"
        self.default_stream_response = "Mock streaming response"
    
    def create(self, model=None, max_tokens=None,
               system=None, messages=None, **kwargs):
        """Mock the messages.create() method"""
        return MockMessage(self.default_response)
    
    def stream(self, model=None, max_tokens=None,
               system=None, messages=None, **kwargs):
        """Mock the messages.stream() method"""
        return MockStreamContext(self.default_stream_response)


class MockModels:
    """Mock for the models API"""
    
    def __init__(self):
        self.available_models = [
            MockModel(
                "claude-haiku-4-5-20251001",
                "Claude 4.5 Haiku",
                "2025-10-01T00:00:00Z"
            ),
            MockModel(
                "claude-sonnet-4-5-20251022",
                "Claude 4.5 Sonnet",
                "2025-10-22T00:00:00Z"
            ),
            MockModel(
                "claude-opus-4-5-20251022",
                "Claude 4.5 Opus",
                "2025-10-22T00:00:00Z"
            ),
        ]
    
    def list(self):
        """Mock the models.list() method"""
        return self.available_models


class MockAnthropicSDK(Mock):
    """
    Mock for the Anthropic SDK.
    
    This mock simulates the Anthropic SDK, including:
    - Model listing (models.list())
    - Message creation (messages.create())
    - Message streaming (messages.stream())
    
    Basic Usage:
        with MockAnthropicAPI.patch():
            ai = AI(api_key='test-key')
            result = ai.ask('test')
            # Returns: "Mock AI response"
    
    Customizing Responses:
        with MockAnthropicAPI.patch():
            ai = AI(api_key='test-key')
            ai.client.messages.default_response = "Custom response"
            result = ai.ask('test')
            # Returns: "Custom response"
    
    Customizing Stream Responses:
        with MockAnthropicAPI.patch():
            ai = AI(api_key='test-key')
            ai.client.messages.default_stream_response = "Streamed text"
            ai.chat(ui, 'Hello')
            # Streams: "Streamed text"
    
    Customizing Model List:
        from test.mocks import MockModel
        
        with MockAnthropicAPI.patch():
            ai = AI(api_key='test-key')
            ai.client.models.available_models = [
                MockModel('test-model', 'Test Model'),
            ]
            ai.available_models = ai._fetch_available_models()
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up the models API
        self.models = MockModels()
        
        # Set up the messages API
        self.messages = MockMessages()
    
    @classmethod
    def patch(cls):
        """Convenience method to patch the Anthropic client."""
        return patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK', cls)
