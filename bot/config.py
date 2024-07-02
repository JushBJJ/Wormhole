import hashlib
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from functools import wraps

import dotenv
import json
import os

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

class UserConfig(BaseModel):
    hash: str = ""
    role: str = "user"
    names: List[str] = []
    profile_picture: str = ""

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
    discord_token: str = os.getenv("token")
    global_salt: str = os.getenv("global_salt") or "else your cluster is compromised"

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

def load_config(config_path: str) -> WormholeConfig:
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    return WormholeConfig(**config_data)

def save_config(config_path: str, config: WormholeConfig):
    with open(config_path, 'w') as f:
        json.dump(config.dict(), f, indent=4)

def compute_user_hash(config: WormholeConfig, user_id: int) -> str:
    return hashlib.sha256(f"{config.global_salt}{user_id}".encode()).hexdigest()

dummy_user_config = UserConfig(
    hash="User hash not found"
)