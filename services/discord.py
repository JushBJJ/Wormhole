import asyncio
import json
import os
import traceback
import discord
import redis.asyncio as redis

from discord.ext import commands, tasks
from typing import Optional
from bot.config import WormholeConfig
from bot.utils.logging import setup_logging
from bot.features.pretty_message import PrettyMessage
from bot.features.embed import create_embed

class DiscordBot(commands.Bot):
    def __init__(self, config: WormholeConfig):
        intents = discord.Intents.all()
        super().__init__(command_prefix="%", intents=intents, help_command=None)
        self.config = config
        self.logger = setup_logging()
        self.config.logger = self.logger

        self.pretty_message = PrettyMessage(config)
        self.message_hashes = {}
        self.last_messages = {}  # Last overall 50 messages, separated by channel and user
        self.evaluations = {}

        self.redis: Optional[redis.Redis] = None
        self.redis_url = os.getenv("REDIS_HOST_URL", "redis://localhost:6379")
        self.redis_channel = os.getenv("REDIS_DISCORD_CHANNEL", "wormhole-discord")
        self.redis_ssh_channel = os.getenv("REDIS_SSH_CHANNEL", "wormhole-ssh-chat")

    async def _setup_last_messages_dict(self) -> None:
        channel_categories: list[str] = await self.config.get_channel_list()
        self.last_messages = {category: set() for category in channel_categories}
        
    async def setup_hook(self) -> None:
        self.logger.info("Setting up bot...")        
        await self.load_extensions()
        self.logger.info("Extensions loaded successfully.")
        self.add_listener(self.before_message, "on_message")
        self.before_invoke(self.before_command)
        self.logger.info("Before-invoke functions set.")
        await self._setup_last_messages_dict()
        self.logger.info("Last messages dict set up.")
        self.redis_reconnect_task.start()
        self.logger.info("Redis reconnect task started.")

    @tasks.loop(seconds=30)
    async def redis_reconnect_task(self):
        try:
            if self.redis is None:
                await self.connect_to_redis()
            else:
                await self.redis.ping()
        except redis.RedisError:
            self.logger.warning("Lost connection to Redis. Attempting to reconnect...")
            await self.connect_to_redis()

    async def connect_to_redis(self):
        try:
            self.redis = await redis.from_url(self.redis_url)
            self.logger.info("Connected to Redis successfully.")
            self.loop.create_task(self.redis_listener())
        except redis.RedisError as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis = None

    async def redis_publish(self, name: str, user_hash: str, content: str, embeds, stickers_to_send, channel_category) -> None:
        if not self.redis:
            self.logger.error("Cannot publish to Redis: No connection")
            return
        elif channel_category != "wormhole":
            return

        message = content
        if embeds:
            message += "<embed>"
        if stickers_to_send:
            message += "<sticker>"
        
        data = {
            "username": name,
            "hash": user_hash,
            "message": message
        }
        try:
            await self.redis.publish(self.redis_ssh_channel, json.dumps(data))
        except redis.RedisError as e:
            self.logger.error(f"Failed to publish to Redis: {str(e)}")

    async def redis_listener(self):
        self.logger.info(f"Starting Redis listener on channel: {self.redis_channel}")
        try:
            async with self.redis.pubsub() as pubsub:
                await pubsub.subscribe(self.redis_channel)
                self.logger.info(f"Subscribed to Redis channel: {self.redis_channel}")
                
                while True:
                    try:
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                        if message:
                            await self.handle_redis_message(message['data'])
                    except redis.RedisError as e:
                        self.logger.error(f"Redis error in listener: {str(e)}")
                        await asyncio.sleep(5)  # Wait before attempting to reconnect
                        break
        except Exception as e:
            self.logger.error(f"Error in Redis listener: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            if self.redis:
                await self.redis.close()
            self.redis = None

    async def handle_redis_message(self, message):
        try:
            decoded_message = message.decode('utf-8')
            message_info = json.loads(decoded_message)
            channels = await self.config.get_channels_by_category("wormhole")
            if channels:
                tasks = []
                for channel in channels:
                    _channel = self.get_channel(int(channel['channel_id']))
                    if not _channel:
                        continue
                    embed = discord.Embed(
                        title=f"{message_info.get('username', 'Unknown User')}",
                        description=f"{message_info.get('message', 'No message')}",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text=f"SSH-Chat - {message_info.get('hash', 'No hash')}")
                    tasks.append(_channel.send(embed=embed))
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                self.logger.error(f"Error sending log message: No wormhole channels found")
        except Exception as e:
            self.logger.error(f"Error handling Redis message: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def before_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return
        if await self.config.is_user_banned(str(message.author.id)):
            return

    async def before_command(self, ctx: commands.Context) -> None:
        if ctx.author == self.user:
            return
        if await self.config.is_user_banned(str(ctx.author.id)):
            raise commands.CheckFailure()

    async def start(self) -> None:
        try:
            self.logger.info("Starting bot...")
            await super().start(os.getenv("token"))
        except Exception as e:
            self.logger.error(f"Error starting bot: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise

    async def close(self) -> None:
        self.logger.info("Stopping bot...")
        self.redis_reconnect_task.cancel()
        if self.redis:
            await self.redis.close()
        if hasattr(self, 'log_observer'):
            self.log_observer.stop()
            self.log_observer.join()
        await super().close()
        self.logger.info("Bot stopped.")

    async def load_extensions(self):
        extensions = [
            "bot.commands.admin",
            "bot.commands.wormhole",
            "bot.commands.general",
            "bot.events"
        ]
        for extension in extensions:
            try:
                if extension not in self.extensions:
                    await self.load_extension(extension)
                    self.logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                self.logger.error(f"Failed to load extension {extension}: {str(e)}")
                self.logger.error(traceback.format_exc())

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        self.logger.info(f"Connected to {len(self.guilds)} guilds")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            return
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send(
                embed=create_embed(
                    title="Command Error",
                    description=f"Unknown command `{ctx.invoked_with}`"
                )
            )
        elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument, commands.UserInputError)):
            command = self.get_command(ctx.invoked_with)
            if command:
                usage = f"{ctx.prefix}{command.qualified_name} {command.signature}"
                await ctx.send(
                    embed=create_embed(
                        title="Usage Error",
                        description=f"Usage: `{usage}`\n\n{command.help or ''}"
                    )
                )
            else:
                await ctx.send(
                    embed=create_embed(
                        title="Command Error",
                        description=f"Unknown command `{ctx.invoked_with}`"
                    )
                )
        else:
            self.logger.error(f"Command error: {str(error)}")
            self.logger.error(traceback.format_exc())
            await ctx.send(
                embed=create_embed(
                    title="Command Error",
                    description="An unexpected error occurred. Please try again later."
                )
            )

async def setup(bot):
    await bot.add_cog(DiscordBot(bot.config))