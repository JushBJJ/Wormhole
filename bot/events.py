import asyncio
import hashlib
import time
import discord
import json

from discord.ext import commands
from services.discord import DiscordBot

class EventHandlers(commands.Cog):
    def __init__(self, bot):
        self.bot: DiscordBot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info(f"Logged in as {self.bot.user.name}")
        await self.bot.change_presence(activity=discord.Game(name="with kawa ^_^"))
        await self.send_startup_message()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if message.webhook_id in self.bot.webhooks:
            return

        user_id = str(message.author.id)
        channel_id = str(message.channel.id)
        message_hash = hashlib.sha256((message.content + user_id + channel_id).encode()).hexdigest()

        if await self.bot.config.is_user_banned(user_id):
            return
        
        # TODO Turn this into 2 lines
        # await self.bot.bot.config.can_send_message(message.author.id)
        user = await self.bot.config.get_user(user_id)
        if not user['can_send_message']:
            return

        if await self.bot.config.get_channel_by_id(channel_id):
            channel_config = await self.bot.config.get_channel_by_id(channel_id)
            await self.handle_config_pre(channel_config, message)

            tasks = list()
            reply_messages = []
            display_name = message.author.display_name
            avatar = message.author.display_avatar.url
            content = message.content
            user_hash = await self.bot.config.get_user_hash(user_id)
            message_reference = message.reference
            channel_category = channel_config["channel_category"]

            embed = await self.bot.pretty_message.to_embed(user_id, display_name, avatar, content)
            attachments = self.bot.pretty_message.to_attachments_message(message.attachments)
            embeds = self.bot.pretty_message.embeds_to_links(message.embeds)
            mentions = self.bot.pretty_message.format_mentions(message.raw_mentions)
            stickers_to_send, sticker_content = await self.bot.pretty_message.handle_stickers(message)

            self.bot.pretty_message.create_rich_message_box(display_name, content, attachments, user_hash)
            await self.bot.config.update_user_avatar(user_id, avatar)
            await self.bot.config.add_username(user_id, display_name)
            channels = await self.bot.config.get_all_channels_in_category_by_id(channel_id)

            if message_reference:
                reply_content = message_reference.resolved.content
                reply_content = reply_content.replace("\n", "\n> ")
                content = f"> {reply_content}\n{content}"
            
            # Check if own channel can manage webhooks
            permissions = message.channel.permissions_for(message.guild.me)
            if not permissions.manage_webhooks:
                await message.channel.send(
                    f":warning: I need the 'Manage Webhooks' permission in this server to send/receive wormhole messages."
                )
                return

            for channel_id in channels:
                if int(channel_id) == message.channel.id:
                    continue
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    permissions = channel.permissions_for(channel.guild.me)
                    if permissions.manage_webhooks:
                        webhooks = await channel.webhooks()
                        webhook = discord.utils.get(webhooks, name="WormholeWebhook")
                        webhook = webhook or await channel.create_webhook(name="WormholeWebhook")
                        if webhook.id not in self.bot.webhooks:
                            self.bot.webhooks.append(webhook.id)
                        content_to_send = content + attachments + sticker_content if attachments or sticker_content or mentions else content
                        tasks.append(webhook.send(
                            content=content_to_send,
                            username=display_name + f" ({user_hash[:6]})",
                            avatar_url=avatar,
                            embeds=message.embeds if message.embeds and message.author.bot else [],
                            allowed_mentions=discord.AllowedMentions(everyone=False)
                        ))
                    else:
                        # Send message if bot can't create webhooks
                        tasks.append(channel.send(
                            f":warning: I need the 'Manage Webhooks' permission in this server to send/receive wormhole messages."
                        ))

            real_messages = []
            messages = await asyncio.gather(*tasks, return_exceptions=True)
            content = content + attachments + sticker_content
            await self.bot.redis_publish(display_name, user_hash, content, embeds, stickers_to_send, channel_category)
            for result in messages:
                if isinstance(result, discord.Message):
                    real_messages.append(result)
                elif isinstance(result, Exception):
                    # URL('https://discord.com/api/v10/channels/<channel_id>/messages')
                    if result.status == 403: # Forbidden
                        await self.bot.config.remove_channel(result.response.url.parts[4])
            message_links = [message.jump_url for message in real_messages]
            await self.bot.config.append_link(message_hash, message_links)
            await self.handle_config_post(channel_config, message)

            if channel_category == "wormhole":
                await self.bot.redis_publish(display_name, user_hash, content, embeds, stickers_to_send, channel_category)

            if self.bot.irc_client and self.bot.irc_client.connection.is_connected():
                header = self.bot.format_irc_header(display_name, user_hash)
                await self.bot.send_irc_message_parts(
                    self.bot.irc_client.connection,
                    channel_category,
                    header,
                    content,
                    message.attachments,
                    sticker_content
                )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send("""Hello! I'm Wormhole, a bot that allows you to connect channels across servers.
                                   
                                    Make sure you have set the correct permissions for me to work properly in specific channels.
                                    To see a list of channels availble to join, use the `%list` command.
                                    To join a channel, use the `%join <channelName>` command.
                                    To leave a channel, use the `%leave` command.
                                   
                                    As a start, try `%join wormhole` to join the default wormhole channel.
                                    :warning: MAKE SURE TO SET PERMISSIONS TO MANAGE WEBHOOKS IN THE SERVER TO SEND/RECIEVE FOR WORMHOLE TO WORK.
                                   
                                    There are some commands that only wormhole admins (not server admins) can use like adding new channels and moderation.
                                    Have fun!
                                   """)
                break

    async def send_startup_message(self):
        channels = await self.bot.config.get_all_channels()
        for channel in channels:
            self.bot.logger.info(f"Loaded Channel: {channel['channel_name']}")
        self.bot.logger.info("Bot is ready!")
    
    async def handle_config_pre(self, channel_config: dict, message: discord.Message):
        if channel_config["react"]:
            await message.add_reaction('⏳')
    
    async def handle_config_post(self, channel_config: dict, message: discord.Message):
        if channel_config["react"]:
            await message.add_reaction('✅')
            await message.remove_reaction('⏳', self.bot.user)

async def setup(bot):
    await bot.add_cog(EventHandlers(bot))