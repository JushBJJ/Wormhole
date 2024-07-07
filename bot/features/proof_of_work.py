from typing import Tuple, Union

import discord
from discord.ext import commands
from bot.config import MessageInfo, UserConfig, WormholeConfig

import hashlib
import time

class PoWHandler:
    def __init__(self, config: WormholeConfig, ctx: commands.Bot):
        self.config = config
        self.ctx = ctx

    async def check_pow(self, message_content: str, user_id: int, channel_id: int) -> Tuple[bool, str]:
        user_config: UserConfig = self.config.get_user_config_by_id(user_id)
        
        hashed_message, solved = calculate_pow(message_content, user_config.difficulty, user_config.hash, user_config.nonce)
        user_config.nonce += 1

        if not solved and user_config.difficulty > 1:
            user_config.can_send_message = False
            error_message = (
                f"PoW check failed. "
                f"User hash: {user_config.hash}, "
                f"User nonce: {user_config.nonce}, "
                f"User difficulty: {user_config.difficulty}"
            )
            self.config.calculate_user_difficulty(user_id)
            self.config.logger.error(error_message)
            return False, "You need to solve the PoW puzzle before sending messages or using commands."

        user_config.can_send_message = True
        before_user_difficulty = int(user_config.difficulty)

        self.config.calculate_user_difficulty(user_id)
        
        notifications = []

        if before_user_difficulty != int(user_config.difficulty) and user_config.difficulty >=2:
            user = self.ctx.get_user(user_id)
            embed = discord.Embed(
                    title = "User difficulty change",
                    description= f"User difficulty has changed to `{user_config.difficulty}`\n\n"
                                "If the user's difficulty > 1, they must solve a PoW puzzle to send messages again",
                    color= discord.Color.red()
                )
            embed.set_thumbnail(url=user.display_avatar.url)
            notifications.append(embed)

        if str(channel_id) in self.config.get_all_channel_ids():
            user_config.message_history.append(
                MessageInfo(timestamp=time.time(), hash=hashed_message)
            )

        return True, notifications

    def get_pow_status(self, user_id: int) -> str:
        user_config: UserConfig = self.config.get_user_config_by_id(user_id)
        return (
            f"Current PoW status:\n"
            f"Difficulty: {user_config.difficulty}\n"
            f"Hash: {user_config.hash}\n"
            f"Nonce: {user_config.nonce}\n"
        )

def calculate_pow(message: str, difficulty: int, user_hash: str, nonce: int) -> Union[str, bool]:
    hash_input = f"{message}{nonce}{user_hash}"
    hash_output = hashlib.sha256(hash_input.encode()).hexdigest()
    if hash_output.startswith('0' * int(difficulty)):
        return hash_output, True
    return hash_output, False