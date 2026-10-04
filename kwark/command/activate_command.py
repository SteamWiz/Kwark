import asyncio
from functools import cached_property

from kwark.command import AICommand
from kwark.ai_services import AIService
from kwark.ai_services.anthropic_ai_service import (
    AnthropicToolset, file_content_type,
)
from kwark.util import parse_yaml_input, parse_mcp_servers
from wizlib.ui import Emphasis


class ActivateCommand(AICommand):
    """Execute an AI prompt directly from standard input.
    
    Unlike other commands that use predefined prompt templates, the activate
    command treats the entire input text as the prompt to send to the AI.
    This allows for flexible, ad-hoc AI queries without needing to create
    prompt template files.
    
    Example:
        echo "Tell a story about angels in the style of Mark Twain" | kwark activate
    """

    name = 'activate'
    require_input = True
    success_message = "Generated response from input prompt"

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
        """Override to parse YAML input and set up MCP toolset"""
        super().handle_vals()

        # Parse YAML input for prompt, file, and MCP
        input_data = parse_yaml_input(
            self.app.stream.text)
        self.prompt_text = input_data['prompt']
        self.file_path = input_data.get('file')
        
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
        # Validate prompt is provided
        if not self.prompt_text or \
                not self.prompt_text.strip():
            self.status = "Error: No prompt text provided"
            return ""

        # Get tool use limit from config (default 20)
        limit = (
            self.app.config.get('kwark-tooluselimit')
            or 20
        )

        # Upload file if specified
        file_id = None
        file_type = "document"
        if self.file_path:
            file_type = file_content_type(
                self.file_path)
            try:
                file_id = self.ai_service.upload_file(
                    self.file_path)
            except FileNotFoundError:
                self.status = (
                    "Error: File not found: "
                    f"{self.file_path}")
                return ""
            except Exception as e:
                # Fail the command (non-zero exit). No file was
                # uploaded, so only MCP clients need cleaning up.
                if hasattr(self, 'toolset') and \
                        self.toolset:
                    self._cleanup_mcp_clients()
                raise RuntimeError(
                    f"Error uploading file: {e}") from e

        # Query with tool support and UI feedback
        try:
            response = (
                self.ai_service.query_with_tools_ui(
                    self.prompt_text,
                    self.app.ui,
                    tool_limit=limit,
                    file_id=file_id,
                    file_type=file_type,
                ).strip()
            )
        except RuntimeError as e:
            self.status = f"Error: {e}"
            return ""
        finally:
            # Delete uploaded file
            if file_id:
                try:
                    self.ai_service.delete_file(
                        file_id)
                except Exception:
                    pass  # Best-effort cleanup
            # Clean up MCP clients
            if hasattr(self, 'toolset') and \
                    self.toolset:
                self._cleanup_mcp_clients()

        # Set status message
        self.status = self.success_message

        return response

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
