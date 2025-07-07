#!/usr/bin/env python3
"""
Test runner script for the A2A Agent Discovery System.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", coverage=False, verbose=False, parallel=False):
    """
    Run the test suite.
    
    Args:
        test_type (str): Type of tests to run (all, unit, integration, aws)
        coverage (bool): Whether to generate coverage report
        verbose (bool): Whether to run tests in verbose mode
        parallel (bool): Whether to run tests in parallel
    """
    # Get the project root directory
    project_root = Path(__file__).parent
    tests_dir = project_root / "tests"
    
    # Ensure we're in the right directory
    os.chdir(project_root)
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    cmd.append(str(tests_dir))
    
    # Add markers based on test type
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "aws":
        cmd.extend(["-m", "aws"])
    elif test_type == "slow":
        cmd.extend(["-m", "slow"])
    
    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=A2A",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
    
    # Add verbose flag
    if verbose:
        cmd.append("-v")
    
    # Add parallel execution
    if parallel:
        cmd.extend(["-n", "auto"])
    
    # Add additional pytest options
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    print(f"Running tests with command: {' '.join(cmd)}")
    print(f"Test type: {test_type}")
    print(f"Coverage: {coverage}")
    print(f"Verbose: {verbose}")
    print(f"Parallel: {parallel}")
    print("-" * 50)
    
    try:
        # Run the tests
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")
        
        return result.returncode
        
    except FileNotFoundError:
        print("❌ Error: pytest not found. Please install test dependencies:")
        print("pip install -r tests/requirements-test.txt")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def install_test_dependencies():
    """Install test dependencies."""
    project_root = Path(__file__).parent
    requirements_file = project_root / "tests" / "requirements-test.txt"
    
    if not requirements_file.exists():
        print("❌ Test requirements file not found")
        return False
    
    print("Installing test dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True)
        print("✅ Test dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install test dependencies: {e}")
        return False


def check_test_environment():
    """Check if test environment is properly set up."""
    print("Checking test environment...")
    
    # Check if pytest is available
    try:
        subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                      capture_output=True, check=True)
        print("✅ pytest is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pytest not found")
        return False
    
    # Check if test directory exists
    tests_dir = Path(__file__).parent / "tests"
    if tests_dir.exists():
        print("✅ Tests directory exists")
    else:
        print("❌ Tests directory not found")
        return False
    
    # Check if test files exist
    test_files = list(tests_dir.glob("test_*.py"))
    if test_files:
        print(f"✅ Found {len(test_files)} test files")
    else:
        print("❌ No test files found")
        return False
    
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run A2A Agent Discovery System tests")
    parser.add_argument(
        "--type", "-t",
        choices=["all", "unit", "integration", "aws", "slow"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies"
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Check test environment"
    )
    
    args = parser.parse_args()
    
    if args.install_deps:
        if install_test_dependencies():
            return 0
        else:
            return 1
    
    if args.check_env:
        if check_test_environment():
            return 0
        else:
            return 1
    
    # Check environment before running tests
    if not check_test_environment():
        print("\nTo fix the test environment, run:")
        print("python run_tests.py --install-deps")
        return 1
    
    # Run tests
    return run_tests(
        test_type=args.type,
        coverage=args.coverage,
        verbose=args.verbose,
        parallel=args.parallel
    )


if __name__ == "__main__":
    sys.exit(main()) 