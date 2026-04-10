# Open Identity Symbols (OIS)

> A global, privacy-first identity system based on Unicode symbols.

Your identity is **three symbols** — permanently yours, globally unique, human-readable.

```
◯-△-⬟   →   circle-triangle-pentagon
```

## Features

- **Unicode IDs** — 3-symbol identifiers from a curated pool of 5,390 safe symbols
- **125 billion+ unique identities** — more than enough for every person on Earth
- **Alias system** — every symbol ID has a human-readable word alias (e.g. `frost-amber-helix`)
- **Privacy-first** — field-level visibility control on profiles
- **TOTP-secured** — two-factor authentication required for all accounts
- **Open standard** — designed to evolve into a federated protocol

## Quick Start

### With Docker (recommended)

```bash
cp .env.example .env
# Edit .env — set a strong SECRET_KEY
docker compose up
```

- Frontend: http://localhost
- API docs: http://localhost:8000/docs

### Local Development

**Backend**

```bash
cd open-identity-symbols
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Start Postgres + Redis (Docker or local)
uvicorn backend.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend/web
npm install
npm run dev     # http://localhost:5173
```

**Tests**

```bash
# From repo root, with venv active
pytest backend/tests/ -v
```

**Load test** (1M ID generation)

```bash
python tests/load/test_id_generation.py
```

## Project Structure

```
open-identity-symbols/
├── backend/
│   ├── core/          # Config, DB, security utilities
│   ├── services/      # Identity engine (Unicode + alias)
│   ├── api/routes/    # FastAPI routes: auth, identity, profile, search
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── data/          # Unicode pool + alias map
│   └── tests/         # pytest test suite
├── frontend/web/      # React + Vite + Tailwind UI
├── tests/load/        # Load / stress tests
├── docs/              # Architecture, API, frontend docs
├── specs/             # Unicode pool, alias, ID generation specs
├── infra/             # Docker, deployment configs
└── docker-compose.yml
```

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register with email + password |
| POST | `/api/v1/auth/confirm-totp` | Confirm TOTP setup |
| POST | `/api/v1/auth/login` | Login with email + password + TOTP |
| POST | `/api/v1/identity/generate` | Generate your 3-symbol ID |
| GET | `/api/v1/identity/me` | Get your identity |
| GET | `/api/v1/identity/{symbol_id}` | Look up any identity |
| GET/PUT | `/api/v1/profile/me` | View or update your profile |
| GET | `/api/v1/profile/{symbol_id}` | View a public profile |
| GET | `/api/v1/search?q=...` | Search by symbol ID or alias |

Full interactive docs at `/docs` when the backend is running.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Auth | JWT, TOTP (pyotp), bcrypt |
| Database | PostgreSQL (SQLite for tests) |
| Cache | Redis |
| Frontend | React 18, Vite, Tailwind CSS, Axios |
| Container | Docker, docker-compose |
| Tests | pytest, httpx |

## Design Decisions

### Symbol Pool
- 5,390 curated Unicode symbols
- Excludes: religious, political, national flags, gendered symbols
- Theoretical capacity: **5390 × 5389 × 5388 ≈ 156 billion unique IDs**

### Alias System
- Each symbol maps to a unique English word
- Compound words used for less-common symbols (e.g. `frostgale`, `amberbrook`)
- ID alias format: `word1-word2-word3`

### Privacy Model
- Profile fields are **private by default**
- Users explicitly mark each field as `public` or `private`
- Public profile only returns `public` fields

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT
