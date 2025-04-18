# Documentation Contributions

Documentation is a crucial part of rhosocial ActiveRecord. Good documentation makes the project more accessible and easier to use. This guide will help you contribute to our documentation.

## Types of Documentation Contributions

You can contribute to documentation in several ways:

1. **API Documentation**: Improving docstrings in the code
2. **User Guides**: Enhancing the guides in the `/docs` directory
3. **Tutorials**: Creating step-by-step tutorials for specific use cases
4. **Examples**: Adding example code that demonstrates features
5. **Translations**: Translating documentation into other languages

## Getting Started with Documentation

1. **Identify Areas for Improvement**:
   - Look for unclear or missing documentation
   - Check for outdated information
   - Consider what documentation would have helped you when learning

2. **Fork and Clone**: Follow the [Development Process](development_process.md) to set up your environment.

3. **Locate Documentation Files**:
   - Code docstrings are in the source files
   - User guides are in the `/docs` directory
   - README and other markdown files are in the repository root

## Documentation Standards

When contributing to documentation, please follow these standards:

- **Clear Language**: Use simple, direct language
- **Consistency**: Maintain a consistent style and terminology
- **Examples**: Include code examples for complex concepts
- **Structure**: Use headings, lists, and other formatting to organize content
- **Completeness**: Cover all parameters, return values, and exceptions

## Docstring Guidelines

For Python code docstrings:

- Follow the [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) for docstrings
- Include type hints in docstrings
- Document parameters, return values, and exceptions
- Provide examples for complex functions

Example:
```python
def find_by_id(id: int) -> Optional[Model]:
    """
    Find a model instance by its primary key.
    
    Args:
        id: The primary key value to search for
        
    Returns:
        The model instance if found, None otherwise
        
    Raises:
        ValueError: If id is None or invalid
        
    Example:
        >>> user = User.find_by_id(123)
        >>> print(user.name)
        "John Doe"
    """
```

## Markdown Guidelines

For markdown documentation:

- Use headings to organize content (# for main title, ## for sections, etc.)
- Use code blocks with language specification for code examples
- Use lists for steps or related items
- Link to other relevant documentation
- Include screenshots or diagrams when helpful

## Translation Guidelines

When translating documentation:

1. **Maintain Technical Accuracy**: Ensure technical terms are correctly translated
2. **Consider Cultural Context**: Adapt to the cultural norms and conventions of the target language
3. **Maintain Consistent Terminology**: Create and use a consistent glossary for technical terms
4. **Review Translations**: Have others review your translations when possible
5. **Translation Directory Naming Convention**:
   - Follow the latest revision of ISO 639 standard
   - Use lowercase for language codes (e.g., `zh`, `en`)
   - Use uppercase for country/region codes (e.g., `CN`, `US`)
   - Separate language and country/region codes with an underscore (e.g., `zh_CN`, `en_US`)
6. **Code Comments and Messages**:
   - Comments, log messages, and exception messages in code should currently be in English only
   - Unless specifically designed for a particular region or language feature

## Documentation Workflow

1. **Use the docs Branch**: Documentation improvements should only be submitted to the docs branch
2. **Limit the Scope of Changes**:
   - Only modify files within the `docs/` directory
   - Do not include executable scripts, binary files, etc.
3. **Preview Changes**: For markdown files, preview them locally before submitting
4. **Submit a Pull Request**:
   - Follow the guidelines in the [Development Process](development_process.md)
   - Describe what documentation you've added or improved
   - Request review from someone familiar with the topic

## Documentation Review Process

When your documentation pull request is reviewed:

- Reviewers will check for technical accuracy
- They'll also look at clarity, completeness, and style
- You may be asked to make revisions
- Once approved, your changes will be merged

## Tips for Effective Documentation

- **Know Your Audience**: Consider the experience level of readers
- **Be Concise**: Keep explanations clear and to the point
- **Show, Don't Just Tell**: Include examples and use cases
- **Update Related Docs**: If you change one document, update related ones
- **Test Your Instructions**: Follow your own instructions to verify they work

Thank you for helping improve rhosocial ActiveRecord's documentation!