"""
Bridge test file to execute tests from the testsuite package
specifically for feature/query/test_advanced_grouping.py
"""
import subprocess
import sys
import os
from pathlib import Path

def run_testsuite_advanced_grouping_tests():
    """
    Execute the tests from the testsuite package to verify
    that the capability markers have been added correctly.
    """
    # Get the path to the testsuite
    testsuite_path = Path("../python-activerecord-testsuite")
    
    if not testsuite_path.exists():
        print(f"Error: Testsuite path {testsuite_path.absolute()} does not exist.")
        return False
    
    # Path to the specific test file
    test_file_path = testsuite_path / "src" / "rhosocial" / "activerecord" / "testsuite" / "feature" / "query" / "test_advanced_grouping.py"
    
    if not test_file_path.exists():
        print(f"Error: Test file {test_file_path.absolute()} does not exist.")
        return False

    print(f"Running tests from: {test_file_path}")
    
    # Set up the Python path to include both src and tests directories
    env = os.environ.copy()
    current_src_path = Path.cwd() / "src"
    testsuite_src_path = testsuite_path / "src"
    
    # Construct PYTHONPATH to include both source directories
    python_path = f"{current_src_path};{testsuite_src_path}"
    if "PYTHONPATH" in env:
        python_path = f"{python_path};{env['PYTHONPATH']}"
    env["PYTHONPATH"] = python_path
    
    # Also set the required environment variable for the testsuite
    env["TESTSUITE_PROVIDER_REGISTRY"] = "rhosocial.activerecord.testsuite.core.default_provider:default_provider_registry"
    
    # Command to run pytest on the specific test file
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file_path),
        "-v",  # Verbose output
        "-s",  # Show print statements
        "-x"   # Stop on first failure
    ]
    
    print(f"Executing command: {' '.join(cmd)}")
    print(f"Working directory: {testsuite_path}")
    print(f"PYTHONPATH: {env['PYTHONPATH']}")
    
    try:
        # Run the tests
        result = subprocess.run(
            cmd,
            cwd=testsuite_path,
            env=env,
            capture_output=True,
            text=True
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            print("[SUCCESS] Tests executed successfully!")
            return True
        else:
            print("[FAILURE] Tests failed!")
            return False
            
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    print("Running bridge test for advanced grouping capability markers...")
    success = run_testsuite_advanced_grouping_tests()
    
    if success:
        print("\n[SUCCESS] Bridge test completed successfully!")
        print("The capability markers have been added to the testsuite test functions.")
    else:
        print("\n[FAILURE] Bridge test failed!")
        sys.exit(1)