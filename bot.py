import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
ADMIN_ID = 0
WEBSITE_URL = "<TBD>"

# Bot initialization
intents = discord.Intents.all()

class WormholeBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix, intents=intents)
        self.client_id = os.getenv("client_id", "")
        self.client_secret = os.getenv("client_secret", "")
        self.token = os.getenv("token", "")
        self.remove_command("help")

    def start_wormhole(self):
        self.run(self.token)

    async def on_ready(self):
        print("Wormhole Loaded.")

    async def global_msg(self, message, others_only=False):
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.topic == "[wormhole] CHANNEL:1":
                    if channel != message.channel or not others_only:
                        await channel.send(self.filter_message(message.content))

    def filter_message(self, text):
        # TODO LLM filtering
        return text

    async def setup_hook(self):
        pass

bot = WormholeBot(command_prefix='%', intents=intents)

@bot.event
async def on_guild_join(guild):
    channel = next((c for c in guild.text_channels if guild.me.permissions_in(c).send_messages), None)
    if channel:
        await channel.send("Thanks for inviting me! To chat with other servers, say `%setup` in the channel you want to set me up in! For a full list of commands, say `%help`")

@bot.event
async def on_message(message):
    if message.author.bot and message.author.id != 735946634160111776 or str(message.author.id) == BANNED_USER or str(message.guild.id) == BANNED_SERVER:
        return
    
    print("Message: ", message.content)
    await bot.process_commands(message)

    if message.channel.topic == "[wormhole] CHANNEL:1" or message.channel.id == 110373943822540800:
        await bot.global_msg(message, others_only=True)
        await message.add_reaction("✅")

@bot.command(name="help")
async def help_command(ctx):
    await ctx.send(f"The Wormhole Bot allows you to communicate with other servers.\n"
                   f"Change a channel's description to [wormhole] in order to use the chat.\n"
                   f"**Commands**\n"
                   f"%help : Display this help message\n"
                   f"%global : Connect to the public server\n"
                   f"%info : Display various info about the bot\n"
                   f"%dc : Disconnect from public server\n"
                   f"%invite : Invite this bot to your server\n"
                   f"%website : Go to this bot's website\n"
                   f"%setup : Set up the bot in the current channel (server admin only)\n"
                   f"%privacy : View the privacy policy")

# TODO: Add more commands

if __name__ == "__main__":
    bot.start_wormhole()
