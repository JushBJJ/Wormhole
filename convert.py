import json
import uuid

def generate_uuid():
    return str(uuid.uuid4())

def convert_config(input_file, output_file):
    # Read the input JSON file
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Initialize the new structure
    new_config = {
        "admins": data["admins"][:2],  # Take only the first two admins
        "servers": [],
        "channel_list": data["channel_list"],
        "channels": {},
        "banned_servers": data["banned_servers"],
        "banned_users": data["banned_users"],
        "banned_words": data["banned_words"],
        "users": {},
        "roles": {
            "admin": {
                "color": "#FF0000",
                "permissions": ["manage_channels", "manage_roles", "ban_users", "view_logs"]
            },
            "moderator": {
                "color": "#00FF00",
                "permissions": ["manage_messages", "timeout_users", "view_logs"]
            },
            "user": {
                "color": "#0000FF",
                "permissions": ["send_messages", "read_messages"]
            }
        },
        "content_filter": {
            "enabled": True,
            "sensitivity": 0.7
        }
    }

    # Convert channels
    for channel_type, channels in data["channels"].items():
        if channel_type not in new_config["channels"]:
            new_config["channels"][channel_type] = {}
        
        for channel_id, channel_data in channels.items():
            new_config["channels"][channel_type][channel_id] = {"react": channel_data["react"]}

    # Create users
    for i, admin_id in enumerate(new_config["admins"]):
        role = "admin" if i == 0 else "user"
        new_config["users"][str(admin_id)] = {
            "uuid": generate_uuid(),
            "role": role
        }

    # Write the new config to the output file
    with open(output_file, 'w') as f:
        json.dump(new_config, f, indent=4)

    print(f"Conversion complete. New config written to {output_file}")

# Usage
input_file = 'config.json'
output_file = 'new_config.json'
convert_config(input_file, output_file)