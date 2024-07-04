from collections import defaultdict
import discord

from typing import Union
from discord.ext import commands

class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    @commands.command(case_insensitive=True)
    async def ping(self, ctx, **kwargs):
        """Check if the bot is responsive"""
        await ctx.send("Pong!")

    @commands.command(name="help")
    async def help(self, ctx, module: str = None, **kwargs):
        """Display help information"""
        if module:
            await self.show_module_help(ctx, module)
        else:
            await self.show_all_help(ctx)

    async def show_all_help(self, ctx):
        help_text = "Available modules:\n"
        modules = defaultdict(list)

        for command in self.bot.commands:
            modules[command.cog_name or "No Category"].append(command)

        for module, cmds in modules.items():
            help_text += f"\n`{module}`:\n"
            for cmd in cmds:
                help_text += f"  {self.bot.command_prefix}{cmd.name}: {cmd.help}\n"

        help_text += f"\nUse `{self.bot.command_prefix}help <module>` for detailed information about a specific module."
        await ctx.send(help_text)

    async def show_module_help(self, ctx, module):
        module = module.lower()
        help_text = f"Commands in {module} module:\n"
        found = False

        for command in self.bot.commands:
            if command.cog_name.lower() == module:
                found = True
                help_text += f"\n`{self.bot.command_prefix}{command.name}`: {command.help}\n"
                if command.params:
                    help_text += "  Parameters:\n"
                    for param, details in command.params.items():
                        if param != "self" and param != "ctx":
                            help_text += f"    {param}"
                            if details.default != details.empty:
                                help_text += f" (optional, default: {details.default})"
                            help_text += "\n"

        if not found:
            await ctx.send(f"No module named '{module}' found.")
            return

        await ctx.send(help_text)

    @commands.command(case_insensitive=True)
    async def info(self, ctx, **kwargs):
        """Display information about the Wormhole bot"""
        info_text = (
            "Wormhole Bot\n"
            "------------\n"
            "Inter-server Communication.\n"
            f"Connected to {len(self.bot.guilds)} servers\n"
            f"Serving {len(self.bot.users)} users\n"
            f"Prefix: {self.bot.command_prefix}"
        )
        await ctx.send(info_text)

    @commands.command(case_insensitive=True)
    async def get_user(self, ctx, user_identifier: Union[str, int], **kwargs):
        try:
            try:
                user_id = int(user_identifier)
                user_config = self.config.get_user_config_by_id(user_id)
                send_method = ctx.author.send
                
                if self.config.get_user_role(ctx.author.id) != "admin" and ctx.author.id != user_id:
                    await ctx.send("You must be a Wormhole admin to view user information by ID.")
            except ValueError:
                user_config = self.config.get_user_config_by_hash(user_identifier)
                send_method = ctx.send

            embed = self.create_user_embed(user_config)
            await send_method(embed=embed)
            if send_method == ctx.author.send:
                await ctx.send("For privacy reasons, I have sent you a DM.")

        except discord.Forbidden:
            await ctx.send("I couldn't send you a DM. Please check your privacy settings.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    def create_user_embed(self, user_config):
        description = f"Names: **{str(user_config.names)}**\n" \
                      f"Role: **{user_config.role}**\n" \
                      f"Hash: **{user_config.hash}**"
        embed = discord.Embed(
            title="User Information",
            description=description,
            color=self.config.get_role_color(user_config.role)
        )
        embed.set_image(url=user_config.profile_picture)
        embed.set_footer(text="Missing info means not registered yet")
        return embed

async def setup(bot):
    await bot.add_cog(GeneralCommands(bot))