"""Alpha module importing yaml."""
import yaml

def load_alpha_config(text: str):
    return yaml.safe_load(text)
