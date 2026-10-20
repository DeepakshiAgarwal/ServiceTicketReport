# CX Service Ticket Dashboard

Static dashboard of Wiom CX service tickets: monthly (last 3 months + MTD) and current-month weekly comparison of
ticket volume, resolution within 4/12/24/48/72 hours and reopen rate by category, sub-category and queue, plus open-ticket
ageing, zone scorecard, partner watchlist, SLA buckets, arrival heatmap and channel mix. Category and queue filters are multi-select.

Open `index.html`, or the GitHub Pages site for this repo.

**Data:** snapshot of `PROD_DB.PUBLIC.SERVICE_TICKET_MODEL` (Snowflake, via Metabase), embedded in `index.html`.
It does not update on its own; it is republished when the data is refreshed.
