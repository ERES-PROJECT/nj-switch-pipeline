import json
import ssl
from pathlib import Path

import pytest
import httpx

from nj_switch.evidence import ArtifactStore, redact, safe_url, sanitize_html
from nj_switch.transport import (AccessError, Transport, public_url,
                                 runtime_browser_network_failure,
                                 runtime_tls_trust_failure,
                                 verified_system_ssl_context)


def test_redaction():
    result = redact({"token": "secret", "nested": {"customerEmail": "person@example.com", "rate": 12}, "ip": "1.2.3.4"})
    assert result["token"] == "[REDACTED]"
    assert result["nested"]["rate"] == 12
    assert "person@" not in json.dumps(result)
    assert result["ip"] == "[REDACTED]"


def test_html_redaction():
    html = sanitize_html('<input type="hidden" value="secret"><script>private_token=123</script><input value="name"><option value="PSE">PSEG</option>')
    assert "secret" not in html and "private_token" not in html
    assert 'value="PSE"' in html


def test_hash_and_dedup(tmp_path):
    store = ArtifactStore(tmp_path)
    a = store.save({"rate": "20.1", "token": "secret"}, "json", "https://example.com?token=x")
    b = store.save({"rate": "20.1", "token": "different"}, "json")
    assert a["id"] == b["id"]
    assert len(list(tmp_path.glob("*.json"))) == 1


@pytest.mark.parametrize("url", ["http://example.com", "https://localhost", "https://127.0.0.1", "https://user:pw@example.com", "https://192.168.1.2"])
def test_unsafe_urls(url):
    with pytest.raises(AccessError):
        public_url(url)


def test_system_ssl_context_keeps_certificate_and_hostname_validation_enabled():
    context = verified_system_ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_runtime_tls_failure_is_narrowly_classified():
    assert runtime_tls_trust_failure(RuntimeError("unable to verify the first certificate"))
    assert runtime_tls_trust_failure(RuntimeError("CERTIFICATE_VERIFY_FAILED"))
    assert not runtime_tls_trust_failure(RuntimeError("HTTP 503"))


def test_browser_network_failure_is_narrowly_classified():
    assert runtime_browser_network_failure(RuntimeError("getaddrinfo ENOTFOUND www.picknrg.com"))
    assert runtime_browser_network_failure(RuntimeError("APIRequestContext.fetch: socket hang up"))
    assert runtime_browser_network_failure(RuntimeError("Timeout 20000ms exceeded"))
    assert not runtime_browser_network_failure(RuntimeError("HTTP 503"))


def test_browser_ca_failure_falls_back_to_verified_system_client():
    class Response:
        status_code = 200
        headers = {"content-type": "application/pdf"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def iter_bytes(self):
            yield b"%PDF-system-trust"

    class Client:
        calls = 0

        def stream(self, method, url, json=None):
            self.calls += 1
            assert method == "GET" and url.startswith("https://example.com/") and json is None
            return Response()

    class BrowserRequest:
        def fetch(self, *_args, **_kwargs):
            raise RuntimeError("unable to verify the first certificate")

    class BrowserContext:
        request = BrowserRequest()

    transport = Transport(delay=0)
    original = transport.client
    transport.client = Client()
    transport.allowed = lambda _url: None
    try:
        data, media_type, final_url = transport.get(
            "https://example.com/document.pdf", BrowserContext()
        )
        assert data == b"%PDF-system-trust"
        assert media_type == "application/pdf"
        assert final_url == "https://example.com/document.pdf"
        assert transport.client.calls == 1
    finally:
        original.close()


def test_browser_network_failure_falls_back_to_verified_system_client():
    class Response:
        status_code = 200
        headers = {"content-type": "application/pdf"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def iter_bytes(self):
            yield b"%PDF-system-network-fallback"

    class Client:
        def stream(self, _method, _url, json=None):
            assert json is None
            return Response()

    class BrowserRequest:
        def fetch(self, *_args, **_kwargs):
            raise RuntimeError("getaddrinfo ENOTFOUND www.picknrg.com")

    class BrowserContext:
        request = BrowserRequest()

    transport = Transport(delay=0)
    original = transport.client
    transport.client = Client()
    transport.allowed = lambda _url: None
    try:
        data, media_type, _ = transport.get(
            "https://www.picknrg.com/en/getLegalDocument?sku=test", BrowserContext()
        )
        assert data == b"%PDF-system-network-fallback"
        assert media_type == "application/pdf"
    finally:
        original.close()


def test_robots_ordinary_4xx_is_unavailable_not_disallow():
    class Response:
        status_code = 403
        text = "Forbidden"

    class Client:
        def get(self, _url):
            return Response()

    transport = Transport(delay=0)
    original = transport.client
    transport.client = Client()
    try:
        transport.allowed("https://example.com/public-plans")
    finally:
        original.close()


def test_robots_rate_limit_remains_blocking():
    class Response:
        status_code = 429
        text = "Try later"

    class Client:
        def get(self, _url):
            return Response()

    transport = Transport(delay=0)
    original = transport.client
    transport.client = Client()
    try:
        with pytest.raises(AccessError, match="HTTP 429"):
            transport.allowed("https://example.com/public-plans")
    finally:
        original.close()


def test_robots_transport_timeout_retries_before_failing(monkeypatch):
    class Response:
        status_code = 200
        text = "User-agent: *\nAllow: /"

    class Client:
        attempts = 0

        def get(self, request_url):
            self.attempts += 1
            if self.attempts < 3:
                raise httpx.ReadTimeout("transient", request=httpx.Request("GET", request_url))
            return Response()

    transport = Transport(delay=0)
    original = transport.client
    transport.client = Client()
    monkeypatch.setattr("nj_switch.transport.time.sleep", lambda _seconds: None)
    try:
        transport.allowed("https://example.com/public-plans")
        assert transport.client.attempts == 3
    finally:
        original.close()
