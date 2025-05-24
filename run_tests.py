#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import jmapc

        print(f"jmapc {jmapc.__version__} is available")
        return True
    except ImportError:
        print("jmapc not found!")
        print("   Install dependencies: pip install -r requirements.txt")
        return False


def run_unit_tests():
    """Run unit tests only (no integration tests)."""
    print("🧪 Running unit tests...")
    cmd = ["pytest", "tests/", "-m", "not integration", "-v"]
    return subprocess.run(cmd).returncode


def run_integration_tests():
    """Run integration tests with real Fastmail token."""
    print("🔗 Running integration tests...")

    token = os.getenv("FASTMAIL_AUTH_TOKEN_TEST")
    if not token:
        print("FASTMAIL_AUTH_TOKEN_TEST not set!")
        print("   Set your real Fastmail token to run integration tests:")
        print("   export FASTMAIL_AUTH_TOKEN_TEST=your_real_token")
        return 1

    cmd = [
        "pytest",
        "tests/",
        "-m",
        "integration",
        "-v",
        "-s",
    ]  # Added -s to see print output
    return subprocess.run(cmd).returncode


def run_all_tests():
    """Run all tests."""
    print("🚀 Running all tests...")
    cmd = ["pytest", "tests/", "-v"]
    return subprocess.run(cmd).returncode


def run_specific_test(test_name):
    """Run a specific test file or test function."""
    print(f"🎯 Running specific test: {test_name}")
    cmd = ["pytest", test_name, "-v", "-s"]
    return subprocess.run(cmd).returncode


def main():
    """Main test runner."""
    # Check dependencies first
    if not check_dependencies():
        return 1

    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        test_type = "unit"

    # Handle specific test files
    if test_type.startswith("tests/") or test_type.endswith(".py"):
        return run_specific_test(test_type)

    if test_type in ["unit", "u"]:
        return run_unit_tests()
    elif test_type in ["integration", "int", "i"]:
        return run_integration_tests()
    elif test_type in ["all", "a"]:
        return run_all_tests()
    else:
        print("Usage: python run_tests.py [unit|integration|all|test_file]")
        print("  unit        - Run unit tests only (default)")
        print(
            "  integration - Run integration tests (requires FASTMAIL_AUTH_TOKEN_TEST)"
        )
        print("  all         - Run all tests")
        print("  test_file   - Run specific test file (e.g., tests/test_auth.py)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
