# Kwark

⚠️ DISCLAIMER: This is a hobby/personal project. Not a commercial product. Not for production use.

## Tap into AI brilliance from a simple shell command

Kwark provides AI-powered assistance through the Anthropic Claude API. The tool has two main commands for interacting with AI:

- **`chat`**: Interactive chat interface with conversation history
- **`activate`**: Execute custom AI prompts with tool support

And several convenience commands:
- `doc`: Summarize discussions for technical documentation
- `branch`: Generate git branch names
- `commit`: Generate git commit messages
- `transcribe`: Transcribe a file (PDF, image or text) to Markdown
- `models`: List available Anthropic AI models
- `journal`: AI-assisted personal journal

All commands use the Anthropic API and require an API key.

## Main Commands

### Chat Command

The `chat` command provides an interactive interface to have conversations with AI. It maintains conversation history and allows for back-and-forth dialogue.

**Input Format:** YAML with optional `prompt:` and `mcp:` entries

```bash
# Start chat with an initial message
cat << EOF | kwark chat
prompt: What is the capital of France?
EOF
# Output: The capital of France is Paris.
# 
# You: What's the population?
# Assistant: Paris has a population of approximately 2.1 million...

# Start chat without initial message
kwark chat
# You: Hello, how are you?
# Assistant: I'm doing well, thank you! How can I help you today?

# Start chat with MCP servers
cat << EOF | kwark chat
prompt: What time is it?
mcp:
  - python /path/to/time_server.py
EOF
```

In chat mode, type your messages and the AI will respond while maintaining conversation context. The conversation continues until you type `quit`, `exit`, or `bye` to end the session, or use Ctrl+C to interrupt.

### Activate Command

The `activate` command executes custom AI prompts with tool support. Unlike other commands that use predefined prompt templates, activate allows for flexible, ad-hoc AI queries.

**Input Format:** YAML with required `prompt:` and optional `file:` and `mcp:` entries

```bash
# Simple query
cat << EOF | kwark activate
prompt: Tell a story about angels in the style of Mark Twain
EOF

# Question answering
cat << EOF | kwark activate
prompt: What is the capital of France?
EOF

# Code generation
cat << EOF | kwark activate
prompt: Write a Python function to calculate fibonacci numbers
EOF

# Attach a file for the AI to process
cat << EOF | kwark activate
prompt: Summarise the key figures in this document.
file: /path/to/statement.pdf
EOF

# Using MCP servers for tool access
cat << EOF | kwark activate
prompt: What time is it right now?
mcp:
  - python /path/to/time_server.py
EOF

# Complex multi-line prompts
cat << EOF | kwark activate
prompt: |
  Analyze the following code and suggest improvements:
  def calc(x, y):
      return x + y
EOF
```

**Note:** The activate command requires a `prompt:` entry. If no prompt is provided, it will return an error.

#### File Uploads

The optional `file:` entry specifies a path to a local file to attach to the prompt. The file is uploaded to the Anthropic API, included as a document in the message, and automatically deleted from Anthropic's servers after the query completes. This is useful for asking questions about PDFs, text files, and other documents.

## MCP Server Configuration

Both the `chat` and `activate` commands support MCP (Model Context Protocol) servers, which provide additional tools that the AI can use to answer queries. This is how you give the AI access to real-time information, APIs, databases, and other external resources.

MCP support is an optional extra. Install Kwark with `pipx install 'kwark[mcp]'` (or `pip install 'kwark[mcp]'`) to use it. If MCP servers are configured but the extra is not installed, `chat` and `activate` exit with an error explaining how to install it.

### Configuration Methods

MCP servers can be configured in two ways, and servers from both sources are merged together:

**1. Configuration File** (applies to all commands):

Create or edit `~/.kwark.yml`:

```yaml
kwark:
  api:
    anthropic:
      key: $(op read "op://Private/Anthropic/api-key")
  mcp:
    - python /path/to/time_server.py
    - node /path/to/weather_server.js --api-key YOUR_KEY
    - /usr/local/bin/custom-tool-server
```

**2. Input YAML** (per-command, merged with config file servers):

```bash
# For activate command
cat << EOF | kwark activate
prompt: What time is it in Tokyo?
mcp:
  - python /path/to/timezone_server.py
EOF

# For chat command
cat << EOF | kwark chat
prompt: Hello, what can you help me with?
mcp:
  - python /path/to/custom_tools.py
EOF
```

### How It Works

1. MCP servers are stdio-based processes that provide tools to the AI
2. Each server entry is a command line (command + arguments)
3. Servers from the config file and input YAML are combined
4. The AI automatically discovers and uses available tools as needed
5. Tool calls are made transparently during conversation or prompt execution

### Example: Time Server

```bash
# In ~/.kwark.yml
kwark:
  mcp:
    - python /usr/local/bin/time_server.py

# Then use it
cat << EOF | kwark activate
prompt: What time is it right now?
EOF
# The AI will automatically call the time server tool to get the current time
```

## Convenience Commands

### Doc Command

The `doc` command processes text from standard input and returns a concise summary suitable for technical documentation.

```bash
pbpaste | kwark doc | pbcopy
```

### Branch Command

The `branch` command generates git branch names from input text.

```bash
echo "Add ability for users to export their transaction history to PDF" | kwark branch
# Output: 20250113-export-transaction-history

# Create a branch directly
git checkout -b $(echo "Implement role-based access controls" | kwark branch)
```

### Commit Command

The `commit` command generates commit messages from git diff output.

```bash
git diff --staged | kwark commit
# Output: Fix validation bug in user registration

# Commit directly with AI-generated message
git add .
git commit -m "$(git diff --staged | kwark commit)"
```

### Transcribe Command

The `transcribe` command transcribes a file (PDF, image or text) to Markdown and writes it to standard output, so it can be redirected to a file.

```bash
kwark transcribe statement.pdf > statement.pdf.md
```

The output starts with an HTML comment containing a disclaimer (the AI may make errors, and tables and other structured data are converted to YAML), then a blank line, then the Markdown. Use `--no-disclaimer` to leave the comment out:

```bash
kwark transcribe receipt.jpg --no-disclaimer
```

Supported file types are `.pdf`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.txt`, `.md` and `.csv`. If the file type is unsupported, the file can't be read, the output is truncated or the API call fails, the error is written to standard error and the command exits with a non-zero status.

The `transcribe` command uses Claude Opus 4.6 (`claude-opus-4-6`) by default. To change it, use `--model` (`-m`) or set `kwark-transcribe-model` in your configuration file. The general `kwark-model` setting does not apply to `transcribe` (see [Model selection](#model-selection)).

### Journal Command

The `journal` command helps you maintain a personal journal with
AI-generated monthly summaries. Journal files are organized by month
and stored in a directory you configure.

**Configuration:** Two entries are required in your config file:

```yaml
kwark:
  journal:
    dir: ~/path/to/your/journal
  editor: /usr/bin/vi
```

**File layout:**

- Monthly journal: `<journal-dir>/<YYYY>/<YYYY><MM>-journal.md`
- Monthly summary: `<journal-dir>/<YYYY>/<YYYY><MM>-summary.md`

**Optional customisation file:**

Place a `feedback-prompt.md` file inside your journal directory to
provide personal guidelines that shape the AI's feedback style and
focus. If the file is absent the AI will still respond, using its
default behaviour.

**What the command does:**

Each time you run `kwark journal`:

1. It ensures a summary exists for the previous month. If no summary
   file is found, it reads all monthly journal files from January of
   the previous year through the end of last month, sends them to the
   AI, and writes a summary file.
2. It opens your configured editor with a temporary file so you can
   write a new journal entry.
3. If you wrote anything, the entry is appended to the monthly journal
   file for the current month. Each day gets a `# YYYY-MM-DD` heading;
   multiple entries on the same day are separated by `---`.
4. If you wrote anything, the AI analyses your entry alongside the
   previous-month summary, any earlier entries for the current month,
   and the guidelines in `feedback-prompt.md` (if present), then
   prints its response together with your entry text.
5. After each entry you are asked whether to add another entry or stop,
   so you can write multiple entries in a single session.

```bash
kwark journal
```

### Models Command

The `models` command lists available Anthropic AI models.

```bash
kwark models
# Output:
# - created_at: '2025-10-01'
#   display_name: Claude Haiku 4.5
#   id: claude-haiku-4-5-20251001
```

**Note:** Kwark uses Claude Sonnet 5 by default. You can select a different model with `--model` (see below).

## Library usage (`kwark.ai`)

Other Python applications can import Kwark's library layer directly. It takes all settings as arguments (no Kwark config is read), prints nothing, and raises `kwark.ai.KwarkAIError` subclasses on failure.

### Transcribe a file to Markdown

```python
from kwark.ai import transcribe, TRANSCRIBE_DISCLAIMER, KwarkAIError

try:
    markdown = transcribe('invoice.pdf')  # api_key=None uses ANTHROPIC_API_KEY
except KwarkAIError as error:
    print(error)
else:
    print(f"{TRANSCRIBE_DISCLAIMER}\n\n{markdown}")
```

Supported file types are `.pdf`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.txt`, `.md` and `.csv`. Optional keyword arguments are `model` (default `claude-opus-4-6`), `api_key`, `prompt` (default `TRANSCRIBE_PROMPT`) and `max_tokens` (default 32000). If the output would be truncated at `max_tokens`, `TruncatedResponseError` is raised. The disclaimer is not added to the result, so callers can add it if they want it.

### Extract structured data

```python
from kwark.ai import extract

schema = {
    'type': 'object',
    'properties': {
        'category': {'type': 'string'},
        'date': {'type': 'string'},
    },
    'required': ['category'],
}
record = extract(markdown, schema,
                 instructions='Classify this document for filing.')
```

`extract()` returns a dict matching the JSON Schema (which must have `type: object`), using forced tool use for most models (see below for the exceptions). Optional keyword arguments are `instructions` (added to the system prompt), `model` (default `claude-sonnet-5`), `api_key` and `max_tokens` (default 4096, including any thinking). If a `required` property is missing from the result, `SchemaValidationError` is raised; if the model doesn't call the tool, `MissingToolUseError`; if the output is truncated, `TruncatedResponseError`.

Claude Opus 5.5, Sonnet 5.5, Fable 5.1 and Mythos 5.1 reject forced tool use. For these models `extract()` lets the model choose (`tool_choice: auto`) and marks the tool `strict`, so the API constrains the tool input to the schema. Strict mode requires `additionalProperties: false` on every object, so `extract()` adds it to a copy of the schema wherever it isn't set. Nothing else is changed: keywords such as `enum`, `const` and `pattern` reach the API and are enforced. Strict mode supports only a subset of JSON Schema; a schema that uses an unsupported keyword (such as `minimum`) gets an API error, raised as `APIError`. If the model doesn't call the tool, `MissingToolUseError` is raised.

## Quick installation (MacOS)

If you don't already have `pipx`:

```bash
brew install pipx
```

Then install with `pipx`:

```bash
pipx install kwark
```

To use MCP servers with `chat` and `activate`, install the `mcp` extra instead:

```bash
pipx install 'kwark[mcp]'
```

If you already installed Kwark without the extra, reinstall it with `pipx install --force 'kwark[mcp]'`.

Kwark can also be used as a Python library (`pip install kwark`); the `mcp` package and its dependencies are only installed with the extra.

## Authentication and configuration

Kwark uses Claude Sonnet 5 by default through the Anthropic API, and requires an API key.

There are three options for providing the API key to Kwark, in order of precedence:

1. **Command line option** (highest precedence): Provide the API key as a `--api-key` option to any kwark command (e.g., `kwark doc --api-key YOUR_KEY` or `kwark chat --api-key YOUR_KEY`)
2. **Configuration file**: Provide the API key in a configuration file using the [WizLib ConfigHandler](https://wizlib.steamwiz.io/api/config-handler) protocol
3. **Environment variable** (lowest precedence): Set the default `ANTHROPIC_API_KEY` environment variable before running the `kwark` command

The command line option takes precedence over both the configuration file and environment variable. If no command line option is provided, the configuration file is checked. If neither is available, the environment variable is used as a fallback.

We recommend storing the key in a password manager such as 1Password, then using a config file to retrieve the key at runtime instead of storing the key itself in a file. For example, create a file at `~/.kwark.yml` with the following contents:

```yaml
kwark:
  api:
    anthropic:
      key: $(op read "op://Private/Anthropic/api-key")
```

### Model selection

All AI commands (`chat`, `activate`, `doc`, `branch`, `commit`, `journal`, `transcribe`) accept a `--model` (`-m`) option to designate the Anthropic model to use:

```bash
git diff --staged | kwark commit --model claude-opus-4-5
echo "add login page" | kwark branch -m claude-haiku-4-5-20251001
```

You can also set a default model in your configuration file:

```yaml
kwark:
  model: claude-opus-4-5
```

The `--model` command line option takes precedence over the configuration file. If neither is specified, Kwark uses Claude Sonnet 5 (`claude-sonnet-5`). Use `kwark models` to list available model IDs.

The `transcribe` command has its own setting and default. It uses `--model` first, then `transcribe: model:` (`kwark-transcribe-model`) from the configuration file, then Claude Opus 4.6 (`claude-opus-4-6`). It ignores the general `model` setting.

```yaml
kwark:
  transcribe:
    model: claude-opus-4-5
```

### Tool Use Limit

The `activate` command supports a configurable limit on the number of tool calls that can be made in succession. This prevents infinite loops or excessive API usage. The default limit is 20 tool calls.

You can configure this limit in your configuration file:

```yaml
kwark:
  tooluselimit: 25
```

If the limit is exceeded, the activate command will return an error message.

<br/>

---

<br/>

<a href="https://www.flaticon.com/free-icons/particles">Particles icon by Freepik-Flaticon</a>
