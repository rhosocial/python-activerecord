# Bug Fixes

Finding and fixing bugs is a valuable contribution to rhosocial ActiveRecord. This guide will help you effectively report and fix bugs.

## Reporting Bugs

If you encounter a bug in rhosocial ActiveRecord:

1. **Search Existing Issues**: Check [GitHub Issues](https://github.com/rhosocial/python-activerecord/issues) to see if the bug has already been reported.

2. **Create a New Issue**:
   - Go to [GitHub Issues](https://github.com/rhosocial/python-activerecord/issues)
   - Click on "New Issue"
   - Select the "Bug Report" template
   - Fill in the template with detailed information

3. **Include Essential Information**:
   - A clear description of what happened and what you expected to happen
   - Steps to reproduce the issue
   - Python version
   - rhosocial ActiveRecord version
   - Database type and version
   - Any relevant code snippets or error messages
   - Environment details (OS, etc.)

4. **Minimal Reproducible Example**: If possible, provide a minimal code example that demonstrates the bug.

## Fixing Bugs

If you want to fix a bug:

1. **Comment on the Issue**: Let others know you're working on it to avoid duplicate efforts.

2. **Fork and Clone**: Follow the [Development Process](development_process.md) to set up your development environment.

3. **Create a Branch**:
   ```bash
   git checkout -b fix/bug-description
   ```

4. **Understand the Problem**:
   - Reproduce the bug locally
   - Use debugging tools to identify the root cause
   - Consider edge cases and potential side effects

5. **Write a Test**:
   - Create a test that reproduces the bug
   - This ensures the bug won't return in the future

6. **Fix the Bug**:
   - Make the necessary code changes
   - Ensure your fix addresses the root cause, not just the symptoms
   - Keep changes focused on the specific bug

7. **Run Tests**:
   ```bash
   python -m pytest
   ```
   Ensure all tests pass, including your new test.

8. **Submit a Pull Request**:
   - Follow the guidelines in the [Development Process](development_process.md)
   - Reference the issue number in your pull request description
   - Explain your approach to fixing the bug

## Best Practices for Bug Fixes

- **Keep Changes Minimal**: Fix only the bug at hand, avoid unrelated changes
- **Maintain Backward Compatibility**: Ensure your fix doesn't break existing functionality
- **Document Edge Cases**: Note any edge cases or limitations in your fix
- **Update Documentation**: If the bug was due to unclear documentation, update it

## Reviewing Bug Fixes

When reviewing bug fixes from others:

- Verify the fix addresses the root cause
- Check for potential side effects
- Ensure tests cover the fixed behavior
- Look for clear code and documentation

## Common Bug Sources

Common areas where bugs might occur in rhosocial ActiveRecord:

- Database dialect differences
- Transaction handling
- Relationship loading
- Query building
- Type conversion
- Concurrency issues

Understanding these areas can help you identify and fix bugs more effectively.

Thank you for helping make rhosocial ActiveRecord more reliable!