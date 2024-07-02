from discord.ext import commands

class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Check if the bot is responsive"""
        await ctx.send("Pong!")

    @commands.command(name="help")
    async def help(self, ctx):
        """Display help information"""
        help_text = "Available commands:\n"
        for command in self.bot.commands:
            help_text += f"{self.bot.command_prefix}{command.name}: {command.help}\n"
        await ctx.send(help_text)

    @commands.command()
    async def info(self, ctx):
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

async def setup(bot):
    await bot.add_cog(GeneralCommands(bot))