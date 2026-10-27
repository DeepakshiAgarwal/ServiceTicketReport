"""Pull every dashboard dataset from Metabase into out/ and rebuild index.html.

    python scripts/refresh_build.py            # refresh data + build
    python scripts/refresh_build.py --build    # build only, from the existing out/ files
"""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from metabase import ROOT, query, sql_file

DATASETS = ["breakdown", "daily", "backlog", "zone", "partner", "channel", "sla", "hourly"]
OUT = os.path.join(ROOT, "out")


def refresh() -> None:
    os.makedirs(OUT, exist_ok=True)

    def run(name):
        rows = query(sql_file(name))
        with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
        return name, len(rows)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, n in pool.map(run, DATASETS):
            print(f"{name:<10} {n:>6} rows")
    asof = query("select to_char(convert_timezone('UTC','Asia/Kolkata',max(ticket_added_time)),'YYYY-MM-DD HH24:MI') asof "
                 "from PROD_DB.PUBLIC.SERVICE_TICKET_MODEL")[0]["asof"]
    with open(os.path.join(OUT, "asof.txt"), "w", encoding="utf-8") as f:
        f.write(asof)
    print(f"Data as of {asof} IST")


def build() -> None:
    parts = []
    for name in DATASETS:
        with open(os.path.join(OUT, name + ".json"), encoding="utf-8") as f:
            parts.append(f'"{name}":' + f.read().strip())
    data = ("{" + ",".join(parts) + "}").replace("</", "<\\/")
    with open(os.path.join(OUT, "asof.txt"), encoding="utf-8") as f:
        asof = f.read().strip()
    with open(os.path.join(ROOT, "src", "dashboard_page.html"), encoding="utf-8") as f:
        page = f.read()
    with open(os.path.join(ROOT, "src", "site_template.html"), encoding="utf-8") as f:
        html = f.read().replace("__DATA__", data).replace("__PAGE__", page).replace("__ASOF__", asof)
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"Built index.html ({os.path.getsize(os.path.join(ROOT, 'index.html')) // 1024:,} KB), data as of {asof} IST")


if __name__ == "__main__":
    if "--build" not in sys.argv:
        refresh()
    build()
