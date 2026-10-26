"""Database module targeting an unreachable database socket."""

import socket

def ping_database_socket(host: str = "127.0.0.1", port: int = 59999, timeout: float = 0.5) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    finally:
        sock.close()
