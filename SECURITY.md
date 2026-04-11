# Security

## Reporting Vulnerabilities

Please **do not** open a public GitHub issue for security vulnerabilities.

Email: ois.protocol@gmail.com

## Security Model

- Passwords hashed with bcrypt (cost 12)
- TOTP (RFC 6238) required on every login
- JWTs signed with HS256, configurable TTL (default 60 min)
- Profile fields are **private by default** — users must opt-in to public visibility
- No PII stored beyond email address

## Known Limitations (MVP)

- No rate limiting yet (planned for v0.2)
- No refresh tokens (sessions expire after TTL)
- TOTP is the only 2FA method (passkeys planned for v0.2)
