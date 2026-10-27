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

Alerts compare every row (all tickets, each workstream, chat/call, category, sub-category, queue and workstream × category)
on equally old tickets, and report a change only when the row has at least 30 tickets and moves past:

| Number | Compared | Limit |
|---|---|---|
| Tickets created | yesterday vs same weekday last week | ±20% |
| Resolved ≤24h | tickets created 2 days ago vs 9 days ago | ±5 pp |
| Reopened ≤48h after resolution | last 7 full days vs the 7 before | ±3 pp |
| P95 resolution time (capped at 72h) | 7-day groups at least 3 days old | ±12 h |

Limits are constants at the top of `scripts/alerts.py`.

### Secrets (Settings → Secrets and variables → Actions)

- `METABASE_API_KEY` — a Metabase API key that can query the Snowflake database (id 113).
- `SLACK_WEBHOOK_URL` — a Slack incoming webhook for the channel that should get the alerts.

## Layout

- `sql/` — `_prelude.sql` (one row per ticket, IST, workstream and chat/call rules) plus one query per dataset; `alerts.sql` for the alerts.
- `src/` — the dashboard page and the standalone page template.
- `index.html` — the built page with the data embedded (generated; do not edit by hand).

Locally: `python scripts/refresh_build.py` (key from `METABASE_API_KEY` or the encrypted `~/.metabase_key`), `python scripts/alerts.py` (prints the message when `SLACK_WEBHOOK_URL` is not set).
