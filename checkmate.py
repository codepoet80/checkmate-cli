#!/usr/bin/env python3
"""
Checkmate CLI - Command-line client for Checkmate todo list service
Uses only Python 3 standard library (no external dependencies)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime
import configparser


class CheckmateClient:
    """Client for interacting with Checkmate service API"""

    def __init__(self, base_url, move, grandmaster):
        self.base_url = base_url.rstrip('/')
        self.move = move
        self.grandmaster = grandmaster
        self.user_agent = 'checkmate-cli/1.0'

    def _make_request(self, endpoint, method='GET', data=None):
        """Make HTTP request to the service"""
        url = f"{self.base_url}/{endpoint}"

        # Add move as query parameter
        if '?' in url:
            url += f"&move={urllib.parse.quote(self.move)}"
        else:
            url += f"?move={urllib.parse.quote(self.move)}"

        headers = {
            'User-Agent': self.user_agent,
            'Grandmaster': self.grandmaster
        }

        if data is not None:
            data = json.dumps(data).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_msg)
                raise Exception(error_json.get('error', error_msg))
            except json.JSONDecodeError:
                raise Exception(f"HTTP {e.code}: {error_msg}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e.reason}")

    def get_tasks(self):
        """Retrieve all tasks for the current move"""
        result = self._make_request('read-notation.php')
        return result.get('tasks', [])

    def update_tasks(self, tasks):
        """Update one or more tasks"""
        result = self._make_request('update-notation.php', method='POST', data=tasks)
        return result.get('tasks', [])

    def cleanup_completed(self):
        """Remove all completed tasks"""
        result = self._make_request('cleanup-notation.php')
        return result.get('tasks', [])

    def find_task_by_id(self, task_id):
        """Find a task by position number or GUID"""
        all_tasks = self.get_tasks()

        # Sort all tasks by sortPosition in reverse order (newest first)
        tasks = sorted(all_tasks, key=lambda t: t.get('sortPosition', 0), reverse=True)

        # Try as position number first
        try:
            position = int(task_id)
            if position < 1 or position > len(tasks):
                raise Exception(f"Task number {position} is out of range (1-{len(tasks)})")
            return tasks[position - 1]  # Convert 1-based to 0-based index
        except ValueError:
            # Not a number, try as GUID
            guid_lower = task_id.lower()

            # Try exact match first
            task = next((t for t in all_tasks if t['guid'].lower() == guid_lower), None)
            if task:
                return task

            # Try prefix match
            matches = [t for t in all_tasks if t['guid'].lower().startswith(guid_lower)]
            if len(matches) == 0:
                raise Exception(f"No task found matching '{task_id}'")
            elif len(matches) > 1:
                matching_guids = ', '.join([t['guid'][:8] for t in matches])
                raise Exception(f"Ambiguous GUID prefix '{task_id}' matches multiple tasks: {matching_guids}")

            return matches[0]

    def create_task(self, title, notes=''):
        """Create a new task"""
        task = {
            'guid': 'new',
            'title': title[:200],  # Max 200 chars
            'notes': notes[:1000],  # Max 1000 chars
            'completed': False,
            'createTime': datetime.now().strftime('%B %d, %Y %H:%M:%S'),
            'completeTime': '',
            'sortPosition': 0
        }
        return self.update_tasks(task)

    def complete_task(self, task_id, completed=True):
        """Mark a task as completed or uncompleted"""
        task = self.find_task_by_id(task_id)

        task['completed'] = completed
        if completed:
            task['completeTime'] = datetime.now().strftime('%B %d, %Y %H:%M:%S')
        else:
            task['completeTime'] = ''

        return self.update_tasks(task)

    def delete_task(self, task_id):
        """Delete a task by setting sortPosition to -1"""
        task = self.find_task_by_id(task_id)

        task['sortPosition'] = -1
        return self.update_tasks(task)

    def update_task(self, task_id, title=None, notes=None):
        """Update task title and/or notes"""
        task = self.find_task_by_id(task_id)

        if title is not None:
            task['title'] = title[:200]
        if notes is not None:
            task['notes'] = notes[:1000]

        return self.update_tasks(task)


class ConfigManager:
    """Manage configuration file"""

    def __init__(self):
        self.config_path = Path.home() / '.checkmate.conf'
        self.config = configparser.ConfigParser()
        if self.config_path.exists():
            self.config.read(self.config_path)

    def get(self, key, section='DEFAULT'):
        """Get configuration value"""
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return None

    def set(self, key, value, section='DEFAULT'):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value

    def save(self):
        """Save configuration to file"""
        with open(self.config_path, 'w') as f:
            self.config.write(f)
        # Set restrictive permissions
        os.chmod(self.config_path, 0o600)


def format_task(task, position, show_notes=False):
    """Format a task for display"""
    status = '✓' if task.get('completed') else '○'
    title = task.get('title', 'Untitled')

    output = f"  {status} {position:2d}. {title}"

    if show_notes:
        if task.get('notes'):
            output += f"\n      Notes: {task['notes']}"

        if task.get('completed') and task.get('completeTime'):
            output += f"\n      Completed: {task['completeTime']}"

    return output


def cmd_list(client, args):
    """List all tasks"""
    all_tasks = client.get_tasks()

    if not all_tasks:
        print("No tasks found.")
        return

    # Sort all tasks by sortPosition in reverse order (newest first)
    tasks = sorted(all_tasks, key=lambda t: t.get('sortPosition', 0), reverse=True)

    # Filter out completed tasks if requested
    if args.hide_completed:
        tasks = [t for t in tasks if not t.get('completed')]

    # Count totals
    incomplete = sum(1 for t in all_tasks if not t.get('completed'))
    completed = sum(1 for t in all_tasks if t.get('completed'))

    # Display all tasks in one list
    position = 1
    for task in tasks:
        print(format_task(task, position, args.verbose))
        position += 1

    print(f"\nTotal: {incomplete} incomplete, {completed} completed")


def cmd_add(client, args):
    """Add a new task"""
    tasks = client.create_task(args.title, args.notes or '')
    print(f"Task created: {args.title}")


def cmd_complete(client, args):
    """Mark task as completed"""
    tasks = client.complete_task(args.task_id, completed=True)
    print(f"Task {args.task_id} marked as completed")


def cmd_uncomplete(client, args):
    """Mark task as not completed"""
    tasks = client.complete_task(args.task_id, completed=False)
    print(f"Task {args.task_id} marked as incomplete")


def cmd_delete(client, args):
    """Delete a task"""
    if not args.force:
        response = input(f"Delete task {args.task_id}? [y/N] ")
        if response.lower() not in ('y', 'yes'):
            print("Cancelled")
            return

    tasks = client.delete_task(args.task_id)
    print(f"Task {args.task_id} deleted")


def cmd_update(client, args):
    """Update a task"""
    tasks = client.update_task(args.task_id, args.title, args.notes)
    print(f"Task {args.task_id} updated")


def cmd_note(client, args):
    """Show note for a task"""
    task = client.find_task_by_id(args.task_id)

    print(f"Task: {task['title']}")
    if task.get('notes'):
        print(f"Notes: {task['notes']}")
    else:
        print("No notes")


def cmd_cleanup(client, args):
    """Remove all completed tasks"""
    if not args.force:
        response = input("Remove all completed tasks? [y/N] ")
        if response.lower() not in ('y', 'yes'):
            print("Cancelled")
            return

    tasks = client.cleanup_completed()
    print("Completed tasks removed")


def cmd_login(client, args):
    """Configure connection settings"""
    config = ConfigManager()

    base_url = args.url or input("Service URL: ")
    move = args.move or input("Move notation: ")
    grandmaster = args.grandmaster or input("Grandmaster name: ")

    config.set('base_url', base_url)
    config.set('move', move)
    config.set('grandmaster', grandmaster)
    config.save()

    print(f"Configuration saved to {config.config_path}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Checkmate CLI - Command-line todo list client',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global options
    parser.add_argument('--url', help='Service base URL')
    parser.add_argument('--move', help='Move notation')
    parser.add_argument('--grandmaster', help='Grandmaster name')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    list_parser = subparsers.add_parser('list', aliases=['ls'], help='List all tasks')
    list_parser.add_argument('-v', '--verbose', action='store_true', help='Show notes and details')
    list_parser.add_argument('--hide-completed', action='store_true', help='Hide completed tasks')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new task')
    add_parser.add_argument('title', help='Task title')
    add_parser.add_argument('-n', '--notes', help='Task notes')

    # Complete command
    complete_parser = subparsers.add_parser('complete', aliases=['check'], help='Mark task as completed')
    complete_parser.add_argument('task_id', help='Task number from list')

    # Uncomplete command
    uncomplete_parser = subparsers.add_parser('uncomplete', aliases=['uncheck'], help='Mark task as incomplete')
    uncomplete_parser.add_argument('task_id', help='Task number from list')

    # Delete command
    delete_parser = subparsers.add_parser('delete', aliases=['rm'], help='Delete a task')
    delete_parser.add_argument('task_id', help='Task number from list')
    delete_parser.add_argument('-f', '--force', action='store_true', help='Skip confirmation')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update a task')
    update_parser.add_argument('task_id', help='Task number from list')
    update_parser.add_argument('-t', '--title', help='New title')
    update_parser.add_argument('-n', '--notes', help='New notes')

    # Note command
    note_parser = subparsers.add_parser('note', aliases=['notes'], help='Show notes for a task')
    note_parser.add_argument('task_id', help='Task number from list')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Remove all completed tasks')
    cleanup_parser.add_argument('-f', '--force', action='store_true', help='Skip confirmation')

    # Login command
    login_parser = subparsers.add_parser('login', help='Configure connection settings')
    login_parser.add_argument('--url', help='Service URL')
    login_parser.add_argument('--move', help='Move notation')
    login_parser.add_argument('--grandmaster', help='Grandmaster name')

    args = parser.parse_args()

    # Handle login command specially (doesn't need client)
    if args.command == 'login':
        cmd_login(None, args)
        return

    # Load configuration
    config = ConfigManager()
    base_url = args.url or config.get('base_url')
    move = args.move or config.get('move')
    grandmaster = args.grandmaster or config.get('grandmaster')

    if not base_url or not move or not grandmaster:
        print("Error: Missing configuration. Please run 'checkmate.py login' first,", file=sys.stderr)
        print("       or provide --url, --move, and --grandmaster options.", file=sys.stderr)
        sys.exit(1)

    # Create client
    client = CheckmateClient(base_url, move, grandmaster)

    # Execute command
    try:
        if args.command in ('list', 'ls'):
            cmd_list(client, args)
        elif args.command == 'add':
            cmd_add(client, args)
        elif args.command in ('complete', 'check'):
            cmd_complete(client, args)
        elif args.command in ('uncomplete', 'uncheck'):
            cmd_uncomplete(client, args)
        elif args.command in ('delete', 'rm'):
            cmd_delete(client, args)
        elif args.command == 'update':
            cmd_update(client, args)
        elif args.command in ('note', 'notes'):
            cmd_note(client, args)
        elif args.command == 'cleanup':
            cmd_cleanup(client, args)
        else:
            parser.print_help()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
