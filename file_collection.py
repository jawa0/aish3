import fnmatch
import os
import re


def parse_sexp(sexp_str):
    tokens = re.findall(r'\(|\)|"[\w*.\\/]*"|\w+[-\w*]*', sexp_str)
    
    def parse_tokens(tokens):
        res = []
        token = tokens.pop(0)
        
        while tokens and token != ')':
            if token == '(':
                res.append(parse_tokens(tokens))
            else:
                res.append(token.strip('"'))
            if tokens: token = tokens.pop(0)
        
        if token != ')':
            raise ValueError("Unbalanced parentheses")
        return res
    
    if tokens and tokens.pop(0) == '(':
        return parse_tokens(tokens)
    else:
        raise ValueError("Invalid S-expression")

def match_files(root_path, patterns, include_subdirs=False):
    matched_files = []
    for path, dirs, files in os.walk(root_path):
        if not include_subdirs and path != root_path:
            dirs.clear()  # Prevent descending into subdirs
        for pattern in patterns:
            for filename in fnmatch.filter(files, pattern):
                matched_files.append(os.path.join(path, filename))
    return matched_files

def handle_subtree(subtree_root, rules):
    subtree_files = []
    for rule in rules:
        command, *args = rule
        if command == 'include':
            subtree_files.extend(match_files(subtree_root, args))
        elif command == 'include-recursive':
            subtree_files.extend(match_files(subtree_root, args, include_subdirs=True))
        # ... handle exclude and exclude-recursive similarly
    return subtree_files

def collect_files(spec, root='.'):
    collected_files = set()
    
    for item in spec:
        if isinstance(item, str):  # Direct inclusion of a file or directory
            if os.path.isdir(os.path.join(root, item)):
                collected_files.update(match_files(os.path.join(root, item), ['*']))
            else:
                collected_files.add(os.path.join(root, item))
        elif isinstance(item, list):  # Handling rules
            command, *args = item
            if command == 'include':
                collected_files.update(match_files(root, args))
            elif command == 'include-recursive':
                collected_files.update(match_files(root, args, include_subdirs=True))
            elif command == 'exclude':
                collected_files.difference_update(match_files(root, args))
            elif command == 'exclude-recursive':
                collected_files.difference_update(match_files(root, args, include_subdirs=True))
            elif command == 'exclude-in':
                subdir, *patterns = args
                collected_files.difference_update(match_files(os.path.join(root, subdir), patterns))
            elif command == 'subtree':
                subtree_root, *rules = args
                collected_files.update(handle_subtree(os.path.join(root, subtree_root), rules))
            # ... Continue for other commands

    return list(collected_files)

if __name__=="__main__":
    # Example usage:
    sexp_str = '''(("exclude" .env)
                    "README.md"
                    ("include-recursive" "*.py")
                    ("exclude" "__pycache__/")
                    ("exclude" "trywake.py")
                    ("exclude" "candlestick.py")
                )'''

    print(f'Parsing S-expression: {sexp_str}')
    input_sexp = parse_sexp(sexp_str)

    # Get relative file paths from the project root directory
    project_files = collect_files(input_sexp, root='.')
    print(project_files)
