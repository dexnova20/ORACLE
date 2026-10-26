"""Module requiring an environment variable without default."""

import os

def load_auth_token() -> str:
    return os.environ["AUTH_SECRET_KEY_MANDATORY"]
