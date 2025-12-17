# Contributing to NODO

First off, thank you for considering contributing to NODO! 🎉

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)

---

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

When creating a bug report, include:

- **Clear title** describing the issue
- **Steps to reproduce** the behavior
- **Expected behavior** vs what actually happened
- **Environment details** (OS, Python version, etc.)
- **Logs** if applicable

### 💡 Suggesting Features

Feature suggestions are welcome! Please:

- Check if the feature already exists or is planned
- Describe the feature and its use case
- Explain why it would be useful to most users

### 🔧 Code Contributions

1. Look for issues labeled `good first issue` or `help wanted`
2. Comment on the issue to let others know you're working on it
3. Fork the repo and create your branch
4. Make your changes
5. Submit a pull request

---

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A code editor (VS Code recommended)

### Setup Steps

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/nodo.git
cd nodo

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r bot/requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# 4. Set up pre-commit hooks
pre-commit install

# 5. Create .env file
cp .env.example .env
# Edit .env with your API keys

# 6. Run tests
pytest

# 7. Start the bot (for testing)
python bot/telegram_bot.py
```

### Project Structure

```
nodo/
├── bot/                  # Main bot code
│   ├── telegram_bot.py   # Entry point
│   ├── ai_analyzer.py    # AI integration
│   ├── yield_scanner.py  # Yield strategy
│   ├── delta_scanner.py  # Delta neutral strategy
│   └── platforms/        # Market integrations
├── api/                  # REST API (planned)
├── docs/                 # Russian documentation
├── docs-en/              # English documentation
└── tests/                # Test files
```

---

## Pull Request Process

### Before Submitting

1. **Create an issue first** for significant changes
2. **Update documentation** if needed
3. **Add tests** for new functionality
4. **Run the full test suite** locally

### PR Checklist

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass locally

### PR Title Format

Use conventional commit format:

```
feat: Add new yield farming filter
fix: Resolve API timeout issue
docs: Update installation guide
refactor: Simplify consensus engine
test: Add tests for delta scanner
```

### Review Process

1. At least one maintainer must review the PR
2. All CI checks must pass
3. No merge conflicts
4. Approved PRs are squash-merged

---

## Style Guidelines

### Python Code Style

We use **Ruff** for linting and formatting:

```bash
# Check code
ruff check .

# Format code
ruff format .
```

Key conventions:

- **PEP 8** compliance
- **Type hints** for function signatures
- **Docstrings** for public functions
- **Max line length**: 100 characters

```python
# Good
async def analyze_market(
    market_url: str,
    strategy: Strategy = Strategy.YIELD,
    depth: int = 3,
) -> AnalysisResult:
    """
    Analyze a prediction market using multi-AI consensus.
    
    Args:
        market_url: URL of the market to analyze
        strategy: Trading strategy to apply
        depth: Number of AI models to consult (1-6)
    
    Returns:
        AnalysisResult with consensus and individual model responses
    
    Raises:
        InvalidMarketError: If market URL is invalid
        APIError: If AI API calls fail
    """
    ...
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code change that neither fixes bug nor adds feature
- `test`: Adding or updating tests
- `chore`: Build process, dependencies, etc.

### Documentation

- Use **Markdown** for all docs
- Include **code examples** where helpful
- Keep language **simple and clear**
- Update docs in **both languages** (Russian and English)

---

## Questions?

Feel free to:

- Open a [Discussion](https://github.com/nodo-ai/nodo/discussions)
- Join our [Telegram group](https://t.me/nodo_ai_chat)
- Email us at hello@nodo.ai

Thank you for contributing! 🚀

