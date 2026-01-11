#!/usr/bin/env python3
"""
Unified test runner for MBED project

Runs unit and integration tests with coverage reporting.
"""

import sys
import os
import unittest
import argparse
from pathlib import Path
import time
from typing import List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def run_tests(test_dir: str = "tests", pattern: str = "test_*.py", 
              verbosity: int = 2) -> unittest.TestResult:
    """
    Run tests in specified directory
    
    Args:
        test_dir: Directory containing tests
        pattern: Test file pattern
        verbosity: Output verbosity level
    
    Returns:
        TestResult object
    """
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern=pattern)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result


def run_with_coverage(test_dir: str = "tests", pattern: str = "test_*.py") -> Tuple[unittest.TestResult, float]:
    """
    Run tests with coverage reporting
    
    Args:
        test_dir: Directory containing tests
        pattern: Test file pattern
    
    Returns:
        Tuple of (TestResult, coverage_percentage)
    """
    try:
        import coverage
        
        # Start coverage
        cov = coverage.Coverage(source=['src/mbed'])
        cov.start()
        
        # Run tests
        result = run_tests(test_dir, pattern)
        
        # Stop coverage
        cov.stop()
        cov.save()
        
        # Generate report
        print("\n" + "="*70)
        print("Coverage Report")
        print("="*70)
        cov.report()
        
        # Get coverage percentage
        total_coverage = cov.report(show_missing=False, skip_empty=True)
        
        return result, total_coverage
        
    except ImportError:
        print("Coverage module not installed. Run: pip install coverage")
        result = run_tests(test_dir, pattern)
        return result, 0.0


def print_summary(result: unittest.TestResult, duration: float, coverage: float = 0.0):
    """
    Print test run summary
    
    Args:
        result: Test result object
        duration: Test run duration in seconds
        coverage: Code coverage percentage
    """
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    # Basic stats
    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    success = total - failures - errors - skipped
    
    print(f"Tests run: {total}")
    print(f"✅ Passed: {success}")
    
    if failures:
        print(f"❌ Failed: {failures}")
    if errors:
        print(f"💥 Errors: {errors}")
    if skipped:
        print(f"⏭️  Skipped: {skipped}")
    
    print(f"⏱️  Duration: {duration:.2f} seconds")
    
    if coverage > 0:
        print(f"📊 Coverage: {coverage:.1f}%")
    
    # Success rate
    if total > 0:
        success_rate = (success / total) * 100
        print(f"Success rate: {success_rate:.1f}%")
    
    print("="*70)
    
    # Return status
    if result.wasSuccessful():
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run MBED tests')
    parser.add_argument(
        '--unit', 
        action='store_true',
        help='Run only unit tests'
    )
    parser.add_argument(
        '--integration', 
        action='store_true',
        help='Run only integration tests'
    )
    parser.add_argument(
        '--coverage', 
        action='store_true',
        help='Run with coverage reporting'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=2,
        help='Increase verbosity'
    )
    parser.add_argument(
        '--pattern', '-p',
        default='test_*.py',
        help='Test file pattern (default: test_*.py)'
    )
    parser.add_argument(
        '--failfast', '-f',
        action='store_true',
        help='Stop on first failure'
    )
    
    args = parser.parse_args()
    
    # Determine test directory
    if args.unit:
        test_dir = 'tests/unit'
        print("Running unit tests...")
    elif args.integration:
        test_dir = 'tests/integration'
        print("Running integration tests...")
    else:
        test_dir = 'tests'
        print("Running all tests...")
    
    # Record start time
    start_time = time.time()
    
    # Run tests
    if args.coverage:
        result, coverage_pct = run_with_coverage(test_dir, args.pattern)
    else:
        result = run_tests(test_dir, args.pattern, args.verbose)
        coverage_pct = 0.0
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Print summary and exit
    exit_code = print_summary(result, duration, coverage_pct)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()