from wizlib.class_family import ClassFamily


class AIService(ClassFamily):
    """Abstract base class for AI service implementations"""

    def __init__(self, api_key=None, model=None):
        """Initialize the AI service

        Args:
            api_key: Optional API key for authentication
            model: Optional model identifier to use
        """
        pass

    # @property
    # def available_models(self):
    #     """Return list of available models

    #     Returns:
    #         List of model dictionaries with at least 'id' and 'display_name' keys
    #     """
    #     pass

    def ask(self, text):
        """Send a one-time prompt and return the plain text response.

        No tools are advertised to the model.

        Args:
            text: The prompt text to send

        Returns:
            String response from the AI
        """
        pass

    def chat(self, ui, initial_message=None, model=None):
        """Start an interactive chat session

        Args:
            ui: UI object for input/output
            initial_message: Optional initial message to start the chat
            model: Optional model to override the default
        """
        pass

    @classmethod
    def create(cls, ai_service_type, api_key=None, model=None):
        ai_service_class = cls.family_member(
            'service_type', ai_service_type)
        ai_service = ai_service_class(api_key, model=model)
        return ai_service
