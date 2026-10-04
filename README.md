
# Kwark

⚠️ DISCLAIMER: This is a hobby/personal project. Not a commercial product. Not for production use.

## Tap into AI brilliance from a simple shell command

**NOTE** Usage documentation lives in the `PACKAGE.md` file, published at https://pypi.org/project/kwark. The text below is for developers (including AI agents).

## Development setup

Requires Python 3.14 or higher. Uses [Dyngle](https://dyngle.steamwiz.io/) for developer controls (installed separately). Shared Dyngle operations live in the `.conf` submodule ([SteamWiz/Conf](https://github.com/SteamWiz/Conf)), so clone with `--recurse-submodules` or run `git submodule update --init`. All commands assume the `pwd` is the root of the project.

- `dyngle run init` - Create the virtual environment and install poetry
- `dyngle run dependencies` - Install the required packages using poetry
- `dyngle run test` - Run the full unit test suite and check coverage (same as CI/CD)
- `dyngle run style` - Run style checks
- `dyngle run build` - Create a local build

The `mcp` package is an optional extra for users (`kwark[mcp]`), but it is also in the Poetry dev group, so `dyngle run dependencies` installs it and the test suite covers MCP. Code must not import `mcp` at module level outside `kwark/ai_services/mcp_client.py`, which guards the import so Kwark works without it.

The `kwark.ai` package is a library layer for other SteamWiz apps (e.g. Filez4Eva). It must import only the standard library and `anthropic`: no WizLib, no `mcp`, no `kwark.command` or `kwark.ai_services`, no config reading and no printing. Settings come in as arguments (`api_key=None` means the SDK default), system prompts are task-specific (no Kwark persona), there are no incidental API calls such as `models.list()`, and errors are raised as `kwark.ai.KwarkAIError` subclasses with the original exception as the cause. To keep `import kwark.ai` lightweight, `kwark/__init__.py` loads `KwarkApp` (defined in `kwark/app.py`) lazily; don't add eager imports there. A subprocess test in `test/test_20261004_ai_transcribe.py` enforces this.

GitHub Actions performs the entire build/test/release cycle using the shared [SteamWiz actions](https://github.com/SteamWiz/actions).

## Libraries

This application makes heavy use of [WizLib](https://wizlib.steamwiz.io/) and all code changes are expected to comply with, and take advantage of, the framework. See in particular the WizLib documentation on testing techniques for WizLib-based applications.
