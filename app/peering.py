from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlsplit, urlunsplit


CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")


def is_private_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address in CGNAT_NETWORK
    )


def normalize_peer_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("互联地址必须是有效的 HTTP(S) 地址")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("互联地址不能包含账号、查询参数或片段")
    if parsed.path not in {"", "/"}:
        raise ValueError("互联地址只能包含主机和端口")
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM
            )
        }
    except OSError as exc:
        raise ValueError("互联地址无法解析") from exc
    if not addresses or any(not is_private_address(address) for address in addresses):
        raise ValueError("互联地址必须指向局域网、回环或 Tailscale 地址")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def local_peer_addresses(port: int) -> list[str]:
    configured = os.getenv("H3_PEER_URL", "").strip()
    if configured:
        return [normalize_peer_url(configured)]
    addresses: set[str] = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.connect(("8.8.8.8", 80))
            addresses.add(connection.getsockname()[0])
    except OSError:
        pass
    try:
        addresses.update(
            item[4][0]
            for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        )
    except OSError:
        pass
    usable = sorted(address for address in addresses if is_private_address(address) and not ipaddress.ip_address(address).is_loopback)
    if not usable:
        usable = ["127.0.0.1"]
    return [f"http://{address}:{port}" for address in usable]


def is_loopback_client(value: str | None) -> bool:
    if not value:
        return False
    try:
        return ipaddress.ip_address(value.split("%", 1)[0]).is_loopback
    except ValueError:
        return value == "localhost"
