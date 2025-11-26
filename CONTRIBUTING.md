# Contributing to MCP Tool Router

Thank you for your interest in contributing to the MCP Tool Router! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip
- git
- (Optional) Docker for container testing

### Setting Up Development Environment

1. **Fork and clone the repository**
```bash
git clone https://github.com/yourusername/mcp-servers-tool-routing.git
cd mcp-servers-tool-routing
```

2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**
```bash
pip install -r requirements-dev.txt
```

4. **Set up pre-commit hooks (optional)**
```bash
pip install pre-commit
pre-commit install
```

## Code Style and Quality

### Code Formatting

We use `black` for code formatting and `isort` for import sorting:

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/
```

### Linting

Run linters before committing:

```bash
# Flake8
flake8 src/ tests/

# Pylint
pylint src/

# Type checking with mypy
mypy src/
```

### Code Style Guidelines

- Follow PEP 8
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and concise
- Use meaningful variable and function names

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/test_router.py

# Run specific test
pytest tests/test_router.py::TestMCPToolRouter::test_router_initialization
```

### Writing Tests

- Write tests for all new functionality
- Aim for at least 80% code coverage
- Use descriptive test names
- Follow the AAA pattern (Arrange, Act, Assert)
- Use fixtures for common setup

Example:
```python
@pytest.mark.asyncio
async def test_new_feature():
    # Arrange
    router = MCPToolRouter()

    # Act
    result = await router.some_method()

    # Assert
    assert result == expected_value
```

## Making Changes

### Branching Strategy

1. Create a new branch for your feature or bugfix:
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bugfix-name
```

2. Make your changes, following the code style guidelines

3. Add tests for your changes

4. Ensure all tests pass:
```bash
pytest
```

5. Commit your changes with a descriptive message:
```bash
git commit -m "Add feature: description of your changes"
```

### Commit Messages

Follow these guidelines for commit messages:

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

Examples:
- `Add circuit breaker status endpoint`
- `Fix connection pool memory leak`
- `Update README with Docker instructions`
- `Refactor router initialization logic`

## Pull Request Process

1. **Update documentation** if you've made changes to:
   - API endpoints
   - Configuration options
   - Public interfaces

2. **Add tests** for new functionality

3. **Ensure all tests pass**:
```bash
pytest
```

4. **Update the README.md** if needed

5. **Create a pull request** with:
   - Clear title describing the change
   - Detailed description of what changed and why
   - Reference to any related issues
   - Screenshots (if UI changes)

6. **Respond to review feedback** promptly

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested your changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No new warnings
```

## Adding New Features

### Adding a New API Endpoint

1. Create route in `src/api/routes/`
2. Add request/response models in `src/api/models/`
3. Update OpenAPI documentation
4. Add tests in `tests/test_api_endpoints.py`
5. Update README with usage examples

### Adding a New MCP Server Type

1. Create server in `src/examples/mock_servers/`
2. Implement MCP protocol handlers
3. Add configuration to `config/servers.yaml`
4. Add tests
5. Update documentation

### Extending the Router

1. Modify `src/core/router.py`
2. Ensure backward compatibility
3. Add comprehensive tests
4. Update type hints
5. Document new behavior

## Documentation

### Code Documentation

- Use docstrings for all public functions and classes
- Include parameter descriptions
- Include return value descriptions
- Include usage examples for complex functions

Example:
```python
async def execute_tool(
    self,
    tool_name: str,
    arguments: Dict[str, Any],
) -> Any:
    """
    Execute a tool on the appropriate server with retry logic

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments

    Returns:
        Tool execution result

    Raises:
        ToolNotFoundError: If tool not found
        ToolExecutionError: If execution fails

    Example:
        >>> result = await router.execute_tool("database:query", {"query": "SELECT 1"})
    """
```

### README Updates

Update the README.md when:
- Adding new features
- Changing configuration options
- Updating dependencies
- Adding new examples

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a git tag
4. Build and test Docker image
5. Create GitHub release

## Getting Help

- Open an issue for bugs or feature requests
- Join discussions in GitHub Discussions
- Review existing issues and pull requests

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## License

By contributing to MCP Tool Router, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to MCP Tool Router! 🎉
