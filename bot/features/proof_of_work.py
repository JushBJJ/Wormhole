from typing import Tuple, Union

import discord
from discord.ext import commands
from bot.config import MessageInfo, UserConfig, WormholeConfig
from bot.features.wormhole_economy import WormholeEconomy

import hashlib
import time

class PoWHandler:
    def __init__(self, config: WormholeConfig, wormhole_economy: WormholeEconomy, ctx: commands.Bot):
        self.config = config
        self.wormhole_economy = wormhole_economy
        self.ctx = ctx

    async def check_pow(self, message_content: str, user_id: int, channel_id: int) -> Tuple[bool, str]:
        user_config: UserConfig = self.config.get_user_config_by_id(user_id)
        
        hashed_message, solved = calculate_pow(message_content, user_config.difficulty, user_config.hash, user_config.nonce)
        user_config.nonce += 1

        if not solved:
            user_config.can_send_message = False
            error_message = (
                f"PoW check failed. "
                f"User hash: {user_config.hash}, "
                f"User nonce: {user_config.nonce}, "
                f"User difficulty: {user_config.difficulty}"
            )
            self.config.calculate_user_difficulty(user_id)
            print(error_message)
            return False, "You need to solve the PoW puzzle before sending messages or using commands."

        user_config.can_send_message = True

        before_global_difficulty = int(self.config.economy.global_difficulty)
        before_user_difficulty = int(user_config.difficulty)

        self.config.calculate_user_difficulty(user_id)
        self.config.update_global_difficulty()
        
        notifications = []
        
        if before_global_difficulty != int(self.config.economy.global_difficulty):
            embed = discord.Embed(
                    title= "Global difficulty change",
                    description= f"Global difficulty has changed to `{self.config.economy.global_difficulty}`",
                    color= "red"
                )
            embed.set_thumbnail(url=self.display_avatar.url)
            notifications.append(embed)

        if before_user_difficulty != int(user_config.difficulty):
            user = self.ctx.get_user(user_id)
            embed = discord.Embed(
                    title = "User difficulty change",
                    description= f"User difficulty has changed to `{user_config.difficulty}`\n\n"
                                "If the user's difficulty > 1, they must solve a PoW puzzle to send messages again",
                    color= "red"
                )
            embed.set_thumbnail(url=user.display_avatar.url)
            notifications.append(embed)

        if str(channel_id) in self.config.get_all_channel_ids():
            user_config.message_history.append(
                MessageInfo(timestamp=time.time(), hash=hashed_message)
            )
            self.wormhole_economy.mint_coins(user_id, user_config.difficulty)

        global_cost = self.config.economy.global_difficulty * self.config.economy.base_reward
        self.config.economy.global_cost = global_cost

        if not self.wormhole_economy.deduct_coins(user_id, global_cost):
            user_config.can_send_message = False
            error_message = (
                f"Not enough coins to send message. "
                f"User coins: {user_config.wormhole_coins}, "
                f"Global cost: {global_cost}, "
                f"Global difficulty: {self.config.economy.global_difficulty}"
            )
            print(error_message)
            return False, "You don't have enough coins to send a message or use commands."

        return True, notifications

    def get_pow_status(self, user_id: int) -> str:
        user_config: UserConfig = self.config.get_user_config_by_id(user_id)
        return (
            f"Current PoW status:\n"
            f"Difficulty: {user_config.difficulty}\n"
            f"Hash: {user_config.hash}\n"
            f"Nonce: {user_config.nonce}\n"
            f"Coins: {user_config.wormhole_coins}"
        )

def calculate_pow(message: str, difficulty: int, user_hash: str, nonce: int) -> Union[str, bool]:
    hash_input = f"{message}{nonce}{user_hash}"
    hash_output = hashlib.sha256(hash_input.encode()).hexdigest()
    if hash_output.startswith('0' * int(difficulty)):
        return hash_output, True
    return hash_output, False