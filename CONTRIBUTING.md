# Contributing to Secure Chat

Thank you for your interest in contributing to Secure Chat! This document provides guidelines and information for contributors.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/secure-chat.git
   cd secure-chat
   ```

2. **Set up development environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install in development mode
   pip install -e .[dev]
   ```

3. **Run tests**
   ```bash
   pytest
   ```

4. **Code quality checks**
   ```bash
   # Linting
   flake8 secure_chat

   # Type checking
   mypy secure_chat

   # Formatting
   black secure_chat

   # Security scanning
   bandit -r secure_chat
   safety check
   ```

## Code Style

This project uses:
- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking
- **Bandit** for security scanning

### Pre-commit Hooks

Install pre-commit hooks to automatically run quality checks:

```bash
pip install pre-commit
pre-commit install
```

## Testing

- Write tests for new features
- Maintain test coverage above 80%
- Run the full test suite before submitting PRs

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=secure_chat --cov-report=html

# Run specific tests
pytest tests/test_specific_feature.py
```

## Security Considerations

- Never commit sensitive data (keys, passwords, tokens)
- Use secure coding practices
- Report security vulnerabilities privately
- Follow OWASP guidelines

## Pull Request Process

1. Create a feature branch from `develop`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation if needed
6. Submit a pull request to `develop`

## Commit Messages

Use clear, descriptive commit messages:

```
feat: add user authentication via OAuth
fix: resolve memory leak in message encryption
docs: update API documentation
test: add integration tests for file sharing
```

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors.

## License

By contributing to this project, you agree that your contributions will be licensed under the same MIT License that covers the project.