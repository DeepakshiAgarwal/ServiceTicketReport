"""Run native Snowflake SQL through Metabase's export endpoint (full results, no 2,000-row cap).

Key: METABASE_API_KEY environment variable (GitHub Actions secret), or on Windows the
DPAPI-encrypted file ~/.metabase_key made with
    Read-Host "New Metabase key" -AsSecureString | ConvertFrom-SecureString | Set-Content "$HOME\\.metabase_key"
"""

import json
import os
import sys
import urllib.parse
import urllib.request

METABASE_URL = os.environ.get("METABASE_URL", "https://metabase.wiom.in")
DATABASE_ID = 113  # Snowflake PROD_DB
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _dpapi_key() -> str:
    path = os.path.join(os.path.expanduser("~"), ".metabase_key")
    if sys.platform != "win32" or not os.path.exists(path):
        return ""
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    raw = bytes.fromhex(open(path, encoding="utf-8-sig").read().strip())
    buf = ctypes.create_string_buffer(raw, len(raw))
    blob_in, blob_out = BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError("Could not decrypt ~/.metabase_key")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData).decode("utf-16-le")
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def api_key() -> str:
    key = os.environ.get("METABASE_API_KEY") or _dpapi_key()
    if not key:
        sys.exit("No Metabase key: set METABASE_API_KEY (GitHub secret) or create ~/.metabase_key")
    return key


def sql_file(name: str) -> str:
    """The shared prelude plus sql/<name>.sql."""
    with open(os.path.join(ROOT, "sql", "_prelude.sql"), encoding="utf-8") as f:
        prelude = f.read()
    with open(os.path.join(ROOT, "sql", name + ".sql"), encoding="utf-8") as f:
        return prelude + f.read()


def query(sql: str) -> list:
    payload = json.dumps({"database": DATABASE_ID, "type": "native", "native": {"query": sql}})
    body = urllib.parse.urlencode({"query": payload}).encode()
    req = urllib.request.Request(
        METABASE_URL + "/api/dataset/json",
        data=body,
        headers={"x-api-key": api_key(), "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if isinstance(data, dict):
        raise RuntimeError(data.get("error") or data.get("message") or str(data)[:500])
    return [{k.lower(): v for k, v in row.items()} for row in data]
