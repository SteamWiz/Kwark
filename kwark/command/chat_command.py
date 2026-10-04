import asyncio
from functools import cached_property

from kwark.command import AICommand
from kwark.ai_services import AIService
from kwark.ai_services.anthropic_ai_service import (
    AnthropicAIService, AnthropicToolset
)
from kwark.util import parse_yaml_input, parse_mcp_servers
from wizlib.ui import Emphasis


class ChatCommand(AICommand):
    """Simple chat command to interact with AI.
    Takes input text and returns an AI response."""

    name = 'chat'

    def _init_mcp_clients(self, server_configs):
        """Initialize MCP clients from server configurations

        Args:
            server_configs: List of server config dicts

        Returns:
            List of connected MCPClientWrapper instances
        """
        if not server_configs:
            return []

        from kwark.ai_services.mcp_client import MCPClientWrapper

        clients = []

        async def connect_all():
            """Connect to all MCP servers"""
            tasks = []
            for cfg in server_configs:
                wrapper = MCPClientWrapper(cfg['command'], cfg['args'])
                tasks.append(self._connect_and_discover(wrapper))
            return await asyncio.gather(*tasks, return_exceptions=True)

        # Use the persistent event loop
        results = self.mcp_loop.run_until_complete(connect_all())

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.app.ui.send(
                    f"Warning: Failed to connect to MCP server: {result}",
                    emphasis=Emphasis.ERROR)
            elif result:
                clients.append(result)

        return clients

    async def _connect_and_discover(self, wrapper):
        """Connect to MCP server and discover tools

        Args:
            wrapper: MCPClientWrapper instance

        Returns:
            wrapper with tools populated, or None on error
        """
        try:
            await wrapper.connect()
            wrapper.tools = await wrapper.list_tools()
            return wrapper
        except Exception as e:
            raise Exception(
                f"{wrapper.command} {' '.join(wrapper.args)}: {str(e)}")

    def handle_vals(self):
        """Override to parse MCP config and set up toolset"""
        super().handle_vals()

        # Parse YAML input for prompt and MCP servers
        input_data = parse_yaml_input(self.app.stream.text)
        self.initial_prompt = input_data['prompt']
        
        # Get MCP servers from config file (kwark-mcp)
        config_mcp_list = self.app.config.get('kwark-mcp') or []
        config_mcp_servers = parse_mcp_servers(config_mcp_list)
        
        # Merge MCP servers from both sources
        all_mcp_servers = config_mcp_servers + input_data['mcp_servers']

        # Only initialize MCP if servers present
        if all_mcp_servers:
            # Fail clearly if the optional mcp extra is not installed
            from kwark.ai_services.mcp_client import require_mcp
            require_mcp()

            # Create event loop for MCP operations
            self.mcp_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.mcp_loop)

            # Initialize MCP clients
            mcp_clients = self._init_mcp_clients(all_mcp_servers)

            # Create toolset with MCP clients
            try:
                self.toolset = AnthropicToolset(mcp_clients=mcp_clients)
            except ValueError as e:
                self.app.ui.send(f"Error: {e}", emphasis=Emphasis.ERROR)
                self.toolset = AnthropicToolset()
        else:
            self.toolset = None  # Use default
            self.mcp_loop = None

    @cached_property
    def ai_service(self):
        """Override to inject MCP toolset if present"""
        # Use parent's ai_service creation (respects mocking)
        service = AIService.create(
            self.ai_service_type, self.api_key,
            model=self.model)

        # Inject MCP toolset and event loop if we created them
        if hasattr(self, 'toolset') and self.toolset:
            service.toolset = self.toolset
            service.mcp_loop = self.mcp_loop

        return service

    @AICommand.wrap
    def execute(self):
        # Use the initial prompt from YAML input if present
        initial_message = self.initial_prompt.strip() if self.initial_prompt else None

        try:
            self.ai_service.chat(self.app.ui, initial_message=initial_message)
        finally:
            # Clean up MCP clients
            if hasattr(self, 'toolset') and self.toolset:
                self._cleanup_mcp_clients()

        self.status = "Chat session completed"

    def _cleanup_mcp_clients(self):
        """Clean up MCP client connections"""
        if not self.toolset or not self.toolset.mcp_clients:
            return

        async def cleanup():
            for client in self.toolset.mcp_clients:
                try:
                    await client.cleanup()
                except Exception:
                    pass  # Ignore cleanup errors

        try:
            if self.mcp_loop and not self.mcp_loop.is_closed():
                self.mcp_loop.run_until_complete(cleanup())
                self.mcp_loop.close()
        except Exception:
            pass  # Ignore cleanup errors
