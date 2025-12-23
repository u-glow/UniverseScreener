#!/usr/bin/env python3
"""
Check and display the current project maturity level.

This script reads pyproject.toml and shows which testing rules are active.
It's called by pre-commit hooks but never fails - just informs.

Exit code: Always 0 (informational only)
"""

import sys
from pathlib import Path

try:
    import tomli
except ImportError:
    print("⚠️  Warning: 'tomli' not installed")
    print("   Install with: pip install tomli")
    sys.exit(0)


MATURITY_DESCRIPTIONS = {
    "EXPLORATION": {
        "icon": "🔬",
        "desc": "Rapid prototyping, no test requirements",
        "testing": "Optional - only if requested",
        "coverage": "0%",
        "hooks": "None active"
    },
    "DEVELOPMENT": {
        "icon": "🔨",
        "desc": "Building core, critical components tested",
        "testing": "Required for money-critical code",
        "coverage": "40%+ recommended",
        "hooks": "Maturity check only"
    },
    "STABILIZATION": {
        "icon": "🔧",
        "desc": "Pre-production, comprehensive testing",
        "testing": "Full test suite required",
        "coverage": "70%+ required",
        "hooks": "Tests run on commit"
    },
    "PRODUCTION": {
        "icon": "🚀",
        "desc": "Live trading, strict enforcement",
        "testing": "Complete with documentation",
        "coverage": "80%+ enforced",
        "hooks": "All checks enforced"
    }
}


def read_maturity() -> tuple[str, bool]:
    """
    Read maturity level and test strategy status from pyproject.toml.
    
    Returns:
        Tuple of (maturity_level, test_strategy_generated)
    """
    try:
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            return "EXPLORATION", False
        
        with open(pyproject_path, "rb") as f:
            data = tomli.load(f)
        
        project = data.get("tool", {}).get("project", {})
        maturity = project.get("maturity", "EXPLORATION")
        test_strategy = project.get("test_strategy_generated", False)
        
        return maturity, test_strategy
    except Exception as e:
        print(f"⚠️  Error reading pyproject.toml: {e}")
        return "EXPLORATION", False


def main():
    """Display current maturity level and active rules."""
    maturity, test_strategy_done = read_maturity()
    
    if maturity not in MATURITY_DESCRIPTIONS:
        print(f"⚠️  Unknown maturity level: {maturity}")
        print(f"   Valid levels: EXPLORATION, DEVELOPMENT, STABILIZATION, PRODUCTION")
        sys.exit(0)
    
    info = MATURITY_DESCRIPTIONS[maturity]
    
    print(f"\n{info['icon']}  Project Maturity: {maturity}")
    print(f"{'=' * 60}")
    print(f"Description:  {info['desc']}")
    print(f"Testing:      {info['testing']}")
    print(f"Coverage:     {info['coverage']}")
    print(f"Hooks:        {info['hooks']}")
    
    if maturity in ["STABILIZATION", "PRODUCTION"] and not test_strategy_done:
        print(f"\n⚠️  Recommendation: Run 'generate test-strategy' in Cursor")
        print(f"   This will create a customized testing strategy for your system")
    
    if maturity == "PRODUCTION":
        print(f"\n✅ PRODUCTION mode active - all quality checks enforced")
    
    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
