"""Module importing external packages requests and stripe."""

import requests
import stripe

def charge_customer(token: str, amount_cents: int) -> dict:
    stripe.api_key = "dummy_key"
    resp = requests.post("https://api.example.com/health")
    return {"status": resp.status_code, "amount": amount_cents}
