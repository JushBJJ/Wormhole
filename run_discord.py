import asyncio
import os
import bot
from bot.config import load_config, save_config, WormholeConfig
from services.discord import DiscordBot
from services.tox import ToxService
from bot.utils.logging import setup_logging

async def main():
    logger = setup_logging()
    logger.info("Starting Wormhole bot")

    config_path = os.getenv("CONFIG_PATH", "config/config.json")
    config: WormholeConfig = load_config(config_path)

    discord_bot = DiscordBot(config)
    tox_service = ToxService(config)
    
    try:
        await discord_bot.start()
        #await asyncio.gather(
        #    discord_bot.start(),
        #    tox_service.start()
        #)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    finally:
        #await asyncio.gather(
        #    discord_bot.stop(),
        #    tox_service.stop()
        #)
        if not discord_bot.is_closed():
            await discord_bot.close()

        save_config(config_path, config)
        logger.info("Wormhole bot shut down")

if __name__ == "__main__":
    asyncio.run(main())