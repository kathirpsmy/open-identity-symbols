# Contributing

Contributions of all sizes are welcome — bug fixes, symbol pool expansions, discovery server improvements, and protocol design ideas.

## Repository Layout

| Folder | What lives here |
|--------|----------------|
| `pwa/` | Static PWA (HTML, JS, service worker) |
| `discovery/` | Optional FastAPI discovery server |
| `data/` | Python source for the Unicode pool and alias map |
| `specs/` | Protocol specifications |
| `docs/` | Landing page and architecture docs |

## Working on the PWA

The PWA is plain HTML + vanilla JS — no build step required. Open `pwa/index.html` directly in a browser or serve the folder locally:

```bash
cd pwa
python -m http.server 8080
# open http://localhost:8080
```

After editing `data/unicode_pool.py` or `data/alias_map.py`, regenerate the JS data files:

```bash
python pwa/scripts/export_data.py
```

Run the derivation test to verify correctness:

```bash
node pwa/scripts/test_derivation.mjs
```

## Working on the Discovery Server

```bash
# Create and activate a virtual environment (always use .venv/)
python -m venv .venv
.venv/Scripts/activate      # Windows
# source .venv/bin/activate # macOS/Linux

pip install -r discovery/requirements.txt

# Run tests (SQLite in-memory, no Postgres needed)
.venv/Scripts/pytest discovery/tests/ -v
```

Or run the full stack with Docker:

```bash
docker compose up
```

## Expanding the Symbol Pool

1. Edit `data/unicode_pool.py` — add ranges or individual code points
2. Ensure `data/alias_map.py` has enough vocabulary (assertion will fail if not)
3. Regenerate: `python pwa/scripts/export_data.py`
4. Run the Node.js derivation test: `node pwa/scripts/test_derivation.mjs`
5. Update `specs/unicode-pool.md` if changing curation rules

## Pull Requests

- One feature or fix per PR
- Tests required for discovery server changes
- Update `specs/` if changing the identity format or derivation algorithm
- No new dependencies without discussion
