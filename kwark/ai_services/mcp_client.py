"""MCP client wrapper for stdio-based MCP server integration

The ``mcp`` package is an optional extra (``kwark[mcp]``). This module must
remain importable without it, because WizLib's ClassFamily imports every
module in ``kwark.ai_services``. Callers should use ``require_mcp()`` before
connecting to MCP servers.
"""
from contextlib import AsyncExitStack

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None


MCP_NOT_INSTALLED_MESSAGE = (
    "MCP servers are configured but the 'mcp' package is not installed. "
    "Install Kwark with MCP support: pipx install 'kwark[mcp]' "
    "(or pip install 'kwark[mcp]')")


class MCPNotInstalledError(RuntimeError):
    """Raised when MCP servers are configured without the mcp package"""


def mcp_available():
    """Return True if the optional mcp package is installed"""
    return stdio_client is not None


def require_mcp():
    """Raise MCPNotInstalledError if the optional mcp package is missing"""
    if not mcp_available():
        raise MCPNotInstalledError(MCP_NOT_INSTALLED_MESSAGE)


class MCPClientWrapper:
    """Manages connection to a single MCP server via stdio"""

    def __init__(self, command, args):
        """Initialize MCP client wrapper

        Args:
            command: Command to run (e.g., 'python', 'node')
            args: List of arguments including script path
        """
        self.command = command
        self.args = args
        self.session = None
        self.exit_stack = None

    async def connect(self):
        """Connect to the MCP server asynchronously"""
        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=None
        )

        self.exit_stack = AsyncExitStack()
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(params)
        )
        read, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.session.initialize()

    async def list_tools(self):
        """List available tools from the MCP server

        Returns:
            List of tool definitions compatible with Anthropic API
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        response = await self.session.list_tools()
        tools = []
        for tool in response.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            })
        return tools

    async def call_tool(self, tool_name, arguments):
        """Call a tool on the MCP server

        Args:
            tool_name: Name of the tool to call
            arguments: Dict of arguments for the tool

        Returns:
            List of content dicts compatible with Anthropic tool_result
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        response = await self.session.call_tool(tool_name, arguments)
        # Convert MCP TextContent to Anthropic format
        content = []
        for item in response.content:
            if item.type == "text":
                content.append({"type": "text", "text": item.text})
        return content

    async def cleanup(self):
        """Clean up resources"""
        if self.exit_stack:
            await self.exit_stack.aclose()
            self.exit_stack = None
            self.session = None
