from unittest.mock import patch
from kwark import KwarkApp


KwarkApp.initialize()


AI_SERVICE_FACTORY_METHOD = 'kwark.ai_services.AIService.create'

class MockAI:

    def __init__(self, *args, **kwargs):
        pass

    def ask(self, text):
        return f"Mock AI response"
    
    def chat(self, ui, *args, **kwargs):
        pass

def patch_ai_service(custom_mock_ai_service=None):
    def mock_factory(*args, **kwargs):
        if custom_mock_ai_service:
            return custom_mock_ai_service()
        else:
            return MockAI()
    return patch(AI_SERVICE_FACTORY_METHOD, mock_factory)

