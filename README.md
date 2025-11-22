# Checkmate CLI

A command-line client for the Checkmate todo list service, written in Python 3 with zero external dependencies.

## Features

- List, add, update, and delete tasks
- Mark tasks as complete/incomplete
- View task notes quickly
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
# Mark task as completed (use task number from list)
./checkmate.py complete 5

# Short alias
./checkmate.py check 5
```

### Uncomplete a Task

```bash
# Mark task as incomplete
./checkmate.py uncomplete 5

# Short alias
./checkmate.py uncheck 5
```

### Update a Task

```bash
# Update title
./checkmate.py update 5 --title "New title"

# Update notes
./checkmate.py update 5 --notes "Updated notes"

# Update both
./checkmate.py update 5 -t "New title" -n "New notes"
```

### View Task Notes

```bash
# Show notes for a task
./checkmate.py note 5

# Alias
./checkmate.py notes 5
```

### Delete a Task

```bash
# Delete with confirmation
./checkmate.py delete 5

# Delete without confirmation
./checkmate.py delete 5 --force

# Short alias
./checkmate.py rm 5 -f
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

## Task Numbering

Tasks are displayed with sequential numbers (1, 2, 3, etc.) when you list them. Use these numbers to interact with tasks. The numbers correspond to the position in the list, making it easy to complete, update, or delete tasks without typing long IDs.

## License

This software is provided as-is for use with the Checkmate todo list service.
