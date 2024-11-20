import asyncio
import json
import os
import traceback
import discord
import redis.asyncio as redis
import irc.client_aio

from discord.ext import commands, tasks
from typing import Dict, List, Optional
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
        self.irc_server = os.getenv("IRC_SERVER")
        self.irc_port = int(os.getenv("IRC_PORT"))
        self.irc_nickname = os.getenv("IRC_NICKNAME")
        self.irc_client = None
        self.setup_once = False

    def format_attachments(self, attachments) -> str:
        if not attachments:
            return ""
        urls = [f"[Attachment: {a.url}]" for a in attachments]
        return " ".join(urls)

    def format_irc_message(self, display_name: str, user_hash: str, content: str, attachments, sticker_content: str) -> str:
        parts = []
        header = f"[{display_name}] ({user_hash[:6]})"
        parts.append(header)

        if content.strip():
            parts.append(content)
        
        attachment_text = self.format_attachments(attachments)
        if attachment_text:
            parts.append(attachment_text)
            
        if sticker_content:
            parts.append(sticker_content)

        return ": ".join([parts[0], " ".join(parts[1:])])

    def format_irc_header(self, display_name: str, user_hash: str) -> str:
        return f"[{display_name}] ({user_hash[:6]})"

    def format_attachment_message(self, header: str, attachment) -> str:
        return f"{header}: [Attachment: {attachment.url}]"

    def format_sticker_message(self, header: str, sticker_content: str) -> str:
        return f"{header}: {sticker_content}"

    def format_content_message(self, header: str, content: str) -> str:
        return f"{header}: {content}"

    async def send_irc_message_parts(self, connection, channel: str, header: str, 
                                   content: str, attachments, sticker_content: str):
        if content.strip():
            connection.privmsg(f"#{channel}", self.format_content_message(header, content))
        
        if sticker_content:
            connection.privmsg(f"#{channel}", self.format_sticker_message(header, sticker_content))

        for attachment in attachments:
            connection.privmsg(f"#{channel}", self.format_attachment_message(header, attachment))

    async def _setup_last_messages_dict(self) -> None:
        channel_categories: list[str] = await self.config.get_channel_list()
        self.last_messages = {category: set() for category in channel_categories}
        
    async def setup_hook(self) -> None:
        if not self.setup_once:
            self.setup_once = True
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

            channel_list = await self.config.get_channel_list()
            _channel_list = []
            for channel_name in channel_list:
                irc_channel = f'#{channel_name}'
                _channel_list.append(irc_channel)
            self.irc_client = IRCClient(self, irc_channel)
            self.irc_client.target_channels = _channel_list
            await self.irc_client.connect_and_start()

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
        if self.irc_client:
            self.irc_client.connection.close()
            self.irc_client = None
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

    async def forward_irc_message_to_discord(self, irc_channel: str, sender: str, message: str):
        channels = await self.config.get_channels_by_category(irc_channel)
        if channels:
            tasks = []
            for channel_data in channels:
                channel = self.get_channel(int(channel_data['channel_id']))
                if channel:
                    permissions = channel.permissions_for(channel.guild.me)
                    if permissions.manage_webhooks:
                        webhooks = await channel.webhooks()
                        webhook = discord.utils.get(webhooks, name="WormholeWebhook")
                        if not webhook:
                            webhook = await channel.create_webhook(name="WormholeWebhook")
                        tasks.append(webhook.send(
                            content=message,
                            username=sender,
                            avatar_url="https://cdn.discordapp.com/attachments/1257498794069590017/1308758643407061013/19ba1725ab283c0ea5b844163e43cefd.png?ex=673f1bf8&is=673dca78&hm=f363368cf02dd73daf2a4ea18b9bedabab06ad984ca2e0bbe51bdadeb17fd5cb&",
                            allowed_mentions=discord.AllowedMentions(everyone=False)
                        ))
                    else:
                        tasks.append(channel.send(
                            f":warning: I need the 'Manage Webhooks' permission in this server to send/receive wormhole messages."
                        ))
            await asyncio.gather(*tasks, return_exceptions=True)

class IRCClient(irc.client_aio.AioSimpleIRCClient):
    def __init__(self, bot, irc_channels):
        super().__init__()
        self.bot = bot
        self.nickname = bot.irc_nickname
        self.target_channels = irc_channels

    async def connect_and_start(self):
        try:
            self.bot.logger.info(f"Connecting to IRC server: {self.bot.irc_server}")
            ssl_factory = irc.connection.AioFactory(ssl=True)
            await self.connection.connect(
                server=self.bot.irc_server,
                port=self.bot.irc_port,
                nickname=self.nickname,
                connect_factory=ssl_factory
            )
        except irc.client.ServerConnectionError as e:
            self.bot.logger.error(f"Failed to connect to IRC server: {e}")
        except Exception as e:
            self.bot.logger.error(f"Error connecting to IRC server: {e}")

    async def process_messages(self):
        while True:
            self.reactor.process_once(timeout=0.1)
            await asyncio.sleep(0.1)

    def on_join(self, connection, event):
        pass

    def on_welcome(self, connection, event):
        self.bot.logger.info(f"IRC connection established")
        for channel in self.target_channels:
            connection.join(channel)
            self.bot.logger.info(f"Joined channel {channel}.")

    def on_privmsg(self, connection, event):
        sender = f"[IRC] {irc.client.NickMask(event.source).nick}"
        message = event.arguments[0]
        target = event.target[1:]
        asyncio.run_coroutine_threadsafe(
            self.bot.forward_irc_message_to_discord(target, sender, message),
            self.bot.loop
        )

    def on_pubmsg(self, connection, event):
        self.on_privmsg(connection, event)

    def disconnect(self):
        self.future.cancel()
        self.connection.disconnect("Bot shutting down.")

async def setup(bot):
    await bot.add_cog(DiscordBot(bot.config))