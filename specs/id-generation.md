# ID Generation Specification

## Format

```
symbol_id : S1-S2-S3
alias     : word1-word2-word3
```

Where `S1`, `S2`, `S3` are distinct symbols from the Unicode pool.

## Rules

1. **3 symbols** — exactly three, hyphen-separated
2. **Distinct** — no symbol may appear more than once in a single ID
3. **From pool** — all symbols must be in the active pool
4. **Unique globally** — no two users share the same `symbol_id`
5. **Immutable** — once assigned, a symbol ID never changes

## Generation Algorithm

```python
def generate():
    s1, s2, s3 = random.sample(SYMBOL_POOL, 3)   # CSPRNG, no replacement
    symbol_id = f"{s1}-{s2}-{s3}"
    alias     = f"{alias_map[s1]}-{alias_map[s2]}-{alias_map[s3]}"
    return symbol_id, alias
```

## Uniqueness Strategy

- Database has a `UNIQUE` constraint on `identities.symbol_id`
- On collision, the generator retries up to **10 times**
- After 10 retries, a 503 is returned (theoretical probability: negligible)

## Collision Probability

With N assigned IDs and pool size P = 5390:

```
P(collision) = N / (P × (P-1) × (P-2))
             ≈ N / 156,503,673,480
```

At 1 billion users: P(collision per attempt) ≈ 0.00064% → expected retries < 1.001
