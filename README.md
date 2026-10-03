# SuperDeal 3.0

SuperDeal 3.0 is a deal-discovery and affiliate platform.

## Development approach

Each phase follows: **Build → automated test → inspect → user validation → next phase**.

## Roadmap

1. **Phase 0 — Foundation**: project structure, configuration, automated tests, health check.
2. **Phase 1 — Deal Parser**: turn raw deal messages into structured deal records.
3. **Phase 2 — Deal Database**: SQLite storage, duplicate detection, status and price history.
4. **Phase 3 — Telegram Hunter**: ingest approved/public deal sources.
5. **Phase 4 — Advanced Deduplication**: identify repeated products while preserving price changes.
6. **Phase 5 — Deal Enrichment**: extract discount, coupon, card, COD and category signals.
7. **Phase 6 — Deal API**: expose searchable deals and deal intelligence.
8. **Phase 7 — Search & Filters**: price, merchant and product filtering.
9. **Phase 8 — Price Intelligence**: historical lows, changes and observations.
10. **Phase 9 — Affiliate-ready URLs**: validate provider/source URLs.
11. **Phase 10 — Web Enrichment**: public page metadata and price verification.
12. **Phase 11 — Freshness & Expiry**: stale/future/expired deal handling.
13. **Phase 12 — Verified Affiliate Provider**: EarnKaro-ready provider contract without undocumented API automation.
14. **Phase 13 — Production Telegram Ingestion**: documented Telegram Bot API source.
15. **Phase 14 — Automated Ingestion Worker**: continuous channel polling and persistence.
16. **Phase 15 — Operational Setup**: configuration, logging and Telegram connectivity checks.
17. **Next — Mobile-first Web**: searchable consumer-facing deal discovery.

## Telegram worker configuration

Copy `.env.example` into your runtime environment and set:

- `TELEGRAM_BOT_TOKEN` — Telegram Bot API token; keep it secret.
- `TELEGRAM_CHANNELS` — comma-separated public channel usernames/IDs.
- `DATABASE_URL` — SQLite database path, for example `sqlite:///data/superdeal.db`.
- `TELEGRAM_POLL_INTERVAL` — delay between polling cycles.
- `TELEGRAM_BATCH_LIMIT` — maximum messages fetched per channel per cycle (1–100).
- `LOG_LEVEL` — logging level, default `INFO`.

The bot must have access to the configured channels. Polling uses Telegram's documented Bot API; this worker does not scrape Telegram user accounts or automate Telegram login.

Before starting ingestion, the runner performs a read-only `getMe` connectivity check. A real token is never committed to the repository.

For a local Python environment:

```bash
pip install -e ".[test]"
pytest
```

CI runs the tests remotely on GitHub Actions, so the product owner does not need Python installed locally.


## Telegram reader modes

SuperDeal supports two Telegram ingestion modes.

**Bot mode** is the existing path for channels where the bot has access.

**User mode** is for external/public channels such as https://t.me/amazinglootsdealsoffers. It uses an authenticated Telegram user account through MTProto/Telethon. The account must itself be able to access the channel.

Set:
TELEGRAM_READER_MODE=user
TELEGRAM_API_ID=<api id>
TELEGRAM_API_HASH=<api hash>
TELEGRAM_SESSION=data/telegram_user
TELEGRAM_CHANNELS=https://t.me/amazinglootsdealsoffers,@another_public_channel

One-time setup:
1. Get API ID and API hash from my.telegram.org under API development tools.
2. Put them in the local .env.
3. Run python -m superdeal.telegram_login.
4. Complete Telegram's login code and 2FA prompt if requested.
5. Start the normal worker.

The session file is local and ignored by Git. Do not share it.

User mode accepts public t.me URLs, public usernames, and numeric IDs already known to the account. Invite-link tokens are not silently treated as public usernames.


## Reliable Telegram ingestion

For a mix of channels you administer and external/public deal channels, use **hybrid** mode. The Bot API path handles channels where the bot is a member, while the authenticated MTProto user reader handles public channels the bot cannot access.

Recommended configuration:

\`\`\`text
TELEGRAM_READER_MODE=hybrid
TELEGRAM_BOT_TOKEN=<existing bot token>
TELEGRAM_API_ID=<Telegram API ID>
TELEGRAM_API_HASH=<Telegram API hash>
TELEGRAM_SESSION=data/telegram_user
TELEGRAM_CHANNELS=-1004397807961,https://t.me/amazinglootsdealsoffers
\`\`\`

Run the one-time user login:

\`\`\`powershell
python -m superdeal.telegram_login
\`\`\`

Hybrid mode polls both readers, merges messages by configured channel/message ID, and keeps the Bot API path working even if the user reader has a temporary error.

The worker logs three separate stages:
- messages received by the Bot API reader
- unique messages collected by the hybrid reader
- deals actually persisted to SQLite

This makes Telegram delivery, routing, and persistence failures visible instead of collapsing everything into "ingested 0".
