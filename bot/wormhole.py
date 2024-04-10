import discord
import logging
import asyncio
import os

from discord.ext import commands
from bot.utils.file import read_config, write_config
from dotenv import load_dotenv

load_dotenv()

ADMIN_ID = 0
WEBSITE_URL = "https://wormhole.jushbjj.com"

intents = discord.Intents.all()


class WormholeBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix, intents=intents)
        self.client_id = os.getenv("client_id", "")
        self.client_secret = os.getenv("client_secret", "")
        self.token = os.getenv("token", "")
        self.remove_command("help")
        
        self.bot_commands = []

    def start_wormhole(self):
        logging.warning("Starting Wormhole...")
        self.run(self.token)

    async def on_ready(self):
        await self.index_commands()
        print("Wormhole Loaded.")
        
    async def index_commands(self):
        self.bot_commands = [command for command in self.commands]

    async def global_msg(self, message):
        config = await self.get_config()
        guilds = list(self.guilds)
        
        for guild in guilds:
            if guild.id in config["banned_servers"]:
                continue
            elif guild.id in config["servers"]:
                for channel in guild.text_channels:
                    if channel.id in config["channels"] and channel.id != message.channel.id:
                        await channel.send(f"```{message.channel.name} ({message.guild.name}) (ID: {message.author.id}) - {message.author.display_name} says:```{message.content}")

    async def get_config(self):
        return await read_config()

    async def get_banned_users(self):
        config = await read_config()
        return config.get("banned_users", [])

    async def get_banned_servers(self):
        config = await read_config()
        return config.get("banned_servers", [])

    async def get_servers(self):
        config = await read_config()
        return config.get("servers", [])

    def is_itself(self, message):
        return message.author.id == self.user.id
    
    def user_is_admin(self, ctx):
        return ctx.author.guild_permissions.VALID_FLAGS.get("administrator", False)


bot = WormholeBot(command_prefix="%", intents=intents)


@bot.event
async def on_guild_join(guild):
    channel = next(
        (c for c in guild.text_channels if guild.me.permissions_in(c).send_messages),
        None,
    )
    if channel:
        await channel.send(
            "Thanks for inviting me! To chat with other servers, say `%join` in the channel you want to connect! For a full list of commands, say `%help`"
        )


@bot.event
async def on_message(message):
    if (
        bot.is_itself(message)
        or message.author.id in await bot.get_banned_users()
        or message.guild.id in await bot.get_banned_servers()
    ):
        return

    await bot.index_commands()
    await bot.process_commands(message)

    if message.guild.id in await bot.get_servers():
        logging.info(f"{message.channel.name} ({message.guild.name}) (ID: {message.author.id}) - {message.author.display_name} says:\n{message.content}")
        await bot.global_msg(message)
        await message.add_reaction("✅") # TOOD make this optional


@bot.command(name="help")
async def help_command(ctx):
    """
    %help: Display this help message
    """
    
    message = "The Wormhole Bot allows you to communicate with other servers."
    
    for command in bot.bot_commands:
        message += f"\n{command.help}"
    
    await ctx.send(message)

@bot.command(name="stats")
async def stats_command(ctx):
    """
    %stats: Display the bot's stats
    """
    n_servers =-len(await bot.get_servers())
    n_users = sum([guild.member_count for guild in ctx.bot.guilds])
    
    await ctx.send(f"Connected to {n_servers} servers.\nTotal {n_users} users.")

@bot.command(name="connect")
async def connect_command(ctx):
    """
    %connect: Connect your server to the public. Do `%join` in the channel you want to connect. By default, all channels are not connected.
    """
    
    if bot.user_is_admin(ctx):
        config = await bot.get_config()
        
        # Check if the server is already connected
        if ctx.guild.id in config["servers"]:
            await ctx.send("This server is already connected.")
            return
        
        config["servers"].append(ctx.guild.id)
        if await write_config(config):
            logging.info(f"Connected to {ctx.guild.name}")
            await ctx.send("Connected server")
        else:
            logging.error(f"Error connecting to {ctx.guild.name}")
            await ctx.send("Error connecting your server. Please contact @JushBJJ")
    else:
        await ctx.send("You must be a server admin to use this command.")
    
@bot.command(name="disconnect")
async def disconnect_command(ctx):
    """
    %disconnect: Disconnect your server
    """
    
    if bot.user_is_admin(ctx):
        config = await bot.get_config()
        
        try:
            config["servers"].remove(ctx.guild.id)
        except ValueError:
            await ctx.send("This server is not connected.")
            return
        
        if await write_config(config):
            logging.info(f"Disconnected from {ctx.guild.name}")
            await ctx.send("Disconnected your server.")
        else:
            logging.error(f"Error disconnecting from {ctx.guild.name}")
            await ctx.send("Error disconnecting your server. Please contact @JushBJJ")
    else:
        await ctx.send("You must be a server admin to use this command.")

@bot.command(name="invite")
async def invite_command(ctx):
    """
    %invite: Invite this bot to your server
    """
    
    await ctx.send(f"https://discord.com/oauth2/authorize?client_id={bot.client_id}&permissions=68608&scope=bot")

@bot.command(name="website")
async def website_command(ctx):
    """
    %website: Go to this bot's website
    """
    
    await ctx.send(WEBSITE_URL)
    
@bot.command(name="join")
async def join_command(ctx):
    """
    %join: Join the server. Automatically connects the server to the server if not already connected.
    """
    
    if ctx.guild.id not in await bot.get_servers():
        await ctx.invoke(connect_command)
    
    config = await bot.get_config()
    channel_id = ctx.channel.id
    
    if channel_id in config["channels"]:
        await ctx.send("This channel is already connected.")
        return
    
    config["channels"].append(channel_id)
    if await write_config(config):
        await ctx.send("Connected channel")
    else:
        await ctx.send("Error connecting channel. Please contact @JushBJJ")
        

@bot.command(name="leave")
async def leave_command(ctx):
    """
    %leave: Stops recieving messages channel. Does NOT disconnect your server.
    """
    
    config = await bot.get_config()
    channel_id = ctx.channel.id
    
    try:
        config["channels"].remove(channel_id)
    except ValueError:
        await ctx.send("This channel is not connected.")
        return
    
    if await write_config(config):
        await ctx.send("Disconnected channel.")
    else:
        await ctx.send("Error disconnecting channel. Please contact @JushBJJ")
        
@bot.command(name="privacy")
async def privacy_command(ctx):
    """
    %privacy: View the privacy policy
    """
    
    await ctx.send(
        "WE WILL STORE:\n"\
        "- Connected server IDs\n"\
        "- Connected channel IDs\n"\
        "- Banned User IDs\n"\
        "- Banned Server IDs\n"\
        "WE DO NOT STORE:\n"\
        "- Your messages\n"\
        "- Your server name\n"\
        "- Your channel name\n"\
    )

@bot.command(name="ping")
async def ping_command(ctx):
    """
    %ping: Check if the bot is online
    """
    
    await ctx.send("Pong!")

if __name__ == "__main__":
    bot.start_wormhole()
