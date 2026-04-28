import yaml
from pathlib import Path


def load_config(config_path: str = "config.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    with open(path) as f:
        config = yaml.safe_load(f)
    
    return config