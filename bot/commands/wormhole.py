from typing import Optional
from discord.ext import commands
from bot.config import WormholeConfig
from bot.commands.admin import is_wormhole_admin
from services.discord import DiscordBot

class WormholeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot: DiscordBot = bot
        self.config: WormholeConfig = bot.config

    @commands.group(case_insensitive=True, invoke_without_command=True)
    @is_wormhole_admin()
    async def wormhole(self, ctx):
        """Wormhole channel management commands"""
        await ctx.send("Invalid wormhole command. Use `help wormhole` for more information.")

    @wormhole.command(name="list")
    async def list_channels(self, ctx):
        """List all available Wormhole channels"""
        channels = await self.config.get_all_channels()
        channel_names = "\n- ".join([channel['channel_name'] for channel in channels])
        await ctx.send(f"Available Wormhole channels:\n- {channel_names}")

    @wormhole.command(name="join")
    async def join(self, ctx, channel_name: str):
        """Join a Wormhole channel"""
        channel_id = str(ctx.channel.id)
        current_channel = await self.config.get_channel_name_by_id(channel_id)
        if not current_channel:
            channel_exists = await self.config.category_exists(channel_name)
            if channel_exists:
                channel_joined = await self.config.get_channel_category_by_id(channel_id)
                if not channel_joined:
                    await self.config.join_channel(channel_name, channel_id, str(ctx.guild.id))
                    await ctx.send(f"Joined Wormhole channel: {channel_name}")
                else:
                    await ctx.send(f"This channel is already connected to {channel_name}")
            else:
                await ctx.send(f"Channel {channel_name} does not exist")
        else:
            await ctx.send(
                f"This channel is already connected to {current_channel}"
                f"\nPlease use `%wormhole leave` to leave the current channel"
            )

    @wormhole.command(name="leave")
    async def leave(self, ctx):
        """Leave the current Wormhole channel"""
        channel_id = str(ctx.channel.id)
        current_channel = await self.config.get_channel_category_by_id(channel_id)
        if current_channel:
            await self.config.leave_channel(channel_id)
            await ctx.send(f"Left Wormhole channel: {current_channel}")
        else:
            await ctx.send("This channel is not connected to any Wormhole channel")

async def setup(bot):
    await bot.add_cog(WormholeCommands(bot))