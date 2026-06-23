"""
Fix corrupted \1/\2 backreferences by restoring from git and re-running migration correctly.
"""
import re
import os
import subprocess
import glob

REPO = "/Users/vistart/PycharmProjects/rhosocial/python-activerecord"

# Mapping functions to extract correct values from type strings
TYPE_REGEXES = [
    (r'VARCHAR\s*\(\s*(\d+)\s*\)', lambda m: f'VarCharType({m.group(1)})', 'VarCharType'),
    (r'DECIMAL\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', lambda m: f'DecimalType(precision={m.group(1)}, scale={m.group(2)})', 'DecimalType'),
    (r'DECIMAL\s*\(\s*(\d+)\s*\)', lambda m: f'DecimalType(precision={m.group(1)})', 'DecimalType'),
    (r'DECIMAL', lambda m: 'DecimalType()', 'DecimalType'),
    (r'VARCHAR', lambda m: 'VarCharType()', 'VarCharType'),
    (r'CHAR\s*\(\s*(\d+)\s*\)', lambda m: f'CharType({m.group(1)})', 'CharType'),
    (r'CHAR', lambda m: 'CharType()', 'CharType'),
    (r'SMALLINT', lambda m: 'SmallIntType()', 'SmallIntType'),
    (r'INTEGER', lambda m: 'IntegerType()', 'IntegerType'),
    (r'BIGINT', lambda m: 'BigIntType()', 'BigIntType'),
    (r'REAL', lambda m: 'FloatType()', 'FloatType'),
    (r'FLOAT', lambda m: 'FloatType()', 'FloatType'),
    (r'DOUBLE\s+PRECISION', lambda m: 'DoubleType()', 'DoubleType'),
    (r'DOUBLE', lambda m: 'DoubleType()', 'DoubleType'),
    (r'TEXT', lambda m: 'TextType()', 'TextType'),
    (r'BOOLEAN', lambda m: 'BooleanType()', 'BooleanType'),
    (r'BLOB', lambda m: 'BlobType()', 'BlobType'),
    (r'TIMESTAMP', lambda m: 'TimestampType()', 'TimestampType'),
    (r'DATE', lambda m: 'DateType()', 'DateType'),
    (r'DATETIME', lambda m: 'DateTimeType()', 'DateTimeType'),
]

MODULE_PATH = "rhosocial.activerecord.backend.expression.types"


def find_type_replacement(type_str):
    """Given a type string like 'VARCHAR(255)' or 'DECIMAL(10,2)', return DataType expression and class name."""
    for regex, builder, cls_name in TYPE_REGEXES:
        m = re.fullmatch(regex, type_str.strip(), re.IGNORECASE)
        if m:
            return builder(m), cls_name
    return None, None


def migrate_content(content):
    """Apply migration to file content. Returns (new_content, needed_types, was_changed)."""
    needed_types = set()
    original = content

    def replace_type(match):
        full = match.group(0)
        type_str = match.group(1)
        replacement, cls_name = find_type_replacement(type_str)
        if replacement:
            needed_types.add(cls_name)
            return full.replace(f'"{type_str}"', replacement)
        return full

    # Pattern 1: ColumnDefinition positional: ColumnDefinition("name", "TYPE"...
    content = re.sub(
        r'ColumnDefinition\(\s*"[^"]*"\s*,\s*"([^"]*)"',
        replace_type,
        content,
    )

    # Pattern 2: data_key="TYPE" keyword argument
    def replace_data_type(match):
        full = match.group(0)
        type_str = match.group(1)
        replacement, cls_name = find_type_replacement(type_str)
        if replacement:
            needed_types.add(cls_name)
            return full.replace(f'"{type_str}"', replacement)
        return full

    content = re.sub(
        r'data_type\s*=\s*"([^"]*)"',
        replace_data_type,
        content,
    )

    # Pattern 3: JSONTableColumn positional
    def replace_jtc_type(match):
        full = match.group(0)
        type_str = match.group(1)
        replacement, cls_name = find_type_replacement(type_str)
        if replacement:
            needed_types.add(cls_name)
            return full.replace(f'"{type_str}"', replacement)
        return full

    content = re.sub(
        r'JSONTableColumn\(\s*"[^"]*"\s*,\s*"([^"]*)"',
        replace_jtc_type,
        content,
    )

    # Add imports if needed
    if needed_types:
        lines = content.split('\n')
        insert_idx = -1
        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                insert_idx = i

        if insert_idx >= 0:
            last_import = insert_idx
            for i in range(insert_idx + 1, len(lines)):
                if lines[i].startswith('from ') or lines[i].startswith('import '):
                    last_import = i
                else:
                    break

            type_names = sorted(needed_types)
            import_line = f"from {MODULE_PATH} import {', '.join(type_names)}"
            already = any(import_line in line for line in lines)
            if not already:
                lines.insert(last_import + 1, import_line)
                content = '\n'.join(lines)

    return content, needed_types, content != original


def fix_file(filepath):
    # Check if file has backreference corruption
    with open(filepath, 'rb') as f:
        content_bytes = f.read()
    has_corruption = b'\\1' in content_bytes or b'\\2' in content_bytes

    # Get git original
    rel = os.path.relpath(filepath, REPO)
    result = subprocess.run(
        ['git', 'show', f'HEAD:{rel}'],
        capture_output=True, text=True, cwd=REPO, timeout=10,
    )
    if result.returncode != 0:
        return False

    git_content = result.stdout

    # If corrupted, start from git original and re-apply migration
    if has_corruption:
        new_content, needed_types, changed = migrate_content(git_content)
        if changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  ✓ {rel}  [{', '.join(sorted(needed_types))}]")
            return True
    return False


def main():
    result = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD'],
        capture_output=True, text=True, cwd=REPO, timeout=10,
    )
    modified = [os.path.join(REPO, f) for f in result.stdout.strip().split('\n') if f]

    print(f"Checking {len(modified)} modified files for corruption...")
    fixed = 0
    for filepath in modified:
        if filepath.endswith('.py'):
            if fix_file(filepath):
                fixed += 1

    print(f"\nFixed {fixed} corrupted files.")


if __name__ == "__main__":
    main()
