import socket

import httpx
import pytest

from app.config import settings
from app.services import remote_fetch


def test_validate_remote_url_rejects_loopback_and_credentials() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        remote_fetch.validate_remote_url("http://127.0.0.1/private")

    with pytest.raises(ValueError, match="credentials"):
        remote_fetch.validate_remote_url("https://user:password@example.com/file")


def test_validate_remote_url_rejects_hosts_that_resolve_privately(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 80))],
    )

    with pytest.raises(ValueError, match="not allowed"):
        remote_fetch.validate_remote_url("http://reader.example.test/file")


def test_fetch_remote_resource_enforces_streamed_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "93.184.216.34"
        assert request.headers["host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(200, content=b"12345", request=request)

    real_client = httpx.Client

    def client_factory(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), follow_redirects=False)

    monkeypatch.setattr(remote_fetch.httpx, "Client", client_factory)

    with pytest.raises(ValueError, match="download limit"):
        remote_fetch.fetch_remote_resource(
            "https://example.com/file",
            max_bytes=4,
            timeout_seconds=1,
        )


def test_private_host_override_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "remote_fetch_allow_private_hosts", True)
    assert remote_fetch.validate_remote_url("http://127.0.0.1/file") == "http://127.0.0.1/file"


def test_fetch_remote_resource_pins_each_redirect_and_preserves_logical_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )

    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/final"}, request=request)
        return httpx.Response(200, content=b"book", request=request)

    real_client = httpx.Client

    def client_factory(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), follow_redirects=False)

    monkeypatch.setattr(remote_fetch.httpx, "Client", client_factory)

    resource = remote_fetch.fetch_remote_resource(
        "https://example.com/start",
        max_bytes=100,
        timeout_seconds=1,
    )

    assert [request.url.host for request in seen_requests] == [
        "93.184.216.34",
        "93.184.216.34",
    ]
    assert all(request.headers["host"] == "example.com" for request in seen_requests)
    assert resource.final_url == "https://example.com/final"
