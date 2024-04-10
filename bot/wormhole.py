import discord
import logging
import os

from discord.ext import commands
from bot.utils.file import read_config, write_config
from colorlog import ColoredFormatter
from dotenv import load_dotenv

load_dotenv()

ADMIN_ID = 0
WEBSITE_URL = "https://wormhole.jushbjj.com"
REPO = "https://github.com/JushBJJ/Wormhole-DIscord-Bot"

intents = discord.Intents.all()


class WormholeBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix, intents=intents)
        self.client_id = os.getenv("client_id", "")
        self.client_secret = os.getenv("client_secret", "")
        self.token = os.getenv("token", "")
        self.remove_command("help")
        
        self.bot_commands = []
        self.logger = self.configure_logging()

    def start_wormhole(self):
        self.logger.warning("Starting Wormhole...")
        self.run(self.token)
        
    def configure_logging(self):
        # Create a custom logger
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Create handlers
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler('wormhole.log')
        c_handler.setLevel(logging.INFO)
        f_handler.setLevel(logging.INFO)
        
        # Create formatters and add it to handlers
        # Using colorlog for console handler
        c_format = ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s',
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )
        # Standard formatter for file handler
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)
        
        # Add handlers to the logger
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)
        
        return logger
    

    async def on_ready(self):
        await self.index_commands()
        logging.info(f"Logged in as {self.user}")
        
    async def index_commands(self):
        self.bot_commands = [command for command in self.commands]
        
    async def filter_message(self, msg):
        # TODO LLM Filtering
        # TODO Make this optional for servers
        
        banned_words = await self.get_banned_words()
        for word in banned_words:
            msg = msg.replace(word, len(word) * "#")

        return msg

    async def global_msg(self, message, msg):
        config = await self.get_config()
        guilds = list(self.guilds)
        
        for guild in guilds:
            if guild.id in config["banned_servers"]:
                continue
            elif guild.id in config["servers"]:
                for channel in guild.text_channels:
                    if channel.id in config["channels"] and channel.id != message.channel.id:
                        filtered_msg = await self.filter_message(msg)
                        await channel.send(filtered_msg)
    
    async def get_config(self):
        return await read_config()
    
    async def get_banned_words(self):
        config = await read_config()
        return config.get("banned_words", [])

    async def get_banned_users(self):
        config = await read_config()
        return config.get("banned_users", [])

    async def get_banned_servers(self):
        config = await read_config()
        return config.get("banned_servers", [])

    async def get_servers(self):
        config = await read_config()
        return config.get("servers", [])
    
    async def get_admins(self):
        config = await read_config()
        return config.get("admins", [])

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
        or not message.guild
    ):
        return

    await bot.index_commands()
    await bot.process_commands(message)
    
    if message.content.startswith(bot.command_prefix):
        return

    if message.guild.id in await bot.get_servers():
        msg = f"```{message.channel.name} ({message.guild.name}) (ID: {message.author.id}) - {message.author.display_name} says:```{message.content}"
        
        if message.attachments:
            for attachment in message.attachments:
                msg += f"\n{attachment.url}" or ""
                
        bot.logger.info(msg)
        await bot.global_msg(message, msg)
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
            bot.logger.info(f"Connected to {ctx.guild.name}")
            await ctx.send("Connected server")
        else:
            bot.logger.error(f"Error connecting to {ctx.guild.name}")
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
            bot.logger.info(f"Disconnected from {ctx.guild.name}")
            await ctx.send("Disconnected your server.")
        else:
            bot.logger.error(f"Error disconnecting from {ctx.guild.name}")
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
    await ctx.send(REPO)
    
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

# Admin-only commands
@bot.command(name="autoindex")
async def autoindex_old_channels_command(ctx):
    """
    %autoindex: Automatically index all channels that has \"[CHANNEL: 1]\" in its topic for all guilds the bot is currently in.
    """

    if ctx.author.id not in await bot.get_admins():
        await ctx.send("You must be an admin to use this command.")
        return
    
    for guild in bot.guilds:
        bot.logger.info(f"Auto-indexing {guild.name}")
        for channel in guild.text_channels:
            topic = channel.topic or ""
            bot.logger.info(f"Topic: {topic}")
            
            if "channel:1" in topic.lower():
                config = await bot.get_config()
                
                # Check first if channel and server is already connected
                if channel.id in config["channels"] and guild.id in config["servers"]:
                    bot.logger.info(f"{channel.name} in {guild.name} is already connected.")
                    await ctx.send(f"{channel.name} in {guild.name} is already connected.")
                    continue
                
                config["channels"].append(channel.id)
                config["servers"].append(guild.id)
                
                try:
                    msg = f"Auto-connected {channel.name} in {guild.name}"
                    await write_config(config)
                    
                    bot.logger.info(msg)
                    await ctx.send(msg)
                    
                    # Broadcast to new channel
                    channel_class = bot.get_channel(channel.id)
                    await channel_class.send("You now have been migrated to the new Wormhole system.\nGithub: https://github.com/JushBJJ/Wormhole-DIscord-Bot")
                except Exception as e:
                    bot.logger.error(e)
                    await ctx.send(f"Error auto-connecting channels: {e}")

    bot.logger.info("Auto-indexing complete.")
    await ctx.send("Auto-indexing complete.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.send("Command not found. Say `%help` for a list of commands.")
    else:
        await ctx.send(f"An error occured: {error}")

if __name__ == "__main__":
    bot.start_wormhole()
