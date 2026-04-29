/**
 * OIS Discovery — Cloudflare Worker + D1
 *
 * Same REST API contract as discovery/ (FastAPI). No PWA changes required.
 * Supports ES256 (P-256) passkeys only — same as current FastAPI implementation.
 *
 * Endpoints:
 *   GET  /health
 *   GET  /challenge
 *   POST /publish
 *   PUT  /profile
 *   GET  /lookup/{symbol_id}
 *   GET  /lookup/alias/{alias}
 *   GET  /lookup/key/{public_key_id}
 *   GET  /lookup/credential/{credential_id}
 *   GET  /search?q=&limit=&offset=
 *
 * Environment bindings (wrangler.toml + secrets):
 *   DB                     D1 database
 *   WEBAUTHN_VERIFY_ORIGIN "true" | "false"  (default "true")
 *   ALLOWED_ORIGINS        comma-separated origins
 *   CHALLENGE_TTL_SECONDS  number string      (default "300")
 */

import { POOL  } from '../../pwa/data/pool.js';
import { ALIAS } from '../../pwa/data/alias.js';

// ─── Encoding helpers ─────────────────────────────────────────────────────────

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

function bytesEqual(a, b) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
}

// ─── DER ECDSA → IEEE P1363 (raw r||s, 64 bytes for P-256) ──────────────────
// Web Crypto verify() expects P1363 format; WebAuthn provides DER-encoded sigs.

function derToRaw(der) {
  let off = 0;
  if (der[off++] !== 0x30) throw new Error('Signature is not a DER SEQUENCE');
  // Skip sequence length (1 or 2 bytes)
  if (der[off] & 0x80) off += (der[off] & 0x7f) + 1; else off++;

  // r INTEGER
  if (der[off++] !== 0x02) throw new Error('Expected INTEGER tag for r');
  const rLen = der[off++];
  let r = der.slice(off, off + rLen); off += rLen;

  // s INTEGER
  if (der[off++] !== 0x02) throw new Error('Expected INTEGER tag for s');
  const sLen = der[off++];
  let s = der.slice(off, off + sLen);

  // Strip leading 0x00 padding bytes (added to preserve sign)
  if (r[0] === 0x00) r = r.slice(1);
  if (s[0] === 0x00) s = s.slice(1);

  const raw = new Uint8Array(64);
  raw.set(r, 32 - r.length);
  raw.set(s, 64 - s.length);
  return raw;
}

// ─── Symbol derivation (mirrors pwa/app.js exactly) ──────────────────────────

function readUint32BE(bytes, off) {
  return ((bytes[off] << 24) | (bytes[off+1] << 16) | (bytes[off+2] << 8) | bytes[off+3]) >>> 0;
}

async function deriveIdentity(spkiBytes) {
  const digest   = new Uint8Array(await crypto.subtle.digest('SHA-256', spkiBytes));
  const poolSize = POOL.length;

  let idxA = readUint32BE(digest, 0) % poolSize;
  let idxB = readUint32BE(digest, 4) % poolSize;
  let idxC = readUint32BE(digest, 8) % poolSize;

  if (idxA === idxB || idxB === idxC || idxA === idxC) {
    idxA = readUint32BE(digest, 3) % poolSize;
    idxB = readUint32BE(digest, 6) % poolSize;
    idxC = readUint32BE(digest, 9) % poolSize;
  }

  return {
    symbolId: `${POOL[idxA]}-${POOL[idxB]}-${POOL[idxC]}`,
    alias:    `${ALIAS[idxA]}-${ALIAS[idxB]}-${ALIAS[idxC]}`,
  };
}

async function publicKeyId(spkiBytes) {
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', spkiBytes));
  return Array.from(digest).map(b => b.toString(16).padStart(2, '0')).join('');
}

// ─── WebAuthn assertion verification (ES256 / P-256) ─────────────────────────

async function verifyAssertion(spkiB64url, cdJsonB64url, authDataB64url, sigB64url, expectedHex, expectedOrigin, doVerify) {
  const cdRaw     = fromBase64Url(cdJsonB64url);
  const authData  = fromBase64Url(authDataB64url);
  const sigDer    = fromBase64Url(sigB64url);
  const spkiBytes = fromBase64Url(spkiB64url);

  const cd = JSON.parse(new TextDecoder().decode(cdRaw));

  if (cd.type !== 'webauthn.get')
    throw new Error(`clientDataJSON.type must be 'webauthn.get', got '${cd.type}'`);

  // Challenge: server issued hex; PWA decoded hex→bytes and passed to get();
  // browser base64url-encoded those bytes into clientDataJSON.challenge.
  const expectedBytes = hexToBytes(expectedHex);
  const actualBytes   = fromBase64Url(cd.challenge || '');
  if (!bytesEqual(actualBytes, expectedBytes)) throw new Error('Challenge mismatch');

  if (doVerify) {
    if (cd.origin !== expectedOrigin)
      throw new Error(`Origin mismatch: expected '${expectedOrigin}', got '${cd.origin}'`);

    if (authData.length < 37) throw new Error('authenticatorData too short');
    const rpId          = new URL(expectedOrigin).hostname;
    const expectedRpHash = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(rpId)));
    if (!bytesEqual(expectedRpHash, authData.slice(0, 32)))
      throw new Error('RP ID hash mismatch');
  }

  if (authData.length < 33 || !(authData[32] & 0x01))
    throw new Error('User Presence flag not set in authenticatorData');

  // verificationData = authenticatorData || SHA-256(clientDataJSON)
  const cdHash = new Uint8Array(await crypto.subtle.digest('SHA-256', cdRaw));
  const vData  = new Uint8Array(authData.length + 32);
  vData.set(authData);
  vData.set(cdHash, authData.length);

  const pubKey = await crypto.subtle.importKey(
    'spki', spkiBytes, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']
  );

  // WebAuthn signatures are DER-encoded; Web Crypto needs P1363 (raw r||s)
  const sigRaw = derToRaw(sigDer);
  const valid  = await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, pubKey, sigRaw, vData);
  if (!valid) throw new Error('Signature verification failed');
}

// ─── CORS ─────────────────────────────────────────────────────────────────────

function resolveOrigin(request, env) {
  const origin  = request.headers.get('Origin') || '';
  const allowed = (env.ALLOWED_ORIGINS || 'https://prysym.github.io').split(',').map(s => s.trim());
  if (allowed.includes(origin)) return origin;
  if (origin.startsWith('http://localhost:')) return origin;
  return allowed[0];
}

function corsHeaders(request, env) {
  return {
    'Access-Control-Allow-Origin':  resolveOrigin(request, env),
    'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

// ─── Response helpers ─────────────────────────────────────────────────────────

function jsonResp(request, env, data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders(request, env) },
  });
}

function errResp(request, env, detail, status) {
  return jsonResp(request, env, { detail }, status);
}

// ─── DB row → public shape ────────────────────────────────────────────────────

function rowToPublic(row) {
  return {
    public_key_id:   row.public_key_id,
    symbol_id:       row.symbol_id,
    alias:           row.alias,
    public_key_spki: row.public_key_spki,
    credential_id:   row.credential_id  || null,
    origin:          row.origin,
    public_profile:  row.public_profile ? JSON.parse(row.public_profile) : null,
    published_at:    row.published_at,
    updated_at:      row.updated_at,
  };
}

// ─── Challenge helpers ────────────────────────────────────────────────────────

async function consumeChallenge(token, env) {
  const row = await env.DB.prepare('SELECT * FROM challenges WHERE token = ?').bind(token).first();
  if (!row) throw { status: 422, detail: 'Invalid or unknown challenge token' };
  if (new Date(row.expires_at + 'Z') < new Date()) {
    await env.DB.prepare('DELETE FROM challenges WHERE token = ?').bind(token).run().catch(() => {});
    throw { status: 422, detail: 'Challenge token has expired — request a new one from GET /challenge' };
  }
  await env.DB.prepare('DELETE FROM challenges WHERE token = ?').bind(token).run();
}

// ─── Handlers ─────────────────────────────────────────────────────────────────

async function handleHealth(request, env) {
  let dbOk = true;
  try { await env.DB.prepare('SELECT 1').first(); } catch { dbOk = false; }
  return jsonResp(request, env, { status: 'ok', db: dbOk ? 'ok' : 'error' });
}

async function handleChallenge(request, env) {
  const ttl = parseInt(env.CHALLENGE_TTL_SECONDS || '300', 10);
  const expiresAt = new Date(Date.now() + ttl * 1000).toISOString().replace('Z', '');

  // Purge stale tokens (best-effort housekeeping, same as FastAPI)
  await env.DB.prepare("DELETE FROM challenges WHERE expires_at < datetime('now')").run().catch(() => {});

  const rawBytes = crypto.getRandomValues(new Uint8Array(32));
  const token    = Array.from(rawBytes).map(b => b.toString(16).padStart(2, '0')).join('');

  await env.DB.prepare('INSERT INTO challenges (token, expires_at) VALUES (?, ?)').bind(token, expiresAt).run();

  return jsonResp(request, env, { token, expires_at: expiresAt });
}

async function handlePublish(request, env) {
  let body;
  try { body = await request.json(); } catch { return errResp(request, env, 'Invalid JSON body', 400); }

  const { symbol_id, alias, public_key_spki, origin, challenge_token, assertion, public_profile } = body ?? {};

  if (!symbol_id || !alias || !public_key_spki || !origin || !challenge_token || !assertion) {
    return errResp(request, env, 'Missing required fields: symbol_id, alias, public_key_spki, origin, challenge_token, assertion', 422);
  }
  if (!assertion.client_data_json || !assertion.authenticator_data || !assertion.signature) {
    return errResp(request, env, 'assertion must include client_data_json, authenticator_data, signature', 422);
  }

  // 1. Decode public key + re-derive symbols (security: server doesn't trust client's symbol claim)
  let spkiBytes;
  try { spkiBytes = fromBase64Url(public_key_spki); }
  catch { return errResp(request, env, 'public_key_spki is not valid base64url', 422); }

  const { symbolId: derived, alias: derivedAlias } = await deriveIdentity(spkiBytes);
  if (derived !== symbol_id)
    return errResp(request, env, `symbol_id mismatch: submitted '${symbol_id}' but key derives to '${derived}'`, 422);
  if (derivedAlias !== alias)
    return errResp(request, env, `alias mismatch: submitted '${alias}' but key derives to '${derivedAlias}'`, 422);

  // 2. Consume challenge (single-use; delete before assertion to prevent replay)
  try { await consumeChallenge(challenge_token, env); }
  catch (e) { return errResp(request, env, e.detail, e.status); }

  // 3. Verify WebAuthn assertion
  const doVerify = (env.WEBAUTHN_VERIFY_ORIGIN ?? 'true') === 'true';
  try {
    await verifyAssertion(
      public_key_spki,
      assertion.client_data_json,
      assertion.authenticator_data,
      assertion.signature,
      challenge_token,
      origin,
      doVerify,
    );
  } catch (e) {
    return errResp(request, env, `Assertion verification failed: ${e.message}`, 401);
  }

  // 4. Upsert
  const pkId        = await publicKeyId(spkiBytes);
  const profileJson = public_profile ? JSON.stringify(public_profile) : null;
  const now         = new Date().toISOString().replace('Z', '');

  const existing = await env.DB.prepare('SELECT * FROM identities WHERE public_key_id = ?').bind(pkId).first();

  if (existing) {
    await env.DB.prepare(
      'UPDATE identities SET public_profile = ?, credential_id = ?, updated_at = ? WHERE public_key_id = ?'
    ).bind(profileJson, assertion.credential_id ?? null, now, pkId).run();
    const row = await env.DB.prepare('SELECT * FROM identities WHERE public_key_id = ?').bind(pkId).first();
    return jsonResp(request, env, {
      public_key_id: row.public_key_id,
      symbol_id:     row.symbol_id,
      alias:         row.alias,
      published_at:  row.published_at,
      updated_at:    row.updated_at,
    }, 201);
  }

  try {
    await env.DB.prepare(
      `INSERT INTO identities
         (public_key_id, symbol_id, alias, public_key_spki, credential_id, origin, public_profile, published_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).bind(pkId, symbol_id, alias, public_key_spki, assertion.credential_id ?? null, origin, profileJson, now, now).run();
  } catch (e) {
    if (e.message?.includes('UNIQUE')) {
      return errResp(request, env, `symbol_id '${symbol_id}' is already claimed by a different key`, 409);
    }
    throw e;
  }

  return jsonResp(request, env, { public_key_id: pkId, symbol_id, alias, published_at: now, updated_at: now }, 201);
}

async function handleProfile(request, env) {
  let body;
  try { body = await request.json(); } catch { return errResp(request, env, 'Invalid JSON body', 400); }

  const { symbol_id, origin, challenge_token, assertion, public_profile } = body ?? {};

  if (!symbol_id || !origin || !challenge_token || !assertion) {
    return errResp(request, env, 'Missing required fields: symbol_id, origin, challenge_token, assertion', 422);
  }

  const existing = await env.DB.prepare('SELECT * FROM identities WHERE symbol_id = ?').bind(symbol_id).first();
  if (!existing) return errResp(request, env, `Symbol '${symbol_id}' not found on this server`, 404);

  try { await consumeChallenge(challenge_token, env); }
  catch (e) { return errResp(request, env, e.detail, e.status); }

  const doVerify = (env.WEBAUTHN_VERIFY_ORIGIN ?? 'true') === 'true';
  try {
    await verifyAssertion(
      existing.public_key_spki,
      assertion.client_data_json,
      assertion.authenticator_data,
      assertion.signature,
      challenge_token,
      origin,
      doVerify,
    );
  } catch (e) {
    return errResp(request, env, `Assertion verification failed: ${e.message}`, 401);
  }

  const profileJson = public_profile ? JSON.stringify(public_profile) : null;
  const now         = new Date().toISOString().replace('Z', '');
  await env.DB.prepare('UPDATE identities SET public_profile = ?, updated_at = ? WHERE symbol_id = ?')
    .bind(profileJson, now, symbol_id).run();

  const row = await env.DB.prepare('SELECT * FROM identities WHERE symbol_id = ?').bind(symbol_id).first();
  return jsonResp(request, env, rowToPublic(row));
}

async function handleLookupAlias(alias, request, env) {
  const row = await env.DB.prepare('SELECT * FROM identities WHERE LOWER(alias) = LOWER(?)').bind(alias).first();
  if (!row) return errResp(request, env, `Alias '${alias}' not found on this server`, 404);
  return jsonResp(request, env, rowToPublic(row));
}

async function handleLookupKey(pkId, request, env) {
  const row = await env.DB.prepare('SELECT * FROM identities WHERE public_key_id = ?').bind(pkId).first();
  if (!row) return errResp(request, env, `Key fingerprint '${pkId}' not found on this server`, 404);
  return jsonResp(request, env, rowToPublic(row));
}

async function handleLookupCredential(credId, request, env) {
  const row = await env.DB.prepare('SELECT * FROM identities WHERE credential_id = ?').bind(credId).first();
  if (!row) return errResp(request, env, 'Credential ID not found on this server. Make sure you are using the correct server URL and that you previously published your identity there.', 404);
  return jsonResp(request, env, rowToPublic(row));
}

async function handleLookupSymbol(symbolId, request, env) {
  const row = await env.DB.prepare('SELECT * FROM identities WHERE symbol_id = ?').bind(symbolId).first();
  if (!row) return errResp(request, env, `Symbol '${symbolId}' not found on this server`, 404);
  return jsonResp(request, env, rowToPublic(row));
}

async function handleSearch(request, env) {
  const url    = new URL(request.url);
  const q      = url.searchParams.get('q') || '';
  const limit  = Math.min(Math.max(parseInt(url.searchParams.get('limit')  || '20', 10), 1), 100);
  const offset = Math.max(parseInt(url.searchParams.get('offset') || '0',  10), 0);

  if (!q) return errResp(request, env, 'q parameter is required', 422);

  const pattern = `%${q}%`;
  const { results } = await env.DB.prepare(
    'SELECT * FROM identities WHERE symbol_id LIKE ? OR alias LIKE ? ORDER BY published_at DESC LIMIT ? OFFSET ?'
  ).bind(pattern, pattern, limit, offset).all();

  const countRow = await env.DB.prepare(
    'SELECT COUNT(*) AS total FROM identities WHERE symbol_id LIKE ? OR alias LIKE ?'
  ).bind(pattern, pattern).first();
  const total = countRow?.total ?? 0;

  return jsonResp(request, env, { results: results.map(rowToPublic), total, limit, offset });
}

// ─── Router ───────────────────────────────────────────────────────────────────

async function route(request, env) {
  const url    = new URL(request.url);
  const path   = url.pathname;
  const method = request.method;

  if (method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders(request, env) });
  }

  if (path === '/health')                         return handleHealth(request, env);
  if (path === '/challenge' && method === 'GET')  return handleChallenge(request, env);
  if (path === '/publish'   && method === 'POST') return handlePublish(request, env);
  if (path === '/profile'   && method === 'PUT')  return handleProfile(request, env);
  if (path === '/search'    && method === 'GET')  return handleSearch(request, env);

  // /lookup/* — specific routes before the greedy symbol route
  const aliasMatch = path.match(/^\/lookup\/alias\/(.+)$/);
  if (aliasMatch) return handleLookupAlias(decodeURIComponent(aliasMatch[1]), request, env);

  const keyMatch = path.match(/^\/lookup\/key\/([0-9a-fA-F]+)$/);
  if (keyMatch) return handleLookupKey(keyMatch[1], request, env);

  const credMatch = path.match(/^\/lookup\/credential\/(.+)$/);
  if (credMatch) return handleLookupCredential(decodeURIComponent(credMatch[1]), request, env);

  const symbolMatch = path.match(/^\/lookup\/(.+)$/);
  if (symbolMatch) return handleLookupSymbol(decodeURIComponent(symbolMatch[1]), request, env);

  return errResp(request, env, `Not found: ${path}`, 404);
}

async function handleRequest(request, env) {
  try {
    return await route(request, env);
  } catch (e) {
    console.error('Unhandled worker error:', e?.stack ?? e);
    return new Response(JSON.stringify({ detail: 'Internal server error', error: e?.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(request, env) },
    });
  }
}

export default { fetch: handleRequest };
