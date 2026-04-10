# Contributing

## Setup

```bash
git clone https://github.com/kathirpsmy/open-identity-symbols
cd open-identity-symbols

# Backend
python -m venv .venv
.venv/Scripts/activate      # Windows
# source .venv/bin/activate # macOS/Linux
pip install -r backend/requirements.txt

# Frontend
cd frontend/web && npm install
```

## Running Tests

```bash
# Always use the venv
.venv/Scripts/pytest backend/tests/ -v
```

## Code Style

- Python: follow PEP 8, use type hints
- JS/JSX: functional components, no class components
- No new dependencies without discussion

## Pull Requests

- One feature or fix per PR
- Tests required for all backend changes
- Update specs/ docs if changing identity format
