import httpx

def charge():
    return httpx.post('https://api.payment-gateway.example/v1/charges')
