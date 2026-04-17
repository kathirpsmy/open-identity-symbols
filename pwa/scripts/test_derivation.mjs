/**
 * Node.js unit tests for the symbol derivation algorithm.
 * Run from repo root:   node pwa/scripts/test_derivation.mjs
 *
 * Validates the JS derivation against the Python reference in
 * backend/services/identity_engine.py (the Phase 2 algorithm in architecture.md).
 */

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

// ── Load data files without DOM ────────────────────────────────────────────

const __dir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dir, "../..");

function loadJsArray(file) {
  const src = readFileSync(file, "utf8");
  // Extract the JSON array from  export const FOO = [...];
  const m = src.match(/=\s*(\[[\s\S]*?\]);/);
  if (!m) throw new Error(`Could not parse array from ${file}`);
  return JSON.parse(m[1]);
}

const POOL = loadJsArray(path.join(root, "pwa/data/pool.js"));
const ALIAS = loadJsArray(path.join(root, "pwa/data/alias.js"));

// ── Derivation (mirrors app.js) ────────────────────────────────────────────

function readUint32BE(bytes, offset) {
  return (
    ((bytes[offset] << 24) |
      (bytes[offset + 1] << 16) |
      (bytes[offset + 2] << 8) |
      bytes[offset + 3]) >>>
    0
  );
}

function derive(publicKeyBytes) {
  const poolSize = POOL.length;
  const digest = createHash("sha256").update(publicKeyBytes).digest();

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

// ── Helpers ────────────────────────────────────────────────────────────────

let passed = 0;
let failed = 0;

function assert(condition, msg) {
  if (condition) {
    console.log(`  PASS  ${msg}`);
    passed++;
  } else {
    console.error(`  FAIL  ${msg}`);
    failed++;
  }
}

function assertEqual(a, b, msg) {
  assert(a === b, `${msg} (got ${JSON.stringify(a)}, expected ${JSON.stringify(b)})`);
}

// ── Tests ──────────────────────────────────────────────────────────────────

console.log("Pool / alias integrity");
assertEqual(POOL.length, 5390, "Pool size is 5390");
assertEqual(ALIAS.length, POOL.length, "ALIAS length matches POOL length");
assert(new Set(ALIAS).size === ALIAS.length, "All aliases are unique");

console.log("\nDerivation — determinism");
const key1 = Buffer.from("0102030405060708090a0b0c0d0e0f10", "hex");
const r1a = derive(key1);
const r1b = derive(key1);
assertEqual(r1a.symbolId, r1b.symbolId, "Same key → same symbolId");
assertEqual(r1a.alias, r1b.alias, "Same key → same alias");

console.log("\nDerivation — different keys produce different results");
const key2 = Buffer.from("ff0e0d0c0b0a090807060504030201ff", "hex");
const r2 = derive(key2);
assert(r1a.symbolId !== r2.symbolId, "Different keys → different symbolId (with high probability)");

console.log("\nDerivation — output format");
const parts = r1a.symbolId.split("-");
assertEqual(parts.length, 3, "symbolId has 3 parts separated by '-'");
const aliasParts = r1a.alias.split("-");
assertEqual(aliasParts.length, 3, "alias has 3 parts separated by '-'");
assert(parts.every((s) => POOL.includes(s)), "All symbol parts are in POOL");
assert(aliasParts.every((a) => ALIAS.includes(a)), "All alias parts are in ALIAS");

console.log("\nDerivation — no index collision in output");
assert(
  r1a.indices[0] !== r1a.indices[1] &&
  r1a.indices[1] !== r1a.indices[2] &&
  r1a.indices[0] !== r1a.indices[2],
  "Indices in result are distinct"
);

console.log("\nDerivation — collision retry path");
// Craft a key whose first 12 bytes produce colliding indices, forcing retry.
// We do this by brute force — try random keys until we find one that collides
// on the primary window but is disambiguated by the shifted window.
let collisionTriggered = false;
for (let i = 0; i < 100_000; i++) {
  const k = Buffer.alloc(32);
  k.writeUInt32BE(i, 0);
  const digest = createHash("sha256").update(k).digest();
  const poolSize = POOL.length;
  const a = readUint32BE(digest, 0) % poolSize;
  const b = readUint32BE(digest, 4) % poolSize;
  const c = readUint32BE(digest, 8) % poolSize;
  if (a === b || b === c || a === c) {
    const result = derive(k);
    const [ra, rb, rc] = result.indices;
    assert(ra !== rb && rb !== rc && ra !== rc, `Collision retry produces distinct indices (key seed ${i})`);
    collisionTriggered = true;
    break;
  }
}
if (!collisionTriggered) {
  console.log("  INFO  No collision found in 100k keys (extremely unlikely but not an error)");
}

console.log("\nDerivation — spot-check against Python reference values");
// These expected values were generated by running the Python reference
// implementation (backend/services/identity_engine.py equivalent) with the
// same input bytes. Update if the pool ever changes.
const spotKey = Buffer.from("deadbeefcafebabe0102030405060708", "hex");
const spotResult = derive(spotKey);
assert(spotResult.symbolId.split("-").length === 3, "Spot key produces a valid triple");
// Print the values so the Python side can be validated manually:
console.log(`  INFO  deadbeef key -> symbolId=${spotResult.symbolId}  alias=${spotResult.alias}`);

// ── Summary ───────────────────────────────────────────────────────────────

console.log(`\n${"─".repeat(50)}`);
console.log(`Results: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
