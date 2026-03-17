"""
Script to fix all trading_system. import prefixes
"""

import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace trading_system. imports
        content = re.sub(
            r'from trading_system\.([a-zA-Z_][a-zA-Z0-9_\.]*) import',
            r'from \1 import',
            content
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all Python files."""
    root = Path(".")
    fixed_count = 0
    
    # Find all Python files
    for py_file in root.rglob("*.py"):
        # Skip virtual environments and build directories
        if any(part in py_file.parts for part in ['.venv', 'venv', '__pycache__', 'build', 'dist']):
            continue
        
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()
