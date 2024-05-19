import time
import discord

from bot.discord.bot import bot

@bot.event
async def on_guild_join(guild):
    channel = next(
        (c for c in guild.text_channels if guild.me.permissions_in(c).send_messages),
        None,
    )
    if channel:
        await channel.send(
            "Thanks for inviting me! To chat with other servers, say `%join <channel name>` in the channel you want to connect! For a full list of commands, say `%help`"
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
    channel_category = await bot.get_channel_category(message.channel.id)

    if (
        message.guild.id in await bot.get_servers()
        and str(message.channel.id) in allowed_channels
    ):
        msg = f"[DISCORD] {message.channel.name} ({message.guild.name}) -  {message.author.display_name} says:\n{message.content}"

        last_message_t = time.time()
        author_id = message.author.id
        no_header = False

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

        await bot.global_msg(message, msg, embed=embed, no_header=no_header)

        channel_config = await bot.get_allowed_channels(as_list=False)

        if (
            channel_config[channel_category]
            .get(str(message.channel.id), {})
            .get("react", False)
        ):
            await message.add_reaction("✅")
