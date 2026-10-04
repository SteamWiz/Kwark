from unittest.mock import Mock, patch, MagicMock
from wizlib.test_case import WizLibTestCase
from wizlib.ui import Emphasis

from kwark.ai_services import AIService
from kwark.ai_services.anthropic_ai_service import (
    AnthropicAIService, AnthropicMessagesBlock, AnthropicToolset
)


class TestAIService(WizLibTestCase):
    """Test AIService base class"""

    def test_create_anthropic_service(self):
        """Test creating an Anthropic AI service via factory"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            service = AIService.create('anthropic', api_key='test-key')
            self.assertIsInstance(service, AnthropicAIService)

    def test_base_init(self):
        """Test AIService base __init__ method"""
        service = AIService(api_key='test', model='test-model')
        # Base init does nothing, just ensure it doesn't raise
        self.assertIsNotNone(service)

    def test_base_ask(self):
        """Test AIService base ask method"""
        service = AIService()
        # Base ask returns None
        result = service.ask('test')
        self.assertIsNone(result)

    def test_base_chat(self):
        """Test AIService base chat method"""
        service = AIService()
        ui = Mock()
        # Base chat returns None
        result = service.chat(ui, initial_message='test')
        self.assertIsNone(result)


class TestAnthropicMessagesBlock(WizLibTestCase):
    """Test AnthropicMessagesBlock"""

    def test_user_says(self):
        """Test adding user message"""
        block = AnthropicMessagesBlock()
        block.user_says("Hello")
        self.assertEqual(len(block.data), 1)
        self.assertEqual(block.data[0]['role'], 'user')
        self.assertEqual(block.data[0]['content'], 'Hello')

    def test_model_says_with_string(self):
        """Test adding model message with string content"""
        block = AnthropicMessagesBlock()
        block.model_says("Response")
        self.assertEqual(len(block.data), 1)
        self.assertEqual(block.data[0]['role'], 'assistant')
        self.assertEqual(block.data[0]['content'], [{"type": "text", "text": "Response"}])

    def test_model_says_with_dict(self):
        """Test adding model message with dict content"""
        block = AnthropicMessagesBlock()
        content = {"type": "text", "text": "Response"}
        block.model_says(content)
        self.assertEqual(len(block.data), 1)
        self.assertEqual(block.data[0]['role'], 'assistant')
        self.assertEqual(block.data[0]['content'], [content])

    def test_tool_says(self):
        """Test adding tool result"""
        block = AnthropicMessagesBlock()
        block.tool_says("tool-123", "Tool result")
        self.assertEqual(len(block.data), 1)
        self.assertEqual(block.data[0]['role'], 'user')
        self.assertEqual(block.data[0]['content'][0]['type'], 'tool_result')
        self.assertEqual(block.data[0]['content'][0]['tool_use_id'], 'tool-123')

    def test_need_user_input(self):
        """Test checking if user input is needed"""
        block = AnthropicMessagesBlock()
        block.user_says("Hello")
        self.assertFalse(block.need_user_input())
        block.model_says("Response")
        self.assertTrue(block.need_user_input())


class TestAnthropicToolset(WizLibTestCase):
    """Test AnthropicToolset"""

    def test_init_without_mcp(self):
        """Test initializing toolset without MCP clients"""
        toolset = AnthropicToolset()
        self.assertEqual(len(toolset.mcp_clients), 0)
        self.assertIn("get_current_time", toolset._local_tools)

    def test_definitions_local_only(self):
        """Test getting tool definitions with local tools only"""
        toolset = AnthropicToolset()
        defs = toolset.definitions
        self.assertEqual(len(defs), 1)
        self.assertEqual(defs[0]['name'], 'get_current_time')

    def test_run_tool_get_current_time(self):
        """Test running get_current_time tool"""
        toolset = AnthropicToolset()
        result = toolset.run_tool('get_current_time', {})
        self.assertIsNotNone(result)
        self.assertIn('T', result)  # ISO format contains 'T'

    def test_run_tool_unknown(self):
        """Test running unknown tool returns None"""
        toolset = AnthropicToolset()
        result = toolset.run_tool('unknown_tool', {})
        self.assertIsNone(result)

    def test_is_mcp_tool_false(self):
        """Test checking if tool is MCP when no MCP clients"""
        toolset = AnthropicToolset()
        self.assertFalse(toolset.is_mcp_tool('get_current_time'))

    def test_find_mcp_client_none(self):
        """Test finding MCP client when none exist"""
        toolset = AnthropicToolset()
        client = toolset.find_mcp_client('any_tool')
        self.assertIsNone(client)

    def test_validate_no_conflicts_with_mcp(self):
        """Test validation catches tool name conflicts"""
        mock_client = Mock()
        mock_client.tools = [{"name": "get_current_time", "description": "test"}]
        
        with self.assertRaises(ValueError) as ctx:
            AnthropicToolset(mcp_clients=[mock_client])
        
        self.assertIn("Tool name conflict", str(ctx.exception))
        self.assertIn("get_current_time", str(ctx.exception))


class TestAI(WizLibTestCase):

    def test_chat_with_initial_message(self):
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')

        u = Mock()
        u.get_text.return_value = 'quit'

        # Mock the streaming response
        mock_stream = MagicMock()
        mock_stream.__enter__.return_value = mock_stream
        mock_stream.__exit__.return_value = None
        mock_stream.text_stream = ['r']

        a.client.messages.stream = Mock(return_value=mock_stream)

        a.chat(u, 'h')

        # Check that the response was sent and then goodbye
        self.assertGreaterEqual(u.send.call_count, 2)
        # Find the call with 'r' - it should be sent without newline
        r_calls = [call for call in u.send.call_args_list
                   if call[0][0] == 'r']
        self.assertEqual(1, len(r_calls))
        # Check goodbye was sent
        goodbye_calls = [call for call in u.send.call_args_list
                         if call[0][0] == 'Goodbye!']
        self.assertEqual(1, len(goodbye_calls))

    def test_chat_empty_input_continues(self):
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')

        u = Mock()
        u.get_text.side_effect = ['', 'exit']

        # Mock the streaming response (shouldn't be called for empty input)
        mock_stream = MagicMock()
        a.client.messages.stream = Mock(return_value=mock_stream)

        a.chat(u)

        # Stream should not be called since first input was empty
        self.assertEqual(0, a.client.messages.stream.call_count)

    def test_chat_exit_command(self):
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')

        u = Mock()
        u.get_text.return_value = 'exit'

        a.chat(u)

        u.send.assert_called_with('Goodbye!', Emphasis.INFO)

    def test_chat_keyboard_interrupt(self):
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')

        u = Mock()
        u.get_text.side_effect = KeyboardInterrupt()

        a.chat(u)

        u.send.assert_called_with('Goodbye!', Emphasis.INFO)

    def test_chat_conversation_flow(self):
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')

        u = Mock()
        u.get_text.side_effect = ['q', 'bye']

        # Mock the streaming response
        mock_stream = MagicMock()
        mock_stream.__enter__.return_value = mock_stream
        mock_stream.__exit__.return_value = None
        mock_stream.text_stream = ['a']

        # Mock the final message with proper content structure
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.type = 'text'
        mock_content.text = 'a'
        mock_message.content = [mock_content]
        mock_stream.get_final_message.return_value = mock_message

        a.client.messages.stream = Mock(return_value=mock_stream)

        a.chat(u)

        # Verify that the stream was called once for the first message
        self.assertEqual(1, a.client.messages.stream.call_count)

    def test_init_without_api_key(self):
        """Test initializing service without explicit API key"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as mock_sdk:
            mock_instance = Mock()
            mock_instance.models.list.return_value = []
            mock_sdk.return_value = mock_instance
            
            a = AnthropicAIService()
            # Should create client without api_key parameter
            mock_sdk.assert_called_once_with()

    def test_ask(self):
        """Test ask sends no tools and returns plain text response"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')

            mock_content = Mock()
            mock_content.type = "text"
            mock_content.text = "Response text"
            mock_message = Mock()
            mock_message.content = [mock_content]
            a.client.messages.create = Mock(return_value=mock_message)

            result = a.ask("Test query")

            self.assertEqual(result, "Response text")
            a.client.messages.create.assert_called_once()
            call_kwargs = a.client.messages.create.call_args[1]
            self.assertNotIn('tools', call_kwargs)

    def test_available_models_error(self):
        """Test available_models when API call fails"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.side_effect = Exception("API Error")
            a = AnthropicAIService(api_key='k')
            
            # Access the cached property
            models = a.available_models
            self.assertEqual(models, [])

    def test_model_name_with_no_models(self):
        """Test model_name when no models available"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')
            
            # Access the cached property
            name = a.model_name
            self.assertIsNone(name)

    def test_chat_eof_error(self):
        """Test chat handles EOFError"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')

        u = Mock()
        u.get_text.side_effect = EOFError()

        a.chat(u)

        u.send.assert_called_with('Goodbye!', Emphasis.INFO)

    def test_chat_with_tool_use(self):
        """Test chat with tool use"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')

        u = Mock()
        u.get_text.side_effect = ['test', 'quit']

        # Mock the streaming response with tool use
        mock_stream = MagicMock()
        mock_stream.__enter__.return_value = mock_stream
        mock_stream.__exit__.return_value = None
        mock_stream.text_stream = ['Using tool']

        # First message: tool use
        mock_tool_content = MagicMock()
        mock_tool_content.type = 'tool_use'
        mock_tool_content.name = 'get_current_time'
        mock_tool_content.id = 'tool-123'
        mock_tool_content.input = {}
        
        mock_message1 = MagicMock()
        mock_message1.content = [mock_tool_content]
        
        # Second message: text response after tool
        mock_text_content = MagicMock()
        mock_text_content.type = 'text'
        mock_text_content.text = 'The time is...'
        
        mock_message2 = MagicMock()
        mock_message2.content = [mock_text_content]
        
        mock_stream.get_final_message.side_effect = [mock_message1, mock_message2]

        a.client.messages.stream = Mock(return_value=mock_stream)

        a.chat(u)

        # Verify tool was used
        self.assertGreaterEqual(a.client.messages.stream.call_count, 2)

    def test_query_with_tools_no_tools(self):
        """Test query_with_tools when no tools are used"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')
            
            # Mock response with no tool use
            mock_content = Mock()
            mock_content.type = 'text'
            mock_content.text = "Simple response"
            mock_message = Mock()
            mock_message.content = [mock_content]
            mock_message.stop_reason = 'end_turn'
            a.client.messages.create = Mock(return_value=mock_message)
            
            result = a.query_with_tools("Test query")
            
            self.assertEqual(result, "Simple response")

    def test_query_with_tools_with_tool_use(self):
        """Test query_with_tools with tool use"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')
            
            # First response: tool use - use MagicMock for dict() compatibility
            mock_tool_content = MagicMock()
            mock_tool_content.type = 'tool_use'
            mock_tool_content.name = 'get_current_time'
            mock_tool_content.id = 'tool-123'
            mock_tool_content.input = {}
            
            mock_message1 = MagicMock()
            mock_message1.content = [mock_tool_content]
            mock_message1.stop_reason = 'tool_use'
            
            # Second response: final text
            mock_text_content = MagicMock()
            mock_text_content.type = 'text'
            mock_text_content.text = "The time is 2pm"
            
            mock_message2 = MagicMock()
            mock_message2.content = [mock_text_content]
            mock_message2.stop_reason = 'end_turn'
            
            a.client.messages.create = Mock(side_effect=[mock_message1, mock_message2])
            
            result = a.query_with_tools("What time is it?")
            
            self.assertEqual(result, "The time is 2pm")
            self.assertEqual(a.client.messages.create.call_count, 2)

    def test_query_with_tools_limit_exceeded(self):
        """Test query_with_tools raises error when tool limit exceeded"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')
            
            # Mock response that keeps requesting tools - use MagicMock
            mock_tool_content = MagicMock()
            mock_tool_content.type = 'tool_use'
            mock_tool_content.name = 'get_current_time'
            mock_tool_content.id = 'tool-123'
            mock_tool_content.input = {}
            
            mock_message = MagicMock()
            mock_message.content = [mock_tool_content]
            mock_message.stop_reason = 'tool_use'
            
            a.client.messages.create = Mock(return_value=mock_message)
            
            with self.assertRaises(RuntimeError) as ctx:
                a.query_with_tools("Test", tool_limit=2)
            
            self.assertIn('Tool use limit', str(ctx.exception))

    def test_query_with_tools_empty_response(self):
        """Test query_with_tools returns empty string when no text content"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')
            
            # Mock response with no text content
            mock_message = Mock()
            mock_message.content = []
            mock_message.stop_reason = 'end_turn'
            a.client.messages.create = Mock(return_value=mock_message)
            
            result = a.query_with_tools("Test query")
            
            self.assertEqual(result, "")

    def test_execute_tool_local(self):
        """Test _execute_tool with local tool"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')
            
            result = a._execute_tool('get_current_time', {})
            
            self.assertIsNotNone(result)
            self.assertIn('T', result)  # ISO format

    def test_execute_tool_mcp(self):
        """Test _execute_tool with MCP tool"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            
            # Create mock MCP client
            mock_client = Mock()
            mock_client.tools = [{"name": "test_tool", "description": "test"}]
            
            async def mock_call_tool(name, args):
                return [{"type": "text", "text": "MCP result"}]
            
            mock_client.call_tool = mock_call_tool
            
            # Create toolset with MCP client
            from kwark.ai_services.anthropic_ai_service import AnthropicToolset
            toolset = AnthropicToolset(mcp_clients=[mock_client])
            
            a = AnthropicAIService(api_key='k', toolset=toolset)
            
            # Need event loop for MCP
            import asyncio
            a.mcp_loop = asyncio.new_event_loop()
            
            result = a._execute_tool('test_tool', {})
            
            self.assertEqual(result, "MCP result")
            a.mcp_loop.close()

    def test_run_mcp_tool_with_debug(self):
        """Test _run_mcp_tool with DEBUG environment variable"""
        import os
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            
            # Create mock MCP client
            mock_client = Mock()
            mock_client.command = "test_command"
            mock_client.session = Mock()
            mock_client.tools = [{"name": "test_tool", "description": "test"}]
            
            async def mock_call_tool(name, args):
                return [{"type": "text", "text": "Debug result"}]
            
            mock_client.call_tool = mock_call_tool
            
            from kwark.ai_services.anthropic_ai_service import AnthropicToolset
            toolset = AnthropicToolset(mcp_clients=[mock_client])
            
            a = AnthropicAIService(api_key='k', toolset=toolset)
            
            import asyncio
            a.mcp_loop = asyncio.new_event_loop()
            
            # Set DEBUG environment variable
            old_debug = os.environ.get('DEBUG')
            os.environ['DEBUG'] = '1'
            
            try:
                result = a._run_mcp_tool('test_tool', {})
                self.assertEqual(result, "Debug result")
            finally:
                if old_debug is None:
                    os.environ.pop('DEBUG', None)
                else:
                    os.environ['DEBUG'] = old_debug
                a.mcp_loop.close()

    def test_run_mcp_tool_not_found(self):
        """Test _run_mcp_tool when tool not found"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')
            
            result = a._run_mcp_tool('nonexistent_tool', {})
            
            self.assertIn('Error', result)
            self.assertIn('not found', result)

    def test_run_mcp_tool_error(self):
        """Test _run_mcp_tool handles errors"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            
            # Create mock MCP client that raises error
            mock_client = Mock()
            mock_client.tools = [{"name": "error_tool", "description": "test"}]
            
            async def mock_call_tool(name, args):
                raise Exception("Tool error")
            
            mock_client.call_tool = mock_call_tool
            
            from kwark.ai_services.anthropic_ai_service import AnthropicToolset
            toolset = AnthropicToolset(mcp_clients=[mock_client])
            
            a = AnthropicAIService(api_key='k', toolset=toolset)
            
            import asyncio
            a.mcp_loop = asyncio.new_event_loop()
            
            result = a._run_mcp_tool('error_tool', {})
            
            self.assertIn('Error calling MCP tool', result)
            a.mcp_loop.close()

    def test_run_mcp_tool_without_loop(self):
        """Test _run_mcp_tool falls back when no persistent loop"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            
            # Create mock MCP client
            mock_client = Mock()
            mock_client.tools = [{"name": "test_tool", "description": "test"}]
            
            async def mock_call_tool(name, args):
                return [{"type": "text", "text": "Fallback result"}]
            
            mock_client.call_tool = mock_call_tool
            
            from kwark.ai_services.anthropic_ai_service import AnthropicToolset
            toolset = AnthropicToolset(mcp_clients=[mock_client])
            
            a = AnthropicAIService(api_key='k', toolset=toolset)
            # Don't set mcp_loop
            
            result = a._run_mcp_tool('test_tool', {})
            
            self.assertEqual(result, "Fallback result")

    def test_chat_with_exit_tool(self):
        """Test chat with exit tool"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            a = AnthropicAIService(api_key='k')

        u = Mock()
        u.get_text.return_value = 'test'

        # Mock the streaming response with exit tool
        mock_stream = MagicMock()
        mock_stream.__enter__.return_value = mock_stream
        mock_stream.__exit__.return_value = None
        mock_stream.text_stream = ['Exiting']

        mock_tool_content = MagicMock()
        mock_tool_content.type = 'tool_use'
        mock_tool_content.name = 'exit'
        mock_tool_content.id = 'tool-exit'
        
        mock_message = MagicMock()
        mock_message.content = [mock_tool_content]
        
        mock_stream.get_final_message.return_value = mock_message

        a.client.messages.stream = Mock(return_value=mock_stream)

        a.chat(u)

        # Should exit without calling tool
        self.assertEqual(1, a.client.messages.stream.call_count)

    def test_run_mcp_tool_with_client(self):
        """Test _run_mcp_tool with mock MCP client"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            
            # Create mock MCP client
            mock_client = Mock()
            mock_client.command = "test"
            mock_client.session = Mock()
            
            # Mock async call_tool to return content blocks
            async def mock_call_tool(name, args):
                return [{"type": "text", "text": "Tool result"}]
            
            mock_client.call_tool = mock_call_tool
            
            # Create toolset with mock client
            mock_toolset = Mock()
            mock_toolset.find_mcp_client = Mock(return_value=mock_client)
            
            a = AnthropicAIService(api_key='k', toolset=mock_toolset)
            
            # Create event loop for testing
            import asyncio
            a.mcp_loop = asyncio.new_event_loop()
            
            try:
                result = a._run_mcp_tool('test_tool', {'arg': 'value'})
                self.assertEqual(result, "Tool result")
            finally:
                a.mcp_loop.close()

    def test_run_mcp_tool_exception(self):
        """Test _run_mcp_tool handles exceptions"""
        with patch('kwark.ai_services.anthropic_ai_service.AnthropicSDK') as m:
            m().models.list.return_value = []
            
            # Create mock MCP client that raises exception
            mock_client = Mock()
            mock_client.command = "test"
            mock_client.session = Mock()
            
            async def mock_call_tool(name, args):
                raise Exception("Tool error")
            
            mock_client.call_tool = mock_call_tool
            
            mock_toolset = Mock()
            mock_toolset.find_mcp_client = Mock(return_value=mock_client)
            
            a = AnthropicAIService(api_key='k', toolset=mock_toolset)
            
            import asyncio
            a.mcp_loop = asyncio.new_event_loop()
            
            try:
                result = a._run_mcp_tool('test_tool', {})
                self.assertIn("Error calling MCP tool", result)
            finally:
                a.mcp_loop.close()
