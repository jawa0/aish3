import os
import argparse
from typing import Set, Optional

def generate_tree(directory: str, show_hidden: bool = False, traverse_hidden: bool = False, ignore_pattern: Optional[str] = None) -> str:
    """
    Generate a directory tree as a string.

    Args:
        directory: The directory to generate the tree for.
        show_hidden: Whether to show hidden files and directories (default: False).
        traverse_hidden: Whether to traverse hidden directories (default: False).
        ignore_pattern: A pipe-delimited string of file and directory names to ignore (default: None).

    Returns:
        The directory tree as a string.
    """
    tree = []
    ignore: Set[str] = set(ignore_pattern.split('|')) if ignore_pattern else set()

    def traverse(current_dir: str, level: int, prefix: str = '') -> None:
        entries = sorted(os.listdir(current_dir))
        num_entries = len(entries)
        visible_entries = []
        for entry in entries:
            if entry in ignore or (not show_hidden and entry.startswith('.')):
                continue
            visible_entries.append(entry)
        num_visible_entries = len(visible_entries)
        for i, entry in enumerate(visible_entries):
            is_last_entry = i == num_visible_entries - 1
            entry_prefix = '└── ' if is_last_entry else '├── '
            full_path = os.path.join(current_dir, entry)
            is_dir = os.path.isdir(full_path)
            if not show_hidden and entry.startswith('.'):
                continue
            entry_suffix = '/' if is_dir and (not traverse_hidden and entry.startswith('.')) else ''
            tree.append(f"{prefix}{entry_prefix}{entry}{entry_suffix}")
            if is_dir and (traverse_hidden or not entry.startswith('.')):
                if is_last_entry:
                    new_prefix = prefix + '    '
                else:
                    new_prefix = prefix + '│   '
                traverse(full_path, level + 1, new_prefix)

    traverse(directory, 0)
    return '\n'.join(tree)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a directory tree.')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to generate the tree for (default: current directory)')
    parser.add_argument('--ignore-dot-files', '-d', action='store_true', help='Ignore files and directories starting with a dot (default: False)')
    parser.add_argument('--expand-dot-folders', '-e', action='store_true', help='Expand directories starting with a dot (default: False)')
    parser.add_argument('--ignore', '-i', help='Pipe-delimited string of file and directory names to ignore')

    args = parser.parse_args()

    show_hidden = not args.ignore_dot_files
    traverse_hidden = args.expand_dot_folders
    ignore_pattern = args.ignore

    stree = generate_tree(args.directory, show_hidden=show_hidden, traverse_hidden=traverse_hidden, ignore_pattern=ignore_pattern)
    print(stree)
    