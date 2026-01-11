#!/usr/bin/env python3
"""
Unified Test Runner for Rapydocs

Runs all tests in the tests/ directory with proper organization and reporting.
This script automatically discovers and runs all test files following the pattern:
- tests/embeddings/parsers/test_*.py
- tests/embeddings/test_*.py  
- tests/mcp/test_*.py
- tests/integration/test_*.py
- tests/database/test_*.py
- tests/utils/test_*.py
- tests/test_*.py (root level)

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --category parsers # Run only parser tests
    python run_tests.py --verbose          # Verbose output
    python run_tests.py --fail-fast        # Stop on first failure
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json

class TestRunner:
    """Unified test runner for the Rapydocs project"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.tests_dir = self.project_root / "tests"
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
    def discover_tests(self, category: Optional[str] = None) -> Dict[str, List[Path]]:
        """Discover all test files organized by category"""
        categories = {
            "parsers": self.tests_dir / "embeddings" / "parsers",
            "embeddings": self.tests_dir / "embeddings",
            "mcp": self.tests_dir / "mcp",
            "integration": self.tests_dir / "integration", 
            "database": self.tests_dir / "database",
            "utils": self.tests_dir / "utils",
            "root": self.tests_dir
        }
        
        discovered = {}
        
        for cat_name, cat_path in categories.items():
            if category and category != cat_name:
                continue
                
            if not cat_path.exists():
                continue
                
            test_files = []
            
            if cat_name == "embeddings":
                # For embeddings, exclude the parsers subdirectory
                test_files = [f for f in cat_path.glob("test_*.py") 
                            if f.parent == cat_path]
            elif cat_name == "root":
                # For root, only direct children
                test_files = [f for f in cat_path.glob("test_*.py")
                            if f.parent == cat_path]
            else:
                # For others, all test files in the directory
                test_files = list(cat_path.glob("test_*.py"))
            
            if test_files:
                discovered[cat_name] = sorted(test_files)
                
        return discovered
        
    def run_test_file(self, test_file: Path, verbose: bool = False) -> Tuple[bool, str, float]:
        """Run a single test file and return (success, output, duration)"""
        start_time = time.time()
        
        try:
            # Change to project root for consistent imports
            result = subprocess.run(
                [sys.executable, str(test_file)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            return success, output, duration
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return False, f"Test timed out after 5 minutes", duration
        except Exception as e:
            duration = time.time() - start_time
            return False, f"Failed to run test: {e}", duration
    
    def run_category(self, category: str, test_files: List[Path], 
                    verbose: bool = False, fail_fast: bool = False) -> bool:
        """Run all tests in a category"""
        print(f"\n{'='*20} {category.upper()} TESTS {'='*20}")
        
        category_success = True
        
        for test_file in test_files:
            test_name = test_file.name
            print(f"\nRunning {test_name}...")
            
            success, output, duration = self.run_test_file(test_file, verbose)
            
            if success:
                print(f"✅ PASSED - {test_name} ({duration:.2f}s)")
                self.passed_tests += 1
            else:
                print(f"❌ FAILED - {test_name} ({duration:.2f}s)")
                if verbose or not success:
                    print(f"Output:\n{output}")
                self.failed_tests += 1
                category_success = False
                
                if fail_fast:
                    print("\n💥 Stopping due to --fail-fast")
                    return False
            
            self.total_tests += 1
            self.results[str(test_file)] = {
                "success": success,
                "duration": duration,
                "output": output
            }
        
        return category_success
    
    def run_all_tests(self, category: Optional[str] = None, 
                     verbose: bool = False, fail_fast: bool = False) -> bool:
        """Run all discovered tests"""
        print(f"🚀 Starting Rapydocs Test Suite")
        print(f"Project root: {self.project_root}")
        print(f"Tests directory: {self.tests_dir}")
        
        if not self.tests_dir.exists():
            print(f"❌ Tests directory not found: {self.tests_dir}")
            return False
        
        # Discover tests
        discovered = self.discover_tests(category)
        
        if not discovered:
            print("❌ No tests found!")
            return False
        
        print(f"\n📋 Discovered test categories: {list(discovered.keys())}")
        total_files = sum(len(files) for files in discovered.values())
        print(f"📊 Total test files: {total_files}")
        
        # Run tests by category
        overall_success = True
        start_time = time.time()
        
        for cat_name, test_files in discovered.items():
            success = self.run_category(cat_name, test_files, verbose, fail_fast)
            overall_success = overall_success and success
            
            if not success and fail_fast:
                break
        
        # Summary
        duration = time.time() - start_time
        self.print_summary(duration)
        
        return overall_success
    
    def print_summary(self, duration: float):
        """Print test run summary"""
        print(f"\n{'='*60}")
        print(f"🏁 TEST SUMMARY")
        print(f"{'='*60}")
        print(f"⏱️  Total time: {duration:.2f}s")
        print(f"📊 Total tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"⏭️  Skipped: {self.skipped_tests}")
        
        if self.failed_tests == 0:
            print(f"🎉 ALL TESTS PASSED!")
        else:
            print(f"💥 {self.failed_tests} TESTS FAILED")
            
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        print(f"📈 Success rate: {success_rate:.1f}%")
    
    def generate_report(self, output_file: str = "test_report.json"):
        """Generate a detailed test report"""
        report = {
            "summary": {
                "total": self.total_tests,
                "passed": self.passed_tests,
                "failed": self.failed_tests,
                "skipped": self.skipped_tests
            },
            "results": self.results
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Detailed report saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Unified test runner for Rapydocs")
    parser.add_argument(
        "--category",
        choices=["parsers", "embeddings", "mcp", "integration", "database", "utils", "root"],
        help="Run tests from specific category only"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output including test outputs"
    )
    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true", 
        help="Stop running tests after the first failure"
    )
    parser.add_argument(
        "--report",
        default="test_report.json",
        help="Generate detailed JSON report (default: test_report.json)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only quick tests (skip integration tests)"
    )
    
    args = parser.parse_args()
    
    # Skip integration tests for quick runs
    if args.quick and not args.category:
        print("🏃 Quick mode: skipping integration tests")
        # We'll handle this in the runner
    
    runner = TestRunner()
    
    try:
        success = runner.run_all_tests(
            category=args.category,
            verbose=args.verbose,
            fail_fast=args.fail_fast
        )
        
        if args.report:
            runner.generate_report(args.report)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⏹️  Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()