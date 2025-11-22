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

    def find_task_by_guid(self, guid_or_prefix):
        """Find a task by exact GUID or prefix match"""
        tasks = self.get_tasks()
        guid_lower = guid_or_prefix.lower()

        # Try exact match first
        task = next((t for t in tasks if t['guid'].lower() == guid_lower), None)
        if task:
            return task

        # Try prefix match
        matches = [t for t in tasks if t['guid'].lower().startswith(guid_lower)]
        if len(matches) == 0:
            raise Exception(f"No task found matching '{guid_or_prefix}'")
        elif len(matches) > 1:
            matching_guids = ', '.join([t['guid'][:8] for t in matches])
            raise Exception(f"Ambiguous GUID prefix '{guid_or_prefix}' matches multiple tasks: {matching_guids}")

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

    def complete_task(self, guid, completed=True):
        """Mark a task as completed or uncompleted"""
        task = self.find_task_by_guid(guid)

        task['completed'] = completed
        if completed:
            task['completeTime'] = datetime.now().strftime('%B %d, %Y %H:%M:%S')
        else:
            task['completeTime'] = ''

        return self.update_tasks(task)

    def delete_task(self, guid):
        """Delete a task by setting sortPosition to -1"""
        task = self.find_task_by_guid(guid)

        task['sortPosition'] = -1
        return self.update_tasks(task)

    def update_task(self, guid, title=None, notes=None):
        """Update task title and/or notes"""
        task = self.find_task_by_guid(guid)

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


def format_task(task, show_notes=False):
    """Format a task for display"""
    status = '✓' if task.get('completed') else '○'
    title = task.get('title', 'Untitled')
    guid = task.get('guid', '')[:8]  # Show first 8 chars of GUID

    output = f"  {status} [{guid}] {title}"

    if show_notes and task.get('notes'):
        output += f"\n    Notes: {task['notes']}"

    if task.get('completed') and task.get('completeTime'):
        output += f"\n    Completed: {task['completeTime']}"

    return output


def cmd_list(client, args):
    """List all tasks"""
    tasks = client.get_tasks()

    if not tasks:
        print("No tasks found.")
        return

    # Separate completed and incomplete tasks
    incomplete = [t for t in tasks if not t.get('completed')]
    completed = [t for t in tasks if t.get('completed')]

    if incomplete:
        print("Incomplete Tasks:")
        for task in sorted(incomplete, key=lambda t: t.get('sortPosition', 0)):
            print(format_task(task, args.verbose))

    if completed and not args.hide_completed:
        if incomplete:
            print()
        print("Completed Tasks:")
        for task in sorted(completed, key=lambda t: t.get('sortPosition', 0)):
            print(format_task(task, args.verbose))

    print(f"\nTotal: {len(incomplete)} incomplete, {len(completed)} completed")


def cmd_add(client, args):
    """Add a new task"""
    tasks = client.create_task(args.title, args.notes or '')
    print(f"Task created: {args.title}")


def cmd_complete(client, args):
    """Mark task as completed"""
    tasks = client.complete_task(args.guid, completed=True)
    print(f"Task {args.guid} marked as completed")


def cmd_uncomplete(client, args):
    """Mark task as not completed"""
    tasks = client.complete_task(args.guid, completed=False)
    print(f"Task {args.guid} marked as incomplete")


def cmd_delete(client, args):
    """Delete a task"""
    if not args.force:
        response = input(f"Delete task {args.guid}? [y/N] ")
        if response.lower() not in ('y', 'yes'):
            print("Cancelled")
            return

    tasks = client.delete_task(args.guid)
    print(f"Task {args.guid} deleted")


def cmd_update(client, args):
    """Update a task"""
    tasks = client.update_task(args.guid, args.title, args.notes)
    print(f"Task {args.guid} updated")


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
    complete_parser.add_argument('guid', help='Task GUID (or prefix)')

    # Uncomplete command
    uncomplete_parser = subparsers.add_parser('uncomplete', aliases=['uncheck'], help='Mark task as incomplete')
    uncomplete_parser.add_argument('guid', help='Task GUID (or prefix)')

    # Delete command
    delete_parser = subparsers.add_parser('delete', aliases=['rm'], help='Delete a task')
    delete_parser.add_argument('guid', help='Task GUID (or prefix)')
    delete_parser.add_argument('-f', '--force', action='store_true', help='Skip confirmation')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update a task')
    update_parser.add_argument('guid', help='Task GUID (or prefix)')
    update_parser.add_argument('-t', '--title', help='New title')
    update_parser.add_argument('-n', '--notes', help='New notes')

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
        elif args.command == 'cleanup':
            cmd_cleanup(client, args)
        else:
            parser.print_help()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
