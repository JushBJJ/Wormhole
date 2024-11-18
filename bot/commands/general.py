import discord
from discord.ext import commands
from bot.config import WormholeConfig

class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config: WormholeConfig = bot.config

    @commands.command(case_insensitive=True)
    async def ping(self, ctx):
        """Check if the bot is responsive"""
        await ctx.send("Pong!")

    @commands.group(case_insensitive=True, invoke_without_command=True)
    async def help(self, ctx, command: str = None):
        """Display help information"""
        if command is None:
            await self.show_all_help(ctx)
        else:
            await self.show_command_help(ctx, command)

    async def show_all_help(self, ctx):
        embed = discord.Embed(title="Wormhole Bot Help", color=discord.Color.blue())
        embed.description = f"Use `{ctx.prefix}help <command>` for more info on a command.\n" \
                            f"Use `{ctx.prefix}help <category>` for more info on a category."

        for cog_name, cog in self.bot.cogs.items():
            commands_list = []
            for command in cog.get_commands():
                if not command.hidden:
                    if isinstance(command, commands.Group):
                        commands_list.append(f"`{command.name}`\*")
                    else:
                        commands_list.append(f"`{command.name}`")
            if commands_list:
                embed.add_field(name=cog_name, value=", ".join(commands_list), inline=False)

        embed.set_footer(text="* denotes a command group")
        await ctx.send(embed=embed)

    async def show_command_help(self, ctx, command_name: str):
        command = self.bot.get_command(command_name)
        if command is None:
            await ctx.send(f"No command called '{command_name}' found.")
            return

        embed = discord.Embed(title=f"Help: {command.qualified_name}", color=discord.Color.blue())
        embed.description = command.help or "No description available."

        if isinstance(command, commands.Group):
            subcommands = []
            for subcommand in command.commands:
                subcommands.append(f"`{subcommand.name}`: {subcommand.help or 'No description'}")
            if subcommands:
                embed.add_field(name="Subcommands", value="\n".join(subcommands), inline=False)

        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in command.aliases), inline=False)

        usage = f"{ctx.prefix}{command.qualified_name}"
        if command.signature:
            usage += f" {command.signature}"
        embed.add_field(name="Usage", value=f"`{usage}`", inline=False)

        await ctx.send(embed=embed)

    @commands.command(case_insensitive=True)
    async def info(self, ctx):
        """Display information about the Wormhole bot"""
        embed = discord.Embed(title="Wormhole Bot", color=discord.Color.blue())
        embed.description = "Inter-server Communication."
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Users", value=str(len(self.bot.users)), inline=True)
        embed.add_field(name="Prefix", value=self.bot.command_prefix, inline=True)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="userinfo")
    async def get_user(self, ctx, user_id_or_hash: str = None):
        """Get user information by ID or hash"""
        author_id = str(ctx.author.id)
        if user_id_or_hash is None:
            user_id_or_hash = author_id

        try:
            user_config = await self.config.get_user_by_hash(user_id_or_hash)
            embed = await self.create_user_embed(user_config)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    async def create_user_embed(self, user_config):
        usernames = await self.config.get_user_usernames(user_config.get('user_id', ''))
        names = ", ".join([username[0] for username in usernames])
        description = f"Names: **{names}**\n" \
                      f"Role: **{user_config.get('role', 'None')}**\n" \
                      f"Hash: **{user_config.get('hash', 'None')}**\n" 
        embed = discord.Embed(
            title="User Information",
            description=description,
            color=await self.config.get_role_color(user_config.get('role', 'user'))
        )
        embed.set_image(url=user_config.get('profile_picture', ''))
        embed.set_footer(text="Missing info means not registered yet")
        return embed

async def setup(bot):
    await bot.add_cog(GeneralCommands(bot))