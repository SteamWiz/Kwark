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

## Quick installation (MacOS)

If you don't already have `pipx`:

```bash
brew install pipx
```

Then install with `pipx`:

```bash
pipx install kwark
```

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

All AI commands (`chat`, `activate`, `doc`, `branch`, `commit`, `journal`) accept a `--model` (`-m`) option to designate the Anthropic model to use:

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
