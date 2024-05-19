from discord.ext import commands
from bot.discord.bot import bot

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

@bot.command(name="mute")
async def ban_command(ctx, user_id: int):
    """
    %mute <user_id>: `Mute a user from channel`
    """
    if await bot.user_is_admin(ctx):
        config = await bot.get_config()
        category = await bot.get_channel_category(ctx.channel.id)
        channel_id = str(ctx.channel.id)
        if user_id in config["channels"][category][channel_id]["muted_users"]:
            await ctx.send("User is already muted.")
            return
        current_channel = ctx.channel.id
        category = await bot.get_channel_category(current_channel)
        config["channels"][category][str(current_channel)]["muted_users"].append(user_id)
        if await write_config(config):
            await ctx.send(f"Muted user {user_id}")
        else:
            await ctx.send("Error muting user.")
    else:
        await ctx.send("You must be a server admin to use this command.")

@bot.command(name="unmute")
async def unmute_command(ctx, user_id: int):
    """
    %unmute <user_id>: `Unmute a user from channel`
    """
    if await bot.user_is_admin(ctx):
        config = await bot.get_config()
        category = await bot.get_channel_category(ctx.channel.id)
        channel_id = str(ctx.channel.id)
        if user_id not in config["channels"][category][channel_id]["muted_users"]:
            await ctx.send("User is not muted.")
            return
        current_channel = ctx.channel.id
        category = await bot.get_channel_category(current_channel)
        config["channels"][category][str(current_channel)]["muted_users"].remove(user_id)
        if await write_config(config):
            await ctx.send(f"Unmuted user {user_id}")
        else:
            await ctx.send("Error unmuting user.")
    else:
        await ctx.send("You must be a server admin to use this command.")

@bot.command(name="connect")
async def connect_command(ctx):
    """
    %connect: `Connect your server to the public. Do '%join' in the channel you want to connect. By default, all channels are not connected.`
    """
    if await bot.user_is_admin(ctx):
        config = await bot.get_config()
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

@bot.command(name="tox-add")
async def tox_add_command(ctx, tox_id: str):
    """
    %tox-add <tox_id>: `Add tox id to local node.`
    """
    if await bot.user_is_admin(ctx):
        await bot.redis.publish("tox_node", "COMMAND: ADD " + tox_id)
    else:
        await ctx.send("You must be a server admin to use this command.")

@bot.command(name="tox-list")
async def tox_list_command(ctx):
    """
    %tox-list: `List all tox IDs in the local node.`
    """
    if await bot.user_is_admin(ctx):
        await bot.redis.publish("tox_node", "COMMAND: LIST")
    else:
        await ctx.send("You must be a server admin to use this command.")

@bot.command(name="tox-id")
async def tox_id_command(ctx):
    """
    %tox-id: `Get the tox id of the node the discord bot is connected to`
    """
    await bot.redis.publish("tox_node", "COMMAND: ID")

@bot.command(name="invite")
async def invite_command(ctx):
    """
    %invite: `Invite this bot to your server`
    """
    await ctx.send(f"https://discord.com/oauth2/authorize?client_id={bot.client_id}&permissions=68608&scope=bot")

@bot.command(name="website")
async def website_command(ctx):
    """
    %website: `Go to this bot's website`
    """
    await ctx.send(WEBSITE_URL)
    await ctx.send(REPO)

@bot.command(name="join")
async def join_command(ctx, channel_name: str = "wormhole"):
    """
    %join <channel name>: `Join the server. Automatically connects the server to the server if not already connected.`
    """
    if ctx.guild.id not in await bot.get_servers():
        await ctx.invoke(connect_command)
    config = await bot.get_config()
    channel_id = str(ctx.channel.id)
    channel_name = channel_name.lower()
    if not channel_name in config["channel_list"]:
        channel_list = ", ".join(config["channel_list"])
        await ctx.send(
            f'Invalid channel name. If you need want to add a new channel you to add them into the "channel_list" list in the config.json file.\nCant access the config file? Contact the bot owner.\n\nValid channel names: {channel_list}'
        )
        return
    elif channel_id in list(config["channels"].get(channel_name, [])):
        await ctx.send("This channel is already connected.")
        return
    elif channel_name not in config["channels"]:
        config["channels"][channel_name] = {}
    config["channels"][channel_name][channel_id] = {}
    for key, value in bot.default_channel_config_options.items():
        if key == "react" and channel_name == "wormhole":
            config["channels"][channel_name][channel_id][key] = True
            continue
        config["channels"][channel_name][channel_id][key] = value
    if await write_config(config):
        await ctx.send(f"Connected to channel `{channel_name}`")
        return
    await ctx.send(
        "Error connecting channel, failed to write into config file. Please try again. If persists, please contact @JushBJJ"
    )

@bot.command(name="leave")
async def leave_command(ctx):
    """
    %leave: `Stops recieving messages channel. Does NOT disconnect your server.`
    """
    config = await bot.get_config()
    channel_id = str(ctx.channel.id)
    channel_list = list(config["channel_list"])
    for channel in channel_list:
        if channel_id in list(config["channels"].get(channel, [])):
            config["channels"][channel].pop(channel_id)
            await write_config(config)
            await ctx.send(
                f"Left channel `{channel}`. If you want the server to be disconnected, say `%disconnect`"
            )
            return
    await ctx.send("Error disconnecting channel. Please contact @JushBJJ")

@bot.command(name="channels")
async def channels_command(ctx):
    """
    %channels: `View all available channels to connect`
    """
    config = await bot.get_config()
    channels = config["channel_list"]
    message = "Available channels:\n"
    for channel in channels:
        message += f"{channel}\n"
    await ctx.send(message)

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
