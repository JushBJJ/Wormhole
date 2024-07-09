from typing import Union
from discord.ext import commands, tasks
from bot.config import MessageInfo, UserConfig, WormholeConfig, save_config, tempMessageInfo
from bot.utils.logging import setup_logging
from bot.features.pretty_message import PrettyMessage
from bot.features.user_management import UserManagement
from bot.features.content_filtering import ContentFiltering
from bot.features.role_management import RoleManagement
from bot.features.proof_of_work import PoWHandler
from bot.features.LLM.gemini import get_closest_command
from bot.features.embed import create_embed

import discord
import os
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
        self.config.logger = self.logger
        #self.redis_client = redis.Redis(host='localhost', port=6379, db=0)

        self.user_management = UserManagement(config)
        self.content_filtering = ContentFiltering(config)
        self.role_management = RoleManagement(config)
        self.pretty_message = PrettyMessage(config)
        self.pow_handler = PoWHandler(config, self)
        
        self.config_path = os.getenv("CONFIG_PATH", "config/config.json")

    async def setup_hook(self) -> None:
        self.logger.info("Setting up bot...")
        await self.load_extensions()
        self.logger.info("Extensions loaded successfully.")
        #self.redis_listener_task = self.loop.create_task(self.listen_to_tox())
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
            return
        if isinstance(result, list):
            tasks = []
            for notification in result:
                tasks.append(message.channel.send(embed=notification))
            
            await asyncio.gather(*tasks)

    async def before_command(self, ctx: commands.Context) -> None:
        if ctx.author == self.user:
            return
        if self.user_management.is_user_banned(ctx.author.id):
            raise commands.CheckFailure()
        success, result = await self.pow_handler.check_pow(ctx.message.content, ctx.author.id, ctx.channel.id)
        if not success:
            return # User failed PoW check
        if isinstance(result, list):  
            tasks = []
            for notification in result:
                tasks.append(ctx.send(embed=notification))
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
            user_config = self.config.get_user_config_by_id(ctx.author.id)
            
            if user_config.difficulty > 1:
                embed = create_embed(description=f"Error: `{str(error)}`")
                await ctx.send(embed=embed)
            
            response = await get_closest_command(
                user_input = ctx.message.content,
                user_role = self.config.get_user_config_by_id(ctx.author.id).role,
                user_id = ctx.author.id,
                commands = self.all_commands,
                #messages = [{"role": msg.role, "content": msg.content} for msg in user_config.temp_command_message_history]
            )
            #user_config.temp_command_message_history.append(tempMessageInfo(role="user", content=ctx.message.content))            
            #user_config.temp_command_message_history.append(tempMessageInfo(role="bot", content=response.response_to_user))
            
            if len(user_config.temp_command_message_history) > 10:
                user_config.temp_command_message_history.pop(0)
            
            if response.moderation.ban_probability > 7:
                user_hash = self.config.get_user_hash(ctx.author.id)
                if user_hash not in self.config.banned_users:
                    self.config.banned_users.append(user_hash)
                    await ctx.send("You have been banned for abusing the bot.")
                return
            elif response.moderation.abuse_probability >= 6:
                user_config.difficulty_penalty += 0.5
                await ctx.send("Your difficulty penalty has been increased by 0.1 due to abusing the bot.")
                return
            elif response.moderation.spam_probability >= 6 or response.moderation.useless_probability >= 6:
                user_config.difficulty_penalty += 1
                await ctx.send("Your difficulty penalty has been increased by 0.5 due to spamming the bot.")
                return
            elif response.matched_command == "":
                await ctx.send(
                    embed=create_embed(
                        title="Command Error",
                        description=f"Unknown command `{ctx.message.content}`"
                    )
                )
                return

            description = f"Error: `{str(error)}`\n\n"\
                            f"Did you mean `{response.matched_command} {response.matched_subcommand}`?\n\n"\
            
            if response.match_probability > 7:
                description += f"Auto-executing command: `Yes`\n"
                description += f"Full command: `%{response.matched_command} {response.matched_subcommand} {' '.join(response.matched_command_parameters)}`"
            else:
                params = self.all_commands[response.matched_command].params
                params = [f"`{key}` - `{value.annotation}`" for key, value in params.items() if key != "kwargs"]
                params_str = "\n".join(params)
                description += f"Command Parameters:\n{params_str}"
            
            await ctx.send(
                embed=create_embed(
                    title="Command Error",
                    description=description
                )
            )
            
            if response.match_probability >= 6:
                matched_command = response.matched_command
                matched_subcommand = response.matched_subcommand or ""
                command = self.get_command(matched_command)
                parameters = response.matched_command_parameters

                if isinstance(command, commands.core.Group):
                    if command.get_command(matched_subcommand) is None and matched_subcommand:
                        try:
                            parameters = [matched_subcommand] + parameters
                            await ctx.invoke(command, *parameters)
                        except Exception as e:
                            await ctx.send(embed=create_embed(
                                title="Command Error",
                                description=f"Command `{matched_command} {matched_subcommand}` not found"
                            ))
                    else:
                        if matched_subcommand:
                            command = command.get_command(matched_subcommand)
                        if len(parameters) == 0:
                            await ctx.invoke(command)
                        else:
                            await ctx.invoke(command, *parameters)
                elif isinstance(command, commands.core.Command):
                    if len(parameters) == 0:
                        await ctx.invoke(command)
                    else:
                        await ctx.invoke(command, *parameters)
                else:
                    await ctx.send(embed=create_embed(
                        title="Command Error",
                        description=f"Command `{matched_command}` not found"
                    ))

            self.logger.info(response)

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

    @commands.command(case_insensitive=True)
    async def tox_add(self, ctx, tox_id: str, **kwargs):
        """Add a Tox ID to the node"""
        message = json.dumps({"message": f"COMMAND: ADD {tox_id}"})
        self.redis_client.publish('tox_node', message)
        await ctx.send(f"Adding Tox ID: {tox_id}")

    @commands.command(case_insensitive=True)
    async def tox_list(self, ctx, **kwargs):
        """List all Tox IDs in the node"""
        message = json.dumps({"message": "COMMAND: LIST"})
        self.redis_client.publish('tox_node', message)
        await ctx.send("Retrieving Tox ID list...")

    @commands.command(case_insensitive=True)
    async def tox_id(self, ctx, **kwargs):
        """Get the Tox ID of the node"""
        message = json.dumps({"message": "COMMAND: ID"})
        self.redis_client.publish('tox_node', message)
        await ctx.send("Retrieving Tox ID of the node...")

async def setup(bot):
    await bot.add_cog(DiscordBot(bot.config))