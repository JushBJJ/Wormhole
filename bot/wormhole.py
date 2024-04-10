import discord
import logging
import os

from discord.ext import commands
from bot.utils.file import read_config, write_config

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
        
        self.bot_commands = [
            self.help_command   
        ]

    def start_wormhole(self):
        self.run(self.token)

    async def on_ready(self):
        print("Wormhole Loaded.")

    async def global_msg(self, message):
        config = await self.get_config()
        guilds = message.bot.guilds
        
        for guild in guilds:
            if guild.id in config["banned_servers"]:
                continue
            elif guild.id in config["servers"]:
                for channel in guild.text_channels:
                    if channel.id in config["channels"] and channel.id not in config["banned_channels"]:
                        await channel.send(message.content)

    async def get_config(self):
        return await read_config()

    async def get_banned_users(self):
        config = await read_config()
        return await config.get("banned_users", [])

    async def get_banned_servers(self):
        config = await read_config()
        return await config.get("banned_servers", [])

    async def get_servers(self):
        config = await read_config()
        return await config.get("servers", [])

    def is_itself(self, message):
        return message.author.id == self.user.id


bot = WormholeBot(command_prefix="%", intents=intents)


@bot.event
async def on_guild_join(guild):
    channel = next(
        (c for c in guild.text_channels if guild.me.permissions_in(c).send_messages),
        None,
    )
    if channel:
        await channel.send(
            "Thanks for inviting me! To chat with other servers, say `%setup` in the channel you want to set me up in! For a full list of commands, say `%help`"
        )


@bot.event
async def on_message(message):
    if (
        bot.is_itself(message)
        or message.author.id in bot.get_banned_users()
        or message.guild.id in bot.get_banned_servers()
    ):
        return

    
    await bot.process_commands(message)

    if message.server.id in bot.get_servers():
        logging.info(f"[{message.guild.name}] {message.author.id} ({message.author.nick}): {message.content}")
        await bot.global_msg(message, others_only=True)
        await message.add_reaction("✅")


@bot.command(name="help")
async def help_command(ctx):
    """
    %help: Display this help message
    """
    
    message = "The Wormhole Bot allows you to communicate with other servers."
    
    for command in bot.bot_commands:
        message += f"\n{command.__doc__}"
    
    await ctx.send(message)

@bot.command(name="stats")
async def stats_command(ctx):
    """
    %stats: Display the bot's stats
    """
    n_servers =-len(bot.get_servers())
    n_users = sum([guild.member_count for guild in ctx.bot.guilds])
    
    await ctx.send(f"Connected to {n_servers} servers.\nTotal {n_users} users.")

@bot.command(name="connect")
async def connect_command(ctx):
    """
    %connect: Connect your server to the public.
    
    Do `%join` in the channel you want to connect. By default, all channels are not connected.
    """
    
    if ctx.author.administrator:
        config = await bot.get_config()
        
        # Check if the server is already connected
        if ctx.guild.id in config["servers"]:
            await ctx.send("This server is already connected.")
            return
        
        config["servers"].append(ctx.guild.id)
        if await write_config(config):
            await ctx.send("Connected to the public server.")
        else:
            await ctx.send("Error connecting to the public server. Please contact @JushBJJ")
    else:
        await ctx.send("You must be a server admin to use this command.")
    
@bot.command(name="disconnect")
async def disconnect_command(ctx):
    """
    %disconnect: Disconnect from the public server
    """
    
    if ctx.author.administrator:
        config = await bot.get_config()
        
        try:
            config["servers"].remove(ctx.guild.id)
        except ValueError:
            await ctx.send("This server is not connected.")
            return
        
        if await write_config(config):
            await ctx.send("Disconnected from the public server.")
        else:
            await ctx.send("Error disconnecting from the public server. Please contact @JushBJJ")
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
    %join: Join the public server. Automatically connects the server to the public server if not already connected.
    """
    
    if ctx.guild.id not in bot.get_servers():
        ctx.invoke(connect_command)
    
    config = await bot.get_config()
    channel_id = ctx.channel.id
    
    if channel_id in config["channels"]:
        await ctx.send("This channel is already connected.")
        return
    
    config["channels"].append(channel_id)
    if await write_config(config):
        await ctx.send("Connected to the public server.")
    else:
        await ctx.send("Error connecting channel. Please contact @JushBJJ")
        

@bot.command(name="leave")
async def leave_command(ctx):
    """
    %leave: Leave the public server. Does NOT disconnect the server from the public server.
    """
    
    config = await bot.get_config()
    channel_id = ctx.channel.id
    
    try:
        config["channels"].remove(channel_id)
    except ValueError:
        await ctx.send("This channel is not connected.")
        return
    
    if await write_config(config):
        await ctx.send("Disconnected from the public server.")
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
