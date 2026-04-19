# Open Identity Symbols (OIS)

> Your identity as three symbols — derived from a key only your device holds.

**[Try it live →](https://PRYSYM.github.io/open-identity-symbols/app/)**

OIS is an open-source identity system that generates a globally unique, human-readable ID — three Unicode symbols — secured by a passkey on your device. No accounts. No servers. Works offline.

```
◯ ‑ △ ‑ ⬟   →   circle-triangle-pentagon
```

Your symbol ID is derived deterministically from the public half of a passkey created by your device's hardware. The same device always produces the same identity. No central authority assigns or controls it.

---

## How It Works

1. **Open the app** — runs entirely in your browser, no install needed
2. **Create a passkey** — your device (phone, laptop, security key) generates a P-256 key pair; the private key never leaves the hardware
3. **Derive your identity** — `SHA-256(SPKI public key bytes)` is sliced into three indices that map into a 5,000-symbol Unicode pool
4. **Get your ID** — e.g. `⚙-🌊-🔥 · gear-wave-fire` — permanent, globally unique, offline-ready

Optionally publish your identity to a discovery server so others can look you up by symbol or alias.

---

## Project Structure

```
open-identity-symbols/
├── pwa/              # Static PWA — runs entirely in the browser
│   ├── index.html
│   ├── app.js        # WebAuthn, IndexedDB, symbol derivation
│   ├── sw.js         # Service worker (offline support)
│   ├── manifest.json
│   ├── data/         # Auto-generated JS data files
│   └── scripts/
│       ├── export_data.py      # Generates pool.js + alias.js from data/
│       └── test_derivation.mjs # Node.js derivation test
├── discovery/        # Optional self-hosted discovery server (FastAPI)
│   ├── api/          # /challenge  /publish  /lookup  /search
│   ├── services/     # Symbol derivation, WebAuthn verification
│   └── tests/        # pytest test suite
├── data/             # Source of truth: Unicode pool + alias map (Python)
│   ├── unicode_pool.py
│   └── alias_map.py
├── specs/            # Protocol specifications
│   ├── unicode-pool.md
│   └── id-generation.md
├── docs/             # Landing page + architecture docs
└── docker-compose.yml  # Self-host the discovery server
```

---

## Try the PWA

The PWA is hosted on GitHub Pages — no setup needed:

**[https://PRYSYM.github.io/open-identity-symbols/app/](https://PRYSYM.github.io/open-identity-symbols/app/)**

It works on any modern browser with WebAuthn support (Chrome, Safari, Firefox, Edge). On mobile, your fingerprint or face ID secures the passkey.

---

## Run the PWA Locally

The PWA is static HTML/JS — no build tool, no bundler. You need a local HTTP server because WebAuthn and ES module imports don't work over `file://`.

**Prerequisites:** Python 3.11+ (for data generation)

```bash
# 1. Clone and enter the repo
git clone https://github.com/PRYSYM/open-identity-symbols
cd open-identity-symbols

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Generate the data files (pool.js + alias.js)
python pwa/scripts/export_data.py

# 4. Serve the PWA directory over HTTP
python -m http.server 8080 --directory pwa
```

Then open **[http://localhost:8080](http://localhost:8080)** in your browser.

> **Note:** WebAuthn requires either `localhost` or HTTPS. The `python -m http.server` approach works fine for local development on `localhost`.

---

## Self-Host the Discovery Server

The discovery server is optional. It lets users publish their symbol ID so others can look them up. Anyone can run their own instance.

```bash
git clone https://github.com/PRYSYM/open-identity-symbols
cd open-identity-symbols
docker compose up
```

The discovery API will be available at `http://localhost:8001`.

See [docs/discovery-server.md](docs/discovery-server.md) for full setup and API reference.

---

## Symbol Pool

- **5,390 curated Unicode symbols** — geometric shapes, arrows, math operators, nature emoji, and more
- Excludes religious, political, national-flag, and gendered symbols
- Capacity: **5390³ ≈ 156 billion unique identities** — enough for every person on Earth many times over
- Alias vocabulary: 5,500+ unique English words (real words + systematic color-nature compounds)

See [specs/unicode-pool.md](specs/unicode-pool.md) for curation rules and [specs/id-generation.md](specs/id-generation.md) for the derivation algorithm.

---

## Vision

OIS is designed to grow into a **standardized, open identity protocol**:

- Any app or service can verify an OIS identity without calling home to a central server
- Multiple discovery servers can federate — no single authority controls the namespace
- The derivation algorithm is deterministic and publicly specified — third parties can implement it independently
- Long-term goal: propose OIS as an open standard (similar in spirit to how email addresses work, but for symbolic, hardware-backed identities)

This is early-stage. The PWA and discovery server are working implementations. The protocol specification and federation layer are the next frontier — contributions welcome.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
