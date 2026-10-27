"""Daily CX ticket alerts to Slack.

Four sections, each with its own dates (see sql/alerts.sql):
  1. Tickets created           yesterday vs the same weekday last week          (day vs day)
  2. Resolved within 24h       tickets created 2 days ago vs 9 days ago         (day vs day; the 24h are over)
  3. Reopened within 48h       tickets created in the week D-10..D-4 vs the week before   (week vs week)
  4. P95 resolution time       same two weeks as section 3                       (week vs week)
Rows: all tickets, workstream, chat/call, category, sub-category, queue, workstream x category.
Posts to the Slack incoming webhook in SLACK_WEBHOOK_URL; without it, only prints the message.

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
MAX_LINES = 10         # per section and direction; the rest is summarised as "and N more"

KIND = {"Workstream": "workstream", "Chat / call": "chat/call", "Category": "category",
        "Sub-category": "sub-category", "Queue": "queue", "Workstream › category": "workstream › category"}


def fmt_day(d: dt.date) -> str:
    return f"{d:%a} {d.day} {d:%b}"


def fmt_range(a: dt.date, b: dt.date) -> str:
    return f"{a.day}–{b.day} {b:%b}" if a.month == b.month else f"{a.day} {a:%b} – {b.day} {b:%b}"


def row_name(r: dict) -> str:
    if r["dim"] == "All tickets":
        return "*All tickets*"
    return f"*{r['val']}* _({KIND.get(r['dim'], r['dim'])})_"


def find_alerts(rows: list) -> dict:
    """{section: [(bad, size, line), ...]}"""
    out = {"vol": [], "r24": [], "reopen": [], "p95": []}
    for r in rows:
        n = lambda k: float(r.get(k) or 0)
        name = row_name(r)

        cur, prev = n("vol_cur"), n("vol_prev")
        if max(cur, prev) >= MIN_TICKETS:
            chg = (cur - prev) / prev if prev else 1.0
            if abs(chg) >= VOLUME_PCT:
                out["vol"].append((chg > 0, abs(chg) / VOLUME_PCT, f"{name}: {cur:,.0f} vs {prev:,.0f} tickets → {chg:+.0%}"))

        bc, bp = n("r24_base_cur"), n("r24_base_prev")
        if bc >= MIN_TICKETS and bp >= MIN_TICKETS:
            a, b = n("r24_cur") / bc, n("r24_prev") / bp
            if abs(a - b) >= R24_PP:
                out["r24"].append((a < b, abs(a - b) / R24_PP, f"{name}: {a:.1%} vs {b:.1%} → {(a - b) * 100:+.1f} points"))

        bc, bp = n("ro_base_cur"), n("ro_base_prev")
        if bc >= MIN_TICKETS and bp >= MIN_TICKETS:
            a, b = n("ro_cur") / bc, n("ro_prev") / bp
            if abs(a - b) >= REOPEN_PP:
                out["reopen"].append((a > b, abs(a - b) / REOPEN_PP, f"{name}: {a:.1%} vs {b:.1%} → {(a - b) * 100:+.1f} points"))

        if n("p95_base_cur") >= MIN_TICKETS and n("p95_base_prev") >= MIN_TICKETS and r.get("p95_cur") is not None and r.get("p95_prev") is not None:
            a, b = n("p95_cur"), n("p95_prev")
            if not (a >= P95_CAP and b >= P95_CAP) and abs(a - b) >= P95_HOURS:
                fa = "72h+" if a >= P95_CAP else f"{a:.1f}h"
                fb = "72h+" if b >= P95_CAP else f"{b:.1f}h"
                out["p95"].append((a > b, abs(a - b) / P95_HOURS, f"{name}: {fa} vs {fb} → {a - b:+.1f} hours"))
    return out


def section(title: str, when: str, why: str, items: list) -> list:
    lines = [f"\n*{title}*", f"{when}", f"_{why}_"]
    if not items:
        return lines + [":white_check_mark: Nothing moved more than usual."]
    for bad, icon, word in ((True, ":red_circle:", "Worse"), (False, ":large_green_circle:", "Better")):
        part = sorted((a for a in items if a[0] == bad), key=lambda a: -a[1])
        if not part:
            continue
        lines.append(f"{icon} {word} ({len(part)})")
        lines += [f"• {a[2]}" for a in part[:MAX_LINES]]
        if len(part) > MAX_LINES:
            lines.append(f"   …and {len(part) - MAX_LINES} more on the dashboard")
    return lines


def message(rows: list, alerts: dict) -> str:
    yday = dt.date.fromisoformat(rows[0]["d_vol_cur"])
    today = yday + dt.timedelta(days=1)
    d = lambda k: today - dt.timedelta(days=k)
    week_cur, week_prev = fmt_range(d(10), d(4)), fmt_range(d(17), d(11))
    total = sum(len(v) for v in alerts.values())

    parts = [
        f"*CX ticket alerts — {fmt_day(today)}*",
        f"{total} numbers moved more than usual. :red_circle: got worse · :large_green_circle: got better.",
        "Each line reads: *this period* vs *the period it is compared with* → change.",
    ]
    parts += section(
        "1) Tickets coming in  (daily)",
        f":calendar: *{fmt_day(d(1))}* vs *{fmt_day(d(8))}*",
        f"Yesterday compared with the same day last week. Flagged when the count moves by {VOLUME_PCT:.0%} or more.",
        alerts["vol"])
    parts += section(
        "2) Tickets solved within 24 hours  (daily)",
        f":calendar: Tickets raised on *{fmt_day(d(2))}* vs *{fmt_day(d(9))}*",
        f"We look 2 days back so every ticket has had its full 24 hours. Flagged when the share moves by {R24_PP * 100:.0f} points or more.",
        alerts["r24"])
    parts += section(
        "3) Tickets reopened within 2 days of being solved  (weekly)",
        f":calendar: Tickets raised in the week *{week_cur}* vs the week *{week_prev}*",
        f"Weekly, because one day has too few reopens. Flagged when the share moves by {REOPEN_PP * 100:.0f} points or more.",
        alerts["reopen"])
    parts += section(
        "4) Time to solve the slowest tickets — P95  (weekly)",
        f":calendar: Tickets raised in the week *{week_cur}* vs the week *{week_prev}*",
        f"95% of tickets were solved within this many hours; lower is better (72h+ means slower than 3 days). Flagged when it moves by {P95_HOURS} hours or more.",
        alerts["p95"])
    parts.append(f"\n_Groups with fewer than {MIN_TICKETS} tickets are skipped so small numbers don't raise alarms._  <{DASHBOARD_URL}|Open the dashboard for details>")
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
    print(f"{len(rows)} rows checked, {sum(len(v) for v in alerts.values())} alerts")
    post(message(rows, alerts))
