"""Parser module with independent syntax error."""

def parse_header(raw_text):
    # Injected syntax error: missing closing parenthesis
    tokens = list(raw_text.strip().split()
    return tokens
