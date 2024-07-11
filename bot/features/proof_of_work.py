from typing import Tuple, Union

import discord
from discord.ext import commands
from bot.config import WormholeConfig

import hashlib
import time

class PoWHandler:
    def __init__(self, config: WormholeConfig, ctx: commands.Bot):
        self.config = config
        self.ctx = ctx

    async def check_pow(self, message: discord.Message, message_content: str, user_id: int, channel_id: int) -> Tuple[bool, str]:
        user_id = str(user_id)
        channel_id = str(channel_id)
        user = await self.config.get_user(user_id)
        hashed_message, solved = calculate_pow(message_content, user['difficulty'], user['hash'], user['nonce'])
        user["nonce"] += 1
        await self.config.update_user_config(user_id, kwargs=user)

        if not solved and user['difficulty'] > 1:
            user["can_send_message"] = False
            error_message = (
                f"PoW check failed. "
                f"User hash: {user['hash']}, "
                f"User nonce: {user['nonce']}, "
                f"User difficulty: {user['difficulty']}"
            )
            await self.config.update_user_config(user_id, kwargs=user)
            await self.config.calculate_user_difficulty(user_id, message.author.joined_at)
            self.config.logger.error(error_message)
            return False, "You need to solve the PoW puzzle before sending messages or using commands."

        user["can_send_message"] = True
        before_user_difficulty = int(user['difficulty'])

        await self.config.update_user_config(user_id, kwargs=user)
        await self.config.calculate_user_difficulty(user_id, message.author.joined_at)
        
        notifications = []
        if before_user_difficulty != int(user['difficulty']) and user['difficulty'] >= 2:
            embed = discord.Embed(
                    title = "User difficulty change",
                    description= f"User difficulty has changed to `{user['difficulty']}`\n\n"
                                "If the user's difficulty > 1, they must solve a PoW puzzle to send messages again",
                    color= discord.Color.red()
                )
            embed.set_thumbnail(url=user['avatar'])
            notifications.append(embed)

        jump_link = message.jump_url
        await self.config.update_user_message_history(user_id, jump_link, hashed_message)
        return True, notifications, hashed_message

    async def get_pow_status(self, user_id: int) -> str:
        user = await self.config.get_user(user_id)
        return (
            f"Current PoW status:\n"
            f"Difficulty: {user['difficulty']}\n"
            f"Hash: {user['hash']}\n"
            f"Nonce: {user['nonce']}\n"
        )

def calculate_pow(message: str, difficulty: int, user_hash: str, nonce: int) -> Union[str, bool]:
    hash_input = f"{message}{nonce}{user_hash}"
    hash_output = hashlib.sha256(hash_input.encode()).hexdigest()
    if hash_output.startswith('0' * int(difficulty)):
        return hash_output, True
    return hash_output, False