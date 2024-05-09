import time
import discord
import asyncio
import redis.asyncio as aioredis
import json
import os
import re

from discord.ext import commands

from bot.utils.file import read_config, write_config
from bot.utils.logging import configure_logging
from dotenv import load_dotenv

load_dotenv()

ADMIN_ID = 0
WEBSITE_URL = "https://wormhole.jushbjj.com"
REPO = "https://github.com/JushBJJ/Wormhole"

intents = discord.Intents.all()


class WormholeBot(commands.Bot):
    def __init__(self, command_prefix, intents, debug=False):
        super().__init__(command_prefix, intents=intents)
        self.client_id = (
            os.getenv("client_id", "") if not debug else os.getenv("DEV_client_id", "")
        )
        self.client_secret = (
            os.getenv("client_secret", "")
            if not debug
            else os.getenv("DEV_client_secret", "")
        )
        self.token = os.getenv("token", "") if not debug else os.getenv("DEV_token", "")
        self.remove_command("help")

        self.bot_commands = []
        self.logger = configure_logging()

        self.default_channel_config_options = {"react": True}  # DEFAULT

        self.redis = aioredis.from_url("redis://localhost", decode_responses=True)
        self.last_message = [time.time(), 0]

    async def setup_hook(self):
        self.bg_task = asyncio.create_task(self.redis_subscriber())

    async def redis_subscriber(self):
        sub = self.redis.pubsub()
        await sub.subscribe("wormhole_channel")

        async for message in sub.listen():
            print(message)
            if message["type"] == "message":
                data = json.loads(message["data"])
                msg = data.get("message", "")
                await self.global_msg(None, msg, discord_only=True)

    def start_wormhole(self):
        self.logger.warning("Updating config...")
        config = asyncio.run(read_config())

        if not config:
            self.logger.error("Error updating config. Exiting...")
            return

        # Update Channels
        # TODO CLEAN???
        # TODO Add telegram config
        for channel_id in config.get("channels", []):
            # Add new configs
            for key, value in self.default_channel_config_options.items():
                if key not in config["channels"][channel_id]:
                    config["channels"][channel_id][key] = value

            # Remove old configs
            for key in config["channels"][channel_id].keys():
                if key not in self.default_channel_config_options:
                    del config["channels"][channel_id][key]

        asyncio.run(write_config(config))
        self.logger.warning("Starting Wormhole...")
        self.run(self.token)

    async def on_ready(self):
        await self.index_commands()
        print(f"Logged in as {self.user}")

    async def index_commands(self):
        self.bot_commands = [command for command in self.commands]

    async def filter_message(self, msg):
        # TODO LLM Filtering
        # TODO Make this optional for servers

        banned_words = await self.get_banned_words()
        for word in banned_words:
            msg = msg.replace(word, len(word) * "#")

        return msg

    async def global_msg(
        self, message, msg, embed=None, discord_only=False, no_header=False
    ):
        config = await self.get_config()
        guilds = list(self.guilds)

        bot.logger.info(msg)
        current_channel = 0 if message == None else message.channel.id

        # Cleaner
        if not no_header:
            header, msg = msg.split("\n", maxsplit=1)
            msg_discord = "```" + header + "```" + "\n" + msg
            msg_telegram = "<b>" + header + "</b>" + "\n" + msg
            msg_signal = header + "\n" + msg
        else:
            msg_discord = msg
            msg_telegram = msg
            msg_signal = msg

        links = re.findall(r"(https?://\S+)", msg)

        # Discord
        bot.logger.info(f"Embed: {embed}")

        if embed:
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url,
            )
        else:
            embed = discord.Embed(
                description=msg,
                color=0x000000,
            )
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url,
            )

            # Check if there are attachments
            if message.attachments:
                for attachment in message.attachments:
                    if attachment.url not in links:
                        links.append(attachment.url)

        for guild in guilds:
            if guild.id in config["banned_servers"]:
                continue
            elif guild.id in config["servers"]:
                for channel in guild.text_channels:
                    if (
                        str(channel.id) in list(config["channels"])
                        and channel.id != current_channel
                    ):
                        # filtered_msg = await self.filter_message(msg_discord)
                        await channel.send(embed=embed)
                        for link in links:
                            await channel.send(link)

        # Telegram
        if not discord_only:
            await self.redis.publish(
                "telegram_channel",
                json.dumps({"message": msg_telegram, "telegram_only": True}),
            )
            await self.redis.publish(
                "signal_channel",
                json.dumps({"message": msg_signal, "signal_only": True}),
            )

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

    async def get_allowed_channels(self, as_list=True):
        config = await read_config()

        if as_list:
            return list(config.get("channels", []))
        return config.get("channels", [])

    def is_itself(self, message):
        return message.author.id == self.user.id

    async def user_is_admin(self, ctx):
        is_manually_admin = ctx.author.id in await self.get_admins()
        is_admin = ctx.author.guild_permissions.administrator
        return is_admin or is_manually_admin


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

    allowed_channels = await bot.get_allowed_channels()

    if (
        message.guild.id in await bot.get_servers()
        and str(message.channel.id) in allowed_channels
    ):
        msg = f"[DISCORD] {message.channel.name} ({message.guild.name}) -  {message.author.display_name} says:\n{message.content}"

        last_message_t = time.time()
        author_id = message.author.id
        no_header = False

        # ik shit implementation but i got other projects to work on

        if (
            last_message_t - bot.last_message[0] < (1000 * 60)
            and author_id == bot.last_message[1]
        ):
            msg = message.content
            no_header = True
        else:
            bot.last_message = [last_message_t, author_id]

        embed = None

        if message.attachments:
            for attachment in message.attachments:
                msg += f"\n{attachment.url}" or ""

        if message.embeds:
            embed = discord.Embed.from_dict(message.embeds[0].to_dict())

        # TODO Add sticker support
        await bot.global_msg(message, msg, embed=embed, no_header=no_header)

        channel_config = await bot.get_allowed_channels(as_list=False)

        if channel_config.get(str(message.channel.id), {}).get("react", False):
            await message.add_reaction("✅")


@bot.command(name="help")
async def help_command(ctx):
    """
    %help: `Display this help message`
    """

    message = "The Wormhole Bot allows you to communicate with other servers."

    for command in bot.bot_commands:
        message += f"\n{command.help}"

    await ctx.send(message)


@bot.command(name="stats")
async def stats_command(ctx):
    """
    %stats: `Display the bot's stats`
    """
    n_servers = len(await bot.get_servers())
    n_users = sum([guild.member_count for guild in ctx.bot.guilds])

    await ctx.send(f"Connected to {n_servers} servers.\nTotal {n_users} users.")


@bot.command(name="connect")
async def connect_command(ctx):
    """
    %connect: `Connect your server to the public. Do \'%join' in the channel you want to connect. By default, all channels are not connected.`
    """

    if await bot.user_is_admin(ctx):
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
    %disconnect: `Disconnect your server`
    """

    if await bot.user_is_admin(ctx):
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
    %invite: `Invite this bot to your server`
    """

    await ctx.send(
        f"https://discord.com/oauth2/authorize?client_id={bot.client_id}&permissions=68608&scope=bot"
    )


@bot.command(name="website")
async def website_command(ctx):
    """
    %website: `Go to this bot's website`
    """

    await ctx.send(WEBSITE_URL)
    await ctx.send(REPO)


@bot.command(name="join")
async def join_command(ctx):
    """
    %join: `Join the server. Automatically connects the server to the server if not already connected.`
    """

    if ctx.guild.id not in await bot.get_servers():
        await ctx.invoke(connect_command)

    config = await bot.get_config()
    channel_id = str(ctx.channel.id)

    if channel_id in list(config["channels"]):
        await ctx.send("This channel is already connected.")
        return

    config["channels"][channel_id] = {}

    for key, value in bot.default_channel_config_options.items():
        config["channels"][channel_id][key] = value

    if await write_config(config):
        await ctx.send("Connected channel")
    else:
        await ctx.send("Error connecting channel. Please contact @JushBJJ")


@bot.command(name="leave")
async def leave_command(ctx):
    """
    %leave: `Stops recieving messages channel. Does NOT disconnect your server.`
    """

    config = await bot.get_config()
    channel_id = str(ctx.channel.id)

    try:
        config["channels"].pop(channel_id)
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
    %privacy: `View the privacy policy`
    """

    await ctx.send(
        "WE WILL STORE:\n"
        "- Connected server IDs\n"
        "- Connected channel IDs\n"
        "- Banned User IDs\n"
        "- Banned Server IDs\n"
        "WE DO NOT STORE:\n"
        "- Your messages\n"
        "- Your server name\n"
        "- Your channel name\n"
    )


@bot.command(name="ping")
async def ping_command(ctx):
    """
    %ping: `Check if the bot is online`
    """

    await ctx.send("Pong!")


# Admin-only commands
@bot.command(name="autoindex")
async def autoindex_old_channels_command(ctx):
    """
    %autoindex: `Automatically index all channels that has \"[CHANNEL: 1]\" in its topic for all guilds the bot is currently in.`
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
                    bot.logger.info(
                        f"{channel.name} in {guild.name} is already connected."
                    )
                    await ctx.send(
                        f"{channel.name} in {guild.name} is already connected."
                    )
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
                    await channel_class.send(
                        "You now have been migrated to the new Wormhole system.\nGithub: https://github.com/JushBJJ/Wormhole-DIscord-Bot"
                    )
                except Exception as e:
                    bot.logger.error(e)
                    await ctx.send(f"Error auto-connecting channels: {e}")

    bot.logger.info("Auto-indexing complete.")
    await ctx.send("Auto-indexing complete.")


@bot.command(name="broadcast")
async def broadcast_command(ctx):
    """
    %broadcast: `Broadcast a message to all connected servers`
    """

    if ctx.author.id not in await bot.get_admins():
        await ctx.send("You must be an admin to use this command.")
        return

    content = ctx.message.content.removeprefix("%broadcast ")
    msg = f"# BROADCAST by {ctx.author.display_name}\n{content}"

    await bot.global_msg(ctx.message, msg)


@bot.command(name="config")
async def config_command(ctx):
    """
    %config: `View the current config`
    """

    config = await bot.get_config()
    await ctx.send(f"```json\n{config}```")


@bot.command(name="set_config")
async def set_config_command(ctx, config_type: str, key: str, value: str):
    """
    %set_config: `Set a config value. Usage: %set_config [channel/server] [key] [value]`
    """

    if ctx.author.id not in await bot.get_admins():
        await ctx.send("You must be an admin to use this command.")
        return

    # Get args
    if config_type not in ["channel", "server"]:
        await ctx.send("Invalid config type. Must be either channel or server.")
        return

    if config_type == "channel":
        if key not in bot.default_channel_config_options:
            await ctx.send(f"Invalid key: {key}")
            await ctx.send(
                f"Valid keys: {', '.join(bot.default_channel_config_options.keys())}"
            )
            return

        value_type = type(bot.default_channel_config_options[key])

        if value_type == bool:
            try:
                value = True if value.lower() == "true" else False
            except ValueError:
                await ctx.send("Value must be a boolean.")
                return
        elif value_type == int:
            try:
                value = int(value)
            except ValueError:
                await ctx.send("Value must be an integer.")
                return
        elif value_type == str:
            value = str(value)
        else:
            await ctx.send("Invalid value type.")
            return

    elif config_type == "server":
        await ctx.send("Server configuration not implemented yet.")
        return
    else:
        await ctx.send("Invalid config type. uhh this shouldn't be executing...")
        return

    config = await bot.get_config()

    config["channels"][str(ctx.channel.id)][key] = value
    await write_config(config)
    await ctx.send(f"Set {key} to {value}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.send("Command not found. Say `%help` for a list of commands.")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing required argument. Say `%help` for a list of commands.")
    else:
        await ctx.send(f"An error occured: {error}")


if __name__ == "__main__":
    bot.start_wormhole()
