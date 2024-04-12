import json
import telegram
import telegram.ext
import asyncio
import redis.asyncio as aioredis
import logging
import threading
import os


from bot.utils.file import read_config, write_config
from bot.utils.logging import configure_logging

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("telegram_token", "")
        self.bot = telegram.ext.ApplicationBuilder().token(self.token).build()
        self.logger = logging.getLogger(__name__)
        
        self.bot.add_handler(telegram.ext.CommandHandler("start", self.start))
        self.bot.add_handler(telegram.ext.CommandHandler("stop", self.stop))
        self.bot.add_handler(telegram.ext.MessageHandler(telegram.ext.filters.TEXT, self.on_message))
        
        self.default_channel_config_options = {
            "react": True # DEFAULT
        }
        
        self.logger=configure_logging()

    def start_wormhole(self):
        self.redis = aioredis.from_url("redis://localhost", decode_responses=True)
        self.logger.info("Starting subscriber thread...")
        thread = threading.Thread(target=self.run_aioredis_loop, daemon=True)
        thread.start()
        self.logger.info("Starting Telegram bot...")
        self.bot.run_polling(allowed_updates=telegram.Update.ALL_TYPES)
    
    def run_aioredis_loop(self):
        asyncio.run(self.redis_subscriber())
    
    async def redis_subscriber(self):
        sub = self.redis.pubsub()
        await sub.subscribe("telegram_channel")
        
        async for message in sub.listen():
            self.logger.info(message)
            if message["type"] == "message":
                data = json.loads(message["data"])
                msg = data.get("message", "")
                telegram_only = bool(data.get("telegram_only", False))
                await self.global_msg(msg, telegram_only=telegram_only)
    
    # Commands
    async def start(self, update, context):
        config = await read_config()
        chat_id = update.effective_chat.id
        
        if chat_id not in config.get("telegram", {}).get("channels", []):
            config["telegram"]["channels"][chat_id] = {}
            
            for key, value in self.default_channel_config_options.items():
                config["telegram"]["channels"][chat_id][key] = value
            
            self.logger.info(f"Adding chat ID {chat_id} to the Wormhole system.")
            await write_config(config)
            await update.message.reply_text("You have been added to the Wormhole system.")
        elif config.get("telegram", {})=={} or config.get("telegram", {}).get("channels", {})=={}:
            await update.message.reply_text(f"Your config is not up to date. Please check the github {REPO}")
    
    async def stop(self, update, context):
        config = await read_config()
        chat_id = update.effective_chat.id
        
        try:
            config["telegram"]["channels"].pop(chat_id)
            self.logger.info(f"Removing chat ID {chat_id} from the Wormhole system.")
            await write_config(config)
            await update.message.reply_text("You have been removed from the Wormhole system.")
        except KeyError:
            await update.message.reply_text("You are not in the Wormhole system.")
    
    # Messages
    async def global_msg(self, msg, telegram_only=True, local_chat_id=0):
        config = await read_config()
        
        for chat_id in config.get("telegram", {}).get("channels", []):
            try:
                if telegram_only:
                    await self.bot.bot.send_message(chat_id, msg, parse_mode=telegram.constants.ParseMode.HTML)
                else:
                    # Usually means that this came from the local class
                    if chat_id!=local_chat_id:
                        self.logger.info(f"Sending message to Telegram: {msg}")
                        await self.bot.bot.send_message(chat_id, msg)
            except Exception as e:
                self.logger.error(f"Error sending message to Telegram: {e}")
                self.logger.error(f"Chat ID: {chat_id}")
    
        if not telegram_only:
            await self.redis.publish("wormhole_channel", json.dumps({"message": msg, "discord_only": telegram_only}))
            await self.redis.publish("signal_channel", json.dumps({"message": msg, "signal_only": telegram_only}))
    
    async def echo(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
        """Echo the user message."""
        await update.message.reply_text(update.message.text)
    
    async def on_message(self, update, context):
        config = await read_config()
        chat_id = str(update.effective_chat.id)
        
        if chat_id in list(config.get("telegram", {}).get("channels", [])):
            msg = f"[TELEGRAM]  (ID: {update.effective_chat.id}) - {update.effective_user.first_name} says:\n{update.message.text}"
            await self.global_msg(msg, telegram_only=False, local_chat_id=chat_id)
            self.logger.info(f"Received message from Telegram: {msg}")
            
            if update.message.sticker:
                await self.global_msg("Stickers are not supported yet...", telegram_only=False, local_chat_id=chat_id)

            # TODO figure out adding reactions to confirm message
        else:
            await update.message.reply_text("You are not in the Wormhole system.")