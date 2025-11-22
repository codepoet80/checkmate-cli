# Checkmate CLI

A command-line client for the Checkmate todo list service, written in Python 3 with zero external dependencies.

## Features

- List, add, update, and delete tasks
- Mark tasks as complete/incomplete
- Clean up completed tasks
- Simple configuration management
- Uses only Python 3 standard library

## Installation

1. Clone or copy this directory
2. Make the script executable:
   ```bash
   chmod +x checkmate.py
   ```
3. Optionally, create a symlink in your PATH:
   ```bash
   ln -s $(pwd)/checkmate.py /usr/local/bin/checkmate
   ```

## Configuration

First, configure your connection to the Checkmate service:

```bash
./checkmate.py login
```

You'll be prompted for:
- **Service URL**: The base URL of your checkmate-service (e.g., `http://localhost/checkmate-service`)
- **Move notation**: Your chess move (e.g., "King to Queen 4")
- **Grandmaster name**: Your grandmaster name (e.g., "Kasparov")

Configuration is saved to `~/.checkmate.conf` with restricted permissions.

You can also provide these as command-line arguments:
```bash
./checkmate.py login --url http://localhost/checkmate-service --move "King to Queen 4" --grandmaster Kasparov
```

## Usage

### List Tasks

```bash
# List all tasks
./checkmate.py list

# List with verbose output (shows notes)
./checkmate.py list -v

# Hide completed tasks
./checkmate.py list --hide-completed

# Short alias
./checkmate.py ls
```

### Add a Task

```bash
# Add a simple task
./checkmate.py add "Buy groceries"

# Add a task with notes
./checkmate.py add "Call dentist" -n "Schedule appointment for next week"
```

### Complete a Task

```bash
# Mark task as completed (use GUID or prefix)
./checkmate.py complete abc123de

# Short alias
./checkmate.py check abc123de
```

### Uncomplete a Task

```bash
# Mark task as incomplete
./checkmate.py uncomplete abc123de

# Short alias
./checkmate.py uncheck abc123de
```

### Update a Task

```bash
# Update title
./checkmate.py update abc123de --title "New title"

# Update notes
./checkmate.py update abc123de --notes "Updated notes"

# Update both
./checkmate.py update abc123de -t "New title" -n "New notes"
```

### Delete a Task

```bash
# Delete with confirmation
./checkmate.py delete abc123de

# Delete without confirmation
./checkmate.py delete abc123de --force

# Short alias
./checkmate.py rm abc123de -f
```

### Cleanup Completed Tasks

```bash
# Remove all completed tasks (with confirmation)
./checkmate.py cleanup

# Skip confirmation
./checkmate.py cleanup --force
```

## Override Configuration

You can override the saved configuration for a single command:

```bash
./checkmate.py --url http://other-server/checkmate --move "Different Move" --grandmaster "Different GM" list
```

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## Architecture

The CLI uses:
- `urllib` for HTTP requests
- `json` for JSON parsing
- `argparse` for command-line interface
- `configparser` for configuration management
- `pathlib` and `os` for file operations

## Security

- Configuration file is stored with 600 permissions (readable only by owner)
- Credentials are sent via HTTP headers (Grandmaster) and query parameters (move)
- User-Agent header is included in all requests

## Task GUID Format

Tasks are identified by GUIDs. When listing tasks, only the first 8 characters are shown for readability. You can use either the full GUID or a unique prefix when specifying tasks in commands.

## License

This software is provided as-is for use with the Checkmate todo list service.
