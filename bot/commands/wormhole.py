from discord.ext import commands
from bot.config import WormholeConfig, ChannelConfig
from bot.commands.admin import is_wormhole_admin

class WormholeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config: WormholeConfig = bot.config

    @commands.command()
    @is_wormhole_admin()
    async def list_channels(self, ctx):
        """List all available Wormhole channels"""
        channels = "\n- ".join(self.config.channel_list)
        await ctx.send(f"Available Wormhole channels: {channels}")

    @commands.command()
    @is_wormhole_admin()
    async def join(self, ctx, channel_name: str):
        """Join a Wormhole channel"""
        if channel_name in self.config.channel_list:
            if str(ctx.channel.id) not in self.config.channels[channel_name]:
                self.config.channels[channel_name][str(ctx.channel.id)] = ChannelConfig()
                await ctx.send(f"Joined Wormhole channel: {channel_name}")
            else:
                await ctx.send(f"This channel is already connected to {channel_name}")
        else:
            await ctx.send(f"Channel {channel_name} does not exist")

    @commands.command()
    @is_wormhole_admin()
    async def leave(self, ctx):
        """Leave the current Wormhole channel"""
        channel_list = self.config.channel_list
        for channel_name, channels in self.config.channels.items():
            if str(ctx.channel.id) in channels and channel_name in channel_list:
                del self.config.channels[channel_name][str(ctx.channel.id)]
                await ctx.send(f"Left Wormhole channel: {channel_name}")
                return
            elif channel_name not in channel_list:
                await ctx.send(f"{channel_name} is a valid channel to leave.\nPlease say `%channel_list` to see the list of valid channels.")
        await ctx.send("This channel is not connected to any Wormhole channel")

async def setup(bot):
    await bot.add_cog(WormholeCommands(bot))