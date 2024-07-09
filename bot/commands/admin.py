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
            return False

    return commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config: WormholeConfig = bot.config

    @commands.group(case_insensitive=True)
    @is_wormhole_admin()
    async def channel(self, ctx):
        """Channel management commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid channel command. Use `help channel` for more information.")

    @channel.command(name="add")
    async def add_channel(self, ctx, channel_name: str):
        """Add a new channel to the Wormhole network"""
        if channel_name not in self.config.channel_list:
            self.config.channel_list.append(channel_name)
            self.config.channels[channel_name] = {str(ctx.channel.id): ChannelConfig()}
            await ctx.send(f"Added channel {channel_name}")
        else:
            await ctx.send(f"Channel {channel_name} already exists")

    @channel.command(name="remove")
    async def remove_channel(self, ctx, channel_name: str):
        """Remove a channel from the Wormhole network"""
        if channel_name in self.config.channel_list:
            self.config.channel_list.remove(channel_name)
            del self.config.channels[channel_name]
            await ctx.send(f"Removed channel {channel_name}")
        else:
            await ctx.send(f"Channel {channel_name} does not exist")

    @commands.group(case_insensitive=True)
    @is_wormhole_admin()
    async def admin(self, ctx):
        """Admin management commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid admin command. Use `help admin` for more information.")

    @admin.command(name="ban")
    async def ban_user(self, ctx, user_id_or_hash: Union[int, str] = None):
        """Ban a user from using the Wormhole bot"""
        user_hash = self.config.get_user_hash(user_id_or_hash)
        if user_hash not in self.config.banned_users:
            self.config.banned_users.append(user_hash)
            await ctx.send(f"Banned user `{user_hash}`")
        else:
            await ctx.send(f"User `{user_hash}` is already banned")

    @admin.command(name="unban")
    async def unban_user(self, ctx, user_id_or_hash: Union[int, str] = None):
        """Unban a user from using the Wormhole bot"""
        user_hash = self.config.get_user_hash(user_id_or_hash)
        if user_hash in self.config.banned_users:
            self.config.banned_users.remove(user_hash)
            await ctx.send(f"Unbanned user `{user_hash}`")
        else:
            await ctx.send(f"User `{user_hash}` is not banned")

    @admin.command(name="admin")
    async def make_admin(self, ctx, user_id_or_hash: Union[int, str] = None):
        """Add a new admin to the wormhole bot"""
        user_hash = self.config.get_user_hash(user_id_or_hash)
        user = self.config.get_user_config_by_hash(user_hash)
        if user.role != "admin":
            self.config.change_user_role(user_hash, "admin")
            await ctx.send(f"{user_hash} is now a Wormhole Admin")
        else:
            await ctx.send(f"{user_hash} is already a Wormhole Admin")

    @admin.command(name="unadmin")
    async def remove_admin(self, ctx, user_id_or_hash: Union[int, str] = None):
        """Remove admin status from a user"""
        user_hash = self.config.get_user_hash(user_id_or_hash)
        user = self.config.get_user_config_by_hash(user_hash)
        if user.role != "user":
            self.config.change_user_role(user_hash, "user")
            await ctx.send(f"{user_hash} is no longer a Wormhole Admin")
        else:
            await ctx.send(f"{user_hash} is already a Wormhole User")

    @admin.command(name="reset_penalty")
    async def reset_user_penalty(self, ctx, user_id_or_hash: Union[int, str] = None):
        """Reset the user's penalty"""
        if user_id_or_hash is None:
            user_id_or_hash = ctx.author.id
        elif not user_id_or_hash.isdigit() and len(user_id_or_hash)==64:
            user_id_or_hash = self.config.get_user_id_by_hash(user_id_or_hash)
        else:
            await ctx.send("Invalid user ID or hash")
            return
        self.config.reset_user_penalty(user_id_or_hash)
        await ctx.send("User penalty reset")

    @commands.group(case_insensitive=True)
    @is_wormhole_admin()
    async def broadcast(self, ctx):
        """Broadcast message commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid broadcast command. Use `help broadcast` for more information.")

    @broadcast.command(name="embed")
    async def broadcast_embed(self, ctx, channel_name: str, *, message: str):
        """Broadcast a message to all channels concurrently with embed"""
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

    @broadcast.command(name="raw")
    async def broadcast_raw(self, ctx, channel_name: str, *, message: str):
        """Broadcast a raw message to a specific channel"""
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