#!/usr/bin/env python3
"""
Fix E2E tests to use async database operations
Converts sync calls to async/await
"""
import os
import re
from pathlib import Path

def fix_async_operations(file_path):
    """Fix async operations in a test file"""
    with open(file_path, 'r') as f:
        content = f.read()

    original = content

    # Fix db_session.commit() -> await db_session.commit()
    content = re.sub(
        r'(\s+)db_session\.commit\(\)',
        r'\1await db_session.commit()',
        content
    )

    # Fix db_session.refresh() -> await db_session.refresh()
    content = re.sub(
        r'(\s+)db_session\.refresh\(',
        r'\1await db_session.refresh(',
        content
    )

    # Fix db_session.rollback() -> await db_session.rollback()
    content = re.sub(
        r'(\s+)db_session\.rollback\(\)',
        r'\1await db_session.rollback()',
        content
    )

    # Fix db_session.flush() -> await db_session.flush()
    content = re.sub(
        r'(\s+)db_session\.flush\(\)',
        r'\1await db_session.flush()',
        content
    )

    # Fix db.commit() -> await db.commit()
    content = re.sub(
        r'(\s+)db\.commit\(\)',
        r'\1await db.commit()',
        content
    )

    # Fix db.refresh() -> await db.refresh()
    content = re.sub(
        r'(\s+)db\.refresh\(',
        r'\1await db.refresh(',
        content
    )

    # Fix db.rollback() -> await db.rollback()
    content = re.sub(
        r'(\s+)db\.rollback\(\)',
        r'\1await db.rollback()',
        content
    )

    # Fix db.flush() -> await db.flush()
    content = re.sub(
        r'(\s+)db\.flush\(\)',
        r'\1await db.flush()',
        content
    )

    # Fix db.execute() -> await db.execute()
    content = re.sub(
        r'(\s+)db\.execute\(',
        r'\1await db.execute(',
        content
    )

    # Fix db_session.execute() -> await db_session.execute()
    content = re.sub(
        r'(\s+)db_session\.execute\(',
        r'\1await db_session.execute(',
        content
    )

    if content != original:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Fix all e2e test files"""
    e2e_dir = Path(__file__).parent / 'tests' / 'e2e'

    if not e2e_dir.exists():
        print(f"Error: {e2e_dir} does not exist")
        return

    files_fixed = 0
    for test_file in e2e_dir.glob('test_*.py'):
        if test_file.name == '__init__.py':
            continue

        print(f"Processing {test_file.name}...", end=' ')
        if fix_async_operations(test_file):
            print("✅ Fixed")
            files_fixed += 1
        else:
            print("⏭️  No changes needed")

    print(f"\n✅ Fixed {files_fixed} files")

if __name__ == '__main__':
    main()
