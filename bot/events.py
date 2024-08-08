import asyncio
import hashlib
import time
import discord
import json

from discord.ext import commands
from bot.features.LLM.ollama import moderate_channel
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
        
        async def wait_for_hash():
            for _ in range(60):
                message_hash = self.bot.message_hashes.get(message.id, None)
                if message_hash is not None:
                    return message_hash
                await asyncio.sleep(0.5)
            return ""

        message_hash = await wait_for_hash()
        user_id = str(message.author.id)
        channel_id = str(message.channel.id)

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
                original_message_link = message_reference.jump_url
                hashed_original_message = await self.bot.config.get_message_hash_by_link(original_message_link)
                if hashed_original_message:
                    reply_message_links = await self.bot.config.get_message_links(hashed_original_message)
                    for link in reply_message_links:
                        try:
                            channel_id, message_id = self.bot.config.parse_message_link(link)
                            channel = self.bot.get_channel(int(channel_id))
                            if channel:
                                reply_message = await channel.fetch_message(int(message_id))
                                reply_messages.append(reply_message)
                        except:
                            pass

            for channel_id in channels:
                if int(channel_id) == message.channel.id:
                    continue
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    reply_to = next((msg for msg in reply_messages if msg.channel == channel), None)
                    send_kwargs = {
                        'embed': embed, 
                        "reference": reply_to, 
                    }
                    tasks.append(channel.send(**send_kwargs))
                    # Send another but for stickers and content
                    send_kwargs_2 = {
                        "stickers": stickers_to_send,
                        "content": attachments + sticker_content + mentions if attachments or sticker_content or mentions else None
                    }
                    tasks.append(channel.send(**send_kwargs_2))
                    if message.embeds and not (attachments or embeds):
                        tasks.append(channel.send(embed=message.embeds[0]))
                    if embeds:
                        tasks.append(channel.send(content=embeds))

            real_messages = []
            # Split the success and error message
            messages = await asyncio.gather(*tasks, return_exceptions=True)
            for result in messages:
                if isinstance(result, discord.Message):
                    real_messages.append(result)
                elif isinstance(result, Exception):
                    # URL('https://discord.com/api/v10/channels/<channel_id>/messages')
                    if result.status == 403: # Forbidden
                        self.bot.logger.error(f"Error sending message to channel: {result.response.url.parts[4]}. Removing...")
                        await self.bot.config.remove_channel(result.response.url.parts[4])
                    else:
                        self.bot.logger.error(f"Error sending message: {result}")
            message_links = [message.jump_url for message in real_messages]
            await self.bot.config.append_link(message_hash, message_links)
            await self.handle_config_post(channel_config, message)
            
            # Handle temporary message and LLM moderation
            channel_category = channel_config["channel_category"]
            self.bot.last_messages[channel_category].add((message.content, user_hash, time.time()))
            #await moderate_channel(self.bot, message, self.bot.last_messages,)

    async def send_startup_message(self):
        channels = await self.bot.config.get_all_channels()
        for channel in channels:
            self.bot.logger.info(f"Loaded Channel: {channel['channel_name']}")
    
    async def handle_config_pre(self, channel_config: dict, message: discord.Message):
        if channel_config["react"]:
            await message.add_reaction('⏳')
    
    async def handle_config_post(self, channel_config: dict, message: discord.Message):
        if channel_config["react"]:
            await message.add_reaction('✅')
            await message.remove_reaction('⏳', self.bot.user)

async def setup(bot):
    await bot.add_cog(EventHandlers(bot))