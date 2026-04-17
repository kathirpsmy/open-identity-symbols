/**
 * Open Identity Symbols — PWA (Phase 2 + Phase 3)
 *
 * Phase 2 flows (no server required):
 *   Generate  — navigator.credentials.create() → public key → SHA-256 → 3 symbols
 *   Retrieve  — navigator.credentials.get()    → credentialId → IDB lookup → show
 *
 * Phase 3 flows (optional discovery server):
 *   Publish   — sign a server challenge → POST /publish → identity is findable globally
 *   Search    — GET /search?q=... → browse published identities on any server
 *   Profile   — sign a challenge → PUT /profile → update public display name / bio
 *
 * Storage strategy (layered durability):
 *   localStorage  — fast read on page load; may be cleared by user
 *   IndexedDB     — survives most "clear cookies" actions; keyed by credentialId
 */

import { POOL } from "./data/pool.js";
import { ALIAS } from "./data/alias.js";

// ─────────────────────────────────────────────────────────────────────────────
// Symbol derivation  (mirrors docs/architecture.md)
// ─────────────────────────────────────────────────────────────────────────────

function readUint32BE(bytes, offset) {
  return (
    ((bytes[offset] << 24) |
      (bytes[offset + 1] << 16) |
      (bytes[offset + 2] << 8) |
      bytes[offset + 3]) >>>
    0
  );
}

async function deriveIdentity(publicKeyBytes) {
  const poolSize = POOL.length;
  const digestBuf = await crypto.subtle.digest("SHA-256", publicKeyBytes);
  const digest = new Uint8Array(digestBuf);

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
    alias: `${ALIAS[idxA]}-${ALIAS[idxB]}-${ALIAS[idxC]}`,
    indices: [idxA, idxB, idxC],
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// IndexedDB  — primary durable store, keyed by credentialId
// ─────────────────────────────────────────────────────────────────────────────

const IDB_NAME = "ois-identities";
const IDB_VER  = 1;
const IDB_STORE = "identities";

function openIDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, IDB_VER);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(IDB_STORE)) {
        db.createObjectStore(IDB_STORE, { keyPath: "credentialId" });
      }
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror   = () => reject(req.error);
  });
}

async function idbSave(identity) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, "readwrite");
    tx.objectStore(IDB_STORE).put(identity);
    tx.oncomplete = resolve;
    tx.onerror    = () => reject(tx.error);
  });
}

async function idbGet(credentialId) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const req = db.transaction(IDB_STORE, "readonly")
                  .objectStore(IDB_STORE)
                  .get(credentialId);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror   = () => reject(req.error);
  });
}

/** Return all stored identities sorted newest-first. */
async function idbGetAll() {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const req = db.transaction(IDB_STORE, "readonly")
                  .objectStore(IDB_STORE)
                  .getAll();
    req.onsuccess = () => {
      const rows = req.result || [];
      rows.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
      resolve(rows);
    };
    req.onerror = () => reject(req.error);
  });
}

async function idbDelete(credentialId) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, "readwrite");
    tx.objectStore(IDB_STORE).delete(credentialId);
    tx.oncomplete = resolve;
    tx.onerror    = () => reject(tx.error);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// localStorage  — fast read cache (mirrors IDB entry for the active identity)
// ─────────────────────────────────────────────────────────────────────────────

const LS_KEY = "ois_identity_v1";

function lsLoad() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)); }
  catch { return null; }
}
function lsSave(data) { localStorage.setItem(LS_KEY, JSON.stringify(data)); }
function lsClear()    { localStorage.removeItem(LS_KEY); }

// ─────────────────────────────────────────────────────────────────────────────
// Unified save / clear
// ─────────────────────────────────────────────────────────────────────────────

async function persistIdentity(identity) {
  lsSave(identity);
  await idbSave(identity).catch(() => {}); // IDB failure is non-fatal
}

async function forgetIdentity(credentialId) {
  lsClear();
  if (credentialId) await idbDelete(credentialId).catch(() => {});
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function toBase64Url(bytes) {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

// ─────────────────────────────────────────────────────────────────────────────
// WebAuthn — create
// ─────────────────────────────────────────────────────────────────────────────

async function createPasskey() {
  const challenge = crypto.getRandomValues(new Uint8Array(32));
  const userId    = crypto.getRandomValues(new Uint8Array(16));

  const credential = await navigator.credentials.create({
    publicKey: {
      challenge,
      rp: { name: "Open Identity Symbols" },
      user: { id: userId, name: "ois-identity", displayName: "OIS Identity" },
      pubKeyCredParams: [
        { type: "public-key", alg: -7   }, // ES256
        { type: "public-key", alg: -257 }, // RS256
        { type: "public-key", alg: -8   }, // EdDSA
      ],
      authenticatorSelection: {
        residentKey: "required",
        userVerification: "required",
      },
      timeout: 120000,
      attestation: "none",
    },
  });

  if (!credential) throw new Error("Passkey creation was cancelled.");

  const spkiBuffer = await credential.response.getPublicKey();
  if (!spkiBuffer) {
    throw new Error(
      "Your browser created a passkey but couldn't export the public key. " +
      "Please try Chrome 85+, Safari 16+, or Firefox 90+."
    );
  }

  return {
    publicKeyBytes: new Uint8Array(spkiBuffer),
    credentialId: toBase64Url(new Uint8Array(credential.rawId)),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// WebAuthn — get (assertion / sign-in)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Ask the user to authenticate with any stored passkey for this origin.
 * Empty allowCredentials = discoverable-credential picker (browser shows all
 * passkeys for this domain, user picks one).
 *
 * Returns the base64url credentialId from the assertion.
 */
async function assertPasskey() {
  const assertion = await navigator.credentials.get({
    publicKey: {
      challenge: crypto.getRandomValues(new Uint8Array(32)),
      allowCredentials: [],   // discoverable — any passkey for this origin
      userVerification: "required",
    },
  });

  if (!assertion) throw new Error("Authentication was cancelled.");
  return toBase64Url(new Uint8Array(assertion.rawId));
}

// ─────────────────────────────────────────────────────────────────────────────
// UI helpers
// ─────────────────────────────────────────────────────────────────────────────

const ALL_STATES = [
  "landing", "generating", "retrieving", "result", "error",
  "publishing", "publish-success", "publish-error",
  "search", "server-config", "recovery",
];

function showState(state) {
  for (const s of ALL_STATES) {
    const el = document.getElementById(`state-${s}`);
    el && (s === state
      ? el.classList.remove("hidden")
      : el.classList.add("hidden"));
  }
}

function showError(msg) {
  document.getElementById("error-message").textContent = msg;
  showState("error");
}

async function copyToClipboard(text, btnEl) {
  try {
    await navigator.clipboard.writeText(text);
    const orig = btnEl.textContent;
    btnEl.textContent = "Copied!";
    setTimeout(() => (btnEl.textContent = orig), 1500);
  } catch {
    const el = document.querySelector(".symbol-id");
    if (el) window.getSelection().selectAllChildren(el);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Flow: generate new identity
// ─────────────────────────────────────────────────────────────────────────────

async function generateIdentity() {
  showState("generating");
  try {
    const { publicKeyBytes, credentialId } = await createPasskey();
    const { symbolId, alias, indices }     = await deriveIdentity(publicKeyBytes);

    const identity = {
      symbolId,
      alias,
      indices,
      credentialId,
      publicKeyB64: toBase64Url(publicKeyBytes),
      createdAt: new Date().toISOString(),
    };

    await persistIdentity(identity);
    renderResult(identity);
  } catch (err) {
    console.error("Generate failed:", err);
    if (err.name === "NotAllowedError") {
      showState("landing");
    } else {
      showError(err.message || "An unexpected error occurred.");
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Flow: retrieve existing identity via passkey assertion
// ─────────────────────────────────────────────────────────────────────────────

async function retrieveIdentity() {
  showState("retrieving");
  try {
    const credentialId = await assertPasskey();

    // Look up stored public key + symbol in IndexedDB
    const stored = await idbGet(credentialId);
    if (stored) {
      lsSave(stored); // re-populate fast cache
      renderResult(stored);
      return;
    }

    // IDB miss — storage was cleared. We can't re-derive without the public key.
    showError(
      "Your passkey was recognised but the identity data is no longer in " +
      "this browser's storage.\n\n" +
      "If you previously published your identity to a discovery server, " +
      "use \u201CRecover from discovery server\u201D on the home screen to restore it. " +
      "Otherwise, you can generate a new identity."
    );
  } catch (err) {
    console.error("Retrieve failed:", err);
    if (err.name === "NotAllowedError") {
      // User dismissed the passkey picker — go back silently
      showState("landing");
    } else {
      showError(err.message || "Could not retrieve identity.");
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Flow: generate new (with confirmation guard)
// ─────────────────────────────────────────────────────────────────────────────

async function handleReset() {
  const confirmed = confirm(
    "This will create a brand-new passkey and derive a different symbol triple.\n\n" +
    "Your existing identity will be forgotten on this device. Continue?"
  );
  if (!confirmed) return;

  const stored = lsLoad();
  await forgetIdentity(stored?.credentialId);
  showState("landing");
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3 — Discovery server config
// ─────────────────────────────────────────────────────────────────────────────

const SERVER_KEY = "ois_server_url_v1";

function getServerUrl()          { return localStorage.getItem(SERVER_KEY) || ""; }
function setServerUrl(url)       { if (url) localStorage.setItem(SERVER_KEY, url); else localStorage.removeItem(SERVER_KEY); }

function fromBase64Url(s) {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  const pad = (4 - s.length % 4) % 4;
  return Uint8Array.from(atob(s + "=".repeat(pad)), (c) => c.charCodeAt(0));
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3 — Publish identity to discovery server
// ─────────────────────────────────────────────────────────────────────────────

async function publishIdentity() {
  const serverUrl = getServerUrl().replace(/\/$/, "");
  if (!serverUrl) {
    showState("server-config");
    return;
  }

  const identity = lsLoad();
  if (!identity) { showState("landing"); return; }

  showState("publishing");
  try {
    // 1. Fetch challenge from server
    const challengeRes = await fetch(`${serverUrl}/challenge`);
    if (!challengeRes.ok) throw new Error(`Server returned ${challengeRes.status} for /challenge`);
    const { token } = await challengeRes.json();

    // 2. Sign with the specific passkey (use stored credentialId)
    const challengeBytes = fromBase64Url(
      btoa(String.fromCharCode(...new Uint8Array(
        Array.from({ length: 32 }, (_, i) => parseInt(token.slice(i * 2, i * 2 + 2), 16))
      ))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "")
    );
    // Simpler: decode hex token directly to bytes
    const hexBytes = new Uint8Array(token.match(/.{2}/g).map((b) => parseInt(b, 16)));

    const assertion = await navigator.credentials.get({
      publicKey: {
        challenge: hexBytes,
        allowCredentials: [{
          id: fromBase64Url(identity.credentialId),
          type: "public-key",
        }],
        userVerification: "required",
      },
    });
    if (!assertion) throw new Error("Passkey authentication cancelled.");

    // 3. Publish
    const body = {
      symbol_id:       identity.symbolId,
      alias:           identity.alias,
      public_key_spki: identity.publicKeyB64,
      origin:          location.origin,
      challenge_token: token,
      assertion: {
        credential_id:       identity.credentialId,
        client_data_json:    toBase64Url(new Uint8Array(assertion.response.clientDataJSON)),
        authenticator_data:  toBase64Url(new Uint8Array(assertion.response.authenticatorData)),
        signature:           toBase64Url(new Uint8Array(assertion.response.signature)),
      },
      public_profile: identity.publicProfile || null,
    };

    const publishRes = await fetch(`${serverUrl}/publish`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });

    const publishData = await publishRes.json();
    if (!publishRes.ok) throw new Error(publishData.detail || `Server error ${publishRes.status}`);

    // Mark as published in IDB/localStorage
    const updated = { ...identity, publishedAt: publishData.published_at, serverUrl };
    await persistIdentity(updated);
    renderResult(updated);
    document.getElementById("publish-success-msg").textContent =
      `Published to ${serverUrl} on ${new Date(publishData.published_at).toLocaleDateString()}`;
    showState("publish-success");

  } catch (err) {
    console.error("Publish failed:", err);
    if (err.name === "NotAllowedError") {
      showState("result");
    } else {
      document.getElementById("publish-error-msg").textContent = err.message;
      showState("publish-error");
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3 — Search
// ─────────────────────────────────────────────────────────────────────────────

async function runSearch() {
  const serverUrl = getServerUrl().replace(/\/$/, "");
  const query = document.getElementById("search-input").value.trim();
  if (!query) return;
  if (!serverUrl) {
    document.getElementById("search-results").innerHTML =
      `<p class="search-hint">No discovery server configured. Set one in server settings.</p>`;
    return;
  }

  document.getElementById("search-results").innerHTML = `<p class="search-hint">Searching…</p>`;

  try {
    const res  = await fetch(`${serverUrl}/search?q=${encodeURIComponent(query)}&limit=20`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Server error ${res.status}`);

    if (data.total === 0) {
      document.getElementById("search-results").innerHTML =
        `<p class="search-hint">No identities found for "${query}".</p>`;
      return;
    }

    document.getElementById("search-results").innerHTML = data.results.map((r) => `
      <div class="search-card">
        <div class="search-symbol">${r.symbol_id}</div>
        <div class="search-alias">${r.alias}</div>
        ${r.public_profile?.display_name
          ? `<div class="search-name">${escapeHtml(r.public_profile.display_name)}</div>`
          : ""}
        <div class="search-meta">Published ${new Date(r.published_at).toLocaleDateString()}</div>
      </div>
    `).join("") + (data.total > 20
      ? `<p class="search-hint">${data.total} total — showing first 20</p>`
      : "");

  } catch (err) {
    document.getElementById("search-results").innerHTML =
      `<p class="search-hint" style="color:var(--danger)">Search failed: ${escapeHtml(err.message)}</p>`;
  }
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3 — Server config state
// ─────────────────────────────────────────────────────────────────────────────

function openServerConfig() {
  document.getElementById("server-url-input").value = getServerUrl();
  showState("server-config");
}

function saveServerConfig() {
  const url = document.getElementById("server-url-input").value.trim();
  if (url && !url.startsWith("http")) {
    alert("Server URL must start with http:// or https://");
    return;
  }
  setServerUrl(url);
  document.getElementById("server-config-saved").textContent =
    url ? `Saved: ${url}` : "Server cleared.";
  // Return to wherever the user came from
  const identity = lsLoad();
  if (identity?.symbolId) renderResult(identity);
  else showState("landing");
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3 — Cross-device recovery via discovery server
// ─────────────────────────────────────────────────────────────────────────────

function openRecovery() {
  document.getElementById("recovery-server-input").value = getServerUrl();
  document.getElementById("recovery-error").textContent  = "";
  showState("recovery");
}

async function recoveryFromDiscovery() {
  const serverUrl = document.getElementById("recovery-server-input").value.trim().replace(/\/$/, "");
  const errorEl   = document.getElementById("recovery-error");
  errorEl.textContent = "";

  if (!serverUrl) {
    errorEl.textContent = "Please enter a discovery server URL.";
    return;
  }
  if (!serverUrl.startsWith("http")) {
    errorEl.textContent = "Server URL must start with http:// or https://";
    return;
  }

  setServerUrl(serverUrl);
  showState("retrieving");

  try {
    // 1. Prove passkey ownership — browser shows discoverable-credential picker
    const assertion = await navigator.credentials.get({
      publicKey: {
        challenge: crypto.getRandomValues(new Uint8Array(32)),
        allowCredentials: [],   // discoverable
        userVerification: "required",
      },
    });
    if (!assertion) throw new Error("Authentication was cancelled.");

    const credentialId = toBase64Url(new Uint8Array(assertion.rawId));

    // 2. Look up the identity on the discovery server by credential ID
    const res = await fetch(`${serverUrl}/lookup/credential/${encodeURIComponent(credentialId)}`);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(
        res.status === 404
          ? "Your passkey was not found on this discovery server. " +
            "Make sure the server URL is correct and that you previously published your identity there."
          : body.detail || `Server error ${res.status}`
      );
    }
    const data = await res.json();

    // 3. Re-derive symbols from the returned public key (verifies server data integrity)
    const publicKeyBytes = fromBase64Url(data.public_key_spki);
    const { symbolId, alias, indices } = await deriveIdentity(publicKeyBytes);

    if (symbolId !== data.symbol_id || alias !== data.alias) {
      throw new Error(
        "The server returned a public key that doesn\u2019t match the stored symbols. " +
        "The server data may be corrupted — contact the server operator."
      );
    }

    // 4. Restore identity locally and show result
    const identity = {
      symbolId,
      alias,
      indices,
      credentialId,
      publicKeyB64: data.public_key_spki,
      createdAt:    data.published_at,
      publishedAt:  data.published_at,
      serverUrl,
    };

    await persistIdentity(identity);
    renderResult(identity);

  } catch (err) {
    console.error("Recovery failed:", err);
    if (err.name === "NotAllowedError") {
      // User dismissed the passkey picker — return to recovery screen
      showState("recovery");
    } else {
      showError(err.message || "Recovery failed.");
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Render result (updated to show publish/server status)
// ─────────────────────────────────────────────────────────────────────────────

function renderResult(identity) {
  document.getElementById("result-symbol-id").textContent = identity.symbolId;
  document.getElementById("result-alias").textContent     = identity.alias;
  document.getElementById("result-created").textContent   = identity.createdAt
    ? new Date(identity.createdAt).toLocaleDateString(undefined, {
        year: "numeric", month: "long", day: "numeric",
      })
    : "";

  const publishStatus = document.getElementById("result-publish-status");
  if (identity.publishedAt && identity.serverUrl) {
    publishStatus.textContent = `Published to ${identity.serverUrl}`;
    publishStatus.classList.remove("hidden");
  } else {
    publishStatus.classList.add("hidden");
  }

  showState("result");
}

// ─────────────────────────────────────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────────────────────────────────────

async function boot() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js").catch(() => {});
  }

  // Wire Phase 2 buttons
  document.getElementById("btn-generate")      .addEventListener("click", generateIdentity);
  document.getElementById("btn-retrieve")      .addEventListener("click", retrieveIdentity);
  document.getElementById("btn-reset")         .addEventListener("click", handleReset);
  document.getElementById("btn-retry")         .addEventListener("click", () => showState("landing"));
  document.getElementById("btn-retry-retrieve").addEventListener("click", retrieveIdentity);

  document.getElementById("btn-copy-symbol").addEventListener("click", (e) => {
    const s = lsLoad(); if (s) copyToClipboard(s.symbolId, e.currentTarget);
  });
  document.getElementById("btn-copy-alias").addEventListener("click", (e) => {
    const s = lsLoad(); if (s) copyToClipboard(s.alias, e.currentTarget);
  });

  // Wire Phase 3 buttons
  document.getElementById("btn-publish")           .addEventListener("click", publishIdentity);
  document.getElementById("btn-search-open")       .addEventListener("click", () => showState("search"));
  document.getElementById("btn-server-config")     .addEventListener("click", openServerConfig);
  document.getElementById("btn-server-config-save").addEventListener("click", saveServerConfig);
  document.getElementById("btn-publish-back")      .addEventListener("click", () => { const s = lsLoad(); if (s?.symbolId) renderResult(s); else showState("landing"); });
  document.getElementById("btn-publish-error-back").addEventListener("click", () => { const s = lsLoad(); if (s?.symbolId) renderResult(s); else showState("landing"); });
  document.getElementById("btn-search-back")       .addEventListener("click", () => { const s = lsLoad(); if (s?.symbolId) renderResult(s); else showState("landing"); });
  document.getElementById("btn-server-config-cancel").addEventListener("click", () => { const s = lsLoad(); if (s?.symbolId) renderResult(s); else showState("landing"); });

  // Wire recovery buttons
  document.getElementById("btn-recovery-open")  .addEventListener("click", openRecovery);
  document.getElementById("btn-recovery-go")    .addEventListener("click", recoveryFromDiscovery);
  document.getElementById("btn-recovery-cancel").addEventListener("click", () => showState("landing"));

  document.getElementById("search-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") runSearch();
  });
  document.getElementById("btn-search-go").addEventListener("click", runSearch);

  // ── Restore identity on page load ──────────────────────────────────────────
  const ls = lsLoad();
  if (ls?.symbolId) { renderResult(ls); return; }

  try {
    const all = await idbGetAll();
    if (all.length > 0) {
      lsSave(all[0]);
      renderResult(all[0]);
      return;
    }
  } catch { /* IDB unavailable */ }

  showState("landing");
}

document.addEventListener("DOMContentLoaded", boot);
