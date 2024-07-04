import asyncio
import discord
import json

from discord.ext import commands

class EventHandlers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info(f"Logged in as {self.bot.user.name}")
        await self.bot.change_presence(activity=discord.Game(name="with kawa ^_^"))
        await self.send_startup_message()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if self.bot.user_management.is_user_banned(message.author.id):
            return
        
        if self.bot.config.get_user_config_by_id(message.author.id).can_send_message == False:
            return

        if str(message.channel.id) in self.bot.config.get_all_channel_ids():
            channel_config = self.bot.config.get_channel_by_id(message.channel.id)
            await channel_config.handle_config_pre(message, self.bot)

            tox_message = json.dumps({
                "message": f"{message.author.name}: {message.content}",
                "from_discord": True
            })
            self.bot.redis_client.publish('tox_node', tox_message)

            tasks = set()
            user_id = message.author.id
            display_name = message.author.display_name
            avatar = message.author.display_avatar.url
            content = message.content
            user_hash = self.bot.config.get_user_hash(user_id)

            embed = self.bot.pretty_message.to_embed(user_id, display_name, avatar, content)
            attachments = self.bot.pretty_message.to_attachments_message(message.attachments)
            embeds = self.bot.pretty_message.embeds_to_links(message.embeds)
            stickers_to_send, sticker_content = await self.bot.pretty_message.handle_stickers(message)

            self.bot.pretty_message.create_rich_message_box(display_name, content, attachments, user_hash)
            self.bot.config.users[str(user_id)].profile_picture = avatar
            self.bot.config.add_username(user_id, display_name)

            for channel_id in self.bot.config.get_all_channels_by_id(message.channel.id):
                if int(channel_id) == message.channel.id:
                    continue
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    if stickers_to_send:
                        tasks.add(channel.send(embed=embed, stickers=stickers_to_send))
                    else:
                        tasks.add(channel.send(embed=embed))
                        if attachments:
                            tasks.add(channel.send(content=attachments))
                        if message.embeds:
                            tasks.add(channel.send(embed=message.embeds[0]))
                        if embeds:
                            tasks.add(channel.send(content=embeds))
                        if sticker_content:
                            tasks.add(channel.send(content=sticker_content))
            await asyncio.gather(*tasks)
            await channel_config.handle_config_post(message, self.bot)

    async def send_startup_message(self):
        for channel_name, channel_id in self.bot.config.channels.items():
            print("Loaded Channel: ", channel_name)
            if channel_name == "wormhole":
                for _id in channel_id.keys():
                    channel = self.bot.get_channel(int(_id))
                    if channel:
                        continue
                        #await channel.send("Wormhole is now online!")
                        # Else, remove channel???

async def setup(bot):
    await bot.add_cog(EventHandlers(bot))