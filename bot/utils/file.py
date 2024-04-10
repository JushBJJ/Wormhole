import aiofiles
import logging
import json

async def read_config() -> dict:
    async with aiofiles.open(f"./config.json", mode="r") as file:
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
    async with aiofiles.open(f"./config.json", mode="w") as file:
        try:
            await file.write(json.dumps(data, indent=4))
            return True
        except Exception as e:
            logging.error(f"Error writing to file: {e}")
            return False
        