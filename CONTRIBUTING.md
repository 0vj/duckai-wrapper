# Contributing to DuckAI Wrapper

Thank you for your interest in contributing to DuckAI Wrapper! We welcome contributions, bug reports, and suggestions from the community.

## Code of Conduct

Please be respectful and constructive in all discussions, issues, and pull requests.

## How Can I Contribute?

### 1. Reporting Bugs
- Search existing issues to ensure the bug hasn't already been reported.
- Create a new issue describing:
  - Clear steps to reproduce the bug.
  - Expected behavior vs. actual behavior.
  - Operating system, Python version, and relevant error logs.

### 2. Suggesting Enhancements
- Open an issue with the tag `enhancement`.
- Describe the feature, use case, and proposed interface.

### 3. Pull Requests
1. Fork the repository and create your feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Set up the development environment:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   uv pip install pytest pytest-asyncio
   playwright install chromium
   ```
3. Make your changes and add tests where appropriate.
4. Run the test suite:
   ```bash
   pytest tests/
   ```
5. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -am 'Add support for new model parameter'
   ```
6. Push to your branch and submit a Pull Request.

## Development Guidelines

- **Code Style:** Keep code modular, clean, and well-typed (using Python type hints).
- **Asynchronous Code:** Maintain `async`/`await` paradigms with non-blocking I/O throughout FastAPI endpoints and Playwright sessions.
- **Testing:** Ensure all unit tests pass before opening a PR.
