"""
Verification script to check if the capability markers were added correctly
to the test_advanced_grouping.py file without running the tests.
"""
import ast
import sys
from pathlib import Path

def verify_capability_markers():
    """Verify that capability markers were properly added to the test functions."""
    # Path to the test file in the testsuite
    test_file_path = Path("../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/query/test_advanced_grouping.py")
    
    if not test_file_path.exists():
        print(f"Error: Test file {test_file_path.absolute()} does not exist.")
        return False
    
    print(f"Verifying capability markers in: {test_file_path}")
    
    try:
        # Read the file content
        with open(test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to verify syntax is valid
        tree = ast.parse(content)
        
        print("[OK] File syntax is valid")
        
        # Check for required imports
        has_basic_import = "from rhosocial.activerecord.backend.capabilities import CapabilityCategory, AdvancedGroupingCapability" in content
        has_utils_import = "from rhosocial.activerecord.testsuite.feature.utils import requires_capability, requires_cube, requires_rollup, requires_grouping_sets" in content
        
        if has_basic_import and has_utils_import:
            print("[OK] Required imports found")
        else:
            print("[ERROR] Required imports not found")
            if not has_basic_import:
                print("  - Missing: from rhosocial.activerecord.backend.capabilities import CapabilityCategory, AdvancedGroupingCapability")
            if not has_utils_import:
                print("  - Missing: from rhosocial.activerecord.testsuite.feature.utils import requires_capability, requires_cube, requires_rollup, requires_grouping_sets")
            return False
        
        # Define expected test functions and their expected markers
        expected_patterns = [
            ("test_cube_basic", "@requires_cube()"),
            ("test_rollup_basic", "@requires_rollup()"),
            ("test_grouping_sets_basic", "@requires_grouping_sets()"),
            ("test_rollup_with_having", "@requires_rollup()"),
            ("test_cube_with_order_by", "@requires_cube()"),
            ("test_multiple_grouping_types", "@requires_capability(CapabilityCategory.ADVANCED_GROUPING, [AdvancedGroupingCapability.CUBE, AdvancedGroupingCapability.ROLLUP])"),
            ("test_complex_grouping_with_joins", "@requires_rollup()")
        ]
        
        # Check each function has the proper marker
        all_found = True
        for func_name, expected_pattern in expected_patterns:
            if expected_pattern in content:
                print(f"[OK] {func_name} has correct marker: {expected_pattern}")
            else:
                print(f"[ERROR] {func_name} missing or incorrect marker. Looking for: {expected_pattern}")
                all_found = False
        
        return all_found
        
    except SyntaxError as e:
        print(f"[ERROR] Syntax error in test file: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error verifying test file: {e}")
        return False

def verify_changes_locally():
    """Verify changes by checking the content directly."""
    test_file_path = Path("../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/query/test_advanced_grouping.py")
    
    with open(test_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n--- First 15 lines of the file ---")
    lines = content.split('\n')
    for i, line in enumerate(lines[:15]):
        print(f"{i+1:2d}: {line}")
    
    print("\n--- Looking for markers in functions ---")
    for line_num, line in enumerate(lines, 1):
        if '@pytest.mark.requires_capability' in line:
            # Print this line and the next few to see the function it decorates
            print(f"Found marker at line {line_num}: {line.strip()}")
            # Print the function definition that follows
            for j in range(1, 4):
                if line_num + j <= len(lines):
                    next_line = lines[line_num + j - 1]  # Adjust for 0-indexing
                    if next_line.strip().startswith('def '):
                        print(f"  -> Function: {next_line.strip()}")
                        break

if __name__ == "__main__":
    print("Verifying capability markers were added to test_advanced_grouping.py...")
    
    success = verify_capability_markers()
    
    if success:
        print("\n*** SUCCESS *** All capability markers are correctly added!")
    else:
        print("\n*** FAILURE *** Some capability markers are missing or incorrect!")
        sys.exit(1)
    
    # Also show a sample of the file to confirm changes
    verify_changes_locally()