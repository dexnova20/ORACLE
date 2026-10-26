"""Gamma module importing yaml."""
import yaml

def load_gamma_config(text: str):
    return yaml.safe_load(text)
