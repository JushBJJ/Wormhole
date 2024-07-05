import discord

bot_avatar_url = "https://images-ext-1.discordapp.net/external/2dZVVL6feMSM7lxfFkKVW__LToSOzmToSEmocJV5vcA/https/cdn.discordapp.com/embed/avatars/0.png?format=webp&quality=lossless&width=320&height=320"

def create_embed(title="Wormhole Bot", 
                 description="Inter-server Communication.", 
                 footer="",
                 color=discord.Color.red(),
                 avatar_url=bot_avatar_url):
    return discord.Embed(
        title=title,
        description=description,
        color=color
    ).set_thumbnail(url=avatar_url).set_footer(text=footer)