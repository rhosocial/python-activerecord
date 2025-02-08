# Contributing to Python ActiveRecord

First off, thank you for considering contributing to `rhosocial-activerecord`! It's people like you that make it such a great tool.

## Where to get Help or Report an Issue

* [TBD]Help: Start with our [documentation](https://github.com/rhosoocial/python-activerecord/wiki/)
* Issue: Search through [GitHub Issues](https://github.com/rhosoocial/python-activerecord/issues) to see if your issue has already been reported

## Issue Guidelines

If you find a bug or have a feature request, please create an issue:

1. Go to [GitHub Issues](https://github.com/rhosoocial/python-activerecord/issues)
2. Create a new issue using the appropriate template
3. Include the following information:
   - For bugs:
     * A clear description of what happened and what you expected to happen
     * Steps to reproduce the issue
     * Python version
     * Python ActiveRecord version
     * Database type and version
     * Any relevant code snippets or error messages
   - For feature requests:
     * A clear description of the feature
     * Use cases that demonstrate why this feature would be valuable
     * Any implementation ideas you have

## Contributing Code

1. Fork the [repository](https://github.com/rhosoocial/python-activerecord)
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/python-activerecord.git
   ```
3. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. Make your changes and write tests if applicable
5. Run the test suite:
   ```bash
   python -m pytest
   ```
6. Commit your changes:
   ```bash
   git commit -m "Add some feature"
   ```
7. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
8. Create a Pull Request from your fork to our main branch

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

## Code Style

* Follow PEP 8 guidelines
* Use meaningful variable and function names
* Write docstrings for functions and classes
* Include type hints where appropriate
* Keep functions focused and concise

## Testing

* Write tests for any new functionality
* Ensure all existing tests pass
* Use pytest for testing
* Aim for good test coverage

## Documentation

If you're adding new features or changing existing ones:

1. Update the docstrings
2. Update the [README.md](README.md) if needed
3. Add or update wiki pages for significant changes

## Share Your Ideas

Have ideas for improvements? You can:

1. Create an issue with the "enhancement" label
2. Start a discussion in the GitHub Discussions section
3. Share your thoughts in our community channels

## Support the Project

If you find `rhosocial-activerecord` useful, you can:

* Star the repository
* Share it with others
* Contribute code or documentation
* Report bugs and provide feedback

## Donations

We deeply appreciate any financial support that helps us maintain and improve `rhosocial-activerecord`.
Your donations directly contribute to:

* Maintaining the project
* Developing new features
* Improving documentation
* Supporting community engagement

### Donation Channels

You can support us through the following channels:

1. GitHub Sponsors (Preferred)
   * Visit our [GitHub Sponsors page](https://github.com/sponsors/rhosoocial)
   * Monthly or one-time donations
   * Directly integrated with GitHub

2. Open Collective
   * Support us on [Open Collective](https://opencollective.com/rhosocial-activerecord)
   * Transparent fund management
   * Available for both individuals and organizations

All donors will be acknowledged in our SPONSORS.md file (unless you prefer to remain anonymous).

## Questions?

If you have any questions about contributing, feel free to:

1. Check our [documentation](https://github.com/rhosoocial/python-activerecord/wiki)
2. Open an issue
3. Start a discussion

Thank you for contributing to Python ActiveRecord!
