"""Client importing one declared package (requests) and one undeclared package (httpx)."""
import requests
import httpx

def fetch_json(url: str):
    response = requests.get(url)
    return response.json()

def fetch_async(url: str):
    client = httpx.Client()
    return client.get(url).text
