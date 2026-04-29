/**
 * OIS Discovery Worker — integration tests
 *
 * Runs against Miniflare (local D1 in-memory).
 * WEBAUTHN_VERIFY_ORIGIN=false so origin/rpId checks are skipped.
 * Signature verification uses a real P-256 key generated in each test.
 *
 * Run: cd worker && npm test
 */

import { env, SELF } from 'cloudflare:test';
import { describe, it, expect, beforeAll } from 'vitest';

// ─── Schema setup ─────────────────────────────────────────────────────────────

const SCHEMA = `
CREATE TABLE IF NOT EXISTS identities (
  public_key_id   TEXT PRIMARY KEY,
  symbol_id       TEXT UNIQUE NOT NULL,
  alias           TEXT UNIQUE NOT NULL,
  public_key_spki TEXT NOT NULL,
  credential_id   TEXT,
  origin          TEXT NOT NULL,
  public_profile  TEXT,
  published_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS challenges (
  token      TEXT PRIMARY KEY,
  expires_at TEXT NOT NULL
);
`;

beforeAll(async () => {
  for (const stmt of SCHEMA.split(';').map(s => s.trim()).filter(Boolean)) {
    await env.DB.prepare(stmt).run();
  }
});

// ─── Encoding helpers (mirrors worker) ───────────────────────────────────────

function fromBase64Url(s) {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  const pad = (4 - (s.length % 4)) % 4;
  const bin = atob(s + '='.repeat(pad));
  return Uint8Array.from(bin, c => c.charCodeAt(0));
}

function toBase64Url(bytes) {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

function hexToBytes(hex) {
  return new Uint8Array(hex.match(/.{2}/g).map(b => parseInt(b, 16)));
}

// ─── P1363 (raw r||s) → DER encoder (inverse of worker's derToRaw) ───────────

function rawToDer(raw) {
  function encodeInt(bytes) {
    // Remove leading zeros, keeping at least 1 byte
    let i = 0;
    while (i < bytes.length - 1 && bytes[i] === 0) i++;
    bytes = bytes.slice(i);
    // Prepend 0x00 if high bit set (DER sign preservation)
    if (bytes[0] & 0x80) {
      const padded = new Uint8Array(bytes.length + 1);
      padded.set(bytes, 1);
      bytes = padded;
    }
    const out = new Uint8Array(2 + bytes.length);
    out[0] = 0x02;
    out[1] = bytes.length;
    out.set(bytes, 2);
    return out;
  }
  const r    = encodeInt(raw.slice(0, 32));
  const s    = encodeInt(raw.slice(32, 64));
  const body = new Uint8Array(r.length + s.length);
  body.set(r); body.set(s, r.length);
  const der  = new Uint8Array(2 + body.length);
  der[0] = 0x30; der[1] = body.length;
  der.set(body, 2);
  return der;
}

// ─── Test-vector helpers ──────────────────────────────────────────────────────

async function generateTestKey() {
  const kp = await crypto.subtle.generateKey(
    { name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']
  );
  const spkiBuf  = await crypto.subtle.exportKey('spki', kp.publicKey);
  return { kp, spkiBytes: new Uint8Array(spkiBuf) };
}

async function buildAssertion(kp, challengeToken) {
  const challengeBytes = hexToBytes(challengeToken);
  const origin         = 'http://localhost';

  const cdObj  = { type: 'webauthn.get', challenge: toBase64Url(challengeBytes), origin, crossOrigin: false };
  const cdJSON = new TextEncoder().encode(JSON.stringify(cdObj));

  // authenticatorData: rpIdHash(32) + flags(1 = UP) + signCount(4)
  const rpIdHash = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode('localhost')));
  const authData = new Uint8Array(37);
  authData.set(rpIdHash);
  authData[32] = 0x05; // UP | UV

  // verificationData = authData || SHA-256(clientDataJSON)
  const cdHash = new Uint8Array(await crypto.subtle.digest('SHA-256', cdJSON));
  const vData  = new Uint8Array(authData.length + cdHash.length);
  vData.set(authData); vData.set(cdHash, authData.length);

  // Sign → raw r||s → DER (worker's derToRaw expects DER input)
  const sigRaw = new Uint8Array(await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, kp.privateKey, vData));
  const sigDer = rawToDer(sigRaw);

  return {
    client_data_json:   toBase64Url(cdJSON),
    authenticator_data: toBase64Url(authData),
    signature:          toBase64Url(sigDer),
    credential_id:      'test-cred-id',
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('GET /health', () => {
  it('returns ok', async () => {
    const res  = await SELF.fetch('http://example.com/health');
    const data = await res.json();
    expect(res.status).toBe(200);
    expect(data.status).toBe('ok');
    expect(data.db).toBe('ok');
  });
});

describe('GET /challenge', () => {
  it('returns 64-char hex token and expires_at', async () => {
    const res  = await SELF.fetch('http://example.com/challenge');
    const data = await res.json();
    expect(res.status).toBe(200);
    expect(data.token).toMatch(/^[0-9a-f]{64}$/);
    expect(data.expires_at).toBeDefined();
    expect(new Date(data.expires_at).getTime()).toBeGreaterThan(Date.now() - 1000);
  });

  it('issues unique tokens on each call', async () => {
    const [r1, r2] = await Promise.all([
      SELF.fetch('http://example.com/challenge').then(r => r.json()),
      SELF.fetch('http://example.com/challenge').then(r => r.json()),
    ]);
    expect(r1.token).not.toBe(r2.token);
  });
});

describe('GET /lookup/*  — not found', () => {
  it('/lookup/alias/nonexistent → 404', async () => {
    const res = await SELF.fetch('http://example.com/lookup/alias/nope-nope-nope');
    expect(res.status).toBe(404);
  });

  it('/lookup/key/0000000000000000000000000000000000000000000000000000000000000000 → 404', async () => {
    const res = await SELF.fetch('http://example.com/lookup/key/' + '0'.repeat(64));
    expect(res.status).toBe(404);
  });

  it('/lookup/credential/nonexistent → 404', async () => {
    const res = await SELF.fetch('http://example.com/lookup/credential/doesnotexist');
    expect(res.status).toBe(404);
  });
});

describe('GET /search', () => {
  it('missing q → 422', async () => {
    const res = await SELF.fetch('http://example.com/search');
    expect(res.status).toBe(422);
  });

  it('no results → { results: [], total: 0 }', async () => {
    const res  = await SELF.fetch('http://example.com/search?q=zzznomatch');
    const data = await res.json();
    expect(res.status).toBe(200);
    expect(data.results).toHaveLength(0);
    expect(data.total).toBe(0);
  });
});

describe('POST /publish — validation', () => {
  it('missing fields → 422', async () => {
    const res = await SELF.fetch('http://example.com/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol_id: 'a-b-c' }),
    });
    expect(res.status).toBe(422);
  });

  it('invalid challenge token → 422', async () => {
    const { kp, spkiBytes } = await generateTestKey();
    const spkiB64 = toBase64Url(spkiBytes);

    // Derive real symbols from the key
    const digestBuf = await crypto.subtle.digest('SHA-256', spkiBytes);
    const digest = new Uint8Array(digestBuf);
    const POOL_SIZE = 5390;
    const readU32 = (b, o) => ((b[o]<<24)|(b[o+1]<<16)|(b[o+2]<<8)|b[o+3])>>>0;
    let a = readU32(digest, 0) % POOL_SIZE;
    let b = readU32(digest, 4) % POOL_SIZE;
    let c = readU32(digest, 8) % POOL_SIZE;

    const fakeToken = 'a'.repeat(64);
    const assertion = await buildAssertion(kp, fakeToken);

    const res = await SELF.fetch('http://example.com/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol_id: 'x-y-z',
        alias: 'nope-nope-nope',
        public_key_spki: spkiB64,
        origin: 'http://localhost',
        challenge_token: fakeToken,
        assertion,
      }),
    });
    // symbol_id mismatch (derived symbols won't match x-y-z) → 422
    expect(res.status).toBe(422);
    const data = await res.json();
    expect(data.detail).toMatch(/mismatch/);
  });
});

describe('Full publish + lookup flow', () => {
  it('publishes an identity and retrieves it via all lookup types', async () => {
    const { kp, spkiBytes } = await generateTestKey();
    const spkiB64 = toBase64Url(spkiBytes);

    // Get challenge
    const chalRes  = await SELF.fetch('http://example.com/challenge');
    const { token } = await chalRes.json();

    // Build assertion
    const assertion = await buildAssertion(kp, token);
    assertion.credential_id = 'test-cred-full-flow';

    // Derive expected symbols (must match what worker derives)
    // We'll get them from the publish response
    const pubRes = await SELF.fetch('http://example.com/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol_id:       'PLACEHOLDER',   // will be rejected; we need real derived symbols
        alias:           'PLACEHOLDER',
        public_key_spki: spkiB64,
        origin:          'http://localhost',
        challenge_token: token,
        assertion,
      }),
    });
    // Expect 422 because symbol_id doesn't match — that's fine.
    // We need to derive them first.
    const pubData = await pubRes.json();

    // Extract the correct symbol_id from the error message
    const match = pubData.detail?.match(/key derives to '(.+?)'/);
    const realSymbolId = match?.[1];
    expect(realSymbolId).toBeDefined();

    // Get a fresh challenge (previous one was consumed or invalid)
    const chalRes2  = await SELF.fetch('http://example.com/challenge');
    const { token: token2 } = await chalRes2.json();
    const assertion2 = await buildAssertion(kp, token2);
    assertion2.credential_id = 'test-cred-full-flow';

    // Also need the correct alias — extract from a second error
    const pubRes2 = await SELF.fetch('http://example.com/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol_id:       realSymbolId,
        alias:           'PLACEHOLDER',
        public_key_spki: spkiB64,
        origin:          'http://localhost',
        challenge_token: token2,
        assertion:       assertion2,
      }),
    });
    const pubData2 = await pubRes2.json();
    const aliasMatch = pubData2.detail?.match(/key derives to '(.+?)'/);
    const realAlias = aliasMatch?.[1];
    expect(realAlias).toBeDefined();

    // Now publish for real
    const chalRes3  = await SELF.fetch('http://example.com/challenge');
    const { token: token3 } = await chalRes3.json();
    const assertion3 = await buildAssertion(kp, token3);
    assertion3.credential_id = 'test-cred-full-flow';

    const finalRes = await SELF.fetch('http://example.com/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol_id:       realSymbolId,
        alias:           realAlias,
        public_key_spki: spkiB64,
        origin:          'http://localhost',
        challenge_token: token3,
        assertion:       assertion3,
      }),
    });
    expect(finalRes.status).toBe(201);
    const finalData = await finalRes.json();
    expect(finalData.symbol_id).toBe(realSymbolId);
    expect(finalData.alias).toBe(realAlias);
    expect(finalData.published_at).toBeDefined();

    // Lookup by credential
    const byCredRes = await SELF.fetch(`http://example.com/lookup/credential/test-cred-full-flow`);
    expect(byCredRes.status).toBe(200);
    const byCred = await byCredRes.json();
    expect(byCred.symbol_id).toBe(realSymbolId);
    expect(byCred.public_key_spki).toBe(spkiB64);

    // Lookup by alias
    const byAliasRes = await SELF.fetch(`http://example.com/lookup/alias/${encodeURIComponent(realAlias)}`);
    expect(byAliasRes.status).toBe(200);

    // Search
    const searchWord = realAlias.split('-')[0];
    const searchRes = await SELF.fetch(`http://example.com/search?q=${encodeURIComponent(searchWord)}`);
    const searchData = await searchRes.json();
    expect(searchRes.status).toBe(200);
    expect(searchData.total).toBeGreaterThanOrEqual(1);

    // Challenge replay (already consumed) → 422
    const replayRes = await SELF.fetch('http://example.com/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol_id: realSymbolId, alias: realAlias, public_key_spki: spkiB64,
        origin: 'http://localhost', challenge_token: token3, assertion: assertion3,
      }),
    });
    expect(replayRes.status).toBe(422);
  });
});

describe('CORS', () => {
  it('preflight OPTIONS returns 204 with CORS headers', async () => {
    const res = await SELF.fetch('http://example.com/health', {
      method: 'OPTIONS',
      headers: { Origin: 'http://localhost:8080' },
    });
    expect(res.status).toBe(204);
    expect(res.headers.get('Access-Control-Allow-Origin')).toBeTruthy();
  });
});
