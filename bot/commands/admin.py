from discord.ext import commands
from bot.config import ChannelConfig, WormholeConfig

def is_wormhole_admin():
    async def predicate(ctx):
        try:
            if not ctx.guild:
                return False
            
            config = ctx.bot.config
            user_id = str(ctx.author.id)
            
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

    @commands.command()
    @is_wormhole_admin()
    async def add_channel(self, ctx, channel_name: str):
        """Add a new channel to the Wormhole network"""
        if channel_name not in self.config.channel_list:
            self.config.channel_list.append(channel_name)
            self.config.channels[channel_name] = {str(ctx.channel.id): ChannelConfig()}
            await ctx.send(f"Added channel {channel_name}")
        else:
            await ctx.send(f"Channel {channel_name} already exists")

    @commands.command()
    @is_wormhole_admin()
    async def remove_channel(self, ctx, channel_name: str):
        """Remove a channel from the Wormhole network"""
        if channel_name in self.config.channel_list:
            self.config.channel_list.remove(channel_name)
            del self.config.channels[channel_name]
            await ctx.send(f"Removed channel {channel_name}")
        else:
            await ctx.send(f"Channel {channel_name} does not exist")

    @commands.command()
    @is_wormhole_admin()
    async def ban_user(self, ctx, user_id: int):
        """Ban a user from using the Wormhole bot"""
        user_uuid = self.config.get_user_uuid(ctx.message.author.id)
        if user_id not in self.config.banned_users:
            self.config.banned_users.append(user_uuid)
            await ctx.send(f"Banned user {user_uuid}")
        else:
            await ctx.send(f"User {user_uuid} is already banned")

    @commands.command()
    @is_wormhole_admin()
    async def unban_user(self, ctx, user_id: int):
        """Unban a user from using the Wormhole bot"""
        user_uuid = self.config.get_user_uuid(ctx.message.author.id)
        if user_id in self.config.banned_users:
            self.config.banned_users.remove(user_uuid)
            await ctx.send(f"Unbanned user {user_uuid}")
        else:
            await ctx.send(f"User {user_uuid} is not banned")

    @commands.command()
    @is_wormhole_admin()
    async def admin(self, ctx, user_id: int):
        """Add a new admin to the wormhole bot"""
        user_uuid = self.config.get_user_uuid(user_id)
        if self.config.get_user_role(user_id)!="admin":
            self.config.change_user_role(user_id, "admin")
            await ctx.send(f"{user_uuid} is now a Wormhole Admin")
        else:
            await ctx.send(f"{user_uuid} is already a Wormhole Admin")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))