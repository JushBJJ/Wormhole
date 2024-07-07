import asyncio
import hashlib
from logging import Logger
import math
import discord
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from functools import wraps

import dotenv
import json
import os
import time

from bot.utils.logging import setup_logging

dotenv.load_dotenv()

def auto_configure_user(func):
    @wraps(func)
    def wrapper(self, user_id: int, *args, **kwargs):
        user_id_str = str(user_id)
        user_config = self.users.get(user_id_str)

        if user_config is None:
            hashed_userid = compute_user_hash(self, user_id)
            self.users[user_id_str] = UserConfig(hash=hashed_userid)
        else:
            if not user_config.hash:
                user_config.hash = compute_user_hash(self, user_id)

            default_config = UserConfig().dict()
            for field, value in default_config.items():
                if field not in user_config.__dict__:
                    setattr(user_config, field, value)
        return func(self, user_id, *args, **kwargs)
    return wrapper

class ChannelConfig(BaseModel):
    react: bool = False
    
    async def handle_config_pre(self, message, bot):
        if self.react:
            await message.add_reaction('⏳')
    
    async def handle_config_post(self, message, bot):
        if self.react:
            await message.remove_reaction('⏳', bot.user)
            await message.add_reaction('✅')

class MessageInfo(BaseModel):
    timestamp: float
    hash: str

class tempMessageInfo(BaseModel):
    role: str
    content: str

class UserConfig(BaseModel):
    hash: str = ""
    role: str = "user"
    names: List[str] = []
    profile_picture: str = ""
    message_history: List[MessageInfo] = Field(default_factory=list)
    temp_command_message_history: List[tempMessageInfo] = Field(default_factory=list)
    difficulty: float = 0
    difficulty_penalty: float = 0
    can_send_message: bool = True
    nonce: int = 0

class RoleConfig(BaseModel):
    color: str
    permissions: List[str]

class ContentFilterConfig(BaseModel):
    enabled: bool = True
    sensitivity: float = 0.7

class WormholeConfig(BaseModel):
    admins: List[int] = Field(default_factory=list)
    servers: List[int] = Field(default_factory=list)
    channel_list: List[str] = Field(default_factory=list)
    channels: Dict[str, Dict[str, ChannelConfig]] = Field(default_factory=dict)
    banned_servers: List[int] = Field(default_factory=list)
    banned_users: List[str] = Field(default_factory=list)
    banned_words: List[str] = Field(default_factory=list)
    users: Dict[str, UserConfig] = Field(default_factory=dict)
    roles: Dict[str, RoleConfig] = Field(default_factory=dict)
    content_filter: ContentFilterConfig = ContentFilterConfig()
    max_difficulty: int = 10
    
    discord_token: str = Field(default_factory=lambda: os.getenv("token"))
    global_salt: str = Field(default_factory=lambda: os.getenv("global_salt") or "else your cluster is compromised")

    class Config:
        extra = "allow"

    def update_config(self, new_config: Dict):
        for key, value in new_config.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.__dict__[key] = value
    
    def get_channel_by_id(self, channel_id: int) -> ChannelConfig:
        channel_id = str(channel_id)
        for channels in self.channels.values():
            if channel := channels.get(channel_id):
                return channel
        return ChannelConfig()

    def get_channel_name_by_id(self, channel_id: int) -> str:
        for name, channels in self.channels.items():
            if str(channel_id) in channels:
                return name
        return ""

    def get_all_channel_ids(self) -> list:
        return [id for channels in self.channels.values() for id in channels]

    def get_all_channels_by_name(self, name: str) -> list:
        return list(self.channels.get(name, {}).keys())

    def get_all_channels_by_id(self, channel_id: int) -> list:
        channel_id = str(channel_id)
        for _, channels in self.channels.items():
            if channel_id in channels:
                return list(channels.keys())
        return []

    @auto_configure_user
    def get_user_color(self, user_id: int) -> int:
        user = self.users[str(user_id)]
        return int(self.roles[user.role].color[1:], 16)

    def get_role_color(self, role: str) -> int:
        return int(self.roles[role].color[1:], 16)

    @auto_configure_user
    def get_user_hash(self, user_id: int) -> str:
        if not isinstance(user_id, int):
            return self.get_user_config_by_hash(user_id).hash
        return self.users[str(user_id)].hash

    def get_user_config_by_hash(self, user_hash: str) -> UserConfig:
        return next((user for user in self.users.values() if user.hash == user_hash), dummy_user_config)

    def get_user_config_by_id(self, user_id: int) -> UserConfig:
        return self.users.get(str(user_id), dummy_user_config)

    def get_user_id_by_hash(self, user_hash: str) -> Optional[int]:
        return next((int(user_id) for user_id, user in self.users.items() if user.hash == user_hash), 0)

    @auto_configure_user
    def get_user_role(self, user_id: int) -> str:
        return self.users[str(user_id)].role

    @auto_configure_user
    def change_user_role(self, user_hash: str, role: str) -> None:
        user_config = self.get_user_config_by_hash(user_hash)
        user_config.role = role
        user_id = str(self.get_user_id_by_hash(user_hash))
        self.users[user_id] = user_config

    @auto_configure_user
    def add_username(self, user_id: int, name: str) -> None:
        if name not in self.users[str(user_id)].names:
            self.users[str(user_id)].names.append(name)

    @auto_configure_user
    def reset_user_difficulty(self, user_id: Union[str, int]) -> None:
        try:
            user_config = self.get_user_config_by_id(user_id)
        except ValueError:
            user_config = self.get_user_id_by_hash(user_id)
        user_config.message_history = []
        user_config.difficulty = 0
    
    def update_user_message_history(self, user_id: int, message_content: str):
        user_config = self.users.get(str(user_id))
        if user_config:
            hashed_content = hashlib.sha256((self.global_salt+str(user_id)+message_content).encode()).hexdigest()
            user_config.message_history.append(MessageInfo(timestamp=time.time(), hash=hashed_content))
            if len(user_config.message_history) > 100: # Temporary
                user_config.message_history.pop(0)

    def calculate_user_difficulty(self, user_id: int) -> float:
        short_term_window = 5 * 60              # 5 minutes
        medium_term_window = 24 * 60 * 60       # 24 hours
        long_term_window = 30 * 24 * 60 * 60    # 30 days
        
        short_term_threshold = 10
        medium_term_threshold = 50
        long_term_threshold = 500
        
        base_difficulty = 1.0
        
        user_id = str(user_id)
        
        user_config = self.users.get(user_id)
        if not user_config:
            self.logger.warning(f"User {user_id} not found")
            return

        current_time = time.time()
        # Count messages in each time window
        short_term_count = self._count_messages(user_id, current_time, short_term_window)
        medium_term_count = self._count_messages(user_id, current_time, medium_term_window)
        long_term_count = self._count_messages(user_id, current_time, long_term_window)

        # Calculate difficulty factors
        short_term_factor = math.pow(short_term_count / short_term_threshold, 2)
        medium_term_factor = math.sqrt(medium_term_count / medium_term_threshold)
        long_term_factor = math.log(long_term_count / long_term_threshold + 1) / math.log(2)

        # Calculate weighted difficulty
        difficulty = base_difficulty * (
            0.6 * short_term_factor +
            0.1 * medium_term_factor +
            0.05 * long_term_factor
        )

        # Apply bonus for consistent long-term usage
        if long_term_count > long_term_threshold and medium_term_count < medium_term_threshold:
            long_term_bonus = 0.9
            difficulty *= long_term_bonus

        penalty = user_config.difficulty_penalty
        self.users[user_id].difficulty = difficulty + penalty
        self.logger.info(f"\nUser {user_id} difficulty: {difficulty:.2f}")
        self.logger.info(f"Short term: {short_term_count} messages in {short_term_window/60:.0f} minutes")
        self.logger.info(f"Medium term: {medium_term_count} messages in {medium_term_window/3600:.0f} hours")
        self.logger.info(f"Long term: {long_term_count} messages in {long_term_window/(24*3600):.0f} days")
        self.logger.info(f"Short term factor: {short_term_factor:.2f}")
        self.logger.info(f"Medium term factor: {medium_term_factor:.2f}")
        self.logger.info(f"Long term factor: {long_term_factor:.2f}")

    def _count_messages(self, user_id: str, current_time: float, time_window: float) -> int:
        return sum(1 for msg in self.users[user_id].message_history if current_time - msg.timestamp <= time_window)

    async def broadcast(self, bot, channel_name: str, embed: Optional[discord.Embed] = None) -> list:
        channels = self.get_all_channels_by_name(channel_name)
        
        async def send_message(channel_id):
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed)
        
        tasks = [send_message(int(channel_id)) for channel_id in channels]
        await asyncio.gather(*tasks)

def load_config(config_path: str) -> WormholeConfig:
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    return WormholeConfig(**config_data)

def save_config(config_path: str, config: WormholeConfig):
    with open(config_path, 'w') as f:
        config_dict = config.dict(exclude={"logger", "discord_token", "global_salt"})
        json.dump(config_dict, f, indent=4)

def compute_user_hash(config: WormholeConfig, user_id: int) -> str:
    return hashlib.sha256(f"{config.global_salt}{user_id}".encode()).hexdigest()

dummy_user_config = UserConfig(
    hash="User hash not found"
)