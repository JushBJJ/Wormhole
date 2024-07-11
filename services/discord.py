from typing import Union
from discord.ext import commands, tasks
from bot.config import WormholeConfig
from bot.utils.logging import setup_logging
from bot.features.pretty_message import PrettyMessage
from bot.features.proof_of_work import PoWHandler
from bot.features.LLM.gemini import get_closest_command
from bot.features.embed import create_embed

import discord
import os
import asyncio
import traceback

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

    async def setup_hook(self) -> None:
        self.logger.info("Setting up bot...")
        await self.load_extensions()
        self.logger.info("Extensions loaded successfully.")
        self.add_listener(self.before_message, "on_message")
        self.before_invoke(self.before_command)

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
        success, result = await self.pow_handler.check_pow(ctx.message, ctx.message.content, ctx.author.id, ctx.channel.id)
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
            await super().start(os.getenv("token"))
        except Exception as e:
            self.logger.error(f"Error starting bot: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise

    async def close(self) -> None:
        self.logger.info("Stopping bot...")
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
                if not extension in self.extensions:
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
            user_config = await self.config.get_user(ctx.author.id)
            
            if user_config['difficulty'] > 1:
                embed = create_embed(description=f"Error: `{str(error)}`")
                await ctx.send(embed=embed)
            
            user_role = await self.config.get_user_role(ctx.author.id)
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

async def setup(bot):
    await bot.add_cog(DiscordBot(bot.config))