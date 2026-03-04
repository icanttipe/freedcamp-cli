# freedcamp-cli

CLI tool for [Freedcamp](https://freedcamp.com) project management.

## Install

### Arch Linux (AUR)

```
yay -S freedcamp-cli
```

### Manual

```
curl -sL https://github.com/icanttipe/freedcamp-cli/raw/main/freedcamp -o ~/.local/bin/freedcamp
chmod +x ~/.local/bin/freedcamp
```

## Setup

```
freedcamp init
```

You'll be prompted for your API key and secret. Get them from Freedcamp under **Settings > API Keys**.

Credentials are stored in `~/.config/freedcamp/config.json` with `600` permissions.

## Usage

```
freedcamp projects                    # List projects
freedcamp tasks <project_id>          # List open tasks
freedcamp tasks <project_id> --all    # Include completed
freedcamp task <task_id>              # Task details

freedcamp create -p <project_id> -t "Title"
freedcamp update <task_id> -s 2       # Set in progress
freedcamp complete <task_id>
freedcamp delete <task_id>

freedcamp raw GET tasks "project_id=123&limit=5"
```

Run `freedcamp <command> --help` for all options.

## MCP server

An MCP server (`freedcamp-mcp`) is included for integration with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and other MCP clients. It exposes all CLI features as tools (list projects, create/update/complete/delete tasks, raw API calls).

Requires `uv`. Add the server to Claude Code:

```
claude mcp add freedcamp -- uv run --script /usr/bin/freedcamp-mcp
```

Or if installed manually:

```
claude mcp add freedcamp -- uv run --script /path/to/freedcamp-mcp.py
```

## Bash completion

Install `bash-completion`, then source the completion file or install it system-wide:

```
source freedcamp-completion.bash
```

The AUR package installs it automatically.

## License

MIT
