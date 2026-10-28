# CX Service Ticket Dashboard

Live: https://deepakshiagarwal.github.io/ServiceTicketReport/

Wiom CX service tickets from `PROD_DB.PUBLIC.SERVICE_TICKET_MODEL` (Snowflake, via Metabase): ticket volume,
resolution within 4/12/24/48/72 hours, P95 resolution time and reopen rate by workstream, chat/call, category,
sub-category and queue, monthly, weekly or for any date range, plus open-ticket ageing, zone, partner, SLA,
arrival-time and channel views.

## Daily refresh and Slack alerts

`.github/workflows/daily.yml` runs every day at 10:00 IST (and from **Actions → Daily refresh and Slack alerts → Run workflow**):

1. `scripts/refresh_build.py` pulls the data from Metabase and rebuilds `index.html`, which is committed and republished.
2. `scripts/alerts.py` posts the day's notable changes to Slack.

The Slack message shows the **category** cut only (one short line per change, 🔴 worse / 🟢 better, empty metrics left out).
Changes are measured on equally old tickets and reported only when the category has at least 50 tickets and moves past (at most 5 lines up and 5 down per metric):

| Number | Compared | Limit |
|---|---|---|
| Tickets created | yesterday vs same weekday last week | ±20% |
| Solved within 24h | tickets raised 2 days ago vs 9 days ago | ±5 points |
| Reopened within 48h of being solved | tickets raised in the week 10–4 days ago vs the week before | ±3 points |
| P95 time to solve (capped at 72h) | same two weeks as reopen | ±12 hours |

Limits are constants at the top of `scripts/alerts.py`.

### Secrets (Settings → Secrets and variables → Actions)

- `METABASE_API_KEY` — a Metabase API key that can query the Snowflake database (id 113).
- `SLACK_WEBHOOK_URL` — a Slack incoming webhook for the channel that should get the alerts.

## Layout

- `sql/` — `_prelude.sql` (one row per ticket, IST, workstream and chat/call rules) plus one query per dataset; `alerts.sql` for the alerts.
- `src/` — the dashboard page and the standalone page template.
- `index.html` — the built page with the data embedded (generated; do not edit by hand).

Locally: `python scripts/refresh_build.py` (key from `METABASE_API_KEY` or the encrypted `~/.metabase_key`), `python scripts/alerts.py` (prints the message when `SLACK_WEBHOOK_URL` is not set).
