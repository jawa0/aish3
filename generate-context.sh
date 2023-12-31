#!/bin/zsh
find . -type d -name "__pycache__" -exec rm -rf {} \;

TREE=$(tree)

echo "Project directory and file layout:"
echo "$TREE"

# Use find to get all .py files, .gitignore files, Makefile but excluding .git directories and read into an array
files=("${(@f)$(find . -name '.git' -prune -false -o -name "*.py" -o -name ".gitignore" -o -name "Makefile")}")

# Loop through each file
for file in "${files[@]}"; do
  echo "========================"
  echo "$file:"
  echo "========================"
  cat "$file"
  echo "\n"
done
