"""Immutable, bounded, redacted evidence. Capture only public shopping data."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import utc_now

SENSITIVE = re.compile(r"token|secret|password|authorization|signature|credential|cookie|session|enrollee|email|phone|address|account|ssn|creditcard|firstname|lastname|^ip$|visitor|deviceid|userid|^uid$|^pwd$|^logid$|refcustnbr", re.I)
MAX_BYTES = 4_000_000


def safe_url(url: str) -> str:
    p = urlsplit(url)
    host = p.hostname or ""
    if p.port:
        host += f":{p.port}"
    return urlunsplit((p.scheme, host, p.path,
                      urlencode([(k, "[REDACTED]" if SENSITIVE.search(k) else v)
                                 for k, v in parse_qsl(p.query, keep_blank_values=True)]), ""))


def redact(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): "[REDACTED]" if SENSITIVE.search(str(k)) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        if value.startswith(("http://", "https://")):
            return safe_url(value)
        value = re.sub(r'https?://[^\s<>"\']+', lambda match: safe_url(match[0]), value)
        value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL REDACTED]", value)
        value = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~-]+", r"\1[REDACTED]", value)
        value = re.sub(r"(?i)(session key\s*:?\s*)(?:<[^>]+>\s*)*([A-Z0-9]{6,})", r"\1[REDACTED]", value)
    return value


def sanitize_html(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    # Raw scripts and hidden inputs frequently contain session identifiers. Public
    # structured data is captured separately as JSON, not retained in script text.
    for tag in soup.select("script, input[type=hidden], textarea"):
        tag.decompose()
    for tag in soup.find_all(True):
        for key in list(tag.attrs):
            if key.startswith("on") or SENSITIVE.search(key) or (key == "value" and tag.name == "input"):
                del tag.attrs[key]
            elif key in ("href", "src", "action"):
                tag.attrs[key] = safe_url(str(tag.attrs[key]))
    return str(redact(str(soup)))


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.records: list[dict] = []

    def save(self, content: str | bytes | dict | list, kind: str, url: str = "", **metadata) -> dict:
        if kind == "json":
            data = json.dumps(redact(content), ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        elif kind == "html":
            data = sanitize_html(str(content)).encode("utf-8")
        elif isinstance(content, str):
            data = str(redact(content)).encode("utf-8")
        else:
            data = content
        if len(data) > MAX_BYTES:
            raise ValueError("Artifact exceeds 4 MB capture limit")
        digest = hashlib.sha256(data).hexdigest()
        path = self.root / f"{digest}.{kind}"
        if not path.exists():
            with path.open("xb") as handle:
                handle.write(data)
        record = {"id": digest, "path": path.name, "kind": kind, "url": safe_url(url),
                  "captured_at": utc_now(), "bytes": len(data), **redact(metadata)}
        self.records.append(record)
        return record
