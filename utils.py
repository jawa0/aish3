import os
import os.path
from typing import Set, Optional


def unique_filename(candidate_filename: str) -> str:
    """
    Function to generate a unique filename in the current directory.

    This function takes a candidate filename, checks if it already exists in 
    the current working directory, and if it does, appends a counter value 
    before the file extension until a unique filename is found.

    Parameters: 
    candidate_filename (str): Initial filename supplied by the user.

    Returns: 
    candidate_filename (str): A unique filename. If the initial filename 
    is not unique, the function will add a counter to the base of the filename,
    incrementing it until a unique filename is found.

    Example:
    >>> unique_filename('test.txt')
    'test_1.txt'
    """

    counter = 1
    name, ext = os.path.splitext(candidate_filename)

    while os.path.exists(candidate_filename):
        candidate_filename = f"{name}_{counter}{ext}"
        counter += 1

    return candidate_filename
    
    
def strip_and_unquote(input_str: str) -> str:
    """
    Strips leading and trailing whitespace and removes surrounding quote characters from a string.

    Args:
        input_str (str): The input string to be processed.

    Returns:
        str: The stripped and unquoted string.
    """
    # Strip the input string
    stripped_str = input_str.strip()
    # Define quote characters to be removed
    quote_chars = ["'", '"', "'''", '"""']
    # Remove wrapping quote characters
    for quote in quote_chars:
        if stripped_str.startswith(quote) and stripped_str.endswith(quote):
            stripped_str = stripped_str[len(quote):-len(quote)]
            break  # Break after the first match to avoid removing nested quotes
    return stripped_str


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
