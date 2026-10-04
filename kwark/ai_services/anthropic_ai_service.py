from collections import UserList
from datetime import datetime
from functools import cached_property

from anthropic import Anthropic as AnthropicSDK

from kwark.ai_services import AIService
from wizlib.ui import Emphasis


DEFAULT_MODEL = 'claude-sonnet-5'
# Models that think adaptively when no `thinking` field is sent, and that
# accept `thinking: {"type": "disabled"}` to turn it off. Matched by exact
# model ID only, because other models (e.g. claude-sonnet-5-5) reject it.
THINKING_DISABLE_MODELS = frozenset({'claude-sonnet-5'})
DEFAULT_MAX_TOKENS = 64000
DEFAULT_MAX_TOKENS_NONSTREAMING = 4096
SYSTEM_PROMPT_TEMPLATE = (
    "You are Kwark, a lightweight AI assistant that"
    " performs specific tasks."
    " You use the {model} model. Now is {now}.\n"
)
FILES_API_BETA = "files-api-2025-04-14"
EXTENSION_TYPE_MAP = {
    # Documents
    "pdf": "document",
    "txt": "document",
    "text": "document",
    "md": "document",
    "csv": "document",
    # Images
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "gif": "image",
    "webp": "image",
}


def file_content_type(file_path):
    """Return Anthropic content type for a file path.

    Args:
        file_path: Path to the file

    Returns:
        'document' or 'image' based on extension,
        defaults to 'document' for unknown extensions
    """
    ext = file_path.rsplit(".", 1)[-1].lower()
    return EXTENSION_TYPE_MAP.get(ext, "document")


class AnthropicMessagesBlock(UserList):

    @staticmethod
    def _content(content):
        if isinstance(content, str):
            return [{"type": "text", "text": content}]
        else:
            return [dict(content)]

    def user_says(self, text, file_id=None,
                  file_type="document"):
        """Record what the user said to send to the model

        Args:
            text: The user's message text
            file_id: Optional Anthropic file ID to attach
            file_type: Content type ('document' or 'image')
        """
        if file_id:
            content = [
                {
                    "type": file_type,
                    "source": {
                        "type": "file",
                        "file_id": file_id,
                    },
                },
                {"type": "text", "text": text},
            ]
        else:
            content = text
        self.data.append({
            "role": "user",
            "content": content,
        })

    def model_says(self, content):
        """Record what the model said for future loops"""
        self.data.append({
            "role": "assistant",
            "content": self._content(content)
        })

    def tool_says(self, id, result):
        self.data.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": id,
                "content": result
            }]
        })

    def need_user_input(self):
        return self.data[-1]['role'] == 'assistant'


class AnthropicAIService(AIService):

    service_type = 'anthropic'

    def __init__(self, api_key=None, model=None, toolset=None):
        if api_key:
            self.client = AnthropicSDK(api_key=api_key)
        else:
            self.client = AnthropicSDK()
        self.model = DEFAULT_MODEL if model is None else model
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            model=self.model, now=datetime.now())
        # Support injecting toolset for MCP integration
        self.toolset = toolset if toolset else AnthropicToolset()
        # Event loop for MCP operations (injected by chat command)
        self.mcp_loop = None

    @cached_property
    def available_models(self):
        """Fetch list of available AnthropicSDK models"""
        try:
            response = self.client.models.list()
            models = []
            for model in response:
                models.append({
                    'id': model.id,
                    'display_name': getattr(model, 'display_name', model.id),
                    'created_at': getattr(model, 'created_at', None),
                })
            return models
        except Exception as e:
            print(f"Error fetching models: {e}")
            return []

    def _base_arguments(self, messages: AnthropicMessagesBlock) -> dict:
        """Common API arguments for non-streaming calls."""
        args = {
            'model': self.model,
            'max_tokens': DEFAULT_MAX_TOKENS_NONSTREAMING,
            'system': self.system_prompt,
            'messages': messages,
        }
        if self.model in THINKING_DISABLE_MODELS:
            args['thinking'] = {'type': 'disabled'}
        return args

    def _api_arguments(self, messages: AnthropicMessagesBlock) -> dict:
        """API arguments for streaming calls (tools + full token budget)."""
        return {
            **self._base_arguments(messages),
            'max_tokens': DEFAULT_MAX_TOKENS,
            'tools': self.toolset.definitions,
        }

    def ask(self, text):
        """Send a single prompt and return the plain text response.

        No tools are advertised to the model.
        """
        messages = AnthropicMessagesBlock()
        messages.user_says(text)
        message = self.client.messages.create(**self._base_arguments(messages))
        for content in message.content:
            if content.type == 'text':
                return content.text
        return ""

    def _execute_tool(self, tool_name, tool_input):
        """Execute a tool (MCP or local) and return result.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input arguments for the tool
            
        Returns:
            String result from tool execution
        """
        if self.toolset.is_mcp_tool(tool_name):
            return self._run_mcp_tool(tool_name, tool_input)
        else:
            return self.toolset.run_tool(tool_name, tool_input)

    def query_with_tools(self, text, tool_limit=20):
        """Send prompt and handle tool use loop, return final text.
        
        Args:
            text: The prompt text to send
            tool_limit: Maximum number of tool calls allowed (default 20)
            
        Returns:
            Final text response after all tool use is complete
            
        Raises:
            RuntimeError: If tool use limit is exceeded
        """
        messages = AnthropicMessagesBlock()
        messages.user_says(text)
        message = self.client.messages.create(**self._api_arguments(messages))
        
        tool_count = 0
        while message.stop_reason == 'tool_use':
            # Process all tool use blocks in this message
            for content in message.content:
                if content.type == 'tool_use':
                    tool_count += 1
                    if tool_count > tool_limit:
                        raise RuntimeError(
                            f'Tool use limit of {tool_limit} exceeded')
                    
                    messages.model_says(content)
                    result = self._execute_tool(content.name, content.input)
                    messages.tool_says(content.id, result)
            
            # Get next response after tool results
            message = self.client.messages.create(
                **self._api_arguments(messages))
        
        # Extract final text from response
        for content in message.content:
            if content.type == 'text':
                return content.text
        
        return ""

    def upload_file(self, file_path):
        """Upload a file to Anthropic for use in messages.

        Args:
            file_path: Path to the local file

        Returns:
            The file ID string from Anthropic
        """
        import mimetypes
        import os
        name = os.path.basename(file_path)
        mime = (
            mimetypes.guess_type(file_path)[0]
            or 'application/octet-stream'
        )
        with open(file_path, "rb") as f:
            resp = self.client.beta.files.upload(
                file=(name, f, mime),
            )
        return resp.id

    def delete_file(self, file_id):
        """Delete a previously uploaded file.

        Args:
            file_id: The Anthropic file ID to delete
        """
        self.client.beta.files.delete(file_id)

    def query_with_tools_ui(
            self, text, ui, tool_limit=20,
            file_id=None, file_type="document"):
        """Send prompt with UI feedback and tool loop.

        Streams text output to stderr and displays
        tool use messages.

        Args:
            text: The prompt text to send
            ui: UI object for displaying output
            tool_limit: Max tool calls allowed
            file_id: Optional uploaded file ID
            file_type: Content type ('document'/'image')

        Returns:
            Final text response after tool use

        Raises:
            RuntimeError: If tool use limit exceeded
        """
        betas = [FILES_API_BETA] if file_id else None
        messages = AnthropicMessagesBlock()
        messages.user_says(
            text, file_id=file_id,
            file_type=file_type)
        message = self._stream(messages, ui, betas)

        tool_count = 0
        while message.stop_reason == 'tool_use':
            for content in message.content:
                if content.type == 'tool_use':
                    tool_count += 1
                    if tool_count > tool_limit:
                        raise RuntimeError(
                            'Tool use limit of '
                            f'{tool_limit} exceeded')

                    messages.model_says(content)
                    ui.send(
                        f'Using tool {content.name}...',
                        emphasis=Emphasis.PRINCIPAL)
                    result = self._execute_tool(
                        content.name, content.input)
                    messages.tool_says(
                        content.id, result)

            message = self._stream(
                messages, ui, betas)

        for content in message.content:
            if content.type == 'text':
                return content.text

        return ""

    def _stream(
            self, messages: AnthropicMessagesBlock,
            ui, betas=None):
        """Stream API text to ui, return message.

        Args:
            messages: The messages block to send
            ui: UI for output display
            betas: Optional list of beta features
        """
        args = self._api_arguments(messages)
        if betas:
            ctx = self.client.beta.messages.stream(
                betas=betas, **args)
        else:
            ctx = self.client.messages.stream(**args)
        with ctx as stream:
            for text in stream.text_stream:
                ui.send(
                    text, Emphasis.GENERAL,
                    newline=False, wrap=80)
            message = stream.get_final_message()
        ui.send("\n")
        return message

    def _run_mcp_tool(self, tool_name, arguments):
        """Run MCP tool synchronously (wraps async call)

        Args:
            tool_name: Name of the MCP tool to call
            arguments: Dict of arguments for the tool

        Returns:
            String result suitable for tool_result content
        """
        import asyncio
        import os

        debug = os.environ.get('DEBUG')

        if debug:
            print(f"\n[DEBUG] _run_mcp_tool called:")
            print(f"  tool_name: {tool_name}")
            print(f"  arguments: {arguments}")

        client = self.toolset.find_mcp_client(tool_name)
        if debug:
            print(f"  client found: {client is not None}")
            if client:
                print(f"  client.command: {client.command}")
                print(f"  client.session: {client.session is not None}")

        if not client:
            return f"Error: MCP tool '{tool_name}' not found"

        # Run async tool call in sync context
        try:
            if debug:
                print(f"  Calling client.call_tool(...) on persistent loop")
                print(f"  mcp_loop: {self.mcp_loop}")

            # Use the persistent event loop that was used for connection
            if self.mcp_loop and not self.mcp_loop.is_closed():
                content_blocks = self.mcp_loop.run_until_complete(
                    client.call_tool(tool_name, arguments))
            else:
                # Fallback to creating new loop (shouldn't happen)
                if debug:
                    print(f"  Warning: No persistent loop, using asyncio.run()")
                content_blocks = asyncio.run(
                    client.call_tool(tool_name, arguments))

            if debug:
                print(f"  content_blocks returned: {content_blocks}")
                print(f"  content_blocks type: {type(content_blocks)}")

            # Convert content blocks to string for Anthropic
            result_parts = []
            for block in content_blocks:
                if block.get("type") == "text":
                    result_parts.append(block["text"])

            result = "\n".join(result_parts) if result_parts else ""

            if debug:
                print(f"  result_parts: {result_parts}")
                print(f"  final result: {result}")

            return result
        except Exception as e:
            if debug:
                print(f"  Exception caught: {type(e).__name__}")
                print(f"  Exception str: '{str(e)}'")
                print(f"  Exception repr: {repr(e)}")
                import traceback
                print(f"  Traceback:")
                traceback.print_exc()
            return f"Error calling MCP tool: {str(e)}"

    def chat(self, ui, initial_message=None):
        """Interactive chat with conversation history using UI"""
        messages = AnthropicMessagesBlock()
        if initial_message:
            messages.user_says(initial_message)
            response = self._stream(messages, ui)
            messages.model_says(response)
        while True:
            try:
                user_input = ui.get_text("\nYou: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    ui.send("Goodbye!", Emphasis.INFO)
                    break
                ui.send("\nKwark: ", Emphasis.GENERAL)
                messages.user_says(user_input)
                message = self._stream(messages, ui)
                while not messages.need_user_input():
                    for content in message.content:
                        if content.type == 'text':
                            messages.model_says(content.text)
                        elif content.type == 'tool_use':
                            if content.name == 'exit':  # A specialized tool
                                return
                            else:
                                messages.model_says(content)
                                id = content.id
                                ui.send(
                                    f'Using tool {content.name}...',
                                    emphasis=Emphasis.PRINCIPAL)

                                result = self._execute_tool(
                                    content.name, content.input)

                                messages.tool_says(id, result)
                                message = self._stream(messages, ui)
            except KeyboardInterrupt:
                ui.send("Goodbye!", Emphasis.INFO)
                break
            except EOFError:
                ui.send("Goodbye!", Emphasis.INFO)
                break


class AnthropicToolset:
    """Manages both local and MCP tools"""

    def __init__(self, mcp_clients=None):
        """Initialize toolset with optional MCP clients

        Args:
            mcp_clients: List of MCPClientWrapper instances with tools
                        already discovered
        """
        self.mcp_clients = mcp_clients or []
        self._local_tools = {
            "get_current_time": {
                "name": "get_current_time",
                "description": "Returns the current time",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        self._validate_no_conflicts()

    def _validate_no_conflicts(self):
        """Check for tool name conflicts between local and MCP tools"""
        local_names = set(self._local_tools.keys())
        for client in self.mcp_clients:
            for tool in client.tools:
                if tool["name"] in local_names:
                    raise ValueError(
                        f"Tool name conflict: '{tool['name']}' exists in "
                        f"both local tools and MCP server"
                    )

    @property
    def definitions(self):
        """Return all tool definitions for Anthropic API"""
        tools = list(self._local_tools.values())
        for client in self.mcp_clients:
            tools.extend(client.tools)
        return tools

    def run_tool(self, tool_name, arguments):
        """Execute local tools synchronously."""
        if tool_name == "get_current_time":
            return datetime.now().astimezone().isoformat()
        return None

    def is_mcp_tool(self, tool_name):
        """Check if a tool is from an MCP server"""
        for client in self.mcp_clients:
            for tool in client.tools:
                if tool["name"] == tool_name:
                    return True
        return False

    def find_mcp_client(self, tool_name):
        """Find the MCP client that provides a tool"""
        for client in self.mcp_clients:
            for tool in client.tools:
                if tool["name"] == tool_name:
                    return client
        return None
