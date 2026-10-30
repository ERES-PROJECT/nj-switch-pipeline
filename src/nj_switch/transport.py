"""Verified, bounded HTTP with conservative robots and per-host throttling."""
import ipaddress
import random
import ssl
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from .evidence import MAX_BYTES

USER_AGENT = "NJSupplierResearch/0.2 (public residential offer research)"


class AccessError(RuntimeError):
    pass


def verified_system_ssl_context() -> ssl.SSLContext:
    """Use the host OS trust store while retaining hostname and certificate checks."""
    return ssl.create_default_context()


def runtime_tls_trust_failure(exc: Exception) -> bool:
    """Identify runtime CA-store failures without treating other network errors as TLS issues."""
    message = str(exc).casefold()
    return any(marker in message for marker in (
        "certificate_verify_failed",
        "certificate verify failed",
        "unable to verify the first certificate",
    ))


def runtime_browser_network_failure(exc: Exception) -> bool:
    """Identify browser-request transport failures eligible for normal HTTP retry."""
    message = str(exc).casefold()
    return any(marker in message for marker in (
        "socket hang up",
        "getaddrinfo enotfound",
        "econnrefused",
        "econnreset",
        "timeout 20000ms exceeded",
    ))


def public_url(url: str):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise AccessError("Only credential-free public HTTPS URLs are supported")
    if parsed.hostname.lower() in ("localhost",) or parsed.hostname.endswith((".local", ".internal")):
        raise AccessError("Local/internal host is not permitted")
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return
    if not ip.is_global:
        raise AccessError("Nonpublic IP address is not permitted")


class Transport:
    def __init__(self, delay: float = 1.0):
        self.client = httpx.Client(
            timeout=20,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
            verify=verified_system_ssl_context(),
        )
        self.robots = {}
        self.last_request = {}
        self.delay = delay

    def close(self):
        self.client.close()

    def _wait(self, url: str):
        host = urlsplit(url).netloc
        remaining = self.delay - (time.monotonic() - self.last_request.get(host, 0))
        if remaining > 0:
            time.sleep(remaining)
        self.last_request[host] = time.monotonic()

    def _client_request(self, method: str, url: str, body=None):
        """Read a bounded response through the verified system-trust client."""
        with self.client.stream(method, url, json=body) as response:
            status = response.status_code
            headers = dict(response.headers)
            chunks = bytearray()
            for chunk in response.iter_bytes():
                chunks.extend(chunk)
                if len(chunks) > MAX_BYTES:
                    raise ValueError("Response exceeds capture size limit")
        return status, headers, bytes(chunks)

    def allowed(self, url: str):
        public_url(url)
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self.robots:
            for attempt in range(3):
                self._wait(url)
                try:
                    response = self.client.get(origin + "/robots.txt")
                    break
                except httpx.TransportError:
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)
            parser = RobotFileParser(origin + "/robots.txt")
            # RFC 9309 section 2.3.1.4 defines 4xx robots responses as
            # "unavailable": crawlers MAY access the requested resources.
            # A 429 is rate limiting, however, so keep treating it as a
            # temporary policy failure rather than silently increasing load.
            if 400 <= response.status_code < 500 and response.status_code != 429:
                parser.parse([])
            elif response.status_code == 200:
                parser.parse(response.text.splitlines())
            else:
                raise AccessError(f"Cannot establish robots policy for {origin}: HTTP {response.status_code}")
            self.robots[origin] = parser
        if not self.robots[origin].can_fetch(USER_AGENT, url):
            raise AccessError("Source robots policy disallows this URL")

    def get(self, url: str, browser_context=None) -> tuple[bytes, str, str]:
        return self.request(url, browser_context=browser_context)

    def request(self, url: str, browser_context=None, method="GET", body=None) -> tuple[bytes, str, str]:
        from urllib.parse import urljoin
        for _ in range(5):
            self.allowed(url)
            for attempt in range(3):
                self._wait(url)
                try:
                    if browser_context is None:
                        status, headers, data = self._client_request(method, url, body)
                    else:
                        try:
                            response = browser_context.request.fetch(
                                url, method=method, data=body, timeout=20000, max_redirects=0
                            )
                            status, headers = response.status, response.headers
                            data = response.body()
                            response.dispose()
                            if len(data) > MAX_BYTES:
                                raise ValueError("Response exceeds capture size limit")
                        except Exception as exc:
                            if not (
                                runtime_tls_trust_failure(exc)
                                or runtime_browser_network_failure(exc)
                            ):
                                raise
                            # Playwright's Node client may use a different CA or
                            # resolver path. Retry the same permitted public URL
                            # through the verified system-trust client; all
                            # ordinary retry and robots limits still apply.
                            status, headers, data = self._client_request(method, url, body)
                    if status in (429, 500, 502, 503, 504) and attempt < 2:
                        time.sleep(min(2 ** attempt + random.random(), 4))
                        continue
                    break
                except httpx.TransportError:
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)
            if status in (301, 302, 303, 307, 308) and headers.get("location"):
                if status == 303 or (status in (301, 302) and method == "POST"):
                    method, body = "GET", None
                url = urljoin(url, headers["location"])
                continue
            if status != 200:
                raise AccessError(f"HTTP {status} fetching public resource")
            return data, headers.get("content-type", ""), url
        raise AccessError("Too many redirects")
