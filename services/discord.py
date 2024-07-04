import time
from typing import Union
from discord.ext import commands, tasks
from bot.config import MessageInfo, UserConfig, WormholeConfig, save_config
from bot.utils.logging import setup_logging
from bot.features.wormhole_economy import WormholeEconomy
from bot.features.pretty_message import PrettyMessage
from bot.features.user_management import UserManagement
from bot.features.content_filtering import ContentFiltering
from bot.features.role_management import RoleManagement
from bot.features.proof_of_work import PoWHandler

import discord
import redis
import json
import asyncio
import traceback

class DiscordBot(commands.Bot):
    def __init__(self, config: WormholeConfig):
        intents = discord.Intents.all()
        super().__init__(command_prefix="%", intents=intents, help_command=None)
        self.config = config
        self.logger = setup_logging()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)

        self.user_management = UserManagement(config)
        self.content_filtering = ContentFiltering(config)
        self.role_management = RoleManagement(config)
        self.pretty_message = PrettyMessage(config)
        self.wormhole_economy = WormholeEconomy(config)
        self.pow_handler = PoWHandler(config, self.wormhole_economy)
        
        self.config_path = "config/config.json"

    async def setup_hook(self) -> None:
        self.logger.info("Setting up bot...")
        await self.load_extensions()
        self.logger.info("Extensions loaded successfully.")
        self.redis_listener_task = self.loop.create_task(self.listen_to_tox())
        self.save_config_loop.start()
        self.add_listener(self.before_message, "on_message")
        self.before_invoke(self.before_command)

    async def before_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return
        if self.user_management.is_user_banned(message.author.id):
            return
        success, result = await self.pow_handler.check_pow(message.content, message.author.id, message.channel.id)
        if not success:
            await message.channel.send(result)
            return
        if isinstance(result, list):
            tasks = []
            for notification in result:
                tasks.append(message.channel.send(notification))
            
            await asyncio.gather(*tasks)

    async def before_command(self, ctx: commands.Context) -> None:
        if ctx.author == self.user:
            return
        if self.user_management.is_user_banned(ctx.author.id):
            raise commands.CheckFailure()
        success, result = await self.pow_handler.check_pow(ctx.message.content, ctx.author.id, ctx.channel.id)
        if not success:
            raise commands.CheckFailure()
        if isinstance(result, list):  
            tasks = []
            for notification in result:
                tasks.append(ctx.send(notification))
            await asyncio.gather(*tasks)

    async def start(self) -> None:
        try:
            self.logger.info("Starting bot...")
            await super().start(self.config.discord_token)
        except Exception as e:
            self.logger.error(f"Error starting bot: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise

    async def close(self) -> None:
        self.logger.info("Stopping bot...")

        if hasattr(self, 'redis_listener_task'):
            self.redis_listener_task.cancel()
            try:
                await self.redis_listener_task
            except asyncio.CancelledError:
                pass

        self.save_config_loop.cancel()
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
        else:
            self.logger.error(f"Command error: {str(error)}")
            self.logger.error(traceback.format_exc())
            await ctx.send(f"An error occurred: {str(error)}")

    async def listen_to_tox(self):
        self.logger.info("Starting Redis listener...")
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe('wormhole_channel')
        
        while not self.is_closed():
            try:
                message = pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    data = json.loads(message['data'])
                    if 'message' in data and data.get('from_tox', False):
                        await self.process_tox_message(data)
                await asyncio.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error in Redis listener: {str(e)}")
                await asyncio.sleep(5)

    async def process_tox_message(self, data):
        for channel_id in self.config.channels:
            channel = self.get_channel(int(channel_id))
            if channel:
                await channel.send(f"[Tox] {data['message']}")

    @tasks.loop(minutes=1)
    async def save_config_loop(self):
        try:
            save_config(self.config_path, self.config)
            self.logger.info(f"Config saved successfully to {self.config_path}")
        except Exception as e:
            self.logger.error(f"Error saving config: {str(e)}")

    @save_config_loop.before_loop
    async def before_save_config_loop(self):
        await self.wait_until_ready()

    @commands.command()
    async def pow_status(self, ctx):
        """Get the current PoW status for the user"""
        status = self.pow_handler.get_pow_status(ctx.author.id)
        await ctx.send(status)

    @commands.command()
    async def tox_add(self, ctx, tox_id: str):
        """Add a Tox ID to the node"""
        message = json.dumps({"message": f"COMMAND: ADD {tox_id}"})
        self.redis_client.publish('tox_node', message)
        await ctx.send(f"Adding Tox ID: {tox_id}")

    @commands.command()
    async def tox_list(self, ctx):
        """List all Tox IDs in the node"""
        message = json.dumps({"message": "COMMAND: LIST"})
        self.redis_client.publish('tox_node', message)
        await ctx.send("Retrieving Tox ID list...")

    @commands.command()
    async def tox_id(self, ctx):
        """Get the Tox ID of the node"""
        message = json.dumps({"message": "COMMAND: ID"})
        self.redis_client.publish('tox_node', message)
        await ctx.send("Retrieving Tox ID of the node...")

async def setup(bot):
    await bot.add_cog(DiscordBot(bot.config))