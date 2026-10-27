"""Daily CX ticket alerts to Slack.

Compares each row (overall, workstream, chat/call, category, sub-category, queue, workstream x category)
on equally old tickets (see sql/alerts.sql) and posts the changes past the limits below to the Slack
incoming webhook in SLACK_WEBHOOK_URL. Without SLACK_WEBHOOK_URL it only prints the message.

    python scripts/alerts.py
"""

import datetime as dt
import json
import os
import urllib.request

from metabase import query, sql_file

DASHBOARD_URL = "https://deepakshiagarwal.github.io/ServiceTicketReport/"

# Standard limits: a row needs at least MIN_TICKETS on both sides (either side for volume).
MIN_TICKETS = 30
VOLUME_PCT = 0.20      # tickets created, +/- 20%
R24_PP = 0.05          # resolved within 24h, +/- 5 percentage points
REOPEN_PP = 0.03       # reopened within 48h of resolution, +/- 3 pp
P95_HOURS = 12         # P95 resolution time, +/- 12 hours (capped at 72h)
P95_CAP = 72.0
MAX_LINES = 25         # per section; the rest is summarised as "and N more"


def day(s: str) -> str:
    return dt.date.fromisoformat(s).strftime("%a %-d %b") if os.name != "nt" else dt.date.fromisoformat(s).strftime("%a %#d %b")


def label(r: dict) -> str:
    if r["dim"] == "All tickets":
        return "All tickets"
    if r["dim"] == "Workstream › category":
        return str(r["val"])
    return f"{r['dim']} › {r['val']}"


def find_alerts(rows: list) -> list:
    out = []  # (bad: bool, size for sorting, text)
    for r in rows:
        n = lambda k: float(r.get(k) or 0)
        name = label(r)

        # Tickets created: yesterday vs same weekday last week (more tickets = worse)
        cur, prev = n("vol_cur"), n("vol_prev")
        if max(cur, prev) >= MIN_TICKETS:
            chg = (cur - prev) / prev if prev else 1.0
            if abs(chg) >= VOLUME_PCT:
                out.append((chg > 0, abs(chg) / VOLUME_PCT, f"*{name}* — Tickets {cur:,.0f} vs {prev:,.0f} ({chg:+.0%})"))

        # Resolved within 24h: D-2 vs D-9 (lower = worse)
        bc, bp = n("r24_base_cur"), n("r24_base_prev")
        if bc >= MIN_TICKETS and bp >= MIN_TICKETS:
            a, b = n("r24_cur") / bc, n("r24_prev") / bp
            if abs(a - b) >= R24_PP:
                out.append((a < b, abs(a - b) / R24_PP, f"*{name}* — Resolved ≤24h {a:.1%} vs {b:.1%} ({(a - b) * 100:+.1f} pp)"))

        # Reopened within 48h of first resolution: 7-day cohorts (higher = worse)
        bc, bp = n("ro_base_cur"), n("ro_base_prev")
        if bc >= MIN_TICKETS and bp >= MIN_TICKETS:
            a, b = n("ro_cur") / bc, n("ro_prev") / bp
            if abs(a - b) >= REOPEN_PP:
                out.append((a > b, abs(a - b) / REOPEN_PP, f"*{name}* — Reopened ≤48h {a:.1%} vs {b:.1%} ({(a - b) * 100:+.1f} pp)"))

        # P95 resolution time, capped at 72h: 7-day cohorts (higher = worse)
        if n("p95_base_cur") >= MIN_TICKETS and n("p95_base_prev") >= MIN_TICKETS and r.get("p95_cur") is not None and r.get("p95_prev") is not None:
            a, b = n("p95_cur"), n("p95_prev")
            if not (a >= P95_CAP and b >= P95_CAP) and abs(a - b) >= P95_HOURS:
                fa = "72h+" if a >= P95_CAP else f"{a:.1f}h"
                fb = "72h+" if b >= P95_CAP else f"{b:.1f}h"
                out.append((a > b, abs(a - b) / P95_HOURS, f"*{name}* — P95 resolution {fa} vs {fb} ({a - b:+.1f}h)"))
    return out


def message(rows: list, alerts: list) -> str:
    r0 = rows[0]
    head = (f"*CX ticket alerts — {day(r0['d_vol_cur'])}*\n"
            f"_Tickets: {day(r0['d_vol_cur'])} vs {day(r0['d_vol_prev'])} · Resolved ≤24h: tickets created {day(r0['d_r24_cur'])} vs {day(r0['d_r24_prev'])} · "
            f"Reopen and P95: last 7 full days vs the 7 before, same ticket age._")
    if not alerts:
        return head + f"\n:white_check_mark: No change past the limits today. <{DASHBOARD_URL}|Open dashboard>"
    parts = [head]
    for bad, title, icon in ((True, "Worse", ":red_circle:"), (False, "Better", ":large_green_circle:")):
        items = sorted((a for a in alerts if a[0] == bad), key=lambda a: -a[1])
        if not items:
            continue
        parts.append(f"\n{icon} *{title} ({len(items)})*")
        parts += [f"• {a[2]}" for a in items[:MAX_LINES]]
        if len(items) > MAX_LINES:
            parts.append(f"…and {len(items) - MAX_LINES} more on the dashboard")
    parts.append(f"\n<{DASHBOARD_URL}|Open dashboard> · limits: ≥{MIN_TICKETS} tickets, volume ±{VOLUME_PCT:.0%}, ≤24h ±{R24_PP * 100:.0f} pp, "
                 f"reopen ±{REOPEN_PP * 100:.0f} pp, P95 ±{P95_HOURS}h")
    return "\n".join(parts)


def post(text: str) -> None:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        print("SLACK_WEBHOOK_URL not set; message not sent:\n")
        print(text)
        return
    req = urllib.request.Request(url, data=json.dumps({"text": text}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        print("Slack:", resp.status, resp.read().decode()[:100])


if __name__ == "__main__":
    rows = query(sql_file("alerts"))
    alerts = find_alerts(rows)
    print(f"{len(rows)} rows checked, {len(alerts)} alerts")
    post(message(rows, alerts))
