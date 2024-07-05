import asyncio
from typing import List, Union, Optional
import discord
from discord.ext import commands
from bot.config import ChannelConfig, WormholeConfig

def is_wormhole_admin():
    async def predicate(ctx):
        try:
            if not ctx.guild:
                return False

            config: WormholeConfig = ctx.bot.config
            user_id: str = str(ctx.author.id)

            if config.get_user_role(user_id) == "admin":
                return True

            await ctx.send("You must be a Wormhole admin to run this command.")
            return False
        except Exception as e:
            print(f"Error in is_wormhole_admin check: {e}")
            return False

    return commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config: WormholeConfig = bot.config

    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def add_channel(self, ctx, channel_name: str, **kwargs):
        """Add a new channel to the Wormhole network"""
        if channel_name not in self.config.channel_list:
            self.config.channel_list.append(channel_name)
            self.config.channels[channel_name] = {str(ctx.channel.id): ChannelConfig()}
            await ctx.send(f"Added channel {channel_name}")
        else:
            await ctx.send(f"Channel {channel_name} already exists")

    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def remove_channel(self, ctx, channel_name: str, **kwargs):
        """Remove a channel from the Wormhole network"""
        if channel_name in self.config.channel_list:
            self.config.channel_list.remove(channel_name)
            del self.config.channels[channel_name]
            await ctx.send(f"Removed channel {channel_name}")
        else:
            await ctx.send(f"Channel {channel_name} does not exist")

    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def ban_user(self, ctx, user_id_or_hash: Union[int, str] = None, **kwargs):
        """Ban a user from using the Wormhole bot"""
        try:
            user_id_or_hash = int(user_id_or_hash)
        except ValueError:
            user_hash = self.config.get_user_hash(user_id_or_hash)
            if user_hash not in self.config.banned_users:
                self.config.banned_users.append(user_hash)
                await ctx.send(f"Banned user `{user_hash}`")
            else:
                await ctx.send(f"User `{user_hash}` is already banned")

    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def unban_user(self, ctx, user_id_or_hash: Union[int, str] = None, **kwargs):
        """Unban a user from using the Wormhole bot"""
        try:
            user_id_or_hash = int(user_id_or_hash)
        except ValueError:
            pass
        finally:
            user_hash = self.config.get_user_hash(user_id_or_hash)
            if user_hash in self.config.banned_users:
                self.config.banned_users.remove(user_hash)
                await ctx.send(f"Unbanned user `{user_hash}`")
            else:
                await ctx.send(f"User `{user_hash}` is not banned")

    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def admin(self, ctx, user_id_or_hash: Union[int, str] = None, **kwargs):
        """Add a new admin to the wormhole bot"""
        user_hash = self.config.get_user_hash(user_id_or_hash)
        user = self.config.get_user_config_by_hash(user_hash)
        if user.role != "admin":
            self.config.change_user_role(user_hash, "admin")
            await ctx.send(f"{user_hash} is now a Wormhole Admin")
        else:
            await ctx.send(f"{user_hash} is already a Wormhole Admin")

    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def unadmin(self, ctx, user_id_or_hash: Union[int, str] = None, **kwargs):
        """Remove admin status from a user"""
        user_hash = self.config.get_user_hash(user_id_or_hash)
        user = self.config.get_user_config_by_hash(user_hash)
        if user.role != "user":
            self.config.change_user_role(user_hash, "user")
            await ctx.send(f"{user_hash} is no longer a Wormhole Admin")
        else:
            await ctx.send(f"{user_hash} is already a Wormhole User")

    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def broadcast(self, ctx, channel_name: str, *, message: str):
        """Broadcast a message to all channels concurrently"""
        if channel_name not in self.config.channel_list:
            await ctx.send(f"Channel {channel_name} does not exist")
            return
        
        embed = discord.Embed(
            title="Broadcast",
            description=message,
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

        async def send_to_channel(channel_id):
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                await channel.send(embed=embed)

        tasks = [send_to_channel(channel_id) for channel_id in self.config.channels[channel_name]]
        await asyncio.gather(*tasks)
    
    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def raw_broadcast(self, ctx, channel_name: str, *, message: str):
        """Broadcast a message to a specific channel"""
        if channel_name not in self.config.channel_list:
            await ctx.send(f"Channel {channel_name} does not exist")
            return
        
        async def send_to_channel(channel_id):
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                await channel.send(message)
        
        tasks = [send_to_channel(channel_id) for channel_id in self.config.channels[channel_name]]
        await asyncio.gather(*tasks)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))