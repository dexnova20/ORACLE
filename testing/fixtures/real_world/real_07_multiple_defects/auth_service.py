"""Authentication service with intentional syntax defect."""

def authenticate(user_token: str) -> bool:
    # Injected syntax error: unclosed bracket
    valid_tokens = ["admin", "root"
    return user_token in valid_tokens
