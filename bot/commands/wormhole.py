from typing import Optional, Union
from discord import NotFound
from discord.ext import commands
from bot.config import WormholeConfig, ChannelConfig
from bot.commands.admin import is_wormhole_admin

class WormholeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config: WormholeConfig = bot.config

    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def list_channels(self, ctx, **kwargs):
        """List all available Wormhole channels"""
        channels = "\n- ".join(self.config.channel_list)
        await ctx.send(f"Available Wormhole channels: {channels}")

    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def join(self, ctx, channel_name: str, **kwargs):
        """Join a Wormhole channel"""
        if self.config.get_channel_name_by_id(ctx.channel.id)=="":
            if channel_name in self.config.channel_list:
                if str(ctx.channel.id) not in self.config.channels[channel_name]:
                    self.config.channels[channel_name][str(ctx.channel.id)] = ChannelConfig()
                    await ctx.send(f"Joined Wormhole channel: {channel_name}")
                else:
                    await ctx.send(f"This channel is already connected to {channel_name}")
            else:
                await ctx.send(f"Channel {channel_name} does not exist")
        else:
            await ctx.send(
                f"This channel is already connected to {self.config.get_channel_name_by_id(ctx.channel.id)}"
                f"\nPlease say `%leave` to leave the current channel"
            )

    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def leave(self, ctx, **kwargs):
        """Leave the current Wormhole channel"""
        channel_list = self.config.channel_list
        for channel_name, channels in self.config.channels.items():
            if str(ctx.channel.id) in channels and channel_name in channel_list:
                del self.config.channels[channel_name][str(ctx.channel.id)]
                await ctx.send(f"Left Wormhole channel: {channel_name}")
                return
            elif channel_name not in channel_list:
                await ctx.send(f"{channel_name} is not a valid channel to leave.\nPlease say `%channel_list` to see the list of valid channels.")
        await ctx.send("This channel is not connected to any Wormhole channel")
    
    @commands.command(case_insensitive=True)
    @is_wormhole_admin()
    async def reset_user_difficulty(self, ctx, user_id_or_hash: Optional[Union[int, str]] = None, **kwargs):
        """Reset the user's difficulty"""
        if user_id_or_hash is None:
            user_id_or_hash = ctx.author.id
        self.config.reset_user_difficulty(user_id_or_hash)
        await ctx.send("User difficulty reset")
    
    @commands.command(case_insensitive=True)
    async def pow_status(self, ctx, user_id_or_hash: Optional[Union[int, str]] = None, **kwargs):
        """Get the current PoW status for the user"""
        if user_id_or_hash is None:
            user_id_or_hash = ctx.author.id
        
        try:
            user_id_or_hash = int(user_id_or_hash)
        except ValueError:
            user_id_or_hash = self.config.get_user_id_by_hash(user_id_or_hash)
        status = self.bot.pow_handler.get_pow_status(user_id_or_hash)
        await ctx.send(status)

async def setup(bot):
    await bot.add_cog(WormholeCommands(bot))