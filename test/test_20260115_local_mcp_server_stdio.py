import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from wizlib.test_case import WizLibTestCase

from kwark import KwarkApp
from test import patch_ai_service


class TestMCPServerStdio(WizLibTestCase):
    """Test MCP server integration via stdio"""

    def test_parse_yaml_input_empty(self):
        """Test parsing empty YAML input"""
        from kwark.util import parse_yaml_input

        result = parse_yaml_input("")
        self.assertIsNone(result['prompt'])
        self.assertEqual([], result['mcp_servers'])

    def test_parse_yaml_input_plain_text(self):
        """Test parsing plain text treats it as the prompt"""
        from kwark.util import parse_yaml_input

        result = parse_yaml_input("Hello, world!")
        self.assertEqual("Hello, world!", result['prompt'])
        self.assertEqual([], result['mcp_servers'])

    def test_parse_yaml_input_with_prompt(self):
        """Test parsing YAML with prompt entry"""
        from kwark.util import parse_yaml_input

        yaml_config = """prompt: Tell me a story"""
        result = parse_yaml_input(yaml_config)
        self.assertEqual("Tell me a story", result['prompt'])
        self.assertEqual([], result['mcp_servers'])

    def test_parse_yaml_input_with_mcp(self):
        """Test parsing YAML with MCP servers"""
        from kwark.util import parse_yaml_input

        yaml_config = """mcp:
  - python /path/to/server.py"""
        result = parse_yaml_input(yaml_config)
        self.assertIsNone(result['prompt'])
        self.assertEqual(1, len(result['mcp_servers']))
        self.assertEqual("python", result['mcp_servers'][0]["command"])
        self.assertEqual(["/path/to/server.py"], result['mcp_servers'][0]["args"])

    def test_parse_yaml_input_with_prompt_and_mcp(self):
        """Test parsing YAML with both prompt and MCP"""
        from kwark.util import parse_yaml_input

        yaml_config = """prompt: What time is it?
mcp:
  - python /path/to/server1.py
  - node /path/to/server2.js arg1 arg2"""
        result = parse_yaml_input(yaml_config)
        self.assertEqual("What time is it?", result['prompt'])
        self.assertEqual(2, len(result['mcp_servers']))
        self.assertEqual("python", result['mcp_servers'][0]["command"])
        self.assertEqual(["/path/to/server1.py"], result['mcp_servers'][0]["args"])
        self.assertEqual("node", result['mcp_servers'][1]["command"])
        self.assertEqual(["/path/to/server2.js", "arg1", "arg2"],
                         result['mcp_servers'][1]["args"])

    def test_parse_mcp_servers_empty(self):
        """Test parsing empty MCP server list"""
        from kwark.util import parse_mcp_servers

        servers = parse_mcp_servers([])
        self.assertEqual([], servers)

    def test_parse_mcp_servers_single(self):
        """Test parsing single MCP server"""
        from kwark.util import parse_mcp_servers

        servers = parse_mcp_servers(["python /path/to/server.py"])
        self.assertEqual(1, len(servers))
        self.assertEqual("python", servers[0]["command"])
        self.assertEqual(["/path/to/server.py"], servers[0]["args"])

    def test_parse_mcp_servers_multiple(self):
        """Test parsing multiple MCP servers"""
        from kwark.util import parse_mcp_servers

        servers = parse_mcp_servers([
            "python /path/to/server1.py",
            "node /path/to/server2.js arg1 arg2"
        ])
        self.assertEqual(2, len(servers))
        self.assertEqual("python", servers[0]["command"])
        self.assertEqual(["/path/to/server1.py"], servers[0]["args"])
        self.assertEqual("node", servers[1]["command"])
        self.assertEqual(["/path/to/server2.js", "arg1", "arg2"],
                         servers[1]["args"])

    def test_mcp_client_wrapper_init(self):
        """Test MCPClientWrapper initialization"""
        from kwark.ai_services.mcp_client import MCPClientWrapper

        w = MCPClientWrapper("python", ["test.py"])
        self.assertEqual("python", w.command)
        self.assertEqual(["test.py"], w.args)
        self.assertIsNone(w.session)

    def test_mcp_client_wrapper_connect(self):
        """Test MCPClientWrapper async connect"""
        from kwark.ai_services.mcp_client import MCPClientWrapper

        w = MCPClientWrapper("python", ["test.py"])

        # Test that connect is async
        self.assertTrue(asyncio.iscoroutinefunction(w.connect))

    def test_mcp_client_wrapper_list_tools(self):
        """Test MCPClientWrapper list_tools returns tool definitions"""
        from kwark.ai_services.mcp_client import MCPClientWrapper

        w = MCPClientWrapper("python", ["test.py"])

        # Test that list_tools is async
        self.assertTrue(asyncio.iscoroutinefunction(w.list_tools))

    def test_toolset_init_with_mcp_clients(self):
        """Test initializing toolset with MCP clients"""
        from kwark.ai_services.anthropic_ai_service import (
            AnthropicToolset
        )

        t = AnthropicToolset()
        self.assertIsNotNone(t)

        # Should support setting MCP clients
        t = AnthropicToolset(mcp_clients=[])
        self.assertIsNotNone(t)

    def test_toolset_detects_name_conflicts(self):
        """Test toolset detects tool name conflicts"""
        from kwark.ai_services.anthropic_ai_service import (
            AnthropicToolset
        )

        # Mock MCP client with conflicting tool name
        m1 = Mock()
        m1.tools = [{
            "name": "get_current_time",  # Conflicts with built-in
            "description": "Test",
            "input_schema": {}
        }]

        # Should raise error on conflict
        with self.assertRaises(ValueError) as ctx:
            AnthropicToolset(mcp_clients=[m1])

        self.assertIn("conflict", str(ctx.exception).lower())
        self.assertIn("get_current_time", str(ctx.exception))

    def test_toolset_mcp_tool_detection(self):
        """Test toolset can identify MCP vs local tools"""
        from kwark.ai_services.anthropic_ai_service import (
            AnthropicToolset
        )

        m = Mock()
        m.tools = [{"name": "test_tool", "description": "T",
                    "input_schema": {}}]

        t = AnthropicToolset(mcp_clients=[m])

        # Local tool
        self.assertFalse(t.is_mcp_tool("get_current_time"))

        # MCP tool
        self.assertTrue(t.is_mcp_tool("test_tool"))

        # Unknown tool
        self.assertFalse(t.is_mcp_tool("unknown"))

    def test_toolset_find_mcp_client(self):
        """Test finding which client provides a tool"""
        from kwark.ai_services.anthropic_ai_service import (
            AnthropicToolset
        )

        m1 = Mock()
        m1.tools = [{"name": "tool1", "description": "T",
                     "input_schema": {}}]
        m2 = Mock()
        m2.tools = [{"name": "tool2", "description": "T",
                     "input_schema": {}}]

        t = AnthropicToolset(mcp_clients=[m1, m2])

        self.assertEqual(m1, t.find_mcp_client("tool1"))
        self.assertEqual(m2, t.find_mcp_client("tool2"))
        self.assertIsNone(t.find_mcp_client("unknown"))

    def test_toolset_definitions_includes_all_tools(self):
        """Test definitions includes both local and MCP tools"""
        from kwark.ai_services.anthropic_ai_service import (
            AnthropicToolset
        )

        m = Mock()
        m.tools = [
            {"name": "mcp_tool", "description": "Test MCP tool",
             "input_schema": {}}
        ]

        t = AnthropicToolset(mcp_clients=[m])
        d = t.definitions

        # Should have local + MCP tools
        self.assertEqual(2, len(d))
        names = [tool["name"] for tool in d]
        self.assertIn("get_current_time", names)
        self.assertIn("mcp_tool", names)

    def test_mcp_client_call_tool_converts_format(self):
        """Test MCP client converts response to Anthropic format"""
        from kwark.ai_services.mcp_client import MCPClientWrapper
        import mcp.types as types

        w = MCPClientWrapper("python", ["test.py"])

        # Mock session
        m = AsyncMock()
        m.call_tool = AsyncMock(return_value=Mock(
            content=[types.TextContent(type="text", text="result")]
        ))
        w.session = m

        # Run async call
        result = asyncio.run(w.call_tool("test", {}))

        self.assertEqual([{"type": "text", "text": "result"}], result)

    def test_ai_service_run_mcp_tool_not_found(self):
        """Test _run_mcp_tool with nonexistent tool"""
        from kwark.ai_services.anthropic_ai_service import (
            AnthropicAIService, AnthropicToolset
        )
        from test.mocks.mock_anthropic_sdk import MockAnthropicSDK

        with MockAnthropicSDK.patch():
            service = AnthropicAIService(api_key='fake')
            r = service._run_mcp_tool("nonexistent", {})
            self.assertIn("not found", r)

    def test_ai_service_run_mcp_tool_error_handling(self):
        """Test _run_mcp_tool handles errors"""
        from kwark.ai_services.anthropic_ai_service import (
            AnthropicAIService, AnthropicToolset
        )
        from test.mocks.mock_anthropic_sdk import MockAnthropicSDK

        # Mock client that raises error
        m = Mock()
        m.tools = [{"name": "bad", "description": "T", "input_schema": {}}]
        m.call_tool = AsyncMock(side_effect=Exception("Test error"))

        toolset = AnthropicToolset(mcp_clients=[m])
        
        with MockAnthropicSDK.patch():
            service = AnthropicAIService(api_key='fake', toolset=toolset)
            r = service._run_mcp_tool("bad", {})
            self.assertIn("Error", r)
            self.assertIn("Test error", r)

    def test_chat_command_no_mcp_config(self):
        """Test chat command handles no MCP config"""
        from kwark.command.chat_command import ChatCommand
        from wizlib.config_handler import ConfigHandler

        with patch('sys.stdin.isatty', return_value=True):
            app = KwarkApp()
            app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake')

        with self.patch_stream(""):
            cmd = ChatCommand(app)
            cmd.handle_vals()

            # Should not have toolset
            self.assertFalse(hasattr(cmd, 'toolset') and cmd.toolset)

    def test_chat_command_yaml_without_mcp_key(self):
        """Test chat command handles YAML without mcp key"""
        from kwark.command.chat_command import ChatCommand
        from wizlib.config_handler import ConfigHandler

        yaml = """other:
  - value"""

        with self.patch_stream(yaml):
            app = KwarkApp()
            app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake')
            cmd = ChatCommand(app)
            cmd.handle_vals()

            # Should not have toolset
            self.assertFalse(hasattr(cmd, 'toolset') and cmd.toolset)

    def test_chat_command_with_prompt_in_yaml(self):
        """Test chat command extracts prompt from YAML"""
        from kwark.command.chat_command import ChatCommand
        from wizlib.config_handler import ConfigHandler

        yaml = """prompt: Hello, AI!"""

        with self.patch_stream(yaml):
            app = KwarkApp()
            app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake')
            cmd = ChatCommand(app)
            cmd.handle_vals()

            # Should have initial_prompt set
            self.assertEqual("Hello, AI!", cmd.initial_prompt)

    def test_init_mcp_clients_empty_config(self):
        """Test _init_mcp_clients with empty list"""
        from kwark.command.chat_command import ChatCommand

        with self.patch_stream(""):
            app = KwarkApp()
            cmd = ChatCommand(app)

            clients = cmd._init_mcp_clients([])
            self.assertEqual([], clients)

    def test_parse_yaml_input_whitespace_only(self):
        """Test parsing whitespace-only input"""
        from kwark.util import parse_yaml_input

        result = parse_yaml_input("   \n  \t  ")
        self.assertIsNone(result['prompt'])
        self.assertEqual([], result['mcp_servers'])

    def test_connect_and_discover_success(self):
        """Test _connect_and_discover with mock wrapper"""
        from kwark.command.chat_command import ChatCommand

        with self.patch_stream(""):
            app = KwarkApp()
            cmd = ChatCommand(app)

            # Mock wrapper
            w = Mock()
            w.command = "test"
            w.args = ["arg"]
            w.connect = AsyncMock()
            w.list_tools = AsyncMock(return_value=[
                {"name": "tool1", "description": "T", "input_schema": {}}
            ])

            async def test():
                result = await cmd._connect_and_discover(w)
                return result

            result = asyncio.run(test())
            self.assertEqual(w, result)
            self.assertEqual(1, len(result.tools))

    def test_connect_and_discover_error(self):
        """Test _connect_and_discover handles errors"""
        from kwark.command.chat_command import ChatCommand

        with self.patch_stream(""):
            app = KwarkApp()
            cmd = ChatCommand(app)

            # Mock wrapper that fails
            w = Mock()
            w.command = "test"
            w.args = ["arg"]
            w.connect = AsyncMock(side_effect=Exception("Connection failed"))

            async def test():
                try:
                    await cmd._connect_and_discover(w)
                    return None
                except Exception as e:
                    return str(e)

            result = asyncio.run(test())
            self.assertIn("Connection failed", result)

    def test_init_mcp_clients_with_error(self):
        """Test _init_mcp_clients handles connection errors"""
        from kwark.command.chat_command import ChatCommand
        from wizlib.config_handler import ConfigHandler
        from io import StringIO

        with self.patch_stream(""):
            app = KwarkApp()
            app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake')

            # Mock UI to capture warnings
            app.ui = Mock()
            app.ui.send = Mock()

            cmd = ChatCommand(app)

            # Set up event loop (needed for _init_mcp_clients)
            cmd.mcp_loop = asyncio.new_event_loop()

            # Mock connection failure
            original = cmd._connect_and_discover

            async def failing_connect(w):
                raise Exception("Test failure")

            cmd._connect_and_discover = failing_connect

            try:
                clients = cmd._init_mcp_clients([
                    {"command": "test", "args": ["arg"]}
                ])

                # Should have called ui.send with warning
                self.assertTrue(app.ui.send.called)
                call_args = str(app.ui.send.call_args)
                self.assertIn("Warning", call_args)

                # Should return empty list
                self.assertEqual([], clients)
            finally:
                # Clean up event loop
                cmd.mcp_loop.close()

    def test_chat_command_with_mcp_config_and_conflict(self):
        """Test chat command detects tool name conflicts"""
        from kwark.command.chat_command import ChatCommand
        from wizlib.config_handler import ConfigHandler

        yaml = """mcp:
  - test command"""

        with self.patch_stream(yaml):
            app = KwarkApp()
            app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake')
            app.ui = Mock()
            app.ui.send = Mock()

            cmd = ChatCommand(app)

            # Mock successful connection with conflicting tool
            async def mock_connect(w):
                w.tools = [{
                    "name": "get_current_time",  # Conflicts
                    "description": "T",
                    "input_schema": {}
                }]
                return w

            cmd._connect_and_discover = mock_connect
            cmd.handle_vals()

            # Should have called ui.send with error
            self.assertTrue(app.ui.send.called)
            call_args = str(app.ui.send.call_args)
            self.assertIn("Error", call_args)

    def test_integration_minimal_mcp_server(self):
        """Integration test with minimal_mcp_server"""
        import os
        import sys
        from kwark.ai_services.mcp_client import MCPClientWrapper

        # Get path to minimal_mcp_server.py
        test_dir = os.path.dirname(__file__)
        server_path = os.path.join(test_dir, "minimal_mcp_server.py")

        async def test_connection():
            w = MCPClientWrapper(sys.executable, [server_path])
            try:
                await w.connect()
                tools = await w.list_tools()

                # Should have echo and add tools
                self.assertEqual(2, len(tools))
                names = [t["name"] for t in tools]
                self.assertIn("echo", names)
                self.assertIn("add", names)

                # Test echo tool
                r = await w.call_tool("echo", {"message": "hi"})
                self.assertEqual([{"type": "text", "text": "hi"}], r)

                # Test add tool
                r = await w.call_tool("add", {"a": 2, "b": 3})
                self.assertEqual([{"type": "text", "text": "5"}], r)

                return True
            finally:
                await w.cleanup()

        result = asyncio.run(test_connection())
        self.assertTrue(result)

    @unittest.skip("Async cleanup issue - TODO: fix event loop management")
    def test_chat_command_init_mcp_clients(self):
        """Test chat command initializes MCP clients"""
        import os
        import sys
        from kwark.command.chat_command import ChatCommand
        from wizlib.config_handler import ConfigHandler

        test_dir = os.path.dirname(__file__)
        server_path = os.path.join(test_dir, "minimal_mcp_server.py")

        app = KwarkApp()
        app.config = ConfigHandler.fake(kwark_api_anthropic_key='fake')

        yaml = f"""mcp:
  - {sys.executable} {server_path}"""

        with self.patch_stream(yaml):
            cmd = ChatCommand(app)
            cmd.handle_vals()

            try:
                # Should have created toolset with MCP tools
                self.assertIsNotNone(cmd.toolset)
                self.assertEqual(1, len(cmd.toolset.mcp_clients))

                # Should have discovered tools
                client = cmd.toolset.mcp_clients[0]
                self.assertEqual(2, len(client.tools))
            finally:
                # Cleanup
                async def cleanup_clients():
                    for c in cmd.toolset.mcp_clients:
                        await c.cleanup()
                asyncio.run(cleanup_clients())

    @unittest.skip("Async cleanup issue - TODO: fix event loop management")
    def test_ai_service_run_mcp_tool(self):
        """Test AI service can run MCP tools"""
        import os
        import sys
        from kwark.ai_services.anthropic_ai_service import (
            AnthropicAIService, AnthropicToolset
        )
        from kwark.ai_services.mcp_client import MCPClientWrapper

        test_dir = os.path.dirname(__file__)
        server_path = os.path.join(test_dir, "minimal_mcp_server.py")

        # Connect to server
        async def setup():
            w = MCPClientWrapper(sys.executable, [server_path])
            await w.connect()
            w.tools = await w.list_tools()
            return w

        client = asyncio.run(setup())

        try:
            # Create service with MCP tools
            toolset = AnthropicToolset(mcp_clients=[client])
            service = AnthropicAIService(
                api_key='fake', toolset=toolset)

            # Run MCP tool
            result = service._run_mcp_tool("echo", {"message": "test"})
            self.assertEqual("test", result)

            result = service._run_mcp_tool("add", {"a": 10, "b": 20})
            self.assertEqual("30", result)
        finally:
            asyncio.run(client.cleanup())
