import logging

from bot.wormhole import bot
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    bot.start_wormhole()