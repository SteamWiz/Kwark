import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from wizlib.test_case import WizLibTestCase

from kwark.ai_services.mcp_client import MCPClientWrapper


class TestMCPClient(WizLibTestCase):
    """Test MCPClientWrapper"""

    def test_init(self):
        """Test initializing MCP client wrapper"""
        client = MCPClientWrapper('python', ['test.py'])
        self.assertEqual(client.command, 'python')
        self.assertEqual(client.args, ['test.py'])
        self.assertIsNone(client.session)
        self.assertIsNone(client.exit_stack)

    def test_connect(self):
        """Test connecting to MCP server"""
        client = MCPClientWrapper('python', ['test.py'])
        
        async def run_test():
            with patch('kwark.ai_services.mcp_client.stdio_client') as mock_stdio, \
                 patch('kwark.ai_services.mcp_client.ClientSession') as mock_session:
                
                # Mock stdio_client context manager
                mock_transport = AsyncMock()
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(Mock(), Mock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Mock ClientSession
                mock_session_instance = AsyncMock()
                mock_session_instance.initialize = AsyncMock()
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
                mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
                
                await client.connect()
                
                self.assertIsNotNone(client.session)
                self.assertIsNotNone(client.exit_stack)
        
        asyncio.run(run_test())

    def test_list_tools_not_connected(self):
        """Test list_tools raises error when not connected"""
        client = MCPClientWrapper('python', ['test.py'])
        
        async def run_test():
            with self.assertRaises(RuntimeError) as ctx:
                await client.list_tools()
            self.assertIn("Not connected", str(ctx.exception))
        
        asyncio.run(run_test())

    def test_list_tools(self):
        """Test listing tools from MCP server"""
        client = MCPClientWrapper('python', ['test.py'])
        
        async def run_test():
            # Mock session
            mock_tool = Mock()
            mock_tool.name = "test_tool"
            mock_tool.description = "A test tool"
            mock_tool.inputSchema = {"type": "object"}
            
            mock_response = Mock()
            mock_response.tools = [mock_tool]
            
            client.session = AsyncMock()
            client.session.list_tools = AsyncMock(return_value=mock_response)
            
            tools = await client.list_tools()
            
            self.assertEqual(len(tools), 1)
            self.assertEqual(tools[0]['name'], 'test_tool')
            self.assertEqual(tools[0]['description'], 'A test tool')
            self.assertEqual(tools[0]['input_schema'], {"type": "object"})
        
        asyncio.run(run_test())

    def test_call_tool_not_connected(self):
        """Test call_tool raises error when not connected"""
        client = MCPClientWrapper('python', ['test.py'])
        
        async def run_test():
            with self.assertRaises(RuntimeError) as ctx:
                await client.call_tool('test_tool', {})
            self.assertIn("Not connected", str(ctx.exception))
        
        asyncio.run(run_test())

    def test_call_tool(self):
        """Test calling a tool on MCP server"""
        client = MCPClientWrapper('python', ['test.py'])
        
        async def run_test():
            # Mock session
            mock_content = Mock()
            mock_content.type = "text"
            mock_content.text = "Tool result"
            
            mock_response = Mock()
            mock_response.content = [mock_content]
            
            client.session = AsyncMock()
            client.session.call_tool = AsyncMock(return_value=mock_response)
            
            result = await client.call_tool('test_tool', {'arg': 'value'})
            
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['type'], 'text')
            self.assertEqual(result[0]['text'], 'Tool result')
            
            client.session.call_tool.assert_called_once_with('test_tool', {'arg': 'value'})
        
        asyncio.run(run_test())

    def test_cleanup(self):
        """Test cleanup of MCP client resources"""
        client = MCPClientWrapper('python', ['test.py'])
        
        async def run_test():
            # Mock exit_stack
            mock_exit_stack = AsyncMock()
            client.exit_stack = mock_exit_stack
            client.session = Mock()
            
            await client.cleanup()
            
            mock_exit_stack.aclose.assert_called_once()
            self.assertIsNone(client.exit_stack)
            self.assertIsNone(client.session)
        
        asyncio.run(run_test())

    def test_cleanup_no_exit_stack(self):
        """Test cleanup when no exit_stack exists"""
        client = MCPClientWrapper('python', ['test.py'])
        
        async def run_test():
            # Should not raise error
            await client.cleanup()
            self.assertIsNone(client.exit_stack)
            self.assertIsNone(client.session)
        
        asyncio.run(run_test())
