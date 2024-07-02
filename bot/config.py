from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import UUID
from functools import wraps

import dotenv
import uuid
import json
import os

dotenv.load_dotenv()

def auto_configure_user(func):
    @wraps(func)
    def wrapper(self, user_id: int, *args, **kwargs):
        user_id_str = str(user_id)
        if user_id_str not in self.users:
            self.users[user_id_str] = UserConfig()
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
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"

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
        
        for channel_name in self.channel_list:
            channel = self.channels[channel_name].get(channel_id, None)
            if channel:
                return channel
        return ChannelConfig()
    
    def get_all_channel_ids(self) -> list:
        channels = []
        
        for channel_name in self.channel_list:
            channels.extend(list(self.channels[channel_name].keys()))
        return channels

    def get_all_channels_by_name(self, name: str) -> list:
        return list(self.channels[name].keys())
    
    def get_all_channels_by_id(self, channel_id: int) -> list:
        channels = []
        channel_id = str(channel_id)
        
        for channel_name in self.channel_list:
            channel_ids = self.channels[channel_name].keys()
            if channel_id in channel_ids:
                channels = channel_ids
                break
        return channels
    
    @auto_configure_user
    def get_user_color(self, user_id: int) -> int:
        user_id = str(user_id)
        user_role = self.users[user_id].role
        return int(self.roles[user_role].color[1:], 16)
    
    @auto_configure_user
    def get_user_uuid(self, user_id: int) -> str:
        user_id = str(user_id)
        return self.users[user_id].uuid

    @auto_configure_user
    def get_user_role(self, user_id: int) -> str:
        user_id = str(user_id)
        return self.users[user_id].role
    
    @auto_configure_user
    def change_user_role(self, user_id: int, role: str) -> None:
        user_id = str(user_id)
        self.users[user_id].role = role

def load_config(config_path: str) -> WormholeConfig:
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    return WormholeConfig(**config_data)

def save_config(config_path: str, config: WormholeConfig):
    with open(config_path, 'w') as f:
        json.dump(config.dict(), f, indent=4)