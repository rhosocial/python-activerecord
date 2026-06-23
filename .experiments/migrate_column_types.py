"""
Migrate ColumnDefinition(data_type="TYPE") and JSONTableColumn(..., data_type="TYPE", ...)
to use DataType expression objects.
"""
import re
import os
import glob

REPO = "/Users/vistart/PycharmProjects/rhosocial/python-activerecord"

TYPE_CLASSES = {
    'DECIMAL': ('DecimalType', r'DECIMAL(?:\s*\(\s*(\d+)\s*(?:,\s*(\d+)\s*)?\))?'),
    'NUMERIC': ('DecimalType', r'NUMERIC'),
    'SMALLINT': ('SmallIntType', r'SMALLINT'),
    'TINYINT': ('SmallIntType', r'TINYINT'),
    'INTEGER': ('IntegerType', r'INTEGER'),
    'BIGINT': ('BigIntType', r'BIGINT'),
    'REAL': ('FloatType', r'REAL'),
    'FLOAT': ('FloatType', r'FLOAT'),
    'DOUBLE PRECISION': ('DoubleType', r'DOUBLE\s+PRECISION'),
    'DOUBLE': ('DoubleType', r'DOUBLE'),
    'VARCHAR': ('VarCharType', r'VARCHAR(?:\s*\(\s*(\d+)\s*\))?'),
    'CHARACTER VARYING': ('VarCharType', r'CHARACTER\s+VARYING(?:\s*\(\s*(\d+)\s*\))?'),
    'CHAR': ('CharType', r'CHAR(?:ACTER)?(?:\s*\(\s*(\d+)\s*\))?'),
    'TEXT': ('TextType', r'TEXT'),
    'BOOLEAN': ('BooleanType', r'BOOLEAN'),
    'BOOL': ('BooleanType', r'BOOL'),
    'BLOB': ('BlobType', r'BLOB'),
    'TIMESTAMP': ('TimestampType', r'TIMESTAMP'),
    'DATE': ('DateType', r'DATE'),
    'DATETIME': ('DateTimeType', r'DATETIME'),
}

def construct_replacement(type_str):
    for canonical_name, (cls_name, regex) in TYPE_CLASSES.items():
        m = re.fullmatch(regex, type_str.strip(), re.IGNORECASE)
        if m:
            groups = m.groups()
            # Filter out None groups
            args = [g for g in groups if g is not None]
            if cls_name == 'DecimalType':
                if len(args) == 2:
                    return f'DecimalType(precision={args[0]}, scale={args[1]})', cls_name
                elif len(args) == 1:
                    return f'DecimalType(precision={args[0]})', cls_name
                else:
                    return 'DecimalType()', cls_name
            elif cls_name == 'VarCharType':
                if args:
                    return f'VarCharType({args[0]})', cls_name
                return 'VarCharType()', cls_name
            elif cls_name == 'CharType':
                if args:
                    return f'CharType({args[0]})', cls_name
                return 'CharType()', cls_name
            else:
                return f'{cls_name}()', cls_name
    return None, None


MODULE_PATH = "rhosocial.activerecord.backend.expression.types"


def migrate_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    needed_types = set()

    # Pattern 1: data_key="TYPE" keyword arguments (may span multiple lines)
    def replace_data_type(match):
        full = match.group(0)
        type_str = match.group(1)
        replacement, cls_name = construct_replacement(type_str)
        if replacement:
            needed_types.add(cls_name)
            return full.replace(f'"{type_str}"', replacement)
        return full

    content = re.sub(
        r'data_type\s*=\s*"([^"]*)"',
        replace_data_type,
        content,
    )

    # Pattern 2: JSONTableColumn("name", "TYPE", ...) positional
    def replace_jtc_type(match):
        full = match.group(0)
        type_str = match.group(1)
        replacement, cls_name = construct_replacement(type_str)
        if replacement:
            needed_types.add(cls_name)
            return full.replace(f'"{type_str}"', replacement)
        return full

    content = re.sub(
        r'JSONTableColumn\(\s*"[^"]*"\s*,\s*"([^"]*)"',
        replace_jtc_type,
        content,
    )

    if needed_types:
        lines = content.split('\n')
        # Find last import line from rhosocial
        insert_idx = -1
        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                insert_idx = i
        
        last_import = insert_idx
        if insert_idx >= 0:
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

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, needed_types
    return False, set()


def main():
    files = []
    root = REPO
    patterns = [
        "src/rhosocial/activerecord/backend/impl/**/*.py",
        "tests/**/*.py",
        "docs/examples/**/*.py",
    ]
    for pattern in patterns:
        matched = glob.glob(os.path.join(root, pattern), recursive=True)
        matched = [f for f in matched if '__pycache__' not in f]
        files.extend(matched)
    files = sorted(set(files))
    
    print(f"Scanning {len(files)} files...")
    changed = 0
    for filepath in files:
        was_changed, types_used = migrate_file(filepath)
        if was_changed:
            rel = os.path.relpath(filepath, REPO)
            type_list = ', '.join(sorted(types_used))
            print(f"  ✓ {rel}  [{type_list}]")
            changed += 1
    
    print(f"\nUpdated {changed} files.")


if __name__ == "__main__":
    main()
