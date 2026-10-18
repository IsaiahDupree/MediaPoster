#!/usr/bin/env python3
"""
Audit script to find all mock AI calls in the codebase.

Usage:
    python scripts/audit_mock_ai.py
    python scripts/audit_mock_ai.py --fix  # Attempt to fix (dry-run by default)
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class MockAIFinding:
    file_path: str
    line_number: int
    line_content: str
    issue_type: str
    severity: str
    recommendation: str

def find_mock_ai_calls(root_dir: Path) -> List[MockAIFinding]:
    """Find all mock AI calls in the codebase."""
    findings = []
    
    # Patterns to search for
    patterns = [
        (r'TODO.*[Aa][Ii]', 'TODO', 'high', 'TODO comment for AI implementation'),
        (r'TODO.*[Oo]pen[Aa][Ii]', 'TODO', 'high', 'TODO comment for OpenAI implementation'),
        (r'mock.*[Aa][Ii]|mock.*openai|MOCK.*AI', 'Mock Function', 'high', 'Mock AI function found'),
        (r'Mock.*summary|mock.*content|mock.*generation', 'Mock Return', 'high', 'Mock return value'),
        (r'# Mock|# mock|# MOCK', 'Mock Comment', 'medium', 'Mock implementation comment'),
        (r'placeholder.*[Aa][Ii]|fake.*[Aa][Ii]', 'Placeholder', 'medium', 'Placeholder AI implementation'),
        (r'def.*_mock.*\(|async def.*_mock.*\(', 'Mock Function Def', 'low', 'Mock function definition (may be test-only)'),
    ]
    
    # Files to check
    python_files = list(root_dir.rglob('*.py'))
    
    # Exclude test files and migrations
    exclude_dirs = {'tests', 'migrations', '__pycache__', '.git', 'venv', 'env'}
    python_files = [
        f for f in python_files 
        if not any(exclude in str(f) for exclude in exclude_dirs)
    ]
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    for pattern, issue_type, severity, recommendation in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Skip if it's clearly a test file or acceptable mock
                            if 'test_' in str(file_path) or 'mock_provider' in str(file_path):
                                continue
                            
                            findings.append(MockAIFinding(
                                file_path=str(file_path.relative_to(root_dir)),
                                line_number=line_num,
                                line_content=line.strip(),
                                issue_type=issue_type,
                                severity=severity,
                                recommendation=recommendation
                            ))
        except Exception as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)
    
    return findings

def group_findings(findings: List[MockAIFinding]) -> Dict[str, List[MockAIFinding]]:
    """Group findings by file."""
    grouped = {}
    for finding in findings:
        if finding.file_path not in grouped:
            grouped[finding.file_path] = []
        grouped[finding.file_path].append(finding)
    return grouped

def print_report(findings: List[MockAIFinding]):
    """Print audit report."""
    grouped = group_findings(findings)
    
    print("=" * 80)
    print("AI MOCK CALLS AUDIT REPORT")
    print("=" * 80)
    print(f"\nTotal findings: {len(findings)}")
    print(f"Files affected: {len(grouped)}\n")
    
    # Count by severity
    high = [f for f in findings if f.severity == 'high']
    medium = [f for f in findings if f.severity == 'medium']
    low = [f for f in findings if f.severity == 'low']
    
    print(f"🔴 High Priority: {len(high)}")
    print(f"🟡 Medium Priority: {len(medium)}")
    print(f"🟢 Low Priority: {len(low)}\n")
    
    # Group by file
    print("\n" + "=" * 80)
    print("FINDINGS BY FILE")
    print("=" * 80)
    
    for file_path, file_findings in sorted(grouped.items()):
        print(f"\n📄 {file_path}")
        print("-" * 80)
        
        for finding in sorted(file_findings, key=lambda x: x.line_number):
            severity_icon = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(finding.severity, '⚪')
            
            print(f"  {severity_icon} Line {finding.line_number}: [{finding.issue_type}]")
            print(f"     {finding.line_content[:100]}")
            print(f"     💡 {finding.recommendation}")
            print()

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Audit mock AI calls in codebase')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix issues (not implemented yet)')
    parser.add_argument('--root', type=str, default='.', help='Root directory to search (default: current dir)')
    
    args = parser.parse_args()
    
    root_dir = Path(args.root).resolve()
    
    if not root_dir.exists():
        print(f"Error: Root directory does not exist: {root_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Scanning: {root_dir}")
    findings = find_mock_ai_calls(root_dir)
    
    if findings:
        print_report(findings)
        
        # Exit with error code if high-priority findings
        high_priority = [f for f in findings if f.severity == 'high']
        if high_priority:
            print(f"\n⚠️  Found {len(high_priority)} high-priority issues!")
            sys.exit(1)
    else:
        print("✅ No mock AI calls found!")
        sys.exit(0)

if __name__ == '__main__':
    main()

