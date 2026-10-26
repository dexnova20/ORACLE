import os
import sys

def get_status() -> dict:
    return {"status": "operational", "pid": os.getpid()}
