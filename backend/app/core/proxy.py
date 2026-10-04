"""Tunnels database connections through an HTTP CONNECT proxy, for networks that block port 5432.

Database drivers can't use HTTP proxies themselves, so each proxied database host gets a small
forwarder on a random localhost port and the connection URL is rewritten to point at it.
"""

import base64
import logging
import socket
import threading
from urllib.parse import unquote, urlparse

from sqlalchemy.engine import make_url

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_local_ports: dict[tuple[str, int], int] = {}


def open_tunnel(proxy: str, host: str, port: int, timeout: float = 15) -> socket.socket:
    """Returns a socket connected to host:port through the proxy."""
    parsed = urlparse(proxy)
    sock = socket.create_connection((parsed.hostname, parsed.port or 80), timeout=timeout)

    request = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n"
    if parsed.username:
        credentials = f"{unquote(parsed.username)}:{unquote(parsed.password or '')}"
        request += f"Proxy-Authorization: Basic {base64.b64encode(credentials.encode()).decode()}\r\n"
    sock.sendall(f"{request}\r\n".encode())

    response = b""
    while b"\r\n\r\n" not in response:
        chunk = sock.recv(4096)
        if not chunk:
            sock.close()
            raise ConnectionError("Proxy closed the connection")
        response += chunk

    status = response.split(b"\r\n", 1)[0].decode(errors="replace")
    if status.split(" ")[1:2] != ["200"]:
        sock.close()
        raise ConnectionError(f"Proxy refused tunnel to {host}:{port}: {status}")

    return sock


def _pipe(source: socket.socket, target: socket.socket) -> None:
    try:
        while data := source.recv(65536):
            target.sendall(data)
    except OSError:
        pass
    finally:
        for sock in (source, target):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()


def _handle(client: socket.socket, proxy: str, host: str, port: int) -> None:
    try:
        upstream = open_tunnel(proxy, host, port)
        upstream.settimeout(None)
    except OSError as exc:
        logger.error("Database proxy tunnel failed: %s", exc)
        client.close()
        return
    threading.Thread(target=_pipe, args=(upstream, client), daemon=True).start()
    _pipe(client, upstream)


def _serve(listener: socket.socket, proxy: str, host: str, port: int) -> None:
    while True:
        client, _ = listener.accept()
        threading.Thread(target=_handle, args=(client, proxy, host, port), daemon=True).start()


def via_proxy(database_url: str, proxy: str) -> str:
    """Returns the URL unchanged when no proxy is set, otherwise rewritten to a local tunnel."""
    if not proxy:
        return database_url

    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or not url.host:
        return database_url

    target = (url.host, url.port or 5432)
    with _lock:
        if target not in _local_ports:
            listener = socket.create_server(("127.0.0.1", 0))
            threading.Thread(target=_serve, args=(listener, proxy, *target), daemon=True).start()
            _local_ports[target] = listener.getsockname()[1]
        local_port = _local_ports[target]

    return url.set(host="127.0.0.1", port=local_port).render_as_string(hide_password=False)
