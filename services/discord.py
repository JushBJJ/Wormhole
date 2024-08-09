from discord.ext import commands
from bot.config import WormholeConfig
from bot.utils.logging import setup_logging
from bot.features.pretty_message import PrettyMessage
from bot.features.proof_of_work import PoWHandler
from bot.features.LLM.gemini import get_closest_command
from bot.features.embed import create_embed
from typing import List, Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

import re
import discord
import os
import asyncio
import traceback

class LogParser:
    def __init__(self):
        self.timestamp_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]'
        self.system_message_pattern = rf'{self.timestamp_pattern}\s+\*\s+(.*)'
        self.user_message_pattern = rf'{self.timestamp_pattern}\s+([^:]+):\s+(.*)'

    def parse_log(self, log_lines: List[str]) -> List[Dict[str, str]]:
        parsed_messages = []
        for line in log_lines:
            parsed_message = self.parse_line(line)
            if parsed_message:
                parsed_messages.append(parsed_message)
        return parsed_messages

    def parse_line(self, line: str) -> Dict[str, str]:
        system_match = re.match(self.system_message_pattern, line)
        if system_match:
            return self.create_system_message(*system_match.groups())

        user_match = re.match(self.user_message_pattern, line)
        if user_match:
            return self.create_user_message(*user_match.groups())

        return None

    def create_system_message(self, timestamp: str, content: str) -> Dict[str, str]:
        return {
            'type': 'system',
            'timestamp': self.parse_timestamp(timestamp),
            'content': self.sanitize_content(content)
        }

    def create_user_message(self, timestamp: str, username: str, content: str) -> Dict[str, str]:
        return {
            'type': 'user',
            'timestamp': self.parse_timestamp(timestamp),
            'username': self.sanitize_username(username),
            'content': self.sanitize_content(content)
        }

    def parse_timestamp(self, timestamp: str) -> str:
        try:
            return str(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return ''

    def sanitize_username(self, username: str) -> str:
        return ''.join(char for char in username if ord(char) >= 32 and ord(char) <= 126)[:50]

    def sanitize_content(self, content: str) -> str:
        return ''.join(char for char in content if ord(char) >= 32)

class LogHandler(FileSystemEventHandler):
    def __init__(self, filename, bot):
        self.filename = filename
        self.file = open(filename, 'r')
        self.file.seek(0, 2)  # Go to the end of the file
        self.bot = bot
        self.log_parser = LogParser()

    def on_modified(self, event):
        if event.src_path == self.filename:
            new_lines = self.file.readlines()
            parsed_messages = self.log_parser.parse_log(new_lines)
            for message in parsed_messages:
                asyncio.run_coroutine_threadsafe(self.bot.send_log_to_discord(message), self.bot.loop)

    def __del__(self):
        self.file.close()

class DiscordBot(commands.Bot):
    def __init__(self, config: WormholeConfig):
        intents = discord.Intents.all()
        super().__init__(command_prefix="%", intents=intents, help_command=None)
        self.config = config
        self.logger = setup_logging()
        self.config.logger = self.logger

        self.pretty_message = PrettyMessage(config)
        self.pow_handler = PoWHandler(config, self)
        self.message_hashes = {}
        self.last_messages = {}  # Last overall 50 messages, separated by channel and user
        self.evaluations = {}

        # Set up log monitoring
        self.log_file = os.getenv("SSH_CHAT_FILE", "log.txt")  # Update this to your log file path
        self.log_observer = None

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
        self.logger.info("Monitoring ssh-chat...")
        self.start_ssh_listen()

    def start_ssh_listen(self):
        event_handler = LogHandler(self.log_file, self)
        self.log_observer = Observer()
        self.log_observer.schedule(event_handler, path=self.log_file, recursive=False)
        self.log_observer.start()
        self.logger.info("ssh-chat monitoring started.")

    async def before_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return
        if await self.config.is_user_banned(str(message.author.id)):
            return
        success, result, hashed_message = await self.pow_handler.check_pow(message, message.content, message.author.id, message.channel.id)
        if not success:
            return
        if isinstance(result, list):
            tasks = []
            for notification in result:
                tasks.append(message.channel.send(embed=notification))
            
            await asyncio.gather(*tasks)
        self.message_hashes[message.id] = hashed_message

    async def before_command(self, ctx: commands.Context) -> None:
        if ctx.author == self.user:
            return
        if await self.config.is_user_banned(str(ctx.author.id)):
            raise commands.CheckFailure()
        success, result, _ = await self.pow_handler.check_pow(ctx.message, ctx.message.content, ctx.author.id, ctx.channel.id)
        if not success:
            return  # User failed PoW check
        if isinstance(result, list):  
            tasks = []
            for notification in result:
                tasks.append(ctx.send(embed=notification))
            await asyncio.gather(*tasks)

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
        if self.log_observer:
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
        else:
            self.logger.error(f"Command error: {str(error)}")
            self.logger.error(traceback.format_exc())
            user_config = await self.config.get_user(str(ctx.author.id))
            
            if user_config['difficulty'] > 1:
                embed = create_embed(description=f"Error: `{str(error)}`")
                await ctx.send(embed=embed)
            
            user_role = await self.config.get_user_role(str(ctx.author.id))
            response = await get_closest_command(
                user_input = ctx.message.content,
                user_role = user_role,
                user_id = ctx.author.id,
                commands = self.all_commands,
            )
            
            if response.moderation.ban_probability > 7:
                user_id = str(ctx.author.id)
                if await self.config.is_user_banned(user_id):
                    await self.config.ban_user(user_id)
                    await ctx.send("You have been banned for abusing the bot.")
                return
            elif response.moderation.abuse_probability >= 6:
                await self.config.update_user_difficulty_penalty(user_id, 0.5)
                await ctx.send("Your difficulty penalty has been increased by 0.5 due to abusing the bot.")
                return
            elif response.moderation.spam_probability >= 6 or response.moderation.useless_probability >= 6:
                await self.config.update_user_difficulty_penalty(user_id, 1)
                await ctx.send("Your difficulty penalty has been increased by 1 due to spamming the bot.")
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
                          f"Did you mean `{response.matched_command} {response.matched_subcommand}`?\n\n"
            
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

    async def send_log_to_discord(self, log_message: Dict[str, str]):
        """ Prototype """
        channels = await self.config.get_channels_by_category("test")
        if channels:
            tasks = []
            for channel in channels:
                _channel = self.get_channel(int(channel['channel_id']))
                if log_message['type'] == 'system':
                    embed = discord.Embed(
                        title="System Message",
                        description=log_message['content']
                    )
                    embed.set_footer(text="SSH-Chat")
                else:
                    embed = discord.Embed(
                        title=f"{log_message['username']}",
                        description=log_message['content']
                    )
                    embed.set_footer(text="SSH-Chat")
                tasks.append(_channel.send(embed=embed))
            await asyncio.gather(*tasks)
        else:
            self.logger.error(f"Error sending log message: No wormhole channels found")


async def setup(bot):
    await bot.add_cog(DiscordBot(bot.config))