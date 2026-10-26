"""Client module importing non-existent internal module."""
from .missing_network_adapter import RemoteClient

def fetch_status():
    client = RemoteClient()
    return client.ping()
