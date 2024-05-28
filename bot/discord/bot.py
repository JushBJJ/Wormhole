import time
import discord
import asyncio
import redis.asyncio as aioredis
import json
import os
import re

from discord.ext import commands
from dotenv import load_dotenv

from bot.utils.file import read_config, write_config
from bot.utils.logging import configure_logging

load_dotenv()

ADMIN_ID = 0
WEBSITE_URL = "https://wormhole.jushbjj.com"
REPO = "https://github.com/JushBJJ/Wormhole"

intents = discord.Intents.all()

class WormholeBot(commands.Bot):
    def __init__(self, command_prefix, intents, debug=False):
        super().__init__(command_prefix, intents=intents)
        self.client_id = (
            os.getenv("client_id", "") if not debug else os.getenv("DEV_client_id", "")
        )
        self.client_secret = (
            os.getenv("client_secret", "")
            if not debug
            else os.getenv("DEV_client_secret", "")
        )
        self.token = os.getenv("token", "") if not debug else os.getenv("DEV_token", "")
        self.remove_command("help")

        self.bot_commands = []
        self.logger = configure_logging()

        self.default_channel_config_options = {
            "react": False,
            "muted_users": [],
        }  # DEFAULT

        self.redis = aioredis.from_url("redis://localhost", decode_responses=True)
        self.last_message = [time.time(), 0]

    async def setup_hook(self):
        self.bg_task = asyncio.create_task(self.redis_subscriber())

    async def redis_subscriber(self):
        sub = self.redis.pubsub()
        await sub.subscribe("wormhole_channel")

        try:
            async for message in sub.listen():
                self.logger.info(f"Received message: {message}")
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"], strict=False)
                        msg = data.get("message", "")

                        if msg.startswith("[Tox Node]: "):
                            command = msg.removeprefix("[Tox Node]: ")

                            if command.startswith("LIST "):
                                nodes = command.removeprefix("LIST ")
                                msg = f"[Tox Node] - Connected nodes: {nodes}"
                                await self.global_msg(
                                    None, msg, discord_only=True, no_header=True
                                )

                            elif command.startswith("ADD "):
                                tox_id = command.removeprefix("ADD ")
                                msg = f"[Tox Node]: Added `{tox_id}` to the node."
                                await self.global_msg(
                                    None, msg, discord_only=True, no_header=True
                                )
                            else:
                                await self.global_msg(
                                    None, msg, discord_only=True, no_header=True
                                )
                        elif data.get("from_tox", False):
                            await self.global_msg(
                                None, msg, discord_only=True, no_header=True
                            )
                        elif data.get("embed", None)!=None:
                            embed = data.get("embed", None)
                            category = data.get("category", None)
                            await self.global_msg(None, msg, embed=embed, category=category, no_header=True, discord_only=True)
                        else:
                            await self.global_msg(None, msg, discord_only=True)

                    except json.JSONDecodeError as e:
                        self.logger.error(f"JSON decoding error: {e}")
                    except Exception as e:
                        self.logger.error(f"Error processing message: {e}")
        except Exception as e:
            self.logger.error(f"Error in redis subscriber: {e}")
        finally:
            await sub.unsubscribe("wormhole_channel")
            self.logger.info("Unsubscribed from wormhole_channel")

    def start_wormhole(self):
        self.logger.warning("Updating config...")
        config = asyncio.run(read_config())

        if not config:
            self.logger.error("Error updating config. Exiting...")
            return

        # Update Channels
        # TODO CLEAN???
        # TODO Add telegram config
        for channel in config["channel_list"]:
            if channel not in config["channels"]:
                config["channels"][channel] = {}

            for channel_id in config["channels"][channel]:
                for key, value in self.default_channel_config_options.items():
                    if key not in config["channels"][channel][channel_id]:
                        config["channels"][channel][channel_id][key] = value
                    elif key not in self.default_channel_config_options:
                        del config["channels"][channel][channel_id][key]

        asyncio.run(write_config(config))
        self.logger.warning("Starting Wormhole...")
        self.run(self.token)

    async def on_ready(self):
        await self.index_commands()
        print(f"Logged in as {self.user}")

    async def index_commands(self):
        self.bot_commands = [command for command in self.commands]

    async def filter_message(self, msg):
        banned_words = await self.get_banned_words()
        for word in banned_words:
            msg = msg.replace(word, len(word) * "#")
        return msg

    async def global_msg(
        self, message, msg, embed=None, discord_only=False, no_header=False, category=None
    ):
        config = await self.get_config()

        self.logger.info(msg)
        current_channel = 0 if message == None else message.channel.id
        author_id = "" if message == None else message.author.id

        if not no_header:
            header, msg = msg.split("\n", maxsplit=1)
            msg_discord = "```" + header + "```" + "\n" + msg
            msg_telegram = "<b>" + header + "</b>" + "\n" + msg
            msg_signal = header + "\n" + msg
        else:
            msg_discord = msg
            msg_telegram = msg
            msg_signal = msg

        links = re.findall(r"(https?://\S+)", msg)

        if current_channel != 0:
            # Gold if you're an admin
            color = 0x000000
            if await self.user_is_admin(message):
                color = 0xFFD700
            
            if embed:
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url,
                )
                embed.color = color
                #embed.set_footer(text=f"UserID: {message.author.id}")
            else:
                embed = discord.Embed(description=msg, color=color)
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url,
                )
                #embed.set_footer(text=f"UserID: {message.author.id}")

                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.url not in links:
                            links.append(attachment.url)
        elif embed!=None and type(embed)==dict:
            embed = discord.Embed.from_dict(embed)
        else:
            embed = None

        if category is None:
            category = "wormhole" if current_channel == 0 else ""

            for channel in config["channels"]:
                if str(current_channel) in config["channels"][channel].keys():
                    category = channel
                    break
        elif config["channels"].get(category, None) == None:
            print(f"Unknown channel category {category}")
            return

        for channel in config["channels"][category]:
            if channel == str(current_channel):
                continue

            channel_class = self.get_channel(int(channel))

            if channel_class == None:
                continue

            guild_id = channel_class.guild.id

            if guild_id in await self.get_banned_servers():
                continue
            elif author_id in config["channels"][category][channel]["muted_users"]:
                continue

            if embed != None:
                await channel_class.send(embed=embed)
                for link in links:
                    await channel_class.send(link)
            else:
                await channel_class.send(msg_discord)

        tox_payload = json.dumps(
            {
                "message": msg,
                "embed": embed.to_dict() if embed else None,
                "category": category
            }
        )

        if not discord_only:
            await self.redis.publish(
                "telegram_channel",
                json.dumps({"message": msg_telegram, "telegram_only": True}),
            )
            await self.redis.publish(
                "signal_channel",
                json.dumps({"message": msg_signal, "signal_only": True}),
            )
            await self.redis.publish("tox_node", tox_payload)

    async def get_config(self):
        return await read_config()

    async def get_banned_words(self):
        config = await self.get_config()
        return config.get("banned_words", [])

    async def get_banned_users(self):
        config = await self.get_config()
        return config.get("banned_users", [])

    async def get_banned_servers(self):
        config = await self.get_config()
        return config.get("banned_servers", [])

    async def get_servers(self):
        config = await self.get_config()
        return config.get("servers", [])

    async def get_admins(self):
        config = await self.get_config()
        return config.get("admins", [])

    async def get_allowed_channels(self, as_list=True):
        config = await self.get_config()
        channel_list = [] if as_list else {}

        for channel_name in config["channels"]:
            if as_list:
                channel_list.extend(
                    list(config["channels"].get(channel_name, {}).keys())
                )
            else:
                channel_list[channel_name] = config["channels"].get(channel_name, {})

        return channel_list

    async def user_is_admin(self, ctx):
        is_manually_admin = ctx.author.id in await self.get_admins()
        is_admin = ctx.author.guild_permissions.administrator
        return is_admin or is_manually_admin

    async def get_channel_category(self, channel_id):
        config = await self.get_config()
        for channel in config["channels"]:
            if str(channel_id) in config["channels"][channel].keys():
                return channel

    def is_itself(self, message):
        return message.author.id == self.user.id

bot = WormholeBot(command_prefix="%", intents=intents)
