import json
import os
import shutil

CONFIG_PATH = "config.json"

# If config.json does not exist, copy from default.config.json
if not os.path.exists(CONFIG_PATH) and os.path.exists("default.config.json"):
    shutil.copy("default.config.json", CONFIG_PATH)

if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError("Configuration file 'config.json' not found. Please create it or copy from 'default.config.json' and make sure the name is correct.")

# Load configuration from config.json
with open(CONFIG_PATH, "r") as config_file:
    config = json.load(config_file)


def save_config():
    """Persist the current in-memory config dict back to config.json (used by the in-game settings screen)."""
    with open(CONFIG_PATH, "w") as config_file:
        json.dump(config, config_file, indent=4)
