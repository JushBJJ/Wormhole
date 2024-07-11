import asyncio
import os
from bot.config import WormholeConfig, initialize_database
from services.discord import DiscordBot
from services.tox import ToxService
from bot.utils.logging import setup_logging

async def main():
    logger = setup_logging()
    logger.info("Starting Wormhole bot")

    config = WormholeConfig()
    await initialize_database(config)
    discord_bot = DiscordBot(config)
    tox_service = ToxService(config)
    
    try:
        await discord_bot.start()
        # If you want to start both services concurrently, uncomment the following:
        # await asyncio.gather(
        #     discord_bot.start(),
        #     tox_service.start()
        # )
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    finally:
        # If you're running both services, uncomment the following:
        # await asyncio.gather(
        #     discord_bot.stop(),
        #     tox_service.stop()
        # )
        if not discord_bot.is_closed():
            await discord_bot.close()

        # If you need to export to JSON before shutting down, uncomment the following line:
        # await config.export_to_json(os.getenv("BACKUP_CONFIG_PATH", "config/backup_config.json"))

        logger.info("Wormhole bot shut down")

if __name__ == "__main__":
    asyncio.run(main())