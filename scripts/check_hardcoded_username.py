#!/usr/bin/env python3
"""
Check for hardcoded username in codebase.
Run this script before commits to prevent hardcoded username issues.
"""
import os
import re
import sys

# Hardcoded usernames to check
HARDCODED_USERNAMES = ['HubAggregatorBot', 'EarnHubAggregatorBot']

# Directories to check
CHECK_DIRS = [
    'app/services',
    'app/api',
    'app/static',
    'app/adapters'
]

# Files to exclude
EXCLUDE_PATTERNS = [
    '__pycache__',
    '.pyc',
    'check_hardcoded_username.py',
    'update_translations_username_api.py',
    'update_welcome_translation.py'
]

def should_check_file(filepath):
    """Check if file should be checked"""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in filepath:
            return False
    return True

def check_file(filepath):
    """Check file for hardcoded usernames"""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line_num, line in enumerate(lines, 1):
                for username in HARDCODED_USERNAMES:
                    if username in line:
                        # Skip comments and documentation
                        stripped = line.strip()
                        if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('*'):
                            continue
                        # Skip test files with expected values
                        if 'test' in filepath.lower() and ('expected' in line.lower() or 'assert' in line.lower()):
                            continue
                        issues.append({
                            'file': filepath,
                            'line': line_num,
                            'username': username,
                            'content': line.strip()[:100]
                        })
    except Exception as e:
        print(f"⚠️  Error reading {filepath}: {e}")
    return issues

def main():
    """Main check function"""
    print("🔍 Checking for hardcoded usernames...\n")
    
    all_issues = []
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    for check_dir in CHECK_DIRS:
        dir_path = os.path.join(base_dir, check_dir)
        if not os.path.exists(dir_path):
            continue
        
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, base_dir)
                
                if not should_check_file(rel_path):
                    continue
                
                issues = check_file(filepath)
                all_issues.extend(issues)
    
    if all_issues:
        print(f"❌ Found {len(all_issues)} issues with hardcoded username:\n")
        for issue in all_issues:
            print(f"  {issue['file']}:{issue['line']}")
            print(f"    Username: {issue['username']}")
            print(f"    Content: {issue['content']}")
            print()
        print("⚠️  Please replace hardcoded username with bot.config.username or {{bot_username}} placeholder")
        return 1
    else:
        print("✅ No hardcoded username found in codebase!")
        return 0

if __name__ == '__main__':
    sys.exit(main())
