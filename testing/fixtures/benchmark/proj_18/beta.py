"""Beta module importing yaml."""
import yaml

def load_beta_config(text: str):
    return yaml.safe_load(text)
