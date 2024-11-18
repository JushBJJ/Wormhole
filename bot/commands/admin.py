import asyncio
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


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config: WormholeConfig = bot.config

    @commands.command(name="add")
    @is_wormhole_admin()
    async def add_channel(self, ctx, channelName: str):
        """Add a new channel to the Wormhole network"""
        if await self.config.category_exists(channelName):
            await self.config.add_channel_to_list(channelName)
            await ctx.send(f"Added channel {channelName}")
        else:
            await ctx.send(f"Channel {channelName} already exists")

    @commands.command(name="remove")
    @is_wormhole_admin()
    async def remove_channel(self, ctx, channelName: str):
        """Remove a channel from the Wormhole network"""
        if await self.config.category_exists(channelName):
            await self.config.remove_channel_from_list(channelName)
            await ctx.send(f"Removed channel {channelName}")
        else:
            await ctx.send(f"Channel {channelName} does not exist")

    @commands.command(name="ban")
    @is_wormhole_admin()
    async def ban_user(self, ctx, userIdOrHash: str = None):
        """Ban a user from using the Wormhole bot"""
        if not await self.config.is_user_banned(userIdOrHash):
            await self.config.ban_user(userIdOrHash)
            await ctx.send(f"Banned user `{userIdOrHash}`")
        else:
            await ctx.send(f"User `{userIdOrHash}` is already banned")

    @commands.command(name="unban")
    @is_wormhole_admin()
    async def unban_user(self, ctx, userIdOrHash: str = None):
        """Unban a user from using the Wormhole bot"""
        if await self.config.is_user_banned(userIdOrHash):
            await self.config.unban_user(userIdOrHash)
            await ctx.send(f"Unbanned user `{userIdOrHash}`")
        else:
            await ctx.send(f"User `{userIdOrHash}` is not banned")

    @commands.command(name="admin")
    @is_wormhole_admin()
    async def make_admin(self, ctx, userIdOrHash: str = None):
        """Grant admin privileges to a user"""
        if await self.config.get_user_role(userIdOrHash) != "admin":
            await self.config.change_user_role(userIdOrHash, "admin")
            await ctx.send(f"{userIdOrHash} is now a Wormhole Admin")
        else:
            await ctx.send(f"{userIdOrHash} is already a Wormhole Admin")

    @commands.command(name="unadmin")
    @is_wormhole_admin()
    async def remove_admin(self, ctx, userIdOrHash: str = None):
        """Revoke admin privileges from a user"""
        if await self.config.get_user_role(userIdOrHash) == "admin":
            await self.config.change_user_role(userIdOrHash, "user")
            await ctx.send(f"{userIdOrHash} is no longer a Wormhole Admin")
        else:
            await ctx.send(f"{userIdOrHash} is already a Wormhole User")

    @commands.command(name="broadcast_embed")
    @is_wormhole_admin()
    async def broadcast_embed(self, ctx, channelName: str, *, message: str):
        """Broadcast a message with an embed to all channels in a category"""
        if not await self.config.category_exists(channelName):
            await ctx.send(f"Channel {channelName} does not exist")
            return
        
        embed = discord.Embed(
            title="Broadcast",
            description=message,
            color=discord.Color.red()
        )

        async def send_to_channel(channel):
            channel = self.bot.get_channel(int(channel["channel_id"]))
            if channel:
                await channel.send(embed=embed)

        tasks = [send_to_channel(channel) for channel in await self.config.get_channels_by_category(channelName)]
        await asyncio.gather(*tasks)

    @commands.command(name="broadcast")
    @is_wormhole_admin()
    async def broadcast_raw(self, ctx, channelName: str, *, message: str):
        """Broadcast a raw message to all channels in a category"""
        if not await self.config.category_exists(channelName):
            await ctx.send(f"Channel {channelName} does not exist")
            return

        async def send_to_channel(channel):
            channel = self.bot.get_channel(int(channel["channel_id"]))
            if channel:
                await channel.send(message)
        
        tasks = [send_to_channel(channel) for channel in await self.config.get_channels_by_category(channelName)]
        await asyncio.gather(*tasks)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))