# SuperDeal 3.0

SuperDeal 3.0 is a deal-discovery and affiliate platform.

## Development approach

Each phase follows: **Build → automated test → inspect → user validation → next phase**.

## Roadmap

1. **Phase 0 — Foundation**: project structure, configuration, automated tests, health check.
2. **Phase 1 — Deal Parser**: turn raw deal messages into structured deal records.
3. **Phase 2 — Deal Database**: SQLite storage, duplicate detection, status and price history.
4. **Phase 3 — Telegram Hunter**: ingest approved/public deal sources.
5. **Phase 4 — Affiliate Layer**: affiliate URL generation and validation.
6. **Phase 5 — Mobile-first Web**: searchable deal discovery website.
7. **Phase 6 — Price Intelligence**: price changes, historical lows and deal signals.
8. **Phase 7 — Automation & Analytics**: continuous processing, alerts and performance tracking.

## Phase 0

No live Telegram or affiliate credentials are used in this phase.

For a local Python environment:

```bash
pip install -e ".[test]"
pytest
```

CI runs the tests remotely on GitHub Actions, so the product owner does not need Python installed locally.
