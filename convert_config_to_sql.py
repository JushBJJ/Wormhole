import asyncpg
import os
import json

import dotenv
dotenv.load_dotenv(dotenv_path=".env_dev")

async def convert(json_txt, config):
    config_json = json_txt

    # Create users first
    for _id, user_config in config_json["users"].items():
        new_user_config = {k: str(v) for k, v in user_config.items()}
        new_user_config["user_id"] = str(_id)
        await config._old_add_user(new_user_config)

    # Create channels
    for category, channels in config_json["channels"].items():
        for channel, channel_config in channels.items():
            channel_id = str(channel)
            server_id = str(0)
            channel_category = str(category)
            react = str(channel_config["react"])
            await config._old_add_channel(channel_id, server_id, channel_category, react)

    # Create roles
    for role, role_config in config_json["roles"].items():
        role_name = str(role)
        role_color = str(role_config["color"])
        await config._old_add_role(role_name, role_color)

    # Add admins
    for admin_id in config_json["admins"]:
        await config._old_add_admin(str(admin_id))

    # Add servers
    for server_id in config_json["servers"]:
        await config._old_add_server(str(server_id), "Unknown")  # Server name not provided in JSON

    # Add channel list
    for channel_name in config_json["channel_list"]:
        await config._old_add_channel_list(str(channel_name))

    # Add banned servers
    for server_id in config_json["banned_servers"]:
        await config._old_add_banned_server(str(server_id))

    # Add banned users
    for user_id in config_json["banned_users"]:
        await config._old_add_banned_user(str(user_id))