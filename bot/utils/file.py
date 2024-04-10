import aiofiles
import logging
import json
import os

config_file = "./default_config.json"

if os.path.exists("./config.json"):
    config_file = "./config.json"

async def read_config() -> dict:
    # Decide whether to use the default config or the user's config
    filename = "./default_config.json"
    
    async with aiofiles.open(config_file, mode="r") as file:
        try:
            return json.loads(await file.read())
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in {type}: {e}")
            return dict({})
        except FileNotFoundError as e:
            logging.error(f"File not found: {e}")
            return dict({})
        except Exception as e:
            logging.error(f"Unknown error: {e}")
            return dict({})
    return dict({})

async def write_config(data: dict) -> bool:
    async with aiofiles.open(config_file, mode="w") as file:
        try:
            await file.write(json.dumps(data, indent=4))
            return True
        except Exception as e:
            logging.error(f"Error writing to file: {e}")
            return False
        