"""API module sending incorrect data type for contract field."""

def create_user_payload(user_id_str: str) -> dict:
    # Contract requires user_id to be an integer, but payload sends string
    return {"user_id": user_id_str, "status": "active"}
