#!/usr/bin/env python3
"""
Verify all test files document which test aspects they cover.

This script is ONLY ENFORCED when maturity = "PRODUCTION" in pyproject.toml.
For other maturity levels, it runs but only warns without failing.

Exit codes:
    0: All test files properly documented OR maturity < PRODUCTION
    1: Missing/incomplete documentation found AND maturity = PRODUCTION
"""

import re
import sys
import tomli
from pathlib import Path
from typing import List, Tuple

# The 10 mandatory test aspects from .cursorrules
REQUIRED_ASPECTS = [
    "Business Logic",
    "Edge Cases",
    "Error Handling",
    "Data Quality",
    "Time Logic",
    "Security",
    "Performance",
    "Idempotency",
    "State",
    "Integration"
]


def read_maturity_level() -> str:
    """
    Read maturity level from pyproject.toml.
    
    Returns:
        Maturity level string or "EXPLORATION" if not found
    """
    try:
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            return "EXPLORATION"
        
        with open(pyproject_path, "rb") as f:
            data = tomli.load(f)
        
        return data.get("tool", {}).get("project", {}).get("maturity", "EXPLORATION")
    except Exception:
        return "EXPLORATION"


def check_test_file(filepath: Path) -> Tuple[bool, str]:
    """
    Check if test file documents covered aspects.
    
    Args:
        filepath: Path to the test file
        
    Returns:
        Tuple of (passed, message)
    """
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return False, f"Could not read file: {e}"
    
    # Look for aspect coverage comment block
    if "Coverage by Test Aspect:" not in content:
        return False, "Missing 'Coverage by Test Aspect:' documentation block"
    
    # Count covered aspects (✅) or N/A (⚠️)
    # Also accept text alternatives: [x], [OK], [NA], [N/A]
    covered_checkmarks = len(re.findall(r'[✅⚠️]', content))
    covered_text = len(re.findall(r'\[(x|X|OK|ok|NA|N/A|na)\]', content))
    covered = covered_checkmarks + covered_text
    
    if covered < len(REQUIRED_ASPECTS):
        return False, (
            f"Only {covered}/{len(REQUIRED_ASPECTS)} aspects documented. "
            f"Each aspect must be marked with ✅, ⚠️, or [x]/[OK]/[NA]"
        )
    
    # Check if at least some aspects are marked as covered (not all N/A)
    actually_covered = len(re.findall(r'✅', content)) + len(re.findall(r'\[(x|X|OK|ok)\]', content))
    if actually_covered == 0:
        return False, "All aspects marked as N/A - at least some should be tested"
    
    return True, "All aspects documented"


def find_test_files(base_path: Path = Path("tests")) -> List[Path]:
    """
    Find all test files in the tests directory.
    
    Args:
        base_path: Base directory to search (default: tests/)
        
    Returns:
        List of test file paths
    """
    if not base_path.exists():
        return []
    
    test_files = []
    for pattern in ["test_*.py", "*_test.py"]:
        test_files.extend(base_path.rglob(pattern))
    
    # Exclude __init__.py and conftest.py
    test_files = [
        f for f in test_files 
        if f.name not in ("__init__.py", "conftest.py")
    ]
    
    return sorted(test_files)


def main():
    """Main entry point for the test aspect checker."""
    maturity = read_maturity_level()
    
    print(f"🔍 Checking test aspect coverage documentation...")
    print(f"   Current maturity level: {maturity}\n")
    
    # Only enforce for PRODUCTION
    enforce = (maturity == "PRODUCTION")
    
    if not enforce:
        print(f"ℹ️  Test aspect documentation not enforced for {maturity} level")
        print(f"   (Will be enforced when maturity = 'PRODUCTION')\n")
    
    test_files = find_test_files()
    
    if not test_files:
        print("⚠️  No test files found in tests/ directory")
        if maturity in ["DEVELOPMENT", "STABILIZATION", "PRODUCTION"]:
            print("   Consider creating tests for critical components")
        sys.exit(0)
    
    failures = []
    successes = []
    
    for test_file in test_files:
        passed, msg = check_test_file(test_file)
        
        if not passed:
            failures.append(f"{test_file}: {msg}")
        else:
            successes.append(test_file)
    
    # Print results
    if successes:
        print(f"✅ {len(successes)} test file(s) properly documented:")
        for success in successes:
            print(f"   • {success}")
        print()
    
    if failures:
        icon = "❌" if enforce else "⚠️ "
        print(f"{icon} {len(failures)} test file(s) missing proper documentation:\n")
        for failure in failures:
            print(f"   • {failure}")
        print()
        
        if enforce:
            print("💡 Fix: Add a test aspect coverage block to each test file.")
            print("   See .cursorrules for the required format.")
            print()
            print("   Example:")
            print('   """')
            print("   Tests for my_module.py")
            print()
            print("   Coverage by Test Aspect:")
            print("   ✅ 1. Business Logic: test_foo, test_bar")
            print("   ✅ 2. Edge Cases: test_empty_input, test_none_values")
            print("   ⚠️  3. Error Handling: N/A (no error conditions)")
            print("   ...")
            print('   """')
            print()
            sys.exit(1)
        else:
            print(f"ℹ️  This will become an error when maturity = 'PRODUCTION'")
            print()
            sys.exit(0)
    
    print("✅ All test files properly document aspect coverage")
    print(f"   Total: {len(successes)} test file(s)")
    sys.exit(0)


if __name__ == "__main__":
    # Check if tomli is available
    try:
        import tomli
    except ImportError:
        print("⚠️  Warning: 'tomli' not installed, assuming EXPLORATION mode")
        print("   Install with: pip install tomli")
        sys.exit(0)
    
    main()
