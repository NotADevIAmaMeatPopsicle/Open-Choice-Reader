from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import socket
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

from app.config import settings


REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


@dataclass(frozen=True, slots=True)
class RemoteResource:
    final_url: str
    content_type: str
    headers: dict[str, str]
    body: bytes


@dataclass(frozen=True, slots=True)
class _RemoteRequestTarget:
    logical_url: str
    request_url: str
    host_header: str | None = None
    sni_hostname: str | None = None


def _resolve_remote_target(url: str) -> _RemoteRequestTarget:
    normalized = url.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Use a full http:// or https:// URL")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not supported")
    if settings.remote_fetch_allow_private_hosts:
        return _RemoteRequestTarget(logical_url=normalized, request_url=normalized)

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ValueError("The remote host could not be resolved") from error

    resolved_addresses = {ipaddress.ip_address(entry[4][0]) for entry in addresses}
    if not resolved_addresses:
        raise ValueError("The remote host did not resolve to an address")
    for address in resolved_addresses:
        if not address.is_global:
            raise ValueError("Private, loopback, link-local, and reserved network addresses are not allowed")

    selected_address = min(
        resolved_addresses,
        key=lambda address: (address.version, int(address)),
    )
    pinned_host = (
        f"[{selected_address.compressed}]"
        if selected_address.version == 6
        else selected_address.compressed
    )
    pinned_netloc = pinned_host if parsed.port is None else f"{pinned_host}:{parsed.port}"
    request_url = urlunparse(parsed._replace(netloc=pinned_netloc))
    return _RemoteRequestTarget(
        logical_url=normalized,
        request_url=request_url,
        host_header=parsed.netloc,
        sni_hostname=parsed.hostname if parsed.scheme == "https" else None,
    )


def validate_remote_url(url: str) -> str:
    return _resolve_remote_target(url).logical_url


def _fetch_remote_resource(
    url: str,
    *,
    max_bytes: int,
    timeout_seconds: float,
    user_agent: str = "OpenChoiceReader/0.1",
    max_redirects: int = 5,
) -> RemoteResource:
    current_url = url

    for redirect_count in range(max_redirects + 1):
        target = _resolve_remote_target(current_url)
        request_headers = {"Host": target.host_header} if target.host_header else None
        request_extensions = (
            {"sni_hostname": target.sni_hostname} if target.sni_hostname else None
        )

        # A client per redirect hop prevents a pooled IP connection from being reused
        # for a different logical hostname that happens to resolve to the same address.
        with httpx.Client(
            follow_redirects=False,
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
        ) as client, client.stream(
            "GET",
            target.request_url,
            headers=request_headers,
            extensions=request_extensions,
        ) as response:
            if response.status_code in REDIRECT_STATUS_CODES:
                location = response.headers.get("location")
                if not location:
                    raise ValueError("The remote server returned a redirect without a location")
                if redirect_count >= max_redirects:
                    raise ValueError("The remote server returned too many redirects")
                current_url = urljoin(target.logical_url, location)
                continue

            response.raise_for_status()
            declared_length = response.headers.get("content-length")
            if declared_length:
                try:
                    declared_bytes = int(declared_length)
                except ValueError:
                    declared_bytes = 0
                if declared_bytes > max_bytes:
                    raise ValueError(f"The remote file exceeds the {max_bytes}-byte download limit")

            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise ValueError(f"The remote file exceeds the {max_bytes}-byte download limit")

            return RemoteResource(
                final_url=target.logical_url,
                content_type=response.headers.get("content-type", ""),
                headers=dict(response.headers),
                body=bytes(body),
            )

    raise ValueError("The remote resource could not be downloaded")


def fetch_remote_resource(
    url: str,
    *,
    max_bytes: int,
    timeout_seconds: float,
    user_agent: str = "OpenChoiceReader/0.1",
    max_redirects: int = 5,
) -> RemoteResource:
    try:
        return _fetch_remote_resource(
            url,
            max_bytes=max_bytes,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
            max_redirects=max_redirects,
        )
    except httpx.HTTPError as error:
        raise ValueError("The remote resource could not be downloaded") from error
