import asyncio
from typing import List, Union, Optional
import discord
from discord.ext import commands
from bot.config import WormholeConfig

def is_wormhole_admin():
    async def predicate(ctx):
        try:
            if not ctx.guild:
                return False

            config: WormholeConfig = ctx.bot.config
            user_id: str = str(ctx.author.id)

            if await config.get_user_role(user_id) == "admin":
                return True

            await ctx.send("You must be a Wormhole admin to run this command.")
            return False
        except Exception as e:
            return False

    return commands.check(predicate)

def user_exists_check():
    async def predicate(cog: commands.Cog, ctx, user_id_or_hash: Union[int, str] = None):
        if user_id_or_hash is None:
            await ctx.send("Please provide a user ID or hash.")
            return False

        user_exists = await cog.config.user_exists(user_id_or_hash)
        
        if not user_exists:
            await ctx.send(f"User `{user_id_or_hash}` does not exist.")
            return False
        return True
    
    return commands.check(lambda ctx: predicate(ctx.cog, ctx, ctx.args[2] if len(ctx.args) > 2 else None))


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
        if await self.config.category_exists(channel_name):
            await self.config.add_channel_to_list(channel_name)
            await ctx.send(f"Added channel {channel_name}")
        else:
            await ctx.send(f"Channel {channel_name} already exists")

    @channel.command(name="remove")
    async def remove_channel(self, ctx, channel_name: str):
        """Remove a channel from the Wormhole network"""
        if await self.config.category_exists(channel_name):
            await self.config.remove_channel_from_list(channel_name)
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
    @user_exists_check()
    async def ban_user(self, ctx, user_id_or_hash: Union[int, str] = None):
        """Ban a user from using the Wormhole bot"""
        if await self.config.is_user_banned(user_id_or_hash):
            await self.config.ban_user(user_id_or_hash)
            await ctx.send(f"Banned user `{user_id_or_hash}`")
        else:
            await ctx.send(f"User `{user_id_or_hash}` is already banned")

    @admin.command(name="unban")
    @user_exists_check()
    async def unban_user(self, ctx, user_id_or_hash: Union[int, str] = None):
        """Unban a user from using the Wormhole bot"""
        if await self.config.is_user_banned(user_id_or_hash):
            await self.config.unban_user(user_id_or_hash)
            await ctx.send(f"Unbanned user `{user_id_or_hash}`")
        else:
            await ctx.send(f"User `{user_id_or_hash}` is not banned")

    @admin.command(name="admin")
    @user_exists_check()
    async def make_admin(self, ctx, user_id_or_hash: Union[int, str] = None):
        """Add a new admin to the wormhole bot"""
        if await self.config.get_user_role(user_id_or_hash) != "admin":
            await self.config.change_user_role(user_id_or_hash, "admin")
            await ctx.send(f"{user_id_or_hash} is now a Wormhole Admin")
        else:
            await ctx.send(f"{user_id_or_hash} is already a Wormhole Admin")

    @admin.command(name="unadmin")
    @user_exists_check()
    async def remove_admin(self, ctx, user_id_or_hash: Union[int, str] = None):
        """Remove admin status from a user"""
        if await self.config.get_user_role(user_id_or_hash) == "admin":
            await self.config.change_user_role(user_id_or_hash, "user")
            await ctx.send(f"{user_id_or_hash} is no longer a Wormhole Admin")
        else:
            await ctx.send(f"{user_id_or_hash} is already a Wormhole User")

    @admin.command(name="reset_penalty")
    @user_exists_check()
    async def reset_user_penalty(self, ctx, user_id_or_hash: Union[int, str] = None):
        """Reset the user's penalty"""
        await self.config.reset_user_penalty(user_id_or_hash)
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
        if not await self.config.category_exists(channel_name):
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
        if not await self.config.category_exists(channel_name):
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