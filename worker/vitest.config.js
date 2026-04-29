import { defineWorkersConfig } from '@cloudflare/vitest-pool-workers/config';

export default defineWorkersConfig({
  test: {
    poolOptions: {
      workers: {
        wrangler: { configPath: './wrangler.toml' },
        miniflare: {
          // Create in-memory D1 for tests (ignores placeholder database_id)
          d1Databases: ['DB'],
          bindings: {
            WEBAUTHN_VERIFY_ORIGIN:  'false', // skip origin/rpIdHash checks in tests
            ALLOWED_ORIGINS:         'http://localhost,https://PRYSYM.github.io',
            CHALLENGE_TTL_SECONDS:   '300',
          },
        },
      },
    },
  },
});
