"""Minimal MCP test server for client testing.

This server provides simple, deterministic tools for testing
MCP client implementations.
"""
import asyncio
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("test-server")

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available test tools."""
    return [
        types.Tool(
            name="echo",
            description="Echo back the input",
            inputSchema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"]
            }
        ),
        types.Tool(
            name="add",
            description="Add two numbers",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent]:
    """Handle tool execution."""
    if name == "echo":
        return [types.TextContent(
            type="text",
            text=arguments["message"]
        )]
    elif name == "add":
        result = arguments["a"] + arguments["b"]
        return [types.TextContent(
            type="text",
            text=str(result)
        )]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the stdio server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
