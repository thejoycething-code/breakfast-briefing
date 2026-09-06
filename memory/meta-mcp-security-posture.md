---
name: meta-mcp-security-posture
description: "Why the CitizenGO Meta MCP can safely hold a Supabase service key — sensitive tables moved out of PostgREST's reach; self-minted role JWTs are rejected by the gateway"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2168d5ed-2f28-4dd8-af26-046baad76925
  modified: 2026-08-29T18:55:47.906Z
---

The hosted MCP for [[meta-organic-reports]] holds a Supabase **service key**, and
that is acceptable because of what the key can reach, not because of what the key
is.

**Supabase rejects self-minted role keys.** A JWT signed with the project's own
legacy secret carrying `role=meta_readonly` is refused at the gateway as
`{"message":"Invalid API key"}` before Postgres sees it — the gateway validates
against **issued** API keys, not merely a valid signature. Diagnosed by comparing
error bodies on the same request: the real `anon` key returns Postgres `42501`
("grant the required privileges"), proving it authenticated and failed on
permissions, while the self-signed token never authenticated at all. Do not
retry this route.

**So the data was removed from reach instead.** On 29 Aug 2026:
- `clacton_actions` (2,192 supporter records: names, emails, postcodes) and
  `clacton_events` moved to a **`private` schema**. PostgREST only serves schemas
  it is configured to expose, so they are unreachable by ANY key — verified:
  `404 PGRST205` with the service key. Rows intact. Reverse with
  `alter table private.clacton_actions set schema public;`
- `meta_page_tokens` **dropped** — 0 rows for its whole life (the collector reads
  `META_TOKENS`, never a table) while sitting on the public API named "tokens".

The API surface is now **12 objects, all `meta_*`**.

A `meta_readonly` Postgres role exists in `sql/readonly-role.sql`, is correct and
verified (reads all 11 reporting objects, refused on the sensitive three, no
writes), but is **unused** — it cannot be reached over PostgREST. Kept for the day
the MCP connects to Postgres directly.

**Why this matters:** the instinct was to restrict the key. The better move was
to ask why the sensitive data was on the same API surface at all — it was there
only because the reporting tables had been added to a campaign project that has
since closed.

**Security review 30 Aug 2026: all 12 findings closed.** The worst was the shared
token `cgo_team_shared_2026` — a fixed prefix, three dictionary words and a year —
combined with a rate limiter keyed on the credential being tried, so every wrong
guess opened a fresh bucket and nothing throttled brute force. Twelve wrong tokens
returned twelve 401s against production. `/api/oauth/authorize` had no limiter at all.

Now: random 36-char token; weak tokens (under 24 chars, fewer than three character
classes) do not authenticate; failures counted by SOURCE in `meta_auth_failures` so
the limit survives a cold start; constant-time digest comparison; per-person
`name:token` entries in `MCP_TOKENS`; every tools/call logged with who and which
tool, never arguments; JSON-RPC batches capped at 20 with quota charged per message;
all tool `limit`/`days` clamped; CI actions pinned to SHAs with Dependabot; Postgres
error detail kept server-side; refresh TTL 7 days; `redirect_uri` required at /token.
`scripts/test-security.js` — 24 cases.

**How to apply:** the token lives in `.env.new-mcp-token` (gitignored, chmod 600) and
has never been in a transcript.

**DECIDED 30 Aug 2026 — one SHARED team token, not per-person.** MCP_TOKENS is
`team:<token>`. The per-person machinery stays wired (name:token entries, identity
carried through OAuth, immediate revocation, per-name logging) and switching to it
later is editing one environment variable. The user judged per-person credentials
overboard for a read-only internal connector, and said to revisit only if Carlo
asks. Do not re-propose it unprompted.

Trade-off, so nobody rediscovers it: revoking one person means rotating for
everyone, and logs attribute to "team" rather than a name.

To revoke everyone including live OAuth sessions, rotate OAUTH_SIGNING_SECRET and
redeploy. The JWT-secret rotation flagged in the review remains deferred and
should not be raised again unless asked.

**Staff use claude.ai and ChatGPT connectors, not Claude Code.** Both reach the
server over OAuth, so `redirectUriAllowed` must keep trusting chatgpt.com and
chat.openai.com for ANY path — OpenAI generates a callback per connection, and
pinning a path presents later as "the connector stopped working".