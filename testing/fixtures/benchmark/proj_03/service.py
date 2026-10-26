"""Module attempting to import a missing internal relative module."""

from .non_existent_helper import dispatch_action

def process_request() -> str:
    return dispatch_action("start")
