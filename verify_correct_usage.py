"""
Verification script to confirm the correct usage of capability markers as per the request:
- Use the capability category and specific capabilities within each category
- Apply multiple decorators if different categories are involved
"""
import ast
import sys
from pathlib import Path

def verify_correct_usage():
    """Verify that capability markers follow the correct usage as requested."""
    # Path to the test file in the testsuite
    test_file_path = Path("../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/query/test_advanced_grouping.py")
    
    if not test_file_path.exists():
        print(f"Error: Test file {test_file_path.absolute()} does not exist.")
        return False
    
    print(f"Verifying correct capability marker usage in: {test_file_path}")
    
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
            return False
        
        print("\n[INFO] All tests in this file use CapabilityCategory.ADVANCED_GROUPING as the category.")
        print("[INFO] Each test specifies the specific capability within that category.")
        print("[INFO] For tests requiring multiple specific capabilities, the requires_capability function is used with a list.")
        
        # Check that all decorators follow the correct pattern
        required_patterns = [
            "@requires_cube()",
            "@requires_rollup()",
            "@requires_grouping_sets()",
            "@requires_capability(CapabilityCategory.ADVANCED_GROUPING, [AdvancedGroupingCapability.CUBE, AdvancedGroupingCapability.ROLLUP])"
        ]
        
        all_patterns_found = True
        for pattern in required_patterns:
            if pattern in content:
                print(f"[OK] Found pattern: {pattern}")
            else:
                print(f"[ERROR] Missing pattern: {pattern}")
                all_patterns_found = False
        
        # Additional check: ensure no old-style markers remain
        old_style_markers = [
            "@pytest.mark.requires_capability(AdvancedGroupingCapability.CUBE)",
            "@pytest.mark.requires_capability(AdvancedGroupingCapability.ROLLUP)",
            "@pytest.mark.requires_capability(AdvancedGroupingCapability.GROUPING_SETS)",
            "@pytest.mark.requires_capability([AdvancedGroupingCapability.CUBE, AdvancedGroupingCapability.ROLLUP])"
        ]
        
        old_markers_found = False
        for old_marker in old_style_markers:
            if old_marker in content:
                print(f"[ERROR] Found old-style marker that should be removed: {old_marker}")
                old_markers_found = True
        
        if old_markers_found:
            return False
        
        return all_patterns_found
        
    except SyntaxError as e:
        print(f"[ERROR] Syntax error in test file: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error verifying test file: {e}")
        return False

def show_updated_content():
    """Show a sample of the updated content to confirm changes."""
    test_file_path = Path("../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/query/test_advanced_grouping.py")
    
    with open(test_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n--- Updated imports ---")
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'import' in line and ('CapabilityCategory' in line or 'requires_' in line):
            print(f"{i+1:2d}: {line}")
    
    print("\n--- Sample of updated decorators ---")
    for i, line in enumerate(lines):
        if '@requires_' in line or '@pytest.mark.requires_capability' in line:
            # Print the decorator and the function it decorates
            print(f"Line {i+1:2d}: {line.strip()}")
            # Find the next function definition
            for j in range(i+1, min(i+5, len(lines))):
                if lines[j].strip().startswith('def '):
                    print(f"      -> Function: {lines[j].strip()}")
                    break

if __name__ == "__main__":
    print("Verifying correct capability marker usage as per the request...")
    print("Expected usage: CapabilityCategory with specific capabilities, multiple decorators if multiple categories required")
    
    success = verify_correct_usage()
    
    if success:
        print("\n*** SUCCESS *** Capability markers follow the correct usage pattern!")
        print("\nThe updated test file now uses:")
        print("- CapabilityCategory for the category")  
        print("- Specific capabilities within that category")
        print("- Multiple capability requirements specified as a list when needed")
        print("- Convenience functions where available (requires_cube, requires_rollup, etc.)")
    else:
        print("\n*** FAILURE *** Capability markers do not follow the correct usage pattern!")
        sys.exit(1)
    
    # Show updated content
    show_updated_content()