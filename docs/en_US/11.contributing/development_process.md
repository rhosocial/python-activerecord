# Development Process

This document outlines the development process for contributing code to rhosocial ActiveRecord.

## Getting Started

1. **Fork the Repository**:
   - Visit the [rhosocial ActiveRecord repository](https://github.com/rhosocial/python-activerecord)
   - Click the "Fork" button to create your own copy

2. **Clone Your Fork**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/python-activerecord.git
   cd python-activerecord
   ```

3. **Set Up Development Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

4. **Create a Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
   Use a descriptive branch name that reflects the changes you're making.

## Coding Standards

When contributing code to rhosocial ActiveRecord, please follow these standards:

- **Follow PEP 8**: Adhere to [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- **Meaningful Names**: Use descriptive variable, function, and class names
- **Documentation**: Write docstrings for all functions, classes, and modules
- **Type Hints**: Include type hints where appropriate
- **Focused Functions**: Keep functions focused on a single responsibility
- **Test Coverage**: Write tests for new functionality

## Testing

All code contributions should include tests:

1. **Write Tests**:
   - Add tests for any new functionality
   - Ensure existing tests pass with your changes

2. **Run Tests**:
   ```bash
   python -m pytest
   ```

3. **Check Coverage**:
   ```bash
   python -m pytest --cov=rhosocial
   ```

## Submitting Changes

1. **Commit Your Changes**:
   ```bash
   git commit -m "Add feature: brief description"
   ```
   Write clear, concise commit messages that explain what your changes do.

2. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request**:
   - Go to your fork on GitHub
   - Click "New Pull Request"
   - Select your branch and provide a description of your changes
   - Reference any related issues

## Code Review Process

After submitting a pull request:

1. Maintainers will review your code
2. Automated tests will run to verify your changes
3. You may be asked to make adjustments
4. Once approved, your changes will be merged

## Continuous Integration

rhosocial ActiveRecord uses GitHub Actions for continuous integration. When you submit a pull request, automated tests will run to verify your changes.

## Version Control Practices

- Keep commits focused on a single change
- Rebase your branch before submitting a pull request
- Avoid merge commits when possible

## Repository Release Conventions

1. **Permanent Branches**:
   - The repository maintains two permanent branches: `main` and `docs`.
   - Non-permanent branches include specific release version branches and feature branches.

2. **Branch Creation Rules**:
   - When developing new features or fixing existing issues, always create a branch based on the `main` branch or a specific release version branch.
   - After development is mature, merge back to the target branch.
   - Recommended branch naming conventions:
     - Feature branches should start with `feature-` followed by the GitHub issue number
     - Bug fix branches should start with `issue-` followed by the GitHub issue number

3. **Version Release Process**:
   - All version releases follow a sequential approach, with each major version release based on the `main` branch.
   - After a release, a major version branch is immediately created.
   - The `main` branch has continuous integration enabled, and feature branches attempting to merge into `main` will automatically trigger continuous integration.
   - Passing continuous integration is a necessary condition for merging into the `main` branch.

4. **Documentation Branch Management**:
   - The `docs` branch is based on the `main` branch and is regularly synchronized with changes from the `main` branch to ensure it remains up-to-date.
   - The `docs` branch is only responsible for receiving documentation updates for the main development version.
   - After changes are merged into the `docs` branch, they are promptly synchronized back to the `main` branch.

## Communication

If you have questions during the development process:

- Comment on the relevant issue
- Start a discussion in GitHub Discussions
- Reach out to maintainers

Thank you for contributing to rhosocial ActiveRecord!